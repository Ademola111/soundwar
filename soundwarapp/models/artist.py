"""
Artist Model
"""
from datetime import datetime, timedelta
from soundwarapp import db


class Artist(db.Model):
    """Artist profile model"""
    __tablename__ = 'artists'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    stage_name = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.Text, nullable=True)
    genre = db.Column(db.String(50), nullable=True)
    profile_image = db.Column(db.String(500), nullable=True)
    
    # Payment status
    is_paid = db.Column(db.Boolean, default=False)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'), nullable=True)
    
    # Verification
    is_verified = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    songs = db.relationship('Song', backref='artist', lazy=True)
    wins = db.relationship('ContestWinner', backref='artist', lazy=True)
    
    def is_past_winner(self):
        """Check if artist has won any contest"""
        return len(self.wins) > 0
    
    def can_participate(self):
        """Check if artist can participate in current contest"""
        from .contest import ContestWinner
        
        # Check if artist has won in the last 12 months
        twelve_months_ago = datetime.utcnow() - timedelta(days=365)
        recent_win = ContestWinner.query.filter(
            ContestWinner.artist_id == self.id,
            ContestWinner.won_at >= twelve_months_ago
        ).first()
        
        return recent_win is None
    
    def months_until_eligible(self):
        """Calculate months until artist can participate again"""
        from .contest import ContestWinner
        
        latest_win = ContestWinner.query.filter(
            ContestWinner.artist_id == self.id
        ).order_by(ContestWinner.won_at.desc()).first()
        
        if not latest_win:
            return 0
        
        eligible_date = latest_win.won_at + timedelta(days=365)
        if datetime.now() >= eligible_date:
            return 0
        
        days_remaining = (eligible_date - datetime.utcnow()).days
        return max(1, days_remaining // 30)
    
    def to_dict(self):
        """Convert to dictionary for JSON response"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'stage_name': self.stage_name,
            'bio': self.bio,
            'genre': self.genre,
            'profile_image': self.profile_image,
            'is_paid': self.is_paid,
            'is_verified': self.is_verified,
            'is_past_winner': self.is_past_winner(),
            'can_participate': self.can_participate(),
            'months_until_eligible': self.months_until_eligible(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
