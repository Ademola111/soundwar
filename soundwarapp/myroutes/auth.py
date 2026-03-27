"""
Authentication Routes
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets

from soundwarapp.models import db, User
from soundwarapp.utils.security import sanitize_input, validate_email, validate_password
from soundwarapp.utils.email import send_password_reset_email

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()
    
    # Sanitize inputs
    email = sanitize_input(data.get('email', '')).lower()
    username = sanitize_input(data.get('username', ''))
    password = data.get('password', '')
    role = sanitize_input(data.get('role', 'user'))
    
    # Validation
    if not validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400
    
    password_valid, password_msg = validate_password(password)
    if not password_valid:
        return jsonify({'error': password_msg}), 400
    
    if len(username) < 3:
        return jsonify({'error': 'Username must be at least 3 characters'}), 400
    
    # Check existing user
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409
    
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already taken'}), 409
    
    # Create user
    user = User(
        email=email,
        username=username,
        password_hash=generate_password_hash(password),
        roles=[role]
    )
    
    db.session.add(user)
    db.session.commit()
    
    # Generate tokens
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    
    response = {
        'message': 'Registration successful',
        'token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict(),
        'requires_payment': role == 'artist'
    }
    
    return jsonify(response), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user"""
    data = request.get_json()
    
    email = sanitize_input(data.get('email', '')).lower()
    password = data.get('password', '')
    
    user = User.query.filter_by(email=email).first()
    
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    
    return jsonify({
        'token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict()
    }), 200


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Request password reset"""
    data = request.get_json()
    email = sanitize_input(data.get('email', '')).lower()
    
    # Always return success to prevent email enumeration
    user = User.query.filter_by(email=email).first()
    
    if user:
        # Generate secure reset token
        reset_token = secrets.token_urlsafe(32)
        user.reset_token = reset_token
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        db.session.commit()
        
        # Send reset email
        reset_url = f"{current_app.config['FRONTEND_URL']}/reset-password?token={reset_token}"
        send_password_reset_email(user.email, user.username, reset_url)
    
    return jsonify({'message': 'If an account exists, reset instructions have been sent'}), 200


@auth_bp.route('/verify-reset-token', methods=['POST'])
def verify_reset_token():
    """Verify password reset token"""
    data = request.get_json()
    token = data.get('token', '')
    
    user = User.query.filter_by(reset_token=token).first()
    
    if not user or not user.reset_token_expires:
        return jsonify({'error': 'Invalid or expired token'}), 400
    
    if datetime.utcnow() > user.reset_token_expires:
        user.reset_token = None
        user.reset_token_expires = None
        db.session.commit()
        return jsonify({'error': 'Token has expired'}), 400
    
    return jsonify({'valid': True}), 200


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password with token"""
    data = request.get_json()
    token = data.get('token', '')
    new_password = data.get('password', '')
    
    # Validate password
    password_valid, password_msg = validate_password(new_password)
    if not password_valid:
        return jsonify({'error': password_msg}), 400
    
    user = User.query.filter_by(reset_token=token).first()
    
    if not user or not user.reset_token_expires:
        return jsonify({'error': 'Invalid or expired token'}), 400
    
    if datetime.utcnow() > user.reset_token_expires:
        user.reset_token = None
        user.reset_token_expires = None
        db.session.commit()
        return jsonify({'error': 'Token has expired'}), 400
    
    # Update password
    user.password_hash = generate_password_hash(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.session.commit()
    
    return jsonify({'message': 'Password reset successful'}), 200


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    user_id = get_jwt_identity()
    access_token = create_access_token(identity=user_id)
    return jsonify({'token': access_token}), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current authenticated user"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({'user': user.to_dict()}), 200
