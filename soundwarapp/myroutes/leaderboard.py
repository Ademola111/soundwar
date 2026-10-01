"""
Leaderboard Routes
"""
from flask import Blueprint, jsonify
from ..models import Song, Contest

leaderboard_bp = Blueprint('leaderboard', __name__, url_prefix='/api/leaderboard')


@leaderboard_bp.route('', methods=['GET'])
def get_leaderboard():
    """Get current contest leaderboard"""
    contest = Contest.get_current()
    
    if not contest:
        return jsonify({
            'leaderboard': [],
            'contest': None
        }), 200
    
    # Get approved songs ordered by vote count
    songs = Song.query.filter_by(
        contest_id=contest.id,
        status='approved'
    ).order_by(Song.vote_count.desc()).all()
    
    leaderboard = []
    for rank, song in enumerate(songs, 1):
        leaderboard.append({
            'rank': rank,
            'song': song.to_dict(),
            'vote_count': song.vote_count
        })
    
    return jsonify({
        'leaderboard': leaderboard,
        'contest': contest.to_dict()
    }), 200


@leaderboard_bp.route('/top/<int:limit>', methods=['GET'])
def get_top_songs(limit):
    """Get top N songs from current contest"""
    contest = Contest.get_current()
    
    if not contest:
        return jsonify({'songs': []}), 200
    
    limit = min(limit, 50)  # Cap at 50
    
    songs = Song.query.filter_by(
        contest_id=contest.id,
        status='approved'
    ).order_by(Song.vote_count.desc()).limit(limit).all()
    
    return jsonify({
        'songs': [song.to_dict() for song in songs]
    }), 200


@leaderboard_bp.route('/contest/<int:contest_id>', methods=['GET'])
def get_contest_leaderboard(contest_id):
    """Get leaderboard for a specific contest"""
    contest = Contest.query.get(contest_id)
    
    if not contest:
        return jsonify({'error': 'Contest not found'}), 404
    
    songs = Song.query.filter_by(
        contest_id=contest.id,
        status='approved'
    ).order_by(Song.vote_count.desc()).all()
    
    leaderboard = []
    for rank, song in enumerate(songs, 1):
        leaderboard.append({
            'rank': rank,
            'song': song.to_dict(),
            'vote_count': song.vote_count
        })
    
    return jsonify({
        'leaderboard': leaderboard,
        'contest': contest.to_dict()
    }), 200
