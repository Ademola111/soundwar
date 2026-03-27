"""
User Model
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from soundwarapp import db


class User(db.Model):
    """User model for authentication and profile"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    roles = db.Column(db.JSON, default=['user'])
    
    # Password reset
    reset_token = db.Column(db.String(255), nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    artist = db.relationship('Artist', backref='user', uselist=False, lazy=True)
    votes = db.relationship('Vote', backref='user', lazy=True)
    
    def set_password(self, password):
        """Hash and set the password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def has_role(self, role):
        """Check if user has a specific role"""
        return role in (self.roles or [])
    
    def to_dict(self):
        """Convert to dictionary for JSON response"""
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'roles': self.roles or ['user'],
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
