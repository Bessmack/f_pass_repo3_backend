"""
Helper functions for sending notifications
"""
from models.notification import create_notification
from __init__ import db


def send_transaction_notification(transaction, sender, receiver):
    """
    Send notifications to both sender and receiver for a transaction
    
    Args:
        transaction: Transaction object
        sender: User object (sender)
        receiver: User object (receiver)
    """
    try:
        # Notification for sender
        sender_notification = create_notification(
            user_id=sender.id,
            title="Money Sent Successfully",
            message=f"You successfully sent ${transaction.amount:.2f} to {receiver.first_name} {receiver.last_name}",
            notification_type='transaction',
            link=f'/user/transactions',
            meta_data={
                'transaction_id': transaction.transaction_id,
                'amount': float(transaction.amount),
                'fee': float(transaction.fee),
                'total': float(transaction.total_amount),
                'recipient': f"{receiver.first_name} {receiver.last_name}",
                'type': 'sent'
            }
        )
        
        # Notification for receiver
        receiver_notification = create_notification(
            user_id=receiver.id,
            title="Money Received",
            message=f"You received ${transaction.amount:.2f} from {sender.first_name} {sender.last_name}",
            notification_type='transaction',
            link=f'/user/transactions',
            meta_data={
                'transaction_id': transaction.transaction_id,
                'amount': float(transaction.amount),
                'sender': f"{sender.first_name} {sender.last_name}",
                'type': 'received'
            }
        )
        
        return sender_notification, receiver_notification
        
    except Exception as e:
        print(f"Error sending transaction notifications: {str(e)}")
        return None, None


def send_deposit_notification(user, amount, status='success'):
    """
    Send notification for deposit/add funds
    
    Args:
        user: User object
        amount: Deposit amount
        status: Status of deposit (success, failed, pending)
    """
    try:
        if status == 'success':
            title = "Funds Added Successfully"
            message = f"${amount:.2f} has been added to your wallet"
            notification_type = 'success'
        elif status == 'failed':
            title = "Deposit Failed"
            message = f"Failed to add ${amount:.2f} to your wallet. Please try again."
            notification_type = 'error'
        else:  # pending
            title = "Deposit Pending"
            message = f"Your deposit of ${amount:.2f} is being processed"
            notification_type = 'info'
        
        notification = create_notification(
            user_id=user.id,
            title=title,
            message=message,
            notification_type=notification_type,
            link='/user/wallet',
            meta_data={
                'amount': float(amount),
                'type': 'deposit',
                'status': status
            }
        )
        
        return notification
        
    except Exception as e:
        print(f"Error sending deposit notification: {str(e)}")
        return None


def send_low_balance_notification(user, current_balance, threshold=10.0):
    """
    Send notification when balance is low
    
    Args:
        user: User object
        current_balance: Current wallet balance
        threshold: Threshold for low balance warning
    """
    try:
        if current_balance <= threshold:
            notification = create_notification(
                user_id=user.id,
                title="Low Balance Alert",
                message=f"Your wallet balance is ${current_balance:.2f}. Consider adding funds.",
                notification_type='warning',
                link='/user/add-funds',
                meta_data={
                    'balance': float(current_balance),
                    'threshold': float(threshold),
                    'type': 'low_balance'
                }
            )
            
            return notification
            
    except Exception as e:
        print(f"Error sending low balance notification: {str(e)}")
        return None


def send_security_notification(user, action, details=None):
    """
    Send security-related notifications
    
    Args:
        user: User object
        action: Security action (login, password_change, etc.)
        details: Additional details
    """
    try:
        actions_map = {
            'login': {
                'title': 'New Login Detected',
                'message': 'A new login to your account was detected. If this wasn\'t you, please secure your account immediately.',
            },
            'password_change': {
                'title': 'Password Changed',
                'message': 'Your account password was successfully changed.',
            },
            'failed_login': {
                'title': 'Failed Login Attempt',
                'message': 'Someone tried to log in to your account with an incorrect password.',
            }
        }
        
        notification_info = actions_map.get(action, {
            'title': 'Security Alert',
            'message': 'A security event occurred on your account.'
        })
        
        notification = create_notification(
            user_id=user.id,
            title=notification_info['title'],
            message=notification_info['message'],
            notification_type='warning',
            link='/user/profile',
            meta_data={
                'action': action,
                'details': details,
                'type': 'security'
            }
        )
        
        return notification
        
    except Exception as e:
        print(f"Error sending security notification: {str(e)}")
        return None


def send_beneficiary_notification(user, beneficiary, action='added'):
    """
    Send notification for beneficiary actions
    
    Args:
        user: User object
        beneficiary: Beneficiary object
        action: Action performed (added, updated, deleted)
    """
    try:
        actions_map = {
            'added': f"New beneficiary '{beneficiary.name}' added successfully",
            'updated': f"Beneficiary '{beneficiary.name}' updated successfully",
            'deleted': f"Beneficiary '{beneficiary.name}' removed"
        }
        
        notification = create_notification(
            user_id=user.id,
            title="Beneficiary Updated",
            message=actions_map.get(action, "Beneficiary list updated"),
            notification_type='info',
            link='/user/contacts',
            meta_data={
                'beneficiary_id': beneficiary.id,
                'beneficiary_name': beneficiary.name,
                'action': action,
                'type': 'beneficiary'
            }
        )
        
        return notification
        
    except Exception as e:
        print(f"Error sending beneficiary notification: {str(e)}")
        return None