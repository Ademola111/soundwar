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
    reparticipation_notified_at = db.Column(db.DateTime, nullable=True)
    
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
        
        # Check if artist has won in the last 24 months
        two_years_ago = datetime.utcnow() - timedelta(days=730)
        recent_win = ContestWinner.query.filter(
            ContestWinner.artist_id == self.id,
            ContestWinner.won_at >= two_years_ago
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
        
        eligible_date = latest_win.won_at + timedelta(days=730)
        if datetime.utcnow() >= eligible_date:
            return 0
        
        days_remaining = (eligible_date - datetime.utcnow()).days
        return max(1, (days_remaining + 29) // 30)

    def needs_reparticipation_notification(self):
        """Check whether a past winner should be notified that they can re-enter."""
        from .contest import ContestWinner

        latest_win = ContestWinner.query.filter(
            ContestWinner.artist_id == self.id
        ).order_by(ContestWinner.won_at.desc()).first()

        if not latest_win:
            return False

        eligible_date = latest_win.won_at + timedelta(days=730)
        if datetime.utcnow() < eligible_date:
            return False

        if not self.reparticipation_notified_at:
            return True

        return self.reparticipation_notified_at < latest_win.won_at

    def get_contest_entry(self, contest):
        """Get the artist's registration record for a given contest season."""
        if contest is None:
            return None
        from .contest import ContestEntry

        return ContestEntry.query.filter_by(
            artist_id=self.id,
            contest_id=contest.id
        ).first()

    def has_participated_in_previous_contest(self, contest):
        """Check whether the artist submitted a song in an earlier contest."""
        if contest is None:
            return False

        from .contest import Contest
        from .song import Song

        return Song.query.join(Contest, Song.contest_id == Contest.id).filter(
            Song.artist_id == self.id,
            Contest.start_date < contest.start_date,
        ).first() is not None

    def has_paid_for_contest(self, contest):
        """Return True only if this artist has a successful payment for the given contest."""
        if contest is None:
            return False

        entry = self.get_contest_entry(contest)
        if entry:
            if entry.is_paid and entry.is_verified:
                from .payment import Payment
                payment = Payment.query.filter_by(
                    user_id=self.user_id,
                    contest_id=contest.id,
                    status='successful'
                ).first()
                return payment is not None
            return False

        # Returning artists must pay for each season; only first-time artists use
        # the legacy profile-level payment flags.
        if self.has_participated_in_previous_contest(contest):
            from .payment import Payment

            return Payment.query.filter_by(
                user_id=self.user_id,
                contest_id=contest.id,
                status='successful'
            ).first() is not None

        return bool(self.is_paid or self.is_verified)

    def can_participate_in_contest(self, contest):
        """Check whether the artist is eligible, paid, and approved for a specific contest."""
        if contest is None:
            return False

        if not self.can_participate():
            return False

        entry = self.get_contest_entry(contest)
        if not entry:
            if self.has_participated_in_previous_contest(contest):
                return self.has_paid_for_contest(contest)
            return bool(self.is_paid and self.is_verified)

        return bool(entry.is_paid and entry.is_verified and entry.status in ('approved', 'pending_approval'))

    def to_dict(self):
        """Convert to dictionary for JSON response"""
        from .contest import Contest

        current_contest = Contest.get_current()
        is_returning_artist = self.has_participated_in_previous_contest(current_contest)
        has_paid_for_current_contest = self.has_paid_for_contest(current_contest)

        return {
            'id': self.id,
            'user_id': self.user_id,
            'stage_name': self.stage_name,
            'bio': self.bio,
            'genre': self.genre,
            'profile_image': self.profile_image,
            'is_paid': self.is_paid,
            'is_verified': self.is_verified,
            'is_returning_artist': is_returning_artist,
            'has_paid_for_current_contest': has_paid_for_current_contest,
            'requires_season_payment': bool(
                current_contest and is_returning_artist and not has_paid_for_current_contest
            ),
            'is_past_winner': self.is_past_winner(),
            'can_participate': self.can_participate(),
            'months_until_eligible': self.months_until_eligible(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
