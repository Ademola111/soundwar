"""
Authentication Routes
"""
import os
import uuid
from urllib.parse import urlparse

from flask import Blueprint, request, jsonify, current_app, url_for
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets
from soundwarapp import db, csrf
from soundwarapp.models import User, Contest
from soundwarapp.models.artist import Artist
from soundwarapp.utils.security import sanitize_input, validate_email, validate_password, validate_username
from soundwarapp.utils.email import send_activation_email, send_password_reset_email

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@csrf.exempt
@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json(silent=True) or {}
    
    if not isinstance(data, dict):
        data = {}
    
    # Sanitize inputs
    email = sanitize_input(data.get('email', '')).lower()
    username = sanitize_input(data.get('username', ''))
    name = sanitize_input(data.get('name', ''))
    password = data.get('password', '')
    requested_role = sanitize_input(data.get('role', 'user')).lower()
    if requested_role not in ('user', 'voter', 'artist'):
        return jsonify({'error': 'Only voter and artist registration is available here'}), 400
    role = 'artist' if requested_role == 'artist' else 'user'
    stageName = sanitize_input(data.get('artistName', ''))
    genre = sanitize_input(data.get('genre', ''))
    
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
    
    if role == 'artist' and Artist.query.filter_by(stage_name=stageName).first():
        return jsonify({'error': 'Stage name already taken'}), 409
    
    # Create user
    if role == 'artist':
        if not stageName:
            return jsonify({'error': 'Artist name is required'}), 400

        user = User(
            email=email,
            username=username,
            name=name,
            password_hash=generate_password_hash(password),
            roles=[role]
        )
        db.session.add(user)
        db.session.commit()
        art = Artist(
            user_id=user.id,
            stage_name=stageName,
            genre=genre
        )
        db.session.add(art)
        db.session.commit()
    else:
        user = User(
            email=email,
            username=username,
            name=name,
            password_hash=generate_password_hash(password),
            roles=[role]
        )
        db.session.add(user)
        db.session.commit()
    
    activation_token = secrets.token_urlsafe(32)
    user.activation_token = activation_token
    user.activation_token_expires = datetime.utcnow() + timedelta(hours=24)
    user.email_verified = False
    db.session.commit()

    activation_url = f"{current_app.config.get('FRONTEND_URL', 'http://localhost:8080')}/activate-account?token={activation_token}"
    send_activation_email(user.email, user.username, activation_url)
    print(f"Activation email sent to {user.email} with url : {activation_url}")
    current_contest = Contest.get_current()
    requires_payment = bool(
        role == 'artist' and
        current_contest is not None and
        user.artist is not None and
        not user.artist.has_paid_for_contest(current_contest)
    )

    response = {
        'user': user.to_dict(),
        'requires_activation': True,
        'message': 'Registration successful. Check your email to activate your account.',
        'requires_payment': requires_payment,
        'is_past_winner': bool(user.artist.is_past_winner() if user.artist else False),
        'can_participate': bool(user.artist.can_participate() if user.artist else True),
        'months_until_eligible': user.artist.months_until_eligible() if user.artist and not user.artist.can_participate() else 0
    }
    
    return jsonify(response), 201


