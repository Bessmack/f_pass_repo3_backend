"""
Notification routes for managing user notifications
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from __init__ import db
from models.notification import Notification
from datetime import datetime

bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')


@bp.route('', methods=['GET'])
@jwt_required()
def get_notifications():
    """Get all notifications for the current user"""
    try:
        current_user_id = int(get_jwt_identity())
        
        # Get query parameters
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Build query
        query = Notification.query.filter_by(user_id=current_user_id)
        
        if unread_only:
            query = query.filter_by(is_read=False)
        
        # Get total count
        total_count = query.count()
        unread_count = Notification.query.filter_by(
            user_id=current_user_id,
            is_read=False
        ).count()
        
        # Get notifications
        notifications = query.order_by(Notification.created_at.desc())\
            .limit(limit).offset(offset).all()
        
        return jsonify({
            'success': True,
            'notifications': [n.to_dict() for n in notifications],
            'total_count': total_count,
            'unread_count': unread_count,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        print(f"Error in get_notifications: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:notification_id>/read', methods=['PUT'])
@jwt_required()
def mark_as_read(notification_id):
    """Mark a notification as read"""
    try:
        current_user_id = int(get_jwt_identity())
        
        notification = Notification.query.get(notification_id)
        
        if not notification:
            return jsonify({'error': 'Notification not found'}), 404
        
        # Check ownership
        if notification.user_id != current_user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        notification.mark_as_read()
        
        return jsonify({
            'success': True,
            'message': 'Notification marked as read',
            'notification': notification.to_dict()
        }), 200
        
    except Exception as e:
        print(f"Error in mark_as_read: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/mark-all-read', methods=['PUT'])
@jwt_required()
def mark_all_as_read():
    """Mark all notifications as read"""
    try:
        current_user_id = int(get_jwt_identity())
        
        # Update all unread notifications
        updated_count = Notification.query.filter_by(
            user_id=current_user_id,
            is_read=False
        ).update({
            'is_read': True,
            'read_at': datetime.utcnow()
        })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Marked {updated_count} notifications as read',
            'updated_count': updated_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in mark_all_as_read: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:notification_id>', methods=['DELETE'])
@jwt_required()
def delete_notification(notification_id):
    """Delete a notification"""
    try:
        current_user_id = int(get_jwt_identity())
        
        notification = Notification.query.get(notification_id)
        
        if not notification:
            return jsonify({'error': 'Notification not found'}), 404
        
        # Check ownership
        if notification.user_id != current_user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        db.session.delete(notification)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Notification deleted'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in delete_notification: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/clear', methods=['DELETE'])
@jwt_required()
def clear_all_notifications():
    """Clear all notifications (delete read notifications)"""
    try:
        current_user_id = int(get_jwt_identity())
        
        # Delete only read notifications
        deleted_count = Notification.query.filter_by(
            user_id=current_user_id,
            is_read=True
        ).delete()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Cleared {deleted_count} read notifications',
            'deleted_count': deleted_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in clear_all_notifications: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/unread-count', methods=['GET'])
@jwt_required()
def get_unread_count():
    """Get count of unread notifications"""
    try:
        current_user_id = int(get_jwt_identity())
        
        unread_count = Notification.query.filter_by(
            user_id=current_user_id,
            is_read=False
        ).count()
        
        return jsonify({
            'success': True,
            'unread_count': unread_count
        }), 200
        
    except Exception as e:
        print(f"Error in get_unread_count: {str(e)}")
        return jsonify({'error': str(e)}), 500