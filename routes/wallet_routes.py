import requests
import json
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from __init__ import db
from models import Wallet, Transaction, User
from utils.helpers import generate_unique_id
import os
from utils.notification_helpers import send_deposit_notification
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

bp = Blueprint('wallet', __name__, url_prefix='/api/wallet')

# Pesapal Configuration - Keep your original variable names
PESAPAY_BASE_URL = os.getenv("PESAPAY_BASE_URL")
PESAPAY_API_KEY = os.getenv("PESAPAY_API_KEY")
PESAPAY_API_SECRET = os.getenv("PESAPAY_API_SECRET")
PESAPAY_IPN_ID = os.getenv("PESAPAY_IPN_ID")
PESAPAY_CALLBACK_URL = os.getenv("PESAPAY_CALLBACK_URL")

# Token cache to avoid requesting new token on every request
_token_cache = {'token': None, 'expires_at': None}

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

def get_pesapal_token():
    """
    Get OAuth access token from Pesapal API
    Caches token to avoid unnecessary API calls (tokens expire after ~5 minutes)
    """
    # Return cached token if still valid
    if _token_cache['token'] and _token_cache['expires_at'] and _token_cache['expires_at'] > datetime.utcnow():
        return _token_cache['token']
    
    try:
        auth_url = f"{PESAPAY_BASE_URL}/Auth/RequestToken"
        
        payload = {
            "consumer_key": PESAPAY_API_KEY,
            "consumer_secret": PESAPAY_API_SECRET
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        print(f"🔑 Requesting new Pesapal token from: {auth_url}")
        
        response = requests.post(auth_url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            token = data.get('token')
            
            if token:
                # Cache token for 4 minutes (expires after 5)
                _token_cache['token'] = token
                _token_cache['expires_at'] = datetime.utcnow() + timedelta(minutes=4)
                print(f"✅ Token acquired and cached")
                return token
            else:
                raise Exception("Token not found in response")
        else:
            raise Exception(f"Token request failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Failed to get Pesapal token: {str(e)}")
        raise

@bp.route('/deposit', methods=['POST'])
@jwt_required()
def pesapay_deposit():
    """
    Initiate Pesapal payment
    Expected payload: { "amount": 100, "phone": "254712345678", "email": "user@example.com", "currency": "KES" }
    """
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        print(f"📥 Received Pesapal deposit request: {data}")
        
        amount = float(data.get('amount', 0))
        phone = data.get('phone')
        email = data.get('email', '')
        currency = data.get('currency', 'KES')
        
        print(f"💰 Amount: {amount}, 📱 Phone: {phone}, 📧 Email: {email}, 👤 User ID: {current_user_id}")

        if amount <= 0:
            return jsonify({'error': 'Invalid amount'}), 400

        # Get user's wallet
        wallet = Wallet.query.filter_by(user_id=current_user_id).first()
        if not wallet:
            return jsonify({'error': 'Wallet not found'}), 404

        # Get OAuth token from Pesapal
        token = get_pesapal_token()
        
        # Generate unique transaction reference (merchant reference)
        transaction_reference = generate_unique_id('PESAPAY')
        
        # Prepare Pesapal v3 payment request
        payload = {
            "id": transaction_reference,
            "currency": currency,
            "amount": amount,
            "description": f"Wallet deposit - {transaction_reference}",
            "callback_url": PESAPAY_CALLBACK_URL,
            "notification_id": PESAPAY_IPN_ID,
            "billing_address": {
                "email_address": email,
                "phone_number": phone,
                "country_code": "KE",
                "first_name": "",
                "middle_name": "",
                "last_name": "",
                "line_1": "",
                "line_2": "",
                "city": "",
                "state": "",
                "postal_code": "",
                "zip_code": ""
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}"
        }

        payment_url = f"{PESAPAY_BASE_URL}/Transactions/SubmitOrderRequest"
        
        print(f"🔗 Sending request to Pesapal: {payment_url}")
        print(f"📦 Payload: {json.dumps(payload, indent=2)}")

        response = requests.post(payment_url, json=payload, headers=headers, timeout=30)
        
        print(f"🔍 Pesapal Response Status: {response.status_code}")
        print(f"🔍 Pesapal Response Text: {response.text}")

        try:
            response_data = response.json()
        except Exception as e:
            print(f"❌ JSON decode failed: {str(e)}")
            return jsonify({'error': 'Invalid response from Pesapal', 'raw': response.text}), 500

        if response.status_code == 200 and response_data.get('status') == '200':
            order_tracking_id = response_data.get('order_tracking_id')
            redirect_url = response_data.get('redirect_url')
            
            # Create pending transaction record
            pending_transaction = Transaction(
                transaction_id=transaction_reference,
                sender_id=current_user_id,
                receiver_id=current_user_id,
                amount=amount,
                fee=0.0,
                total_amount=amount,
                type='pesapay_deposit',
                status='pending',
                note=f'Pesapal deposit pending - Ref: {transaction_reference}',
                merchant_request_id=order_tracking_id,
                checkout_request_id=transaction_reference
            )
            
            db.session.add(pending_transaction)
            db.session.commit()
            
            print(f"✅ Pending transaction created: {pending_transaction.transaction_id}")
            
            return jsonify({
                'success': True,
                'message': 'Payment initiated successfully',
                'transaction_id': pending_transaction.transaction_id,
                'order_tracking_id': order_tracking_id,
                'redirect_url': redirect_url,
                'reference': transaction_reference
            }), 200
        else:
            error_message = response_data.get('message', 'Payment initiation failed')
            error_details = response_data.get('error', {})
            print(f"❌ Pesapal error: {error_message}")
            return jsonify({
                'error': error_message,
                'details': error_details
            }), 400

    except requests.exceptions.Timeout:
        print("❌ Pesapal API timeout")
        return jsonify({'error': 'Payment service timeout. Please try again.'}), 408
    except requests.exceptions.ConnectionError:
        print("❌ Pesapal API connection error")
        return jsonify({'error': 'Cannot connect to payment service. Please try again.'}), 503
    except Exception as e:
        print(f"❌ Error in pesapay_deposit: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@bp.route('/pesapay-callback', methods=['POST', 'GET'])
@limiter.limit("10 per minute")  # More restrictive for IPN
def pesapay_callback():
    """
    Handle Pesapal IPN (Instant Payment Notification)
    Pesapal sends: OrderTrackingId and OrderMerchantReference as query parameters
    """
    try:
        # Pesapal sends these as query parameters
        order_tracking_id = request.args.get('OrderTrackingId')
        merchant_reference = request.args.get('OrderMerchantReference')
        
        print(f"📥 Pesapal IPN received:")
        print(f"   OrderTrackingId: {order_tracking_id}")
        print(f"   OrderMerchantReference: {merchant_reference}")
        
        if not order_tracking_id or not merchant_reference:
            print("❌ Missing required parameters")
            return jsonify({"status": "error", "message": "Missing parameters"}), 400

        # Get transaction status from Pesapal API
        token = get_pesapal_token()
        status_url = f"{PESAPAY_BASE_URL}/Transactions/GetTransactionStatus"
        
        params = {"orderTrackingId": order_tracking_id}
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        print(f"🔍 Checking transaction status with Pesapal...")
        response = requests.get(status_url, params=params, headers=headers, timeout=30)
        
        print(f"🔍 Status Response: {response.status_code}")
        print(f"🔍 Status Data: {response.text}")
        
        if response.status_code != 200:
            print(f"❌ Failed to get status from Pesapal")
            return jsonify({"status": "error", "message": "Failed to verify payment"}), 500
            
        status_data = response.json()
        
        # FIX: Handle both payment_status_code and payment_status_description
        payment_status_code = status_data.get('payment_status_code')
        payment_status_description = status_data.get('payment_status_description', '').upper()
        amount = float(status_data.get('amount', 0))
        currency = status_data.get('currency')
        payment_method = status_data.get('payment_method')
        status_code = status_data.get('status_code')  # This might be the actual status code
        
        print(f"🔍 Payment Details:")
        print(f"   Status Code: {payment_status_code}")
        print(f"   Status Description: {payment_status_description}")
        print(f"   Status Code (alt): {status_code}")
        print(f"   Amount: {amount} {currency}")
        print(f"   Payment Method: {payment_method}")

        # Find the transaction by transaction_id (which is the merchant_reference)
        transaction = Transaction.query.filter_by(
            transaction_id=merchant_reference
        ).first()

        if not transaction:
            print(f"⚠️ No transaction found for reference: {merchant_reference}")
            # Still return 200 to Pesapal so they don't retry
            return jsonify({"status": "ok", "message": "Transaction not found or already processed"}), 200

        # Get the user's wallet
        wallet = Wallet.query.filter_by(user_id=transaction.sender_id).first()
        
        if not wallet:
            print(f"❌ Wallet not found for user_id: {transaction.sender_id}")
            transaction.status = 'failed'
            transaction.note = 'Wallet not found'
            transaction.updated_at = datetime.utcnow()
            db.session.commit()
            return jsonify({"status": "error", "message": "Wallet not found"}), 404

        # FIX: Determine payment status using multiple fields
        is_completed = False
        is_failed = False
        
        # Check using status_code (which appears to be 1 for completed)
        if status_code == 1:
            is_completed = True
        elif status_code in [2, 3]:
            is_failed = True
        
        # Also check payment_status_description as backup
        if payment_status_description == 'COMPLETED':
            is_completed = True
        elif payment_status_description in ['FAILED', 'CANCELLED', 'INVALID']:
            is_failed = True
        
        # Process based on payment status
        if is_completed:
            print("✅ Payment successful!")
            
            # Only update if not already completed
            if transaction.status != 'completed':
                # Update wallet balance
                wallet.balance += amount
                wallet.updated_at = datetime.utcnow()
                
                # Update transaction status
                transaction.status = 'completed'
                transaction.amount = amount  # Update with actual amount from Pesapal
                transaction.note = f'Pesapal deposit successful - TXN: {order_tracking_id} via {payment_method}'
                transaction.merchant_request_id = order_tracking_id
                transaction.updated_at = datetime.utcnow()
                
                db.session.commit()
                
                # Send success notification
                send_deposit_notification(wallet, amount, status='success')
                
                print(f"✅ Wallet updated! New balance: {wallet.balance}")
                print(f"✅ Transaction {transaction.transaction_id} marked as completed")
            else:
                print("ℹ️ Transaction already completed")
            
        elif is_failed:
            print(f"❌ Payment failed")
            
            if transaction.status != 'failed':
                transaction.status = 'failed'
                transaction.note = f'Pesapal deposit failed - Status: {payment_status_description}, Method: {payment_method}'
                transaction.merchant_request_id = order_tracking_id
                transaction.updated_at = datetime.utcnow()
                
                db.session.commit()
                
                # Send failure notification
                send_deposit_notification(wallet, amount, status='failed')
                
                print(f"❌ Transaction {transaction.transaction_id} marked as failed")
            else:
                print("ℹ️ Transaction already marked as failed")
        
        else:
            print(f"⚠️ Payment still processing - Status: {payment_status_description}")
            # Update transaction note with current status but don't change status
            transaction.note = f'Payment processing - {payment_status_description}'
            transaction.merchant_request_id = order_tracking_id
            transaction.updated_at = datetime.utcnow()
            db.session.commit()

        # Always return 200 to Pesapal to acknowledge receipt
        return jsonify({"status": "ok", "message": "Callback processed"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ Callback error: {str(e)}")
        import traceback
        traceback.print_exc()
        # Still return 200 to prevent Pesapal retries
        return jsonify({"status": "error", "message": "Internal server error"}), 200

@bp.route('/payment-status/<reference>', methods=['GET'])
@jwt_required()
def check_payment_status(reference):
    """
    Check Pesapal payment status by merchant reference
    Frontend can poll this endpoint to check payment status
    """
    try:
        current_user_id = get_jwt_identity()
        
        print(f"🔍 Checking payment status for reference: {reference}")
        print(f"👤 User ID: {current_user_id}")
        
        # Find the transaction by transaction_id
        transaction = Transaction.query.filter_by(transaction_id=reference).first()
        
        if not transaction:
            print(f"❌ Transaction not found for reference: {reference}")
            return jsonify({
                'success': False,
                'error': 'Transaction not found'
            }), 404
        
        # Verify the transaction belongs to the current user
        if str(transaction.sender_id) != str(current_user_id):
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403
        
        # If transaction is still pending and we have order_tracking_id, check with Pesapal
        pesapal_status = None
        if transaction.status == 'pending' and transaction.merchant_request_id:
            try:
                pesapal_status = check_pesapal_transaction_status(transaction.merchant_request_id)
                
                # If Pesapal shows completed but our DB shows pending, update it
                if pesapal_status == 1 and transaction.status == 'pending':
                    wallet = Wallet.query.filter_by(user_id=current_user_id).first()
                    if wallet:
                        wallet.balance += transaction.amount
                        wallet.updated_at = datetime.utcnow()
                        
                        transaction.status = 'completed'
                        transaction.note = f'Pesapal deposit completed (verified via status check)'
                        transaction.updated_at = datetime.utcnow()
                        
                        db.session.commit()
                        
                        send_deposit_notification(wallet, transaction.amount, status='success')
                        print(f"✅ Transaction updated to completed via status check")
                
                # If Pesapal shows failed but our DB shows pending, update it
                elif pesapal_status in [2, 3] and transaction.status == 'pending':
                    transaction.status = 'failed'
                    transaction.note = f'Pesapal deposit failed (verified via status check)'
                    transaction.updated_at = datetime.utcnow()
                    db.session.commit()
                    print(f"❌ Transaction updated to failed via status check")
                    
            except Exception as e:
                print(f"⚠️ Could not check Pesapal status: {str(e)}")
        
        print(f"✅ Transaction found: {transaction.transaction_id}")
        print(f"📊 Transaction status: {transaction.status}")
        if pesapal_status is not None:
            print(f"📊 Pesapal status code: {pesapal_status}")
        
        return jsonify({
            'success': True,
            'status': transaction.status,
            'pesapal_status_code': pesapal_status,
            'transaction': transaction.to_dict(),
            'message': f'Transaction is {transaction.status}'
        }), 200
        
    except Exception as e:
        print(f"❌ Error checking payment status: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def check_pesapal_transaction_status(order_tracking_id):
    """
    Check transaction status directly from Pesapal API
    Returns payment_status_code: 0=invalid, 1=completed, 2=failed, 3=reversed
    """
    try:
        token = get_pesapal_token()
        status_url = f"{PESAPAY_BASE_URL}/Transactions/GetTransactionStatus"
        
        params = {"orderTrackingId": order_tracking_id}
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        response = requests.get(status_url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Use status_code instead of payment_status_code
            status_code = data.get('status_code')
            payment_status_description = data.get('payment_status_description', '').upper()
            
            # Determine status based on multiple fields
            if status_code == 1 or payment_status_description == 'COMPLETED':
                return 1  # COMPLETED
            elif status_code in [2, 3] or payment_status_description in ['FAILED', 'CANCELLED', 'INVALID']:
                return 2  # FAILED
            else:
                return 0  # INVALID or unknown
        else:
            print(f"❌ Status check failed: {response.status_code} - {response.text}")
            return 0
            
    except Exception as e:
        print(f"❌ Error checking Pesapal status: {str(e)}")
        return 0

# Keep your existing wallet routes unchanged
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
    
@bp.route('/chart-data', methods=['GET'])
@jwt_required()
def get_chart_data():
    """Get chart data for balance overview"""
    try:
        current_user_id = get_jwt_identity()
        time_period = request.args.get('period', 'monthly')  # weekly, monthly, yearly
        
        print(f"📊 Getting chart data for user {current_user_id}, period: {time_period}")
        
        # Get user's wallet
        wallet = Wallet.query.filter_by(user_id=current_user_id).first()
        if not wallet:
            return jsonify({'error': 'Wallet not found'}), 404
        
        # Calculate date range based on time period
        end_date = datetime.utcnow()
        if time_period == 'weekly':
            start_date = end_date - timedelta(days=7)
            group_format = '%a'  # Mon, Tue, etc.
        elif time_period == 'monthly':
            start_date = end_date - timedelta(days=30)
            group_format = 'Week %U'  # Week 1, Week 2, etc.
        else:  # yearly
            start_date = end_date - timedelta(days=365)
            group_format = '%b'  # Jan, Feb, etc.
        
        # Get transactions for the period
        transactions = Transaction.query.filter(
            Transaction.created_at >= start_date,
            Transaction.created_at <= end_date,
            db.or_(
                Transaction.sender_id == current_user_id,
                Transaction.receiver_id == current_user_id
            )
        ).order_by(Transaction.created_at.asc()).all()
        
        # Calculate running balance for the period
        chart_data = calculate_running_balance(transactions, current_user_id, wallet.balance, time_period, group_format)
        
        print(f"✅ Generated {len(chart_data)} data points for {time_period} chart")
        
        return jsonify({
            'success': True,
            'period': time_period,
            'data': chart_data
        }), 200
        
    except Exception as e:
        print(f"❌ Error getting chart data: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

def calculate_running_balance(transactions, user_id, current_balance, time_period, group_format):
    """Calculate running balance for chart data"""
    if not transactions:
        # Return current balance if no transactions
        return [{'label': 'Current', 'balance': float(current_balance)}]
    
    # Sort transactions by date
    transactions.sort(key=lambda x: x.created_at)
    
    # Initialize balance history
    balance_history = {}
    running_balance = current_balance
    
    # Work backwards from current balance
    for transaction in reversed(transactions):
        # Determine if user sent or received money
        if transaction.sender_id == user_id:
            # User sent money - add back to balance
            running_balance += float(transaction.amount + transaction.fee)
        elif transaction.receiver_id == user_id:
            # User received money - subtract from balance
            running_balance -= float(transaction.amount)
        
        # Group by time period
        if time_period == 'weekly':
            date_key = transaction.created_at.strftime('%a')
        elif time_period == 'monthly':
            week_num = (transaction.created_at.day - 1) // 7 + 1
            date_key = f"Week {week_num}"
        else:  # yearly
            date_key = transaction.created_at.strftime('%b')
        
        # Store the earliest balance for each period
        if date_key not in balance_history:
            balance_history[date_key] = running_balance
    
    # Convert to list format for chart
    chart_data = []
    for label, balance in balance_history.items():
        chart_data.append({
            'label': label,
            'balance': float(balance)
        })
    
    # Sort by label for proper ordering
    if time_period == 'weekly':
        day_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        chart_data.sort(key=lambda x: day_order.index(x['label']) if x['label'] in day_order else 7)
    elif time_period == 'monthly':
        chart_data.sort(key=lambda x: int(x['label'].split(' ')[1]))
    else:  # yearly
        month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        chart_data.sort(key=lambda x: month_order.index(x['label']) if x['label'] in month_order else 12)
    
    return chart_data