"""
Voting Routes
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import IntegrityError
from soundwarapp import csrf, db
from ..models import User, Song, Vote, Contest

votes_bp = Blueprint('votes', __name__, url_prefix='/api/votes')


@votes_bp.route('/cast', methods=['POST'])
@csrf.exempt
@jwt_required()
def cast_vote():
    """Cast a vote for a song"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid vote request'}), 400
    song_id = data.get('song_id')
    
    if not song_id:
        return jsonify({'error': 'Song ID required'}), 400
    
    # Get song and verify it exists and is approved
    song = Song.query.get(song_id)
    
    if not song:
        return jsonify({'error': 'Song not found'}), 404
    
    if song.status != 'approved':
        return jsonify({'error': 'Song is not available for voting'}), 400
    
    # Get current contest
    contest = Contest.get_current()
    
    if not contest:
        return jsonify({'error': 'No active contest'}), 400

    if song.contest_id != contest.id:
        return jsonify({'error': 'Song is not part of the active contest'}), 400
    
    # Check if contest is in voting phase
    if contest.phase != 'voting':
        return jsonify({'error': 'Voting is not currently open'}), 400
    
    # Check if user has already voted in this contest
    existing_vote = Vote.query.filter_by(
        user_id=user.id,
        contest_id=contest.id
    ).first()
    
    if existing_vote:
        return jsonify({
            'error': 'You have already voted in this contest',
            'voted_song_id': existing_vote.song_id
        }), 409
    
    # Create vote
    vote = Vote(
        user_id=user.id,
        song_id=song.id,
        contest_id=contest.id
    )
    
    # Increment song vote count
    song.vote_count += 1
    
    db.session.add(vote)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'You have already voted in this contest'}), 409
    
    return jsonify({
        'message': 'Vote cast successfully',
        'vote': vote.to_dict()
    }), 201


@votes_bp.route('/status', methods=['GET'])
@jwt_required()
def get_vote_status():
    """Check if user has voted in current contest"""
    user_id = get_jwt_identity()
    
    contest = Contest.get_current()
    
    if not contest:
        return jsonify({
            'has_voted': False,
            'voted_song_id': None
        }), 200
    
    vote = Vote.query.filter_by(
        user_id=user_id,
        contest_id=contest.id
    ).first()
    
    return jsonify({
        'has_voted': vote is not None,
        'voted_song_id': vote.song_id if vote else None,
        'voted_at': vote.created_at.isoformat() if vote else None
    }), 200


@votes_bp.route('/my-vote', methods=['GET'])
@jwt_required()
def get_my_vote():
    """Get user's vote for current contest with song details"""
    user_id = get_jwt_identity()
    
    contest = Contest.get_current()
    
    if not contest:
        return jsonify({'vote': None}), 200
    
    vote = Vote.query.filter_by(
        user_id=user_id,
        contest_id=contest.id
    ).first()
    
    if not vote:
        return jsonify({'vote': None}), 200
    
    # Include song details
    song = Song.query.get(vote.song_id)
    
    return jsonify({
        'vote': {
            **vote.to_dict(),
            'song': song.to_dict() if song else None
        }
    }), 200


@votes_bp.route('/my-history', methods=['GET'])
@jwt_required()
def get_my_vote_history():
    """Return all votes a user has cast, including song and artist details."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    votes = []
    for vote in sorted(user.votes, key=lambda item: item.created_at, reverse=True):
        song = Song.query.get(vote.song_id)
        artist = song.artist if song else None
        votes.append({
            'id': vote.id,
            'song_id': vote.song_id,
            'song_title': song.title if song else None,
            'artist_id': artist.id if artist else None,
            'artist_name': artist.stage_name if artist else None,
            'contest_id': vote.contest_id,
            'contest_title': vote.contest.title if vote.contest else None,
            'created_at': vote.created_at.isoformat() if vote.created_at else None,
        })

    return jsonify({'votes': votes, 'votes_cast': len(votes)}), 200
