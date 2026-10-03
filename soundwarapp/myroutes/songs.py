"""
Song Routes
"""
import os
import uuid
import math
from flask import Blueprint, current_app, request, jsonify, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from soundwarapp import csrf, db
from ..models import User, Song, Contest
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
@csrf.exempt
@jwt_required()
def submit_song():
    """Submit a song for the current contest"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or not user.artist:
        return jsonify({'error': 'Artist profile required'}), 403
    
    artist = user.artist
    
    # Get current contest
    contest = Contest.get_current()
    if not contest:
        return jsonify({'error': 'No active contest'}), 400

    # Returning artists must pay for each new season. First-time artists retain
    # the existing registration payment flow.
    if not artist.has_paid_for_contest(contest):
        return jsonify({'error': 'Payment required for this contest season'}), 403

    # Check if artist can participate
    if not artist.can_participate():
        return jsonify({
            'error': 'Past winners cannot participate for 12 months',
            'months_remaining': artist.months_until_eligible()
        }), 403
    
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
    
    title = sanitize_input(request.form.get('title', ''))
    audio_file = request.files.get('audio_file')
    cover_file = request.files.get('cover_file')
    duration_value = request.form.get('duration', '')

    if not title:
        return jsonify({'error': 'Song title is required'}), 400
    if not audio_file or not audio_file.filename:
        return jsonify({'error': 'An MP3 file is required'}), 400
    if os.path.splitext(audio_file.filename)[1].lower() != '.mp3':
        return jsonify({'error': 'Only MP3 files are allowed'}), 400

    max_size = 15 * 1024 * 1024
    audio_data = audio_file.stream.read(max_size + 1)
    if not audio_data:
        return jsonify({'error': 'The uploaded MP3 file is empty'}), 400
    if len(audio_data) > max_size:
        return jsonify({'error': 'The MP3 file must be 15 MB or smaller'}), 413

    try:
        duration = float(duration_value)
    except (TypeError, ValueError):
        return jsonify({'error': 'Song duration is required'}), 400
    if not math.isfinite(duration) or duration <= 0:
        return jsonify({'error': 'Song duration must be a positive number of seconds'}), 400

    cover_data = None
    cover_extension = None
    if cover_file and cover_file.filename:
        cover_extension = os.path.splitext(cover_file.filename)[1].lower()
        allowed_cover_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.webp': 'image/webp',
        }
        if cover_extension not in allowed_cover_types or cover_file.mimetype != allowed_cover_types[cover_extension]:
            return jsonify({'error': 'Cover art must be a JPG, PNG, or WebP image'}), 400
        cover_data = cover_file.stream.read(5 * 1024 * 1024 + 1)
        if not cover_data:
            return jsonify({'error': 'The cover art image is empty'}), 400
        if len(cover_data) > 5 * 1024 * 1024:
            return jsonify({'error': 'Cover art must be 5 MB or smaller'}), 413

    upload_folder = current_app.config.get('SONG_UPLOAD_FOLDER') or os.path.join(
        current_app.static_folder, 'songs'
    )
    os.makedirs(upload_folder, exist_ok=True)
    filename = f'{uuid.uuid4().hex}.mp3'
    file_path = os.path.join(upload_folder, filename)
    with open(file_path, 'wb') as uploaded_song:
        uploaded_song.write(audio_data)

    cover_url = None
    cover_path = None
    if cover_data and cover_extension:
        cover_folder = current_app.config.get('SONG_COVER_FOLDER') or os.path.join(
            current_app.static_folder, 'covers'
        )
        os.makedirs(cover_folder, exist_ok=True)
        cover_filename = f'{uuid.uuid4().hex}{cover_extension}'
        cover_path = os.path.join(cover_folder, cover_filename)
        with open(cover_path, 'wb') as uploaded_cover:
            uploaded_cover.write(cover_data)
        cover_url = url_for('static', filename=f'covers/{cover_filename}', _external=True)
    
    # Create song
    song = Song(
        artist_id=artist.id,
        contest_id=contest.id,
        title=title,
        audio_url=url_for('static', filename=f'songs/{filename}', _external=True),
        cover_image=cover_url,
        duration=int(round(duration)),
        status='pending'
    )
    
    db.session.add(song)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        os.remove(file_path)
        if cover_path and os.path.exists(cover_path):
            os.remove(cover_path)
        raise
    
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
