"""
Song Routes
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from ..models import db, User, Song, Contest
from ..utils.security import sanitize_input

songs_bp = Blueprint('songs', __name__, url_prefix='/api/songs')


@songs_bp.route('', methods=['GET'])
def get_songs():
    """Get all approved songs for current contest"""
    contest = Contest.get_current()
    
    if not contest:
        return jsonify({'songs': []}), 200
    
    songs = Song.query.filter_by(
        contest_id=contest.id,
        status='approved'
    ).order_by(Song.vote_count.desc()).all()
    
    return jsonify({
        'songs': [song.to_dict() for song in songs]
    }), 200


@songs_bp.route('/<int:song_id>', methods=['GET'])
def get_song(song_id):
    """Get song by ID"""
    song = Song.query.get(song_id)
    
    if not song:
        return jsonify({'error': 'Song not found'}), 404
    
    return jsonify({'song': song.to_dict()}), 200


@songs_bp.route('/my-submissions', methods=['GET'])
@jwt_required()
def get_my_submissions():
    """Get current user's song submissions"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or not user.artist:
        return jsonify({'songs': []}), 200
    
    songs = Song.query.filter_by(artist_id=user.artist.id).all()
    
    return jsonify({
        'songs': [song.to_dict(include_artist=False) for song in songs]
    }), 200


@songs_bp.route('/submit', methods=['POST'])
@jwt_required()
def submit_song():
    """Submit a song for the current contest"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or not user.artist:
        return jsonify({'error': 'Artist profile required'}), 403
    
    artist = user.artist
    
    # Check if artist has paid
    if not artist.is_paid:
        return jsonify({'error': 'Payment required to submit songs'}), 403
    
    # Check if artist can participate
    if not artist.can_participate():
        return jsonify({
            'error': 'Past winners cannot participate for 12 months',
            'months_remaining': artist.months_until_eligible()
        }), 403
    
    # Get current contest
    contest = Contest.get_current()
    if not contest:
        return jsonify({'error': 'No active contest'}), 400
    
    # Check if contest is in submission phase
    if contest.get_phase() != 'submission':
        return jsonify({'error': 'Contest is not accepting submissions'}), 400
    
    # Check if artist already submitted to this contest
    existing = Song.query.filter_by(
        artist_id=artist.id,
        contest_id=contest.id
    ).first()
    
    if existing:
        return jsonify({'error': 'You have already submitted to this contest'}), 409
    
    data = request.get_json()
    
    # Create song
    song = Song(
        artist_id=artist.id,
        contest_id=contest.id,
        title=sanitize_input(data.get('title', '')),
        audio_url=data.get('audio_url'),
        cover_image=data.get('cover_image'),
        duration=data.get('duration'),
        status='pending'
    )
    
    db.session.add(song)
    db.session.commit()
    
    return jsonify({
        'message': 'Song submitted successfully. Pending approval.',
        'song': song.to_dict()
    }), 201


@songs_bp.route('/<int:song_id>', methods=['PUT'])
@jwt_required()
def update_song(song_id):
    """Update song (only if pending)"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    song = Song.query.get(song_id)
    
    if not song:
        return jsonify({'error': 'Song not found'}), 404
    
    if not user.artist or song.artist_id != user.artist.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if song.status != 'pending':
        return jsonify({'error': 'Cannot edit approved/rejected songs'}), 400
    
    data = request.get_json()
    
    if 'title' in data:
        song.title = sanitize_input(data['title'])
    if 'audio_url' in data:
        song.audio_url = data['audio_url']
    if 'cover_image' in data:
        song.cover_image = data['cover_image']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Song updated',
        'song': song.to_dict()
    }), 200
