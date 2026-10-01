"""
Artist Routes
"""
import os
import uuid
from flask import Blueprint, request, jsonify
from flask import current_app, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from urllib.parse import urlparse
from werkzeug.utils import secure_filename
from soundwarapp import csrf, db
from ..models import User, Artist
from ..utils.security import sanitize_input

artists_bp = Blueprint('artists', __name__, url_prefix='/api/artists')


@artists_bp.route('', methods=['GET'])
def get_artists():
    """Get all verified artists"""
    artists = Artist.query.filter_by(is_paid=True, is_verified=True).all()
    return jsonify({
        'artists': [artist.to_dict() for artist in artists]
    }), 200


@artists_bp.route('/<int:artist_id>', methods=['GET'])
def get_artist(artist_id):
    """Get artist by ID"""
    artist = Artist.query.get(artist_id)
    
    if not artist:
        return jsonify({'error': 'Artist not found'}), 404
    
    return jsonify({'artist': artist.to_dict()}), 200


@artists_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_artist_profile():
    """Get current user's artist profile"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or not user.artist:
        return jsonify({'error': 'Artist profile not found'}), 404
    
    return jsonify({'artist': user.artist.to_dict()}), 200


@artists_bp.route('/profile', methods=['PUT'])
@csrf.exempt
@jwt_required()
def update_artist_profile():
    """Update artist profile"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or not user.artist:
        return jsonify({'error': 'Artist profile not found'}), 404
    
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid profile update'}), 400

    artist = user.artist
    
    # Update allowed fields
    if 'stage_name' in data:
        stage_name = sanitize_input(data['stage_name'])
        if not stage_name or len(stage_name) > 100:
            return jsonify({'error': 'Stage name is required and must be 100 characters or fewer'}), 400
        artist.stage_name = stage_name
    if 'bio' in data:
        bio = sanitize_input(data['bio'])
        if len(bio) > 1000:
            return jsonify({'error': 'Bio must be 1000 characters or fewer'}), 400
        artist.bio = bio
    if 'genre' in data:
        genre = sanitize_input(data['genre'])
        if len(genre) > 50:
            return jsonify({'error': 'Genre must be 50 characters or fewer'}), 400
        artist.genre = genre
    if 'profile_image' in data:
        profile_image = data['profile_image']
        if profile_image in (None, ''):
            artist.profile_image = None
        elif not isinstance(profile_image, str) or len(profile_image) > 500:
            return jsonify({'error': 'Profile image URL must be 500 characters or fewer'}), 400
        else:
            parsed_url = urlparse(profile_image)
            if parsed_url.scheme not in ('http', 'https') or not parsed_url.netloc:
                return jsonify({'error': 'Profile image must be a valid HTTP or HTTPS URL'}), 400
            artist.profile_image = profile_image
    
    db.session.commit()
    
    return jsonify({
        'message': 'Profile updated successfully',
        'artist': artist.to_dict()
    }), 200


@artists_bp.route('/profile/image', methods=['POST'])
@csrf.exempt
@jwt_required()
def upload_artist_profile_image():
    """Upload and save the current artist's display picture."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user or not user.artist:
        return jsonify({'error': 'Artist profile not found'}), 404

    image = request.files.get('profile_image')
    if not image or not image.filename:
        return jsonify({'error': 'Choose an image to upload'}), 400

    extension = os.path.splitext(secure_filename(image.filename))[1].lower()
    allowed_types = {
        '.jpg': ('image/jpeg', lambda data: data.startswith(b'\xff\xd8\xff')),
        '.jpeg': ('image/jpeg', lambda data: data.startswith(b'\xff\xd8\xff')),
        '.png': ('image/png', lambda data: data.startswith(b'\x89PNG\r\n\x1a\n')),
        '.webp': ('image/webp', lambda data: data.startswith(b'RIFF') and data[8:12] == b'WEBP'),
    }
    image_type = allowed_types.get(extension)
    if not image_type or image.mimetype != image_type[0]:
        return jsonify({'error': 'Display picture must be a JPG, PNG, or WebP image'}), 400

    image_data = image.stream.read(5 * 1024 * 1024 + 1)
    if not image_data or not image_type[1](image_data):
        return jsonify({'error': 'The selected file is not a valid image'}), 400
    if len(image_data) > 5 * 1024 * 1024:
        return jsonify({'error': 'Display picture must be 5 MB or smaller'}), 413

    relative_folder = 'images/artist'
    upload_folder = current_app.config.get('ARTIST_PROFILE_UPLOAD_FOLDER') or os.path.join(
        current_app.static_folder, relative_folder
    )
    os.makedirs(upload_folder, exist_ok=True)
    filename = f'{uuid.uuid4().hex}{extension}'
    image_path = os.path.join(upload_folder, filename)

    with open(image_path, 'wb') as profile_image:
        profile_image.write(image_data)

    image_url = url_for('static', filename=f'{relative_folder}/{filename}', _external=True)
    user.artist.profile_image = image_url
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        if os.path.exists(image_path):
            os.remove(image_path)
        raise

    return jsonify({
        'message': 'Display picture updated',
        'artist': user.artist.to_dict(),
    }), 200


@artists_bp.route('/create', methods=['POST'])
@csrf.exempt
@jwt_required()
def create_artist_profile():
    """Create artist profile for user"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if user.artist:
        return jsonify({'error': 'Artist profile already exists'}), 409
    
    data = request.get_json()
    
    # Create artist profile
    artist = Artist(
        user_id=user.id,
        stage_name=sanitize_input(data.get('stage_name', user.username)),
        bio=sanitize_input(data.get('bio', '')),
        genre=sanitize_input(data.get('genre', '')),
        profile_image=data.get('profile_image')
    )
    
    # Update user role
    if 'artist' not in user.roles:
        user.roles = user.roles + ['artist']
    
    db.session.add(artist)
    db.session.commit()
    
    return jsonify({
        'message': 'Artist profile created',
        'artist': artist.to_dict()
    }), 201


@artists_bp.route('/check-eligibility', methods=['GET'])
@jwt_required()
def check_eligibility():
    """Check if artist can participate in current contest"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or not user.artist:
        return jsonify({'error': 'Artist profile not found'}), 404
    
    artist = user.artist
    can_participate = artist.can_participate()
    
    return jsonify({
        'can_participate': can_participate,
        'is_past_winner': artist.is_past_winner(),
        'months_until_eligible': artist.months_until_eligible() if not can_participate else 0
    }), 200
