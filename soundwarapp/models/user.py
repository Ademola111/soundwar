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
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    profile_image = db.Column(db.String(500), nullable=True)
    roles = db.Column(db.JSON, default=['user'])
    email_verified = db.Column(db.Boolean, nullable=False, default=True)
    
    # Password reset
    reset_token = db.Column(db.String(255), nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)
    activation_token = db.Column(db.String(255), nullable=True)
    activation_token_expires = db.Column(db.DateTime, nullable=True)
    
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
    
    def get_vote_history(self):
        """Return a user-friendly list of votes cast with song and artist details."""
        history = []
        for vote in sorted(self.votes, key=lambda item: item.created_at, reverse=True):
            song = vote.song
            artist = song.artist if song else None
            history.append({
                'id': vote.id,
                'song_id': vote.song_id,
                'song_title': song.title if song else None,
                'artist_id': artist.id if artist else None,
                'artist_name': artist.stage_name if artist else None,
                'contest_id': vote.contest_id,
                'created_at': vote.created_at.isoformat() if vote.created_at else None,
            })
        return history

    def to_dict(self):
        """Convert to dictionary for JSON response"""
        profile = None
        if self.artist:
            profile = self.artist.to_dict()

        vote_history = self.get_vote_history()

        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'username': self.username,
            'profile_image': self.profile_image,
            'email_verified': self.email_verified,
            'roles': self.roles or ['user'],
            'artist_profile': profile,
            'votes_cast': len(vote_history),
            'vote_history': vote_history,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
