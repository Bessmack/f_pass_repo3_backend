from __init__ import db
from datetime import datetime

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    fee = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(50), default='transfer')  # 'transfer', 'add_funds'
    status = db.Column(db.String(20), default='completed')  # 'completed', 'pending', 'failed'
    note = db.Column(db.Text)
    merchant_request_id = db.Column(db.String(100), index=True)  # For matching callbacks
    checkout_request_id = db.Column(db.String(100), index=True)  # M-Pesa checkout ID
    mpesa_receipt_number = db.Column(db.String(50))  # M-Pesa receipt number
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Add this line
    
    def to_dict(self):
        """Convert transaction to dictionary"""
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'amount': round(self.amount, 2),
            'fee': round(self.fee, 2),
            'total_amount': round(self.total_amount, 2),
            'type': self.type,
            'status': self.status,
            'note': self.note,
            'merchant_request_id': self.merchant_request_id,
            'checkout_request_id': self.checkout_request_id,
            'mpesa_receipt_number': self.mpesa_receipt_number,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Transaction {self.transaction_id} - {self.amount}>'