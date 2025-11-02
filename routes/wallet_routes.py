import requests
import base64
import hashlib
import json
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from __init__ import db
from models import Wallet, Transaction, User
from utils.helpers import generate_unique_id
import os
from utils.notification_helpers import send_deposit_notification

bp = Blueprint('wallet', __name__, url_prefix='/api/wallet')

# Pesapay Configuration
PESAPAY_BASE_URL = os.getenv("PESAPAY_BASE_URL", "https://pay.pesapay.com/api")
PESAPAY_MERCHANT_ID = os.getenv("PESAPAY_MERCHANT_ID")
PESAPAY_API_KEY = os.getenv("PESAPAY_API_KEY")
PESAPAY_API_SECRET = os.getenv("PESAPAY_API_SECRET")
PESAPAY_CALLBACK_URL = os.getenv("PESAPAY_CALLBACK_URL")

def generate_pesapay_signature(api_key, api_secret, merchant_id, amount, currency, reference, timestamp):
    """
    Generate Pesapay API signature
    """
    data = f"{api_key}{api_secret}{merchant_id}{amount}{currency}{reference}{timestamp}"
    return hashlib.sha256(data.encode()).hexdigest()

@bp.route('/deposit', methods=['POST'])
@jwt_required()
def pesapay_deposit():
    """Initiate Pesapay payment"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        print(f"📥 Received Pesapay deposit request: {data}")
        
        amount = float(data.get('amount'))
        phone = data.get('phone')
        currency = data.get('currency', 'USD')
        
        print(f"💰 Amount: {amount}, 📱 Phone: {phone}, 👤 User ID: {current_user_id}")

        if amount <= 0:
            return jsonify({'error': 'Invalid amount'}), 400

        # Get user's wallet
        wallet = Wallet.query.filter_by(user_id=current_user_id).first()
        if not wallet:
            return jsonify({'error': 'Wallet not found'}), 404

        # Generate unique transaction reference
        transaction_reference = generate_unique_id('PESAPAY')
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        
        # Generate Pesapay signature
        signature = generate_pesapay_signature(
            PESAPAY_API_KEY,
            PESAPAY_API_SECRET,
            PESAPAY_MERCHANT_ID,
            f"{amount:.2f}",
            currency,
            transaction_reference,
            timestamp
        )

        # Prepare Pesapay payment request
        payment_url = f"{PESAPAY_BASE_URL}/v1/payments/request"
        
        payload = {
            "merchant_id": PESAPAY_MERCHANT_ID,
            "api_key": PESAPAY_API_KEY,
            "signature": signature,
            "timestamp": timestamp,
            "amount": f"{amount:.2f}",
            "currency": currency,
            "reference": transaction_reference,
            "description": f"Wallet deposit - {transaction_reference}",
            "callback_url": PESAPAY_CALLBACK_URL,
            "customer": {
                "phone": phone,
                "email": "",  # You can get user email if available
                "name": ""    # You can get user name if available
            },
            "metadata": {
                "user_id": str(current_user_id),
                "wallet_id": wallet.wallet_id,
                "transaction_type": "wallet_deposit"
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        print(f"🔗 Sending request to Pesapay: {payment_url}")
        print(f"📦 Payload: {json.dumps(payload, indent=2)}")

        response = requests.post(payment_url, json=payload, headers=headers, timeout=30)
        
        print(f"🔍 Pesapay Response Status: {response.status_code}")
        print(f"🔍 Pesapay Response Text: {response.text}")

        try:
            response_data = response.json()
        except Exception as e:
            print(f"❌ JSON decode failed: {str(e)}")
            return jsonify({'error': 'Invalid response from Pesapay', 'raw': response.text}), 500

        if response.status_code == 200 and response_data.get('success'):
            # Create pending transaction record
            pesapay_transaction_id = response_data.get('data', {}).get('transaction_id')
            payment_url = response_data.get('data', {}).get('payment_url')
            
            pending_transaction = Transaction(
                transaction_id=transaction_reference,
                sender_id=current_user_id,
                receiver_id=current_user_id,
                amount=amount,
                fee=0.0,
                total_amount=amount,
                type='pesapay_deposit',
                status='pending',
                note=f'Pesapay deposit pending - Ref: {transaction_reference}',
                merchant_request_id=pesapay_transaction_id,
                checkout_request_id=transaction_reference
            )
            
            db.session.add(pending_transaction)
            db.session.commit()
            
            print(f"✅ Pending transaction created: {pending_transaction.transaction_id}")
            
            return jsonify({
                'success': True,
                'message': 'Payment initiated successfully',
                'transaction_id': pending_transaction.transaction_id,
                'pesapay_transaction_id': pesapay_transaction_id,
                'payment_url': payment_url,  # URL for user to complete payment
                'reference': transaction_reference
            }), 200
        else:
            error_message = response_data.get('message', 'Payment initiation failed')
            print(f"❌ Pesapay error: {error_message}")
            return jsonify({'error': error_message}), 400

    except requests.exceptions.Timeout:
        print("❌ Pesapay API timeout")
        return jsonify({'error': 'Payment service timeout. Please try again.'}), 408
    except requests.exceptions.ConnectionError:
        print("❌ Pesapay API connection error")
        return jsonify({'error': 'Cannot connect to payment service. Please try again.'}), 503
    except Exception as e:
        print(f"❌ Error in pesapay_deposit: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@bp.route('/pesapay-callback', methods=['POST'])
def pesapay_callback():
    """Handle Pesapay payment callback"""
    try:
        data = request.get_json()
        print(f"📥 Pesapay Callback received: {json.dumps(data, indent=2)}")
        
        # Verify callback signature (important for security)
        callback_signature = request.headers.get('X-Pesapay-Signature')
        if not verify_pesapay_callback_signature(data, callback_signature):
            print("❌ Invalid callback signature")
            return jsonify({"status": "error", "message": "Invalid signature"}), 400

        transaction_reference = data.get('reference')
        status = data.get('status')  # 'success', 'failed', 'pending'
        pesapay_transaction_id = data.get('transaction_id')
        amount = data.get('amount')
        currency = data.get('currency')
        
        print(f"🔍 Callback Details:")
        print(f"   Reference: {transaction_reference}")
        print(f"   Status: {status}")
        print(f"   Pesapay TXN ID: {pesapay_transaction_id}")
        print(f"   Amount: {amount} {currency}")

        # Find the pending transaction
        transaction = Transaction.query.filter_by(
            transaction_id=transaction_reference,
            status='pending'
        ).first()

        if not transaction:
            print(f"⚠️ No pending transaction found for reference: {transaction_reference}")
            return jsonify({"status": "error", "message": "Transaction not found"}), 404

        # Get the user's wallet
        wallet = Wallet.query.filter_by(user_id=transaction.sender_id).first()
        
        if not wallet:
            print(f"❌ Wallet not found for user_id: {transaction.sender_id}")
            transaction.status = 'failed'
            transaction.note = 'Wallet not found'
            db.session.commit()
            return jsonify({"status": "error", "message": "Wallet not found"}), 404

        if status == 'success':
            print("✅ Payment successful!")
            
            # Update wallet balance
            wallet.balance += float(amount)
            wallet.updated_at = datetime.utcnow()
            
            # Update transaction status
            transaction.status = 'completed'
            transaction.note = f'Pesapay deposit successful - TXN: {pesapay_transaction_id}'
            transaction.merchant_request_id = pesapay_transaction_id
            transaction.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            # Send success notification
            send_deposit_notification(wallet, float(amount), status='success')
            
            print(f"✅ Wallet updated! New balance: ${wallet.balance}")
            print(f"✅ Transaction {transaction.transaction_id} marked as completed")
            
        elif status == 'failed':
            print(f"❌ Payment failed")
            
            transaction.status = 'failed'
            transaction.note = f'Pesapay deposit failed - {data.get("message", "Payment failed")}'
            transaction.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            # Send failure notification
            send_deposit_notification(wallet, float(amount), status='failed')
            
            print(f"❌ Transaction {transaction.transaction_id} marked as failed")

        return jsonify({"status": "success", "message": "Callback processed"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ Callback error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": "Internal server error"}), 500

def verify_pesapay_callback_signature(data, signature):
    """
    Verify Pesapay callback signature for security
    """
    try:
        # Implement signature verification based on Pesapay documentation
        # This is a simplified version - adjust based on actual Pesapay requirements
        expected_data = f"{data.get('reference')}{data.get('amount')}{data.get('currency')}{PESAPAY_API_SECRET}"
        expected_signature = hashlib.sha256(expected_data.encode()).hexdigest()
        
        return signature == expected_signature
    except Exception as e:
        print(f"❌ Signature verification error: {str(e)}")
        return False

@bp.route('/payment-status/<reference>', methods=['GET'])
@jwt_required()
def check_payment_status(reference):
    """Check Pesapay payment status by reference"""
    try:
        current_user_id = get_jwt_identity()
        
        print(f"🔍 Checking payment status for reference: {reference}")
        print(f"👤 User ID: {current_user_id}")
        
        # Find the transaction by reference
        transaction = Transaction.query.filter_by(transaction_id=reference).first()
        
        if not transaction:
            print(f"❌ Transaction not found for reference: {reference}")
            return jsonify({
                'success': False,
                'error': 'Transaction not found'
            }), 404
        
        # Verify the transaction belongs to the current user
        if transaction.sender_id != current_user_id:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403
        
        # Optionally, you can also check with Pesapay API for latest status
        status_from_pesapay = check_pesapay_transaction_status(reference)
        
        print(f"✅ Transaction found: {transaction.transaction_id}")
        print(f"📊 Transaction status: {transaction.status}")
        print(f"📊 Pesapay status: {status_from_pesapay}")
        
        return jsonify({
            'success': True,
            'status': transaction.status,
            'pesapay_status': status_from_pesapay,
            'transaction': transaction.to_dict(),
            'message': f'Transaction is {transaction.status}'
        }), 200
        
    except Exception as e:
        print(f"❌ Error checking payment status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def check_pesapay_transaction_status(reference):
    """
    Check transaction status directly from Pesapay API
    """
    try:
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        signature = generate_pesapay_signature(
            PESAPAY_API_KEY,
            PESAPAY_API_SECRET,
            PESAPAY_MERCHANT_ID,
            "0.00",  # Amount not needed for status check
            "USD",
            reference,
            timestamp
        )
        
        payload = {
            "merchant_id": PESAPAY_MERCHANT_ID,
            "api_key": PESAPAY_API_KEY,
            "signature": signature,
            "timestamp": timestamp,
            "reference": reference
        }
        
        status_url = f"{PESAPAY_BASE_URL}/v1/payments/status"
        response = requests.post(status_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('data', {}).get('status', 'unknown')
        else:
            return 'api_error'
            
    except Exception as e:
        print(f"❌ Error checking Pesapay status: {str(e)}")
        return 'check_failed'

# Keep the existing wallet routes (get_wallet, add_funds) unchanged
@bp.route('', methods=['GET'])
@jwt_required()
def get_wallet():
    """Get user's wallet"""
    try:
        current_user_id = get_jwt_identity()
        wallet = Wallet.query.filter_by(user_id=current_user_id).first()

        if not wallet:
            return jsonify({'error': 'Wallet not found'}), 404

        return jsonify({
            'success': True,
            'wallet': wallet.to_dict()
        }), 200

    except Exception as e:
        print(f"Error in get_wallet: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/add-funds', methods=['POST'])
@jwt_required()
def add_funds():
    """Add funds to wallet (manual/admin)"""
    try:
        current_user_id = get_jwt_identity()
        wallet = Wallet.query.filter_by(user_id=current_user_id).first()

        if not wallet:
            return jsonify({'error': 'Wallet not found'}), 404

        data = request.get_json()
        amount = float(data.get('amount', 0))

        if amount <= 0:
            return jsonify({'error': 'Invalid amount'}), 400
        
        if amount > 10000:
            return jsonify({'error': 'Maximum amount is $10,000'}), 400

        # Add funds to wallet
        wallet.balance = wallet.balance + amount
        wallet.updated_at = datetime.utcnow()

        # Create transaction record
        transaction = Transaction(
            transaction_id=generate_unique_id('TXN'),
            sender_id=current_user_id,
            receiver_id=current_user_id,
            amount=amount,
            fee=0.0,
            total_amount=amount,
            type='add_funds',
            status='completed',
            note=data.get('note', 'Added funds to wallet')
        )

        db.session.add(transaction)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Funds added successfully',
            'wallet': wallet.to_dict(),
            'transaction': transaction.to_dict()
        }), 200

    except ValueError:
        return jsonify({'error': 'Invalid amount format'}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Error in add_funds: {str(e)}")
        return jsonify({'error': str(e)}), 500