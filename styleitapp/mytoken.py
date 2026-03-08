import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
from datetime import datetime, timedelta, timezone
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from flask import current_app

def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=current_app.config['SECURITY_PASSWORD_SALT'])

def confirm_token(token, expiration=300):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token,
            salt=current_app.config['SECURITY_PASSWORD_SALT'],
            max_age=expiration
        )
    except SignatureExpired:
        return "<h1>Token has expired</h1>"
    return email

""" used to activate newly signed up users via email """
def generate_activation_token(email):
    # expiration_time = datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=24)
    payload = {
        'email': email,
        "iat": int(now.timestamp()),
        'exp': int(exp.timestamp()),
        # 'exp':expiration_time,
        'type': 'activation'
    }
    token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def confirm_activation_code(token):
    """
    Verify and decode the JWT activation code.
    """
    try:
        decoded = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"], options={"require": ["exp", "iat", "email"]})
        if decoded.get('type') != 'activation':
            return {"valid": False, "error": "Invalid token type."}
        if 'email' not in decoded:
            return {"valid": False, "error": "Email not found in token."}
        # Check if the token has expired
        if decoded['exp'] < int(datetime.now(timezone.utc).timestamp()):
            return {"valid": False, "error": "Token has expired."}
        # If everything is valid, return the email
        email = decoded.get("email")
        
        if not email:
            return {"valid": False, "error": "Email not found in token."}
        # If the email is valid, return it
        return {"valid": True, "email": email}

    except ExpiredSignatureError:
        return {"valid": False, "error": "Token has expired."}
    except InvalidTokenError:
        return {"valid": False, "error": "Invalid token."}


""" used to generate password reset tokens for users who forgot their password """
def generate_password_reset_token(email):
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=1)
    payload = {
        'email': email,
        "iat": int(now.timestamp()),
        'exp': int(exp.timestamp()),
        'type': 'password_reset'
    }
    token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm=current_app.config['JWT_ALGORITHM'])
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token

def confirm_password_reset_token(token):
    try:
        decoded = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=[current_app.config['JWT_ALGORITHM']], options={"require": ["exp", "iat", "email"]})
        if decoded.get('type') != 'password_reset':
            return {"valid": False, "error": "Invalid token type."}
        if 'email' not in decoded:
            return {"valid": False, "error": "Email not found in token."}
        if decoded['exp'] < int(datetime.now(timezone.utc).timestamp()):
            return {"valid": False, "error": "Token has expired."}
        email = decoded.get("email")
        if not email:
            return {"valid": False, "error": "Email not found in token."}
        return {"valid": True, "email": email}

    except ExpiredSignatureError:
        return {"valid": False, "error": "Token has expired."}
    except InvalidTokenError:
        return {"valid": False, "error": "Invalid token."}