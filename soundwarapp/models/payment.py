"""
Payment Model
"""
from datetime import datetime
from soundwarapp import db


class Payment(db.Model):
    """Payment record for contest registration."""
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    contest_id = db.Column(db.Integer, db.ForeignKey('contests.id'), nullable=True)
    
    # Flutterwave transaction details
    transaction_id = db.Column(db.String(100), unique=True, nullable=False)
    tx_ref = db.Column(db.String(100), unique=True, nullable=False)
    flw_ref = db.Column(db.String(100), nullable=True)
    
    # Payment details
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='NGN')
    status = db.Column(db.String(20), default='pending')  # pending, successful, failed
    
    # Payment method
    payment_type = db.Column(db.String(50), nullable=True)
    
    # Purpose
    payment_purpose = db.Column(db.String(50), default='contest_registration')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.now)
    verified_at = db.Column(db.DateTime, nullable=True)
    
    # Relationship
    user = db.relationship('User', backref='payments')
    contest = db.relationship('Contest', backref='payments')
    
    def to_dict(self):
        """Convert to dictionary for JSON response"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'contest_id': self.contest_id,
            'transaction_id': self.transaction_id,
            'tx_ref': self.tx_ref,
            'amount': float(self.amount),
            'currency': self.currency,
            'status': self.status,
            'payment_type': self.payment_type,
            'payment_purpose': self.payment_purpose,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None
        }
