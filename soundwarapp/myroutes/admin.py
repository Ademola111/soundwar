"""
Admin Routes
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import date, datetime, time, timedelta
from functools import wraps
from soundwarapp import csrf, db
from soundwarapp.models import User, Artist, Song, Vote, Contest, ContestEntry, ContestWinner, Payment
from soundwarapp.utils.reparticipation import process_reparticipation_notifications, start_reparticipation_scheduler

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or 'admin' not in (user.roles or []):
            return jsonify({'error': 'Admin access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
def get_dashboard():
    """Get platform totals and active-season dashboard statistics."""
    contest = Contest.get_current()
    if contest:
        season_songs = Song.query.filter_by(contest_id=contest.id)
        season_artist_ids = {
            artist_id for (artist_id,) in db.session.query(ContestEntry.artist_id).filter_by(
                contest_id=contest.id
            ).all()
        }
        season_artist_ids.update(
            artist_id for (artist_id,) in db.session.query(Song.artist_id).filter_by(
                contest_id=contest.id
            ).distinct().all()
        )
        season_votes = Vote.query.filter_by(contest_id=contest.id)
        season_payments = Payment.query.filter_by(contest_id=contest.id, status='successful')
        total_revenue = db.session.query(
            db.func.coalesce(db.func.sum(Payment.amount), 0)
        ).filter_by(contest_id=contest.id, status='successful').scalar()
    else:
        season_songs = Song.query.filter(db.false())
        season_artist_ids = set()
        season_votes = Vote.query.filter(db.false())
        season_payments = Payment.query.filter(db.false())
        total_revenue = 0

    stats = {
        'total_users': User.query.count(),
        'total_artists': len(season_artist_ids),
        'total_songs': season_songs.count(),
        'pending_songs': season_songs.filter_by(status='pending').count(),
        'approved_songs': season_songs.filter_by(status='approved').count(),
        'total_votes': season_votes.count(),
        'total_payments': season_payments.count(),
        'total_revenue': float(total_revenue or 0),
    }

    recent_activity = []
    if contest:
        season_end = contest.voting_end_date
        for user in User.query.filter(
            User.created_at >= contest.start_date,
            User.created_at <= season_end,
        ).order_by(User.created_at.desc()).limit(5).all():
            recent_activity.append({
                'timestamp': user.created_at.isoformat() if user.created_at else None,
                'type': 'user',
                'title': 'New user registered this season',
                'detail': user.username,
            })
    for song in season_songs.order_by(Song.created_at.desc()).limit(5).all():
        recent_activity.append({
            'timestamp': song.created_at.isoformat() if song.created_at else None,
            'type': 'song',
            'title': 'Song submitted for approval',
            'detail': f'{song.title} by {song.artist.stage_name}',
        })
    for payment in season_payments.order_by(Payment.verified_at.desc()).limit(5).all():
        activity_time = payment.verified_at or payment.created_at
        recent_activity.append({
            'timestamp': activity_time.isoformat() if activity_time else None,
            'type': 'payment',
            'title': 'Payment received',
            'detail': f'{payment.currency} {float(payment.amount):,.2f} · {payment.user.username}',
        })
    recent_activity.sort(key=lambda activity: activity['timestamp'] or '', reverse=True)
    
    return jsonify({
        'stats': stats,
        'current_contest': contest.to_dict() if contest else None,
        'recent_activity': recent_activity[:6],
    }), 200


@admin_bp.route('/songs/pending', methods=['GET'])
@admin_required
def get_pending_songs():
    """Get pending song submissions for the active contest season."""
    contest = Contest.get_current()
    songs = Song.query.filter_by(
        contest_id=contest.id if contest else None,
        status='pending',
    ).all() if contest else []
    
    return jsonify({
        'songs': [song.to_dict() for song in songs]
    }), 200


@admin_bp.route('/songs/<int:song_id>/approve', methods=['POST'])
@csrf.exempt
@admin_required
def approve_song(song_id):
    """Approve a song submission"""
    song = Song.query.get(song_id)
    
    if not song:
        return jsonify({'error': 'Song not found'}), 404
    
    if song.status != 'pending':
        return jsonify({'error': 'Song is not pending'}), 400
    
    song.status = 'approved'
    song.approved_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'message': 'Song approved',
        'song': song.to_dict()
    }), 200


@admin_bp.route('/songs/<int:song_id>/reject', methods=['POST'])
@csrf.exempt
@admin_required
def reject_song(song_id):
    """Reject a song submission"""
    song = Song.query.get(song_id)
    
    if not song:
        return jsonify({'error': 'Song not found'}), 404
    
    if song.status != 'pending':
        return jsonify({'error': 'Song is not pending'}), 400
    
    data = request.get_json()
    
    song.status = 'rejected'
    song.rejection_reason = data.get('reason', 'Does not meet guidelines')
    db.session.commit()
    
    return jsonify({
        'message': 'Song rejected',
        'song': song.to_dict()
    }), 200


@admin_bp.route('/contests', methods=['GET'])
@admin_required
def get_contests():
    """Get all contests"""
    contests = Contest.query.order_by(Contest.created_at.desc()).all()
    
    return jsonify({
        'contests': [contest.to_dict() for contest in contests]
    }), 200


@admin_bp.route('/contests/<int:contest_id>/phase', methods=['POST'])
@csrf.exempt
@admin_required
def advance_contest_phase(contest_id):
    """Advance a contest one phase and persist the admin override."""
    contest = Contest.query.get(contest_id)
    if not contest:
        return jsonify({'error': 'Contest not found'}), 404

    next_phase = {
        'submission': 'voting',
        'voting': 'completed',
    }.get(contest.get_phase())
    if not next_phase:
        return jsonify({'error': 'This contest has already completed'}), 409

    data = request.get_json(silent=True) or {}
    requested_phase = data.get('phase') if isinstance(data, dict) else None
    if requested_phase != next_phase:
        return jsonify({'error': f'The next phase must be {next_phase}'}), 400

    contest.phase = next_phase
    contest.phase_override = True
    db.session.commit()

    return jsonify({
        'message': f'Contest advanced to {next_phase}',
        'contest': contest.to_dict(),
    }), 200


@admin_bp.route('/contests/<int:contest_id>/dates', methods=['PUT'])
@csrf.exempt
@admin_required
def update_contest_dates(contest_id):
    """Update contest milestone dates without changing its current phase."""
    contest = Contest.query.get(contest_id)
    if not contest:
        return jsonify({'error': 'Contest not found'}), 404

    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid contest date data'}), 400

    date_fields = ('start_date', 'submission_end_date', 'voting_end_date')
    if any(not data.get(field) for field in date_fields):
        return jsonify({'error': 'Start, submission close, and voting end dates are required'}), 400

    try:
        start_date = datetime.fromisoformat(data['start_date'])
        submission_end_date = datetime.fromisoformat(data['submission_end_date'])
        voting_end_date = datetime.fromisoformat(data['voting_end_date'])
    except (TypeError, ValueError):
        return jsonify({'error': 'Contest dates must be valid ISO date/time values'}), 400

    if not start_date < submission_end_date < voting_end_date:
        return jsonify({'error': 'Contest dates must be ordered: start, submission close, then voting end'}), 400

    contest.start_date = start_date
    contest.submission_end_date = submission_end_date
    contest.voting_end_date = voting_end_date
    db.session.commit()

    return jsonify({
        'message': 'Contest dates updated successfully',
        'contest': contest.to_dict(),
    }), 200


@admin_bp.route('/contests', methods=['POST'])
@csrf.exempt
@admin_required
def create_contest():
    """Create a new contest with the next sequential season title."""
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid contest data'}), 400

    required_dates = ('start_date', 'submission_end_date', 'voting_end_date')
    if any(not data.get(field) for field in required_dates):
        return jsonify({'error': 'Start, submission close, and voting end dates are required'}), 400

    try:
        start_date = datetime.fromisoformat(data['start_date'])
        submission_end_date = datetime.fromisoformat(data['submission_end_date'])
        voting_end_date = datetime.fromisoformat(data['voting_end_date'])
    except (TypeError, ValueError):
        return jsonify({'error': 'Contest dates must be valid ISO date/time values'}), 400

    if not start_date < submission_end_date < voting_end_date:
        return jsonify({'error': 'Contest dates must be ordered: start, submission close, then voting end'}), 400
    
    # Deactivate current contest
    current = Contest.get_current()
    if current:
        current.is_active = False

    next_season_number = Contest.query.count() + 1
    
    contest = Contest(
        title=f'Season {next_season_number}',
        description=data.get('description'),
        start_date=start_date,
        submission_end_date=submission_end_date,
        voting_end_date=voting_end_date,
        is_active=True
    )
    
    db.session.add(contest)
    db.session.commit()
    
    return jsonify({
        'message': 'Contest created',
        'contest': contest.to_dict()
    }), 201


@admin_bp.route('/reparticipation-notifications', methods=['POST'])
@admin_required
def trigger_reparticipation_notifications():
    """Manually trigger past winner re-participation reminder emails."""
    sent = process_reparticipation_notifications()
    return jsonify({
        'message': 'Re-participation notification sweep completed',
        'notifications_sent': sent
    }), 200


@admin_bp.route('/contests/<int:contest_id>/finalize', methods=['POST'])
@admin_required
def finalize_contest(contest_id):
    """Finalize contest and declare winner"""
    contest = Contest.query.get(contest_id)
    
    if not contest:
        return jsonify({'error': 'Contest not found'}), 404
    
    if contest.winner:
        return jsonify({'error': 'Contest already has a winner'}), 400
    
    # Get song with most votes
    winning_song = Song.query.filter_by(
        contest_id=contest.id,
        status='approved'
    ).order_by(Song.vote_count.desc()).first()
    
    if not winning_song:
        return jsonify({'error': 'No songs in contest'}), 400
    
    # Create winner record
    winner = ContestWinner(
        contest_id=contest.id,
        artist_id=winning_song.artist_id,
        song_id=winning_song.id,
        final_vote_count=winning_song.vote_count
    )
    
    contest.is_active = False
    contest.phase = 'completed'
    
    # Reset notification state so this artist can be alerted again after the next cooldown period
    winning_song.artist.reparticipation_notified_at = None

    db.session.add(winner)
    db.session.commit()
    
    return jsonify({
        'message': 'Contest finalized',
        'winner': winner.to_dict()
    }), 200


@admin_bp.route('/winners', methods=['GET'])
@admin_required
def get_all_winners():
    """Get all past winners"""
    winners = ContestWinner.query.order_by(ContestWinner.won_at.desc()).all()
    
    result = []
    for winner in winners:
        artist = Artist.query.get(winner.artist_id)
        song = Song.query.get(winner.song_id)
        contest = Contest.query.get(winner.contest_id)
        
        result.append({
            'winner': winner.to_dict(),
            'artist': artist.to_dict() if artist else None,
            'song': song.to_dict() if song else None,
            'contest': contest.to_dict() if contest else None
        })
    
    return jsonify({'winners': result}), 200


@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users():
    """Get all users with activity counts for the active contest season."""
    contest = Contest.get_current()
    users = User.query.order_by(User.created_at.desc()).all()
    song_query = db.session.query(
        Song.artist_id,
        db.func.count(Song.id),
        db.func.sum(Song.vote_count),
    )
    vote_query = db.session.query(Vote.user_id, db.func.count(Vote.id))
    if contest:
        song_query = song_query.filter(Song.contest_id == contest.id)
        vote_query = vote_query.filter(Vote.contest_id == contest.id)
    else:
        song_query = song_query.filter(db.false())
        vote_query = vote_query.filter(db.false())
    song_stats = {
        artist_id: (song_count, int(votes_received or 0))
        for artist_id, song_count, votes_received in song_query.group_by(Song.artist_id).all()
    }
    votes_cast_by_user = dict(vote_query.group_by(Vote.user_id).all())

    user_data = []
    for user in users:
        artist = user.artist
        songs_count, votes_received = song_stats.get(artist.id, (0, 0)) if artist else (0, 0)
        entry = artist.get_contest_entry(contest) if artist and contest else None
        user_data.append({
            'id': user.id,
            'name': user.name,
            'username': user.username,
            'email': user.email,
            'roles': user.roles if isinstance(user.roles, list) else [user.roles],
            'is_active': user.is_active,
            'artist_profile': artist.to_dict() if artist else None,
            'status': (
                'pending_payment' if entry and not entry.is_paid
                else 'active' if entry
                else 'not_entered' if artist and contest
                else 'active'
            ),
            'songs_count': songs_count,
            'votes_received': votes_received,
            'votes_cast': votes_cast_by_user.get(user.id, 0),
            'created_at': user.created_at.isoformat() if user.created_at else None,
        })
    
    return jsonify({
        'users': user_data
    }), 200


@admin_bp.route('/users/<int:user_id>/status', methods=['PUT'])
@csrf.exempt
@admin_required
def update_user_status(user_id):
    """Activate or deactivate a user account."""
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict) or not isinstance(data.get('is_active'), bool):
        return jsonify({'error': 'is_active must be a boolean'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    admin_id = get_jwt_identity()
    if str(user.id) == str(admin_id) and not data['is_active']:
        return jsonify({'error': 'You cannot deactivate your own admin account'}), 400

    user.is_active = data['is_active']
    db.session.commit()

    return jsonify({
        'message': 'User account activated' if user.is_active else 'User account deactivated',
        'user': {
            'id': user.id,
            'is_active': user.is_active,
        },
    }), 200


@admin_bp.route('/payments', methods=['GET'])
@admin_required
def get_payments():
    """List payment records for admin review."""
    payments = Payment.query.order_by(Payment.created_at.desc(), Payment.id.desc()).all()
    return jsonify({
        'payments': [{
            **payment.to_dict(),
            'user': {
                'id': payment.user.id,
                'name': payment.user.name,
                'username': payment.user.username,
                'email': payment.user.email,
            } if payment.user else None,
            'contest_title': payment.contest.title if payment.contest else None,
        } for payment in payments],
    }), 200


@admin_bp.route('/payments/<int:payment_id>/status', methods=['PUT'])
@csrf.exempt
@admin_required
def update_payment_status(payment_id):
    """Update a payment's administrative status."""
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid payment status data'}), 400

    status = data.get('status')
    if status not in ('pending', 'successful', 'reversed'):
        return jsonify({'error': 'Status must be pending, successful, or reversed'}), 400

    payment = Payment.query.get(payment_id)
    if not payment:
        return jsonify({'error': 'Payment not found'}), 404

    payment.status = status
    if status == 'successful':
        payment.verified_at = datetime.utcnow()
    elif status == 'pending':
        payment.verified_at = None

    artist = payment.user.artist if payment.user else None
    if artist and payment.contest_id:
        entry = ContestEntry.query.filter_by(
            artist_id=artist.id,
            contest_id=payment.contest_id,
        ).first()
        if entry:
            has_successful_payment = Payment.query.filter_by(
                user_id=payment.user_id,
                contest_id=payment.contest_id,
                status='successful',
            ).filter(Payment.id != payment.id).first() is not None or status == 'successful'
            entry.is_paid = has_successful_payment
            entry.is_verified = has_successful_payment
            entry.status = 'approved' if has_successful_payment else 'pending_payment'

    if artist:
        latest_successful_payment = Payment.query.filter_by(
            user_id=payment.user_id,
            status='successful',
        ).order_by(Payment.verified_at.desc(), Payment.created_at.desc()).first()
        artist.is_paid = latest_successful_payment is not None
        artist.is_verified = latest_successful_payment is not None
        artist.payment_id = latest_successful_payment.id if latest_successful_payment else None

    db.session.commit()

    return jsonify({
        'message': 'Payment status updated',
        'payment': {
            **payment.to_dict(),
            'user': {
                'id': payment.user.id,
                'name': payment.user.name,
                'username': payment.user.username,
                'email': payment.user.email,
            } if payment.user else None,
            'contest_title': payment.contest.title if payment.contest else None,
        },
    }), 200


