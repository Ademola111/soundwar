"""
SoundWars Flask API - Routes
"""
from .auth import auth_bp
from .artists import artists_bp
from .songs import songs_bp
from .votes import votes_bp
from .payments import payments_bp
from .leaderboard import leaderboard_bp
from .admin import admin_bp

__all__ = [
    'auth_bp',
    'artists_bp', 
    'songs_bp',
    'votes_bp',
    'payments_bp',
    'leaderboard_bp',
    'admin_bp'
]
