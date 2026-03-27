"""
Vote Model
"""
from datetime import datetime
from soundwarapp import db


class Vote(db.Model):
    """Vote model - one vote per user per contest"""
    __tablename__ = 'votes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    song_id = db.Column(db.Integer, db.ForeignKey('songs.id'), nullable=False)
    contest_id = db.Column(db.Integer, db.ForeignKey('contests.id'), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Unique constraint: one vote per user per contest
    __table_args__ = (
        db.UniqueConstraint('user_id', 'contest_id', name='unique_user_contest_vote'),
    )
    
    def to_dict(self):
        """Convert to dictionary for JSON response"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'song_id': self.song_id,
            'contest_id': self.contest_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
