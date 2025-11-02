"""
Notification model for storing user notifications
"""
from __init__ import db
from datetime import datetime


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default='info')  # info, success, warning, error, transaction
    is_read = db.Column(db.Boolean, default=False, index=True)
    link = db.Column(db.String(500))  # Optional link to related resource
    meta_data = db.Column(db.JSON)  # Additional data (transaction_id, amount, etc.) - renamed from metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    read_at = db.Column(db.DateTime)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic'))
    
    def to_dict(self):
        """Convert notification to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'message': self.message,
            'type': self.type,
            'is_read': self.is_read,
            'link': self.link,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None
        }
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()
            db.session.commit()
    
    def __repr__(self):
        return f'<Notification {self.id} - {self.title}>'


def create_notification(user_id, title, message, notification_type='info', link=None, metadata=None):
    """
    Helper function to create a notification
    
    Args:
        user_id: User ID to send notification to
        title: Notification title
        message: Notification message
        notification_type: Type of notification
        link: Optional link to related resource
        metadata: Optional additional data
    
    Returns:
        Notification: Created notification object
    """
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notification_type,
        link=link,
        metadata=metadata
    )
    
    db.session.add(notification)
    db.session.commit()
    
    return notification


def create_transaction_notification(transaction, user_id, is_sender=False):
    """
    Create a notification for a transaction
    
    Args:
        transaction: Transaction object
        user_id: User ID to notify
        is_sender: Whether the user is the sender
    
    Returns:
        Notification: Created notification object
    """
    if is_sender:
        title = "Money Sent Successfully"
        message = f"You successfully sent ${transaction.amount:.2f}"
    else:
        title = "Money Received"
        message = f"You received ${transaction.amount:.2f}"
    
    metadata = {
        'transaction_id': transaction.transaction_id,
        'amount': float(transaction.amount),
        'type': transaction.type,
        'status': transaction.status
    }
    
    return create_notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type='transaction',
        link=f'/user/transactions/{transaction.transaction_id}',
        metadata=metadata
    )