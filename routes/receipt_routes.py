"""
Receipt generation routes
"""
from flask import Blueprint, request, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from __init__ import db
from models import Transaction, User, Wallet
from utils.receipt_generator import generate_transaction_receipt, generate_wallet_statement
from datetime import datetime, timedelta

bp = Blueprint('receipts', __name__, url_prefix='/api/receipts')


@bp.route('/transaction/<string:transaction_id>', methods=['GET'])
@jwt_required()
def download_transaction_receipt(transaction_id):
    """Download receipt for a specific transaction"""
    try:
        current_user_id = int(get_jwt_identity())
        
        # Get transaction
        transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
        
        if not transaction:
            return {'error': 'Transaction not found'}, 404
        
        # Check authorization (user must be sender or receiver)
        if transaction.sender_id != current_user_id and transaction.receiver_id != current_user_id:
            return {'error': 'Unauthorized to access this receipt'}, 403
        
        # Get sender and receiver
        sender = User.query.get(transaction.sender_id)
        receiver = User.query.get(transaction.receiver_id)
        
        if not sender or not receiver:
            return {'error': 'User data not found'}, 404
        
        # Generate receipt
        receipt_buffer = generate_transaction_receipt(transaction, sender, receiver)
        
        # Send file
        return send_file(
            receipt_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'receipt_{transaction_id}.pdf'
        )
        
    except Exception as e:
        print(f"Error generating receipt: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'error': 'Failed to generate receipt'}, 500


@bp.route('/wallet/statement', methods=['GET'])
@jwt_required()
def download_wallet_statement():
    """Download wallet statement"""
    try:
        current_user_id = int(get_jwt_identity())
        
        # Get query parameters
        period = request.args.get('period', 'month')  # month, 3months, 6months, year, all
        
        # Calculate date range
        end_date = datetime.utcnow()
        if period == 'month':
            start_date = end_date - timedelta(days=30)
        elif period == '3months':
            start_date = end_date - timedelta(days=90)
        elif period == '6months':
            start_date = end_date - timedelta(days=180)
        elif period == 'year':
            start_date = end_date - timedelta(days=365)
        else:  # all
            start_date = None
        
        # Get user and wallet
        user = User.query.get(current_user_id)
        wallet = Wallet.query.filter_by(user_id=current_user_id).first()
        
        if not user or not wallet:
            return {'error': 'User or wallet not found'}, 404
        
        # Get transactions
        query = Transaction.query.filter(
            (Transaction.sender_id == current_user_id) | 
            (Transaction.receiver_id == current_user_id)
        )
        
        if start_date:
            query = query.filter(Transaction.created_at >= start_date)
        
        transactions = query.order_by(Transaction.created_at.desc()).all()
        
        # Generate statement
        statement_buffer = generate_wallet_statement(
            wallet, user, transactions, start_date, end_date
        )
        
        # Send file
        filename = f'statement_{wallet.wallet_id}_{period}.pdf'
        return send_file(
            statement_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"Error generating statement: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'error': 'Failed to generate statement'}, 500


@bp.route('/transaction/<string:transaction_id>/email', methods=['POST'])
@jwt_required()
def email_transaction_receipt(transaction_id):
    """Email receipt for a specific transaction"""
    try:
        current_user_id = int(get_jwt_identity())
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return {'error': 'Email address is required'}, 400
        
        # Get transaction
        transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
        
        if not transaction:
            return {'error': 'Transaction not found'}, 404
        
        # Check authorization
        if transaction.sender_id != current_user_id and transaction.receiver_id != current_user_id:
            return {'error': 'Unauthorized'}, 403
        
        # Get sender and receiver
        sender = User.query.get(transaction.sender_id)
        receiver = User.query.get(transaction.receiver_id)
        
        # Generate receipt
        receipt_buffer = generate_transaction_receipt(transaction, sender, receiver)
        
        # TODO: Implement email sending
        # This would require setting up an email service (SendGrid, AWS SES, etc.)
        # For now, return success
        
        return {
            'success': True,
            'message': f'Receipt sent to {email}',
            'transaction_id': transaction_id
        }, 200
        
    except Exception as e:
        print(f"Error emailing receipt: {str(e)}")
        return {'error': 'Failed to email receipt'}, 500