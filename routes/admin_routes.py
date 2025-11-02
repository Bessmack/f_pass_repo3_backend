from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from __init__ import db
from models import User, Wallet, Transaction
from utils.decorators import admin_required
from datetime import datetime

bp = Blueprint('admin', __name__, url_prefix='/api/admin')


@bp.route('/users', methods=['GET'])
@admin_required
def admin_get_users():
    """Get all users"""
    try:
        users = User.query.all()
        return jsonify({
            'success': True,
            'users': [u.to_dict() for u in users],
            'count': len(users)
        }), 200
    except Exception as e:
        print(f"Error in admin_get_users: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/users/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
@admin_required
def admin_user_detail(user_id):
    """Get, update or delete user"""
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if request.method == 'GET':
            return jsonify({
                'success': True,
                'user': user.to_dict(),
                'wallet': user.wallet.to_dict() if user.wallet else None
            }), 200
        
        elif request.method == 'PUT':
            data = request.get_json()
            
            if 'status' in data:
                user.status = data['status']
            if 'role' in data:
                user.role = data['role']
            
            user.updated_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'User updated successfully',
                'user': user.to_dict()
            }), 200
        
        elif request.method == 'DELETE':
            db.session.delete(user)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'User deleted successfully'
            }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in admin_user_detail: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/wallets', methods=['GET'])
@admin_required
def admin_get_wallets():
    """Get all wallets"""
    try:
        wallets = Wallet.query.all()
        
        # Get wallet with user info
        wallet_list = []
        for wallet in wallets:
            wallet_data = wallet.to_dict()
            if wallet.user:
                wallet_data['user'] = {
                    'id': wallet.user.id,
                    'name': f"{wallet.user.first_name} {wallet.user.last_name}",
                    'email': wallet.user.email
                }
            wallet_list.append(wallet_data)
        
        return jsonify({
            'success': True,
            'wallets': wallet_list,
            'count': len(wallet_list)
        }), 200
    except Exception as e:
        print(f"Error in admin_get_wallets: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/wallets/<int:wallet_id>/adjust', methods=['POST'])
@admin_required
def admin_adjust_wallet(wallet_id):
    """Adjust wallet balance (admin only)"""
    try:
        wallet = Wallet.query.get(wallet_id)
        
        if not wallet:
            return jsonify({'error': 'Wallet not found'}), 404
        
        data = request.get_json()
        action = data.get('action')  # 'add' or 'deduct'
        amount = float(data.get('amount', 0))
        
        if amount <= 0:
            return jsonify({'error': 'Invalid amount'}), 400
        
        if action == 'add':
            wallet.balance += amount
        elif action == 'deduct':
            if wallet.balance < amount:
                return jsonify({'error': 'Insufficient balance'}), 400
            wallet.balance -= amount
        else:
            return jsonify({'error': 'Invalid action'}), 400
        
        wallet.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Wallet {action}ed successfully',
            'wallet': wallet.to_dict()
        }), 200
        
    except ValueError:
        return jsonify({'error': 'Invalid amount format'}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Error in admin_adjust_wallet: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/transactions', methods=['GET'])
@admin_required
def admin_get_transactions():
    """Get all transactions"""
    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        transactions = Transaction.query\
            .order_by(Transaction.created_at.desc())\
            .limit(limit).offset(offset).all()
        
        # Add user names to transactions
        transactions_list = []
        for t in transactions:
            t_data = t.to_dict()
            
            sender = User.query.get(t.sender_id)
            receiver = User.query.get(t.receiver_id)
            
            t_data['sender_name'] = f"{sender.first_name} {sender.last_name}" if sender else None
            t_data['receiver_name'] = f"{receiver.first_name} {receiver.last_name}" if receiver else None
            
            transactions_list.append(t_data)
        
        return jsonify({
            'success': True,
            'transactions': transactions_list,
            'count': len(transactions_list)
        }), 200
    except Exception as e:
        print(f"Error in admin_get_transactions: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/stats', methods=['GET'])
@admin_required
def admin_stats():
    """Get system statistics"""
    try:
        total_users = User.query.count()
        active_users = User.query.filter_by(status='active').count()
        total_transactions = Transaction.query.count()
        total_revenue = db.session.query(db.func.sum(Transaction.fee)).scalar() or 0
        total_wallet_balance = db.session.query(db.func.sum(Wallet.balance)).scalar() or 0
        
        # Recent transactions
        recent_transactions = Transaction.query\
            .order_by(Transaction.created_at.desc())\
            .limit(10).all()
        
        return jsonify({
            'success': True,
            'total_users': total_users,
            'active_users': active_users,
            'total_transactions': total_transactions,
            'total_revenue': round(total_revenue, 2),
            'total_wallet_balance': round(total_wallet_balance, 2),
            'recent_transactions': [t.to_dict() for t in recent_transactions]
        }), 200
    except Exception as e:
        print(f"Error in admin_stats: {str(e)}")
        return jsonify({'error': str(e)}), 500