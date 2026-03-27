"""
Admin Routes
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from functools import wraps

from ..models import db, User, Artist, Song, Vote, Contest, ContestWinner, Payment

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
    """Get admin dashboard statistics"""
    stats = {
        'total_users': User.query.count(),
        'total_artists': Artist.query.filter_by(is_paid=True).count(),
        'total_songs': Song.query.count(),
        'pending_songs': Song.query.filter_by(status='pending').count(),
        'approved_songs': Song.query.filter_by(status='approved').count(),
        'total_votes': Vote.query.count(),
        'total_payments': Payment.query.filter_by(status='successful').count()
    }
    
    contest = Contest.get_current()
    
    return jsonify({
        'stats': stats,
        'current_contest': contest.to_dict() if contest else None
    }), 200


@admin_bp.route('/songs/pending', methods=['GET'])
@admin_required
def get_pending_songs():
    """Get all pending song submissions"""
    songs = Song.query.filter_by(status='pending').all()
    
    return jsonify({
        'songs': [song.to_dict() for song in songs]
    }), 200


@admin_bp.route('/songs/<int:song_id>/approve', methods=['POST'])
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


@admin_bp.route('/contests', methods=['POST'])
@admin_required
def create_contest():
    """Create a new contest"""
    data = request.get_json()
    
    # Deactivate current contest
    current = Contest.get_current()
    if current:
        current.is_active = False
    
    contest = Contest(
        title=data.get('title'),
        description=data.get('description'),
        start_date=datetime.fromisoformat(data.get('start_date')),
        submission_end_date=datetime.fromisoformat(data.get('submission_end_date')),
        voting_end_date=datetime.fromisoformat(data.get('voting_end_date')),
        is_active=True
    )
    
    db.session.add(contest)
    db.session.commit()
    
    return jsonify({
        'message': 'Contest created',
        'contest': contest.to_dict()
    }), 201


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
    """Get all users"""
    users = User.query.order_by(User.created_at.desc()).all()
    
    return jsonify({
        'users': [user.to_dict() for user in users]
    }), 200