@csrf.exempt
@auth_bp.route('/admin/register', methods=['POST'])
def register_admin():
    """Bootstrap the first admin using a deployment-provided setup key."""
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        data = {}
    setup_key = current_app.config.get('ADMIN_SETUP_KEY')
    provided_key = data.get('setup_key', '')

    if not setup_key:
        return jsonify({'error': 'Admin registration is disabled: ADMIN_SETUP_KEY is not configured'}), 503
    if not isinstance(provided_key, str) or not secrets.compare_digest(provided_key, setup_key):
        return jsonify({'error': 'Invalid admin setup key'}), 403

    existing_admins = User.query.all()
    if any(
        'admin' in (user.roles if isinstance(user.roles, list) else [user.roles])
        for user in existing_admins
    ):
        return jsonify({'error': 'Admin registration is already complete'}), 409

    name = sanitize_input(data.get('name', ''))
    username = sanitize_input(data.get('username', ''))
    email = sanitize_input(data.get('email', '')).lower()
    password = data.get('password', '')

    if not name:
        return jsonify({'error': 'Name is required'}), 400
    username_valid, username_message = validate_username(username)
    if not username_valid:
        return jsonify({'error': username_message}), 400
    if not validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400
    password_valid, password_message = validate_password(password)
    if not password_valid:
        return jsonify({'error': password_message}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already taken'}), 409

    user = User(
        email=email,
        username=username,
        name=name,
        password_hash=generate_password_hash(password),
        roles=['admin'],
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({'message': 'Admin account created. Sign in through the admin login page.'}), 201


@csrf.exempt
@auth_bp.route('/admin/login', methods=['POST'])
def login_admin():
    """Authenticate an admin account through the dedicated admin endpoint."""
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        data = {}
    email = sanitize_input(data.get('email', '')).lower()
    password = data.get('password', '')

    user = User.query.filter_by(email=email).first()
    roles = user.roles if user and isinstance(user.roles, list) else ([user.roles] if user else [])
    if not user or 'admin' not in roles or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid admin email or password'}), 401

    return jsonify({
        'token': create_access_token(identity=str(user.id)),
        'refresh_token': create_refresh_token(identity=str(user.id)),
        'user': user.to_dict(),
    }), 200


@csrf.exempt
@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user"""
    data = request.get_json()
    
    email = sanitize_input(data.get('email', '')).lower()
    password = data.get('password', '')
    
    user = User.query.filter_by(email=email).first()
    
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid email or password'}), 401

    if not user.email_verified:
        return jsonify({
            'error': 'Please activate your account using the link sent to your email.',
            'requires_activation': True,
        }), 403
    
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    
    login_response = {
        'token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict()
    }

    if user.artist:
        login_response.update({
            'requires_payment': not user.artist.is_paid,
            'is_past_winner': user.artist.is_past_winner(),
            'can_participate': user.artist.can_participate(),
            'months_until_eligible': 0 if user.artist.can_participate() else user.artist.months_until_eligible()
        })

    return jsonify(login_response), 200


@csrf.exempt
@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Request password reset"""
    data = request.get_json(silent=True) or {}
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
        print(f"Password reset email sent to {user.email} with url : {reset_url}"    )
    return jsonify({'message': 'If an account exists, reset instructions have been sent'}), 200


@csrf.exempt
@auth_bp.route('/verify-reset-token', methods=['POST'])
def verify_reset_token():
    """Verify password reset token"""
    data = request.get_json(silent=True) or {}
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


@csrf.exempt
@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password with token"""
    data = request.get_json(silent=True) or {}
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


@csrf.exempt
@auth_bp.route('/activate', methods=['POST'])
def activate_account():
    """Activate an account using its one-time email token."""
    data = request.get_json(silent=True) or {}
    token = data.get('token', '')
    user = User.query.filter_by(activation_token=token).first()

    if not user or not user.activation_token_expires:
        return jsonify({'error': 'Invalid or expired activation link'}), 400

    if datetime.utcnow() > user.activation_token_expires:
        user.activation_token = None
        user.activation_token_expires = None
        db.session.commit()
        return jsonify({'error': 'Activation link has expired'}), 400

    user.email_verified = True
    user.activation_token = None
    user.activation_token_expires = None
    db.session.commit()
    return jsonify({'message': 'Account activated successfully'}), 200


@csrf.exempt
@auth_bp.route('/resend-activation', methods=['POST'])
def resend_activation():
    """Issue a fresh activation link without revealing account existence."""
    data = request.get_json(silent=True) or {}
    email = sanitize_input(data.get('email', '')).lower()
    user = User.query.filter_by(email=email).first()

    if user and not user.email_verified:
        activation_token = secrets.token_urlsafe(32)
        user.activation_token = activation_token
        user.activation_token_expires = datetime.utcnow() + timedelta(hours=24)
        db.session.commit()
        activation_url = f"{current_app.config.get('FRONTEND_URL', 'http://localhost:8080')}/activate-account?token={activation_token}"
        send_activation_email(user.email, user.username, activation_url)

    return jsonify({'message': 'If the account exists and is not active, a new activation link has been sent'}), 200


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


@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_current_user_profile():
    """Get the current logged-in user's editable profile information."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({'user': user.to_dict()}), 200


@auth_bp.route('/profile', methods=['PUT'])
@csrf.exempt
@jwt_required()
def update_current_user_profile():
    """Update the current user's profile details including profile image."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        data = {}

    if request.form:
        form_data = request.form.to_dict()
        data = {**form_data, **data}

    name = data.get('name')
    if name is not None:
        cleaned_name = sanitize_input(name)
        if not cleaned_name or len(cleaned_name) > 100:
            return jsonify({'error': 'Name is required and must be 100 characters or fewer'}), 400
        user.name = cleaned_name

    username = data.get('username')
    if username is not None:
        cleaned_username = sanitize_input(username)
        if len(cleaned_username) < 3 or len(cleaned_username) > 30:
            return jsonify({'error': 'Username must be between 3 and 30 characters'}), 400
        existing = User.query.filter(User.username == cleaned_username, User.id != user.id).first()
        if existing:
            return jsonify({'error': 'Username already taken'}), 409
        user.username = cleaned_username

    uploaded_image = request.files.get('profile_image')
    if uploaded_image and uploaded_image.filename:
        extension = os.path.splitext(uploaded_image.filename)[1].lower()
        allowed_types = {
            '.jpg': ('image/jpeg', lambda data: data.startswith(b'\xff\xd8\xff')),
            '.jpeg': ('image/jpeg', lambda data: data.startswith(b'\xff\xd8\xff')),
            '.png': ('image/png', lambda data: data.startswith(b'\x89PNG\r\n\x1a\n')),
            '.webp': ('image/webp', lambda data: data.startswith(b'RIFF') and data[8:12] == b'WEBP'),
        }
        image_type = allowed_types.get(extension)
        if not image_type or uploaded_image.mimetype != image_type[0]:
            return jsonify({'error': 'Profile picture must be a JPG, PNG, or WebP image'}), 400

        image_data = uploaded_image.stream.read(5 * 1024 * 1024 + 1)
        if not image_data or not image_type[1](image_data):
            return jsonify({'error': 'The selected profile picture is not a valid image'}), 400
        if len(image_data) > 5 * 1024 * 1024:
            return jsonify({'error': 'Profile picture must be 5 MB or smaller'}), 413

        relative_folder = 'images/user'
        upload_folder = current_app.config.get('USER_PROFILE_UPLOAD_FOLDER') or os.path.join(
            current_app.static_folder, relative_folder
        )
        os.makedirs(upload_folder, exist_ok=True)
        filename = f'{uuid.uuid4().hex}{extension}'
        image_path = os.path.join(upload_folder, filename)
        with open(image_path, 'wb') as profile_image_file:
            profile_image_file.write(image_data)
        user.profile_image = url_for('static', filename=f'{relative_folder}/{filename}', _external=True)
    else:
        profile_image = data.get('profile_image')
        if profile_image is not None:
            if profile_image in ('', None):
                user.profile_image = None
            else:
                if not isinstance(profile_image, str) or len(profile_image) > 500:
                    return jsonify({'error': 'Profile image URL must be 500 characters or fewer'}), 400
                parsed = urlparse(profile_image)
                if parsed.scheme not in ('http', 'https') or not parsed.netloc:
                    return jsonify({'error': 'Profile image must be a valid HTTP or HTTPS URL'}), 400
                user.profile_image = profile_image

    db.session.commit()
    return jsonify({'message': 'Profile updated successfully', 'user': user.to_dict()}), 200
