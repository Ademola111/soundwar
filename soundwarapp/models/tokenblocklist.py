"""
Token Blocklist Model
"""
from datetime import datetime, timezone
from soundwarapp import db

class TokenBlocklist(db.Model):
    __tablename__ = 'tokenblocklist'
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, index=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    artist = db.relationship('Artist', backref='tokenblocklist', uselist=False, lazy=True)
    user = db.relationship('User', backref='tokenblocklist', uselist=False, lazy=True)

def to_dict(self):
        """Convert to dictionary for JSON response"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'artist_id': self.artist_id,
            'jti': self.jti,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
