"""
Contest Model
"""
from datetime import datetime
from soundwarapp import db


class Contest(db.Model):
    """Contest model for monthly competitions"""
    __tablename__ = 'contests'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Contest phases
    phase = db.Column(db.String(20), default='submission')  # submission, voting, completed
    phase_override = db.Column(db.Boolean, default=False, nullable=False)
    
    # Dates
    start_date = db.Column(db.DateTime, nullable=False)
    submission_end_date = db.Column(db.DateTime, nullable=False)
    voting_end_date = db.Column(db.DateTime, nullable=False)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    songs = db.relationship('Song', backref='contest', lazy=True)
    votes = db.relationship('Vote', backref='contest', lazy=True)
    winner = db.relationship('ContestWinner', backref='contest', uselist=False, lazy=True)
    
    @classmethod
    def get_current(cls):
        """Get the current active contest"""
        return cls.query.filter_by(is_active=True).first()
    
    def get_phase(self):
        """Return an admin-set phase, or derive it from dates when not overridden."""
        if self.phase_override:
            return self.phase

        now = datetime.now()
        
        if now < self.start_date:
            return 'upcoming'
        elif now < self.submission_end_date:
            return 'submission'
        elif now < self.voting_end_date:
            return 'voting'
        else:
            return 'completed'
    
    def to_dict(self):
        """Convert to dictionary for JSON response"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'phase': self.get_phase(),
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'submission_end_date': self.submission_end_date.isoformat() if self.submission_end_date else None,
            'voting_end_date': self.voting_end_date.isoformat() if self.voting_end_date else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ContestEntry(db.Model):
    """Represents an artist's registration and payment for a single contest season."""
    __tablename__ = 'contest_entries'

    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.id'), nullable=False)
    contest_id = db.Column(db.Integer, db.ForeignKey('contests.id'), nullable=False)

    status = db.Column(db.String(30), default='pending_payment')
    is_paid = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        db.UniqueConstraint('artist_id', 'contest_id', name='uq_artist_contest_entry'),
    )

    artist = db.relationship('Artist', backref='contest_entries')
    contest = db.relationship('Contest', backref='contest_entries')

    def to_dict(self):
        return {
            'id': self.id,
            'artist_id': self.artist_id,
            'contest_id': self.contest_id,
            'status': self.status,
            'is_paid': self.is_paid,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


ArtistContestEntry = ContestEntry


class ContestWinner(db.Model):
    """Contest winner record"""
    __tablename__ = 'contest_winners'
    
    id = db.Column(db.Integer, primary_key=True)
    contest_id = db.Column(db.Integer, db.ForeignKey('contests.id'), unique=True, nullable=False)
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.id'), nullable=False)
    song_id = db.Column(db.Integer, db.ForeignKey('songs.id'), nullable=False)
    
    # Winner details
    final_vote_count = db.Column(db.Integer, nullable=False)
    prize_amount = db.Column(db.Numeric(10, 2), nullable=True)
    
    # Timestamps
    won_at = db.Column(db.DateTime, default=datetime.now)
    
    def to_dict(self):
        """Convert to dictionary for JSON response"""
        return {
            'id': self.id,
            'contest_id': self.contest_id,
            'artist_id': self.artist_id,
            'song_id': self.song_id,
            'final_vote_count': self.final_vote_count,
            'prize_amount': float(self.prize_amount) if self.prize_amount else None,
            'won_at': self.won_at.isoformat() if self.won_at else None
        }
