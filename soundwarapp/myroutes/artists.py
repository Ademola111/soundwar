"""
Artist Routes
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..models import db, User, Artist
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
@jwt_required()
def update_artist_profile():
    """Update artist profile"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or not user.artist:
        return jsonify({'error': 'Artist profile not found'}), 404
    
    data = request.get_json()
    artist = user.artist
    
    # Update allowed fields
    if 'stage_name' in data:
        artist.stage_name = sanitize_input(data['stage_name'])
    if 'bio' in data:
        artist.bio = sanitize_input(data['bio'])
    if 'genre' in data:
        artist.genre = sanitize_input(data['genre'])
    if 'profile_image' in data:
        artist.profile_image = data['profile_image']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Profile updated successfully',
        'artist': artist.to_dict()
    }), 200


@artists_bp.route('/create', methods=['POST'])
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