@admin_bp.route('/analytics', methods=['GET'])
@admin_required
def get_analytics():
    """Get live analytics for the active contest season."""
    contest = Contest.get_current()
    now = datetime.now()
    today = now.date()
    first_day = today - timedelta(days=6)
    daily_votes = []
    for day_offset in range(7):
        day = first_day + timedelta(days=day_offset)
        day_start = datetime.combine(day, time.min)
        day_end = day_start + timedelta(days=1)
        daily_votes.append({
            'date': day.isoformat(),
            'label': day.strftime('%b %d'),
            'votes': Vote.query.filter(
                Vote.created_at >= day_start,
                Vote.created_at < day_end,
                Vote.contest_id == contest.id if contest else db.false(),
            ).count(),
        })

    this_week_start = datetime.combine(today - timedelta(days=6), time.min)
    previous_week_start = this_week_start - timedelta(days=7)
    current_artist_registrations = ContestEntry.query.filter(
        ContestEntry.created_at >= this_week_start,
        ContestEntry.contest_id == contest.id if contest else db.false(),
    ).count()
    previous_artist_registrations = ContestEntry.query.filter(
        ContestEntry.created_at >= previous_week_start,
        ContestEntry.created_at < this_week_start,
        ContestEntry.contest_id == contest.id if contest else db.false(),
    ).count()
    current_user_registrations = User.query.filter(User.created_at >= this_week_start).count()
    previous_user_registrations = User.query.filter(
        User.created_at >= previous_week_start,
        User.created_at < this_week_start,
    ).count()

    top_songs = []
    if contest:
        songs = Song.query.filter_by(contest_id=contest.id, status='approved').order_by(
            Song.vote_count.desc()
        ).limit(5).all()
        top_songs = [{
            'title': song.title,
            'artist': song.artist.stage_name,
            'votes': song.vote_count,
        } for song in songs]

    revenue_query = db.session.query(db.func.coalesce(db.func.sum(Payment.amount), 0)).filter(
        Payment.status == 'successful',
        Payment.contest_id == contest.id if contest else db.false(),
    )

    return jsonify({
        'daily_votes': daily_votes,
        'top_songs': top_songs,
        'registration_trend': {
            'artists_this_week': current_artist_registrations,
            'artists_last_week': previous_artist_registrations,
            'users_this_week': current_user_registrations,
            'users_last_week': previous_user_registrations,
        },
        'contest_revenue': float(revenue_query.scalar() or 0),
        'contest_title': contest.title if contest else None,
    }), 200
