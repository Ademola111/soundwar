"""
Song Model
"""
from datetime import datetime
from soundwarapp import db


class Song(db.Model):
    """Song submission model"""
    __tablename__ = 'songs'
    
    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.id'), nullable=False)
    contest_id = db.Column(db.Integer, db.ForeignKey('contests.id'), nullable=False)
    
    title = db.Column(db.String(200), nullable=False)
    audio_url = db.Column(db.String(500), nullable=False)
    cover_image = db.Column(db.String(500), nullable=True)
    duration = db.Column(db.Integer, nullable=True)  # Duration in seconds
    
    # Approval status
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    rejection_reason = db.Column(db.Text, nullable=True)
    
    # Vote count (denormalized for performance)
    vote_count = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    approved_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    votes = db.relationship('Vote', backref='song', lazy=True)
    
    def to_dict(self, include_artist=True):
        """Convert to dictionary for JSON response"""
        data = {
            'id': self.id,
            'artist_id': self.artist_id,
            'contest_id': self.contest_id,
            'title': self.title,
            'audio_url': self.audio_url,
            'cover_image': self.cover_image,
            'duration': self.duration,
            'status': self.status,
            'vote_count': self.vote_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None
        }
        
        if include_artist and self.artist:
            data['artist'] = {
                'id': self.artist.id,
                'stage_name': self.artist.stage_name,
                'profile_image': self.artist.profile_image
            }
        
        return data
