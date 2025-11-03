"""
Updated Admin Routes with Real Database Data
Replace your existing routes/admin_routes.py with this file
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from __init__ import db
from models import User, Wallet, Transaction
from utils.decorators import admin_required, active_user_required
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_

bp = Blueprint('admin', __name__, url_prefix='/api/admin')


@bp.route('/users', methods=['GET'])
@admin_required
def admin_get_users():
    """Get all users with their wallet information"""
    try:
        # Get query parameters for filtering and pagination
        search = request.args.get('search', '')
        status = request.args.get('status', '')  # 'active' or 'inactive'
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Build query
        query = User.query
        
        # Apply search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    User.first_name.ilike(search_term),
                    User.last_name.ilike(search_term),
                    User.email.ilike(search_term)
                )
            )
        
        # Apply status filter
        if status:
            query = query.filter_by(status=status)
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        users = query.order_by(User.created_at.desc()).limit(limit).offset(offset).all()
        
        # Format user data with wallet info
        users_data = []
        for user in users:
            user_dict = user.to_dict()
            
            # Add wallet information
            if user.wallet:
                user_dict['wallet'] = {
                    'wallet_id': user.wallet.wallet_id,
                    'balance': round(user.wallet.balance, 2),
                    'currency': user.wallet.currency,
                    'status': user.wallet.status
                }
            else:
                user_dict['wallet'] = None
            
            # Add transaction statistics
            sent_count = Transaction.query.filter_by(sender_id=user.id, type='transfer').count()
            received_count = Transaction.query.filter(
                and_(
                    Transaction.receiver_id == user.id,
                    Transaction.sender_id != user.id,
                    Transaction.type == 'transfer'
                )
            ).count()
            
            user_dict['transaction_stats'] = {
                'sent': sent_count,
                'received': received_count,
                'total': sent_count + received_count
            }
            
            users_data.append(user_dict)
        
        return jsonify({
            'success': True,
            'users': users_data,
            'count': len(users_data),
            'total_count': total_count,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        print(f"Error in admin_get_users: {str(e)}")
        import traceback
        traceback.print_exc()
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
            user_data = user.to_dict()
            
            # Add wallet info
            if user.wallet:
                user_data['wallet'] = user.wallet.to_dict()
            
            # Add detailed transaction history
            sent_transactions = Transaction.query.filter_by(
                sender_id=user.id, 
                type='transfer'
            ).order_by(Transaction.created_at.desc()).limit(10).all()
            
            received_transactions = Transaction.query.filter(
                and_(
                    Transaction.receiver_id == user.id,
                    Transaction.sender_id != user.id,
                    Transaction.type == 'transfer'
                )
            ).order_by(Transaction.created_at.desc()).limit(10).all()
            
            user_data['recent_transactions'] = {
                'sent': [t.to_dict() for t in sent_transactions],
                'received': [t.to_dict() for t in received_transactions]
            }
            
            return jsonify({
                'success': True,
                'user': user_data
            }), 200
        
        elif request.method == 'PUT':
            data = request.get_json()
            
            # Update user fields
            if 'first_name' in data:
                user.first_name = data['first_name'].strip()
            if 'last_name' in data:
                user.last_name = data['last_name'].strip()
            if 'phone' in data:
                user.phone = data['phone'].strip() if data['phone'] else None
            if 'country' in data:
                user.country = data['country'].strip()
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
            # Don't allow deleting the current admin
            current_user_id = int(get_jwt_identity())
            if user_id == current_user_id:
                return jsonify({'error': 'Cannot delete your own account'}), 400
            
            db.session.delete(user)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'User deleted successfully'
            }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in admin_user_detail: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@bp.route('/wallets', methods=['GET'])
@admin_required
def admin_get_wallets():
    """Get all wallets with user information"""
    try:
        search = request.args.get('search', '')
        status = request.args.get('status', '')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Build query
        query = Wallet.query.join(User)
        
        # Apply search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    User.first_name.ilike(search_term),
                    User.last_name.ilike(search_term),
                    User.email.ilike(search_term),
                    Wallet.wallet_id.ilike(search_term)
                )
            )
        
        # Apply status filter
        if status:
            query = query.filter(Wallet.status == status)
        
        # Get total count
        total_count = query.count()
        
        # Get wallets with pagination
        wallets = query.order_by(Wallet.created_at.desc()).limit(limit).offset(offset).all()
        
        # Format wallet data
        wallet_list = []
        for wallet in wallets:
            wallet_data = wallet.to_dict()
            
            if wallet.user:
                wallet_data['user'] = {
                    'id': wallet.user.id,
                    'name': f"{wallet.user.first_name} {wallet.user.last_name}",
                    'email': wallet.user.email,
                    'status': wallet.user.status
                }
                
                # Add transaction statistics
                total_sent = db.session.query(
                    func.sum(Transaction.total_amount)
                ).filter(
                    Transaction.sender_id == wallet.user_id,
                    Transaction.type == 'transfer',
                    Transaction.status == 'completed'
                ).scalar() or 0
                
                total_received = db.session.query(
                    func.sum(Transaction.amount)
                ).filter(
                    Transaction.receiver_id == wallet.user_id,
                    Transaction.sender_id != wallet.user_id,
                    Transaction.type == 'transfer',
                    Transaction.status == 'completed'
                ).scalar() or 0
                
                wallet_data['transaction_totals'] = {
                    'sent': round(total_sent, 2),
                    'received': round(total_received, 2)
                }
            
            wallet_list.append(wallet_data)
        
        # Calculate overall statistics
        total_balance = db.session.query(func.sum(Wallet.balance)).scalar() or 0
        active_wallets = Wallet.query.filter_by(status='active').count()
        
        return jsonify({
            'success': True,
            'wallets': wallet_list,
            'count': len(wallet_list),
            'total_count': total_count,
            'statistics': {
                'total_balance': round(total_balance, 2),
                'active_wallets': active_wallets,
                'average_balance': round(total_balance / max(total_count, 1), 2)
            },
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        print(f"Error in admin_get_wallets: {str(e)}")
        import traceback
        traceback.print_exc()
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
        note = data.get('note', '')
        
        if amount <= 0:
            return jsonify({'error': 'Invalid amount'}), 400
        
        old_balance = wallet.balance
        
        if action == 'add':
            wallet.balance += amount
            transaction_type = 'add_funds'
            transaction_note = f'Admin added funds: {note}' if note else 'Admin added funds'
        elif action == 'deduct':
            if wallet.balance < amount:
                return jsonify({'error': 'Insufficient balance'}), 400
            wallet.balance -= amount
            transaction_type = 'admin_deduction'
            transaction_note = f'Admin deducted funds: {note}' if note else 'Admin deducted funds'
        else:
            return jsonify({'error': 'Invalid action'}), 400
        
        wallet.updated_at = datetime.utcnow()
        
        # Create transaction record for audit trail
        from utils.helpers import generate_unique_id
        admin_user_id = int(get_jwt_identity())
        
        transaction = Transaction(
            transaction_id=generate_unique_id('ADM'),
            sender_id=admin_user_id if action == 'add' else wallet.user_id,
            receiver_id=wallet.user_id if action == 'add' else admin_user_id,
            amount=amount,
            fee=0.0,
            total_amount=amount,
            type=transaction_type,
            status='completed',
            note=transaction_note
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Wallet {action}ed successfully',
            'wallet': wallet.to_dict(),
            'old_balance': round(old_balance, 2),
            'new_balance': round(wallet.balance, 2),
            'amount_changed': round(amount, 2)
        }), 200
        
    except ValueError:
        return jsonify({'error': 'Invalid amount format'}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Error in admin_adjust_wallet: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@bp.route('/transactions', methods=['GET'])
@admin_required
def admin_get_transactions():
    """Get all transactions with filters"""
    try:
        # Get query parameters
        transaction_type = request.args.get('type', 'all')  # 'all', 'transfer', 'deposit'
        status = request.args.get('status', '')  # 'completed', 'pending', 'failed'
        search = request.args.get('search', '')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        # Build query
        query = Transaction.query
        
        # Apply type filter
        if transaction_type != 'all':
            query = query.filter(Transaction.type == transaction_type)
        
        # Apply status filter
        if status:
            query = query.filter(Transaction.status == status)
        
        # Apply date filters
        if date_from:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Transaction.created_at >= date_from_obj)
        
        if date_to:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Transaction.created_at < date_to_obj)
        
        # Apply search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Transaction.transaction_id.ilike(search_term),
                    Transaction.note.ilike(search_term)
                )
            )
        
        # Get total count
        total_count = query.count()
        
        # Get transactions with pagination
        transactions = query.order_by(Transaction.created_at.desc())\
            .limit(limit).offset(offset).all()
        
        # Format transaction data with user names
        transactions_list = []
        for t in transactions:
            t_data = t.to_dict()
            
            # Get sender and receiver info
            sender = User.query.get(t.sender_id)
            receiver = User.query.get(t.receiver_id)
            
            t_data['sender_name'] = f"{sender.first_name} {sender.last_name}" if sender else None
            t_data['sender_email'] = sender.email if sender else None
            t_data['receiver_name'] = f"{receiver.first_name} {receiver.last_name}" if receiver else None
            t_data['receiver_email'] = receiver.email if receiver else None
            
            transactions_list.append(t_data)
        
        return jsonify({
            'success': True,
            'transactions': transactions_list,
            'count': len(transactions_list),
            'total_count': total_count,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        print(f"Error in admin_get_transactions: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@bp.route('/stats', methods=['GET'])
@admin_required
def admin_stats():
    """Get comprehensive system statistics"""
    try:
        # Get time period from query params
        period = request.args.get('period', 'all')  # 'today', 'week', 'month', 'year', 'all'
        
        # Calculate date range
        end_date = datetime.utcnow()
        if period == 'today':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start_date = end_date - timedelta(days=7)
        elif period == 'month':
            start_date = end_date - timedelta(days=30)
        elif period == 'year':
            start_date = end_date - timedelta(days=365)
        else:
            start_date = None
        
        # User Statistics
        total_users = User.query.count()
        active_users = User.query.filter_by(status='active').count()
        admin_users = User.query.filter_by(role='admin').count()
        
        # New users in period
        new_users_query = User.query
        if start_date:
            new_users_query = new_users_query.filter(User.created_at >= start_date)
        new_users = new_users_query.count()
        
        # Transaction Statistics
        completed_transactions_query = Transaction.query.filter_by(status='completed')
        if start_date:
            completed_transactions_query = completed_transactions_query.filter(
                Transaction.created_at >= start_date
            )
        
        total_transactions = completed_transactions_query.count()
        
        # Transaction volume by type
        transfer_count = completed_transactions_query.filter_by(type='transfer').count()
        deposit_count = completed_transactions_query.filter(
            or_(
                Transaction.type == 'add_funds',
                Transaction.type == 'pesapay_deposit'
            )
        ).count()
        
        # Revenue Statistics
        total_revenue = db.session.query(func.sum(Transaction.fee)).filter(
            Transaction.status == 'completed'
        )
        if start_date:
            total_revenue = total_revenue.filter(Transaction.created_at >= start_date)
        total_revenue = total_revenue.scalar() or 0
        
        # Total transaction volume
        total_volume = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.status == 'completed',
            Transaction.type == 'transfer'
        )
        if start_date:
            total_volume = total_volume.filter(Transaction.created_at >= start_date)
        total_volume = total_volume.scalar() or 0
        
        # Wallet Statistics
        total_wallet_balance = db.session.query(func.sum(Wallet.balance)).scalar() or 0
        active_wallets = Wallet.query.filter_by(status='active').count()
        average_balance = total_wallet_balance / max(active_wallets, 1)
        
        # Failed transactions
        failed_transactions = Transaction.query.filter_by(status='failed')
        if start_date:
            failed_transactions = failed_transactions.filter(Transaction.created_at >= start_date)
        failed_count = failed_transactions.count()
        
        # Pending transactions
        pending_transactions = Transaction.query.filter_by(status='pending')
        if start_date:
            pending_transactions = pending_transactions.filter(Transaction.created_at >= start_date)
        pending_count = pending_transactions.count()
        
        # Recent transactions (last 10)
        recent_transactions = Transaction.query\
            .order_by(Transaction.created_at.desc())\
            .limit(10).all()
        
        recent_tx_list = []
        for tx in recent_transactions:
            tx_data = tx.to_dict()
            sender = User.query.get(tx.sender_id)
            receiver = User.query.get(tx.receiver_id)
            tx_data['sender_name'] = f"{sender.first_name} {sender.last_name}" if sender else None
            tx_data['receiver_name'] = f"{receiver.first_name} {receiver.last_name}" if receiver else None
            recent_tx_list.append(tx_data)
        
        # Daily transaction trend (last 7 days)
        daily_stats = []
        for i in range(6, -1, -1):
            day_start = (end_date - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            day_count = Transaction.query.filter(
                Transaction.created_at >= day_start,
                Transaction.created_at < day_end,
                Transaction.status == 'completed'
            ).count()
            
            day_volume = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.created_at >= day_start,
                Transaction.created_at < day_end,
                Transaction.status == 'completed',
                Transaction.type == 'transfer'
            ).scalar() or 0
            
            daily_stats.append({
                'date': day_start.strftime('%Y-%m-%d'),
                'count': day_count,
                'volume': round(day_volume, 2)
            })
        
        return jsonify({
            'success': True,
            'period': period,
            'users': {
                'total': total_users,
                'active': active_users,
                'new': new_users
            },
            'transactions': {
                'total': total_transactions,
                'transfers': transfer_count,
                'deposits': deposit_count,
                'failed': failed_count,
                'pending': pending_count
            },
            'revenue': {
                'total': round(total_revenue, 2),
                'average_per_transaction': round(total_revenue / max(total_transactions, 1), 2)
            },
            'wallets': {
                'total_balance': round(total_wallet_balance, 2),
                'active_wallets': active_wallets,
                'average_balance': round(average_balance, 2)
            },
            'daily_trend': daily_stats,
            'recent_transactions': recent_tx_list
        }), 200
        
    except Exception as e:
        print(f"Error in admin_stats: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@bp.route('/dashboard', methods=['GET'])
@admin_required
def admin_dashboard():
    """Get dashboard overview data"""
    try:
        # Quick stats for dashboard
        total_users = User.query.count()
        active_users = User.query.filter_by(status='active').count()
        
        # Today's stats
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_transactions = Transaction.query.filter(
            Transaction.created_at >= today_start,
            Transaction.status == 'completed'
        ).count()
        
        today_revenue = db.session.query(func.sum(Transaction.fee)).filter(
            Transaction.created_at >= today_start,
            Transaction.status == 'completed'
        ).scalar() or 0
        
        # Total wallet balance
        total_balance = db.session.query(func.sum(Wallet.balance)).scalar() or 0
        
        # Growth calculations (compare with last week)
        last_week = datetime.utcnow() - timedelta(days=7)
        users_last_week = User.query.filter(User.created_at < last_week).count()
        user_growth = ((total_users - users_last_week) / max(users_last_week, 1)) * 100
        
        return jsonify({
            'success': True,
            'overview': {
                'total_users': total_users,
                'active_users': active_users,
                'user_growth': round(user_growth, 1),
                'today_transactions': today_transactions,
                'today_revenue': round(today_revenue, 2),
                'total_wallet_balance': round(total_balance, 2)
            }
        }), 200
        
    except Exception as e:
        print(f"Error in admin_dashboard: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500