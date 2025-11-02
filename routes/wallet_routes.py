import requests
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from __init__ import db
from models import Wallet, Transaction, User
from utils.helpers import generate_unique_id
import os

bp = Blueprint('wallet', __name__, url_prefix='/api/wallet')

# M-Pesa Config (Daraja Sandbox/Test)
MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE")
MPESA_PASSKEY = os.getenv("MPESA_PASSKEY")
CALLBACK_URL = os.getenv("CALLBACK_URL")

def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(url, auth=(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET))
    data = response.json()
    print("🔑 Access Token Response:", data)
    return data.get("access_token")

@bp.route('/deposit', methods=['POST'])
@jwt_required()
def mpesa_deposit():
    """Initiate M-Pesa STK Push"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        print(f"📥 Received data: {data}")
        
        amount = float(data.get('amount'))
        phone = data.get('phone')
        
        print(f"💰 Amount: {amount}, 📱 Phone: {phone}, 👤 User ID: {current_user_id}")

        if amount <= 0:
            return jsonify({'error': 'Invalid amount'}), 400

        # Get user's wallet
        wallet = Wallet.query.filter_by(user_id=current_user_id).first()
        if not wallet:
            return jsonify({'error': 'Wallet not found'}), 404

        access_token = get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        password = f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}".encode("utf-8")
        import base64
        password = base64.b64encode(password).decode("utf-8")

        stk_push_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        
        # Use user_id as AccountReference to track who initiated the transaction
        payload = {
            "BusinessShortCode": MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone,
            "PartyB": MPESA_SHORTCODE,
            "PhoneNumber": phone,
            "CallBackURL": CALLBACK_URL,
            "AccountReference": str(current_user_id),  # Store user_id here
            "TransactionDesc": "Deposit to Wallet"
        }

        res = requests.post(stk_push_url, json=payload, headers=headers)
        print("🔍 Raw STK Push Response Text:", res.text)
        print("🔍 HTTP Status Code:", res.status_code)

        try:
            response_data = res.json()
        except Exception as e:
            print("❌ JSON decode failed:", str(e))
            return jsonify({'error': 'Invalid response from Safaricom', 'raw': res.text}), 500
        
        print(f"🔍 STK Push Response: {response_data}")
        print(f"🔍 HTTP Status: {res.status_code}")

        if "ResponseCode" in response_data and response_data["ResponseCode"] == "0":
            # Create pending transaction record
            checkout_request_id = response_data.get("CheckoutRequestID")
            merchant_request_id = response_data.get("MerchantRequestID")
            
            pending_transaction = Transaction(
                transaction_id=generate_unique_id('TXN'),
                sender_id=current_user_id,
                receiver_id=current_user_id,
                amount=amount,
                fee=0.0,
                total_amount=amount,
                type='mpesa_deposit',
                status='pending',
                note=f'M-Pesa deposit pending - {merchant_request_id}',
                merchant_request_id=merchant_request_id,  # Store for callback matching
                checkout_request_id=checkout_request_id
            )
            
            db.session.add(pending_transaction)
            db.session.commit()
            
            print(f"✅ Pending transaction created: {pending_transaction.transaction_id}")
            
            return jsonify({
                'success': True,
                'message': 'STK push initiated. Enter your M-Pesa PIN to complete transaction.',
                'transaction_id': pending_transaction.transaction_id,
                'checkout_request_id': checkout_request_id
            }), 200
        else:
            return jsonify({'error': response_data}), 400

    except Exception as e:
        print(f"Error in mpesa_deposit: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/mpesa-callback', methods=['POST'])
def mpesa_callback():
    """Handle M-Pesa Callback from Safaricom"""
    try:
        data = request.get_json()
        print(f"📥 M-Pesa Callback received: {data}")
        
        result = data.get('Body', {}).get('stkCallback', {})
        
        merchant_request_id = result.get('MerchantRequestID')
        checkout_request_id = result.get('CheckoutRequestID')
        result_code = result.get('ResultCode')
        result_desc = result.get('ResultDesc')
        
        print(f"🔍 Callback Details:")
        print(f"   MerchantRequestID: {merchant_request_id}")
        print(f"   CheckoutRequestID: {checkout_request_id}")
        print(f"   ResultCode: {result_code}")
        print(f"   ResultDesc: {result_desc}")

        # Find the pending transaction using MerchantRequestID
        transaction = Transaction.query.filter_by(
            merchant_request_id=merchant_request_id,
            status='pending'
        ).first()

        if not transaction:
            print(f"⚠️ No pending transaction found for MerchantRequestID: {merchant_request_id}")
            # Still return success to Safaricom
            return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200

        # Get the user's wallet using the transaction's sender_id
        wallet = Wallet.query.filter_by(user_id=transaction.sender_id).first()
        
        if not wallet:
            print(f"❌ Wallet not found for user_id: {transaction.sender_id}")
            transaction.status = 'failed'
            transaction.note = 'Wallet not found'
            db.session.commit()
            return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200

        if result_code == 0:  # Success
            print("✅ Payment successful!")
            
            metadata = result.get('CallbackMetadata', {}).get('Item', [])
            amount = next((x['Value'] for x in metadata if x['Name'] == 'Amount'), 0)
            mpesa_receipt = next((x['Value'] for x in metadata if x['Name'] == 'MpesaReceiptNumber'), None)
            phone = next((x['Value'] for x in metadata if x['Name'] == 'PhoneNumber'), None)
            
            print(f"💰 Amount: {amount}")
            print(f"🧾 M-Pesa Receipt: {mpesa_receipt}")
            print(f"📱 Phone: {phone}")
            
            # Update wallet balance
            wallet.balance += float(amount)
            wallet.updated_at = datetime.utcnow()
            
            # Update transaction status
            transaction.status = 'completed'
            transaction.note = f'M-Pesa deposit successful - Receipt: {mpesa_receipt}'
            transaction.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            print(f"✅ Wallet updated! New balance: ${wallet.balance}")
            print(f"✅ Transaction {transaction.transaction_id} marked as completed")
            
        else:
            # Payment failed or cancelled
            print(f"❌ Payment failed: {result_desc}")
            
            transaction.status = 'failed'
            transaction.note = f'M-Pesa deposit failed - {result_desc}'
            transaction.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            print(f"❌ Transaction {transaction.transaction_id} marked as failed")

        return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ Callback error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"ResultCode": 1, "ResultDesc": "Error"}), 500


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
    """Add funds to wallet"""
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