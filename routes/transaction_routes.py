from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from __init__ import db
from models import User, Wallet, Transaction
from utils.helpers import generate_unique_id
from datetime import datetime

bp = Blueprint('transaction', __name__, url_prefix='/api/transactions')


def calculate_fee(amount):
    """Calculate transaction fee (1.5%)"""
    return round(amount * 0.015, 2)


@bp.route('/send', methods=['POST'])
@jwt_required()
def send_money():
    """Send money from one wallet to another"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()

        wallet_id = data.get('wallet_id')  # receiver's wallet ID
        amount = float(data.get('amount', 0))
        note = data.get('note', '')

        print(f"📤 Send Money Request:")
        print(f"   From User: {current_user_id}")
        print(f"   To Wallet: {wallet_id}")
        print(f"   Amount: ${amount}")
        print(f"   Note: {note}")

        # Validation
        if not wallet_id or amount <= 0:
            return jsonify({'error': 'Invalid wallet ID or amount'}), 400

        # Get sender's wallet
        sender_wallet = Wallet.query.filter_by(user_id=current_user_id).first()
        if not sender_wallet:
            return jsonify({'error': 'Sender wallet not found'}), 404

        # Get receiver's wallet
        receiver_wallet = Wallet.query.filter_by(wallet_id=wallet_id).first()
        if not receiver_wallet:
            return jsonify({'error': 'Receiver wallet not found'}), 404

        # Check if sending to self
        if sender_wallet.wallet_id == receiver_wallet.wallet_id:
            return jsonify({'error': 'Cannot send money to yourself'}), 400

        # Calculate fee and total
        fee = calculate_fee(amount)
        total_amount = amount + fee

        print(f"💰 Transaction Details:")
        print(f"   Amount: ${amount}")
        print(f"   Fee: ${fee}")
        print(f"   Total: ${total_amount}")
        print(f"   Sender Balance: ${sender_wallet.balance}")

        # Check balance
        if sender_wallet.balance < total_amount:
            return jsonify({
                'error': f'Insufficient balance. You need ${total_amount:.2f} (including ${fee:.2f} fee), but have ${sender_wallet.balance:.2f}'
            }), 400

        # Perform transaction
        sender_wallet.balance -= total_amount
        sender_wallet.updated_at = datetime.utcnow()
        
        receiver_wallet.balance += amount
        receiver_wallet.updated_at = datetime.utcnow()

        # Create transaction record
        transaction = Transaction(
            transaction_id=generate_unique_id('TXN'),
            sender_id=current_user_id,
            receiver_id=receiver_wallet.user_id,
            amount=amount,
            fee=fee,
            total_amount=total_amount,
            type='transfer',
            status='completed',
            note=note,
            created_at=datetime.utcnow()
        )

        db.session.add(transaction)
        db.session.commit()

        print(f"✅ Transaction successful!")
        print(f"   Transaction ID: {transaction.transaction_id}")
        print(f"   Sender new balance: ${sender_wallet.balance}")
        print(f"   Receiver new balance: ${receiver_wallet.balance}")

        # Get receiver user details
        receiver_user = User.query.get(receiver_wallet.user_id)

        return jsonify({
            'success': True,
            'message': f'Successfully sent ${amount:.2f} to {receiver_user.first_name} {receiver_user.last_name}',
            'transaction': {
                'transaction_id': transaction.transaction_id,
                'sender_wallet': sender_wallet.wallet_id,
                'receiver_wallet': receiver_wallet.wallet_id,
                'receiver_name': f"{receiver_user.first_name} {receiver_user.last_name}",
                'amount': amount,
                'fee': fee,
                'total': total_amount,
                'sender_new_balance': sender_wallet.balance,
                'timestamp': transaction.created_at.isoformat()
            }
        }), 200

    except ValueError:
        return jsonify({'error': 'Invalid amount format'}), 400
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error in send_money: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@bp.route('', methods=['GET'])
@jwt_required()
def get_transactions():
    """Get user's transactions"""
    try:
        current_user_id = get_jwt_identity()
        transaction_type = request.args.get('type', 'all')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))

        # Build query based on type
        query = Transaction.query
        
        if transaction_type == 'sent':
            query = query.filter(
                Transaction.sender_id == current_user_id,
                Transaction.type == 'transfer'
            )
        elif transaction_type == 'received':
            query = query.filter(
                Transaction.receiver_id == current_user_id,
                Transaction.sender_id != current_user_id,
                Transaction.type == 'transfer'
            )
        else:
            # All transactions (sent, received, deposits, withdrawals)
            query = query.filter(
                (Transaction.sender_id == current_user_id) |
                (Transaction.receiver_id == current_user_id)
            )

        transactions = query.order_by(Transaction.created_at.desc()) \
            .limit(limit).offset(offset).all()

        # Get all unique user IDs
        user_ids = set()
        for t in transactions:
            if t.sender_id:
                user_ids.add(t.sender_id)
            if t.receiver_id:
                user_ids.add(t.receiver_id)
        
        # Fetch all users at once
        users = User.query.filter(User.id.in_(user_ids)).all()
        user_dict = {u.id: u for u in users}

        # Build transaction list with names
        transactions_list = []
        for t in transactions:
            sender = user_dict.get(t.sender_id)
            receiver = user_dict.get(t.receiver_id)

            t_data = t.to_dict()
            t_data.update({
                'sender_name': f"{sender.first_name} {sender.last_name}" if sender else None,
                'receiver_name': f"{receiver.first_name} {receiver.last_name}" if receiver else None,
                'is_sent': t.sender_id == current_user_id and t.type == 'transfer',
                'is_received': t.receiver_id == current_user_id and t.sender_id != current_user_id and t.type == 'transfer'
            })
            transactions_list.append(t_data)

        return jsonify({
            'success': True,
            'transactions': transactions_list,
            'count': len(transactions_list)
        }), 200

    except Exception as e:
        print(f"Error in get_transactions: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/<string:transaction_id>', methods=['GET'])
@jwt_required()
def get_transaction(transaction_id):
    """Get specific transaction"""
    try:
        current_user_id = get_jwt_identity()
        transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()

        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404

        # Check authorization
        if transaction.sender_id != current_user_id and transaction.receiver_id != current_user_id:
            return jsonify({'error': 'Unauthorized'}), 403

        # Get sender and receiver
        sender = User.query.get(transaction.sender_id)
        receiver = User.query.get(transaction.receiver_id)

        transaction_data = transaction.to_dict()
        transaction_data.update({
            'sender_name': f"{sender.first_name} {sender.last_name}" if sender else None,
            'receiver_name': f"{receiver.first_name} {receiver.last_name}" if receiver else None,
            'is_sent': transaction.sender_id == current_user_id,
            'is_received': transaction.receiver_id == current_user_id
        })

        return jsonify({
            'success': True,
            'transaction': transaction_data
        }), 200

    except Exception as e:
        print(f"Error in get_transaction: {str(e)}")
        return jsonify({'error': str(e)}), 500