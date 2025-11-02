from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from __init__ import db
from models import User
from datetime import datetime

bp = Blueprint('user', __name__, url_prefix='/api/users')


@bp.route('/profile', methods=['GET', 'PUT'])
@jwt_required()
def user_profile():
    """Get or update user profile"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if request.method == 'GET':
            return jsonify({
                'success': True,
                'user': user.to_dict()
            }), 200
        
        # PUT - Update profile
        data = request.get_json()
        
        if 'first_name' in data:
            user.first_name = data['first_name'].strip()
        if 'last_name' in data:
            user.last_name = data['last_name'].strip()
        if 'phone' in data:
            user.phone = data['phone'].strip() if data['phone'] else None
        if 'country' in data:
            user.country = data['country'].strip()
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in user_profile: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        if not data.get('current_password') or not data.get('new_password'):
            return jsonify({'error': 'Current and new password are required'}), 400
        
        if not user.check_password(data['current_password']):
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        if len(data['new_password']) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        user.set_password(data['new_password'])
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in change_password: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('', methods=['GET'])
@jwt_required()
def get_all_users():
    """Get all users (for sending money)"""
    try:
        current_user_id = get_jwt_identity()
        
        # Get all active users except current user
        users = User.query.filter(
            User.id != current_user_id,
            User.status == 'active'
        ).all()
        
        return jsonify({
            'success': True,
            'users': [u.to_dict() for u in users]
        }), 200
        
    except Exception as e:
        print(f"Error in get_all_users: {str(e)}")
        return jsonify({'error': str(e)}), 500