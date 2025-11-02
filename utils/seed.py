"""
Database seeding utilities
"""
from __init__ import db
from models import User, Wallet
from utils.helpers import generate_unique_id


def create_default_admin():
    """Create default admin user if not exists"""
    admin = User.query.filter_by(email='admin@example.com').first()
    
    if not admin:
        admin = User(
            first_name='Admin',
            last_name='User',
            email='admin@example.com',
            role='admin',
            status='active',
            phone='+1234567890',
            country='United States'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.flush()
        
        # Create admin wallet
        admin_wallet = Wallet(
            user_id=admin.id,
            wallet_id=generate_unique_id('QP'),
            balance=10000.0
        )
        db.session.add(admin_wallet)
        
        try:
            db.session.commit()
            print("✅ Default admin user created:")
            print("   Email: admin@example.com")
            print("   Password: admin123")
            print("   Wallet Balance: $10,000.00")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Failed to create admin user: {str(e)}")
    else:
        print("ℹ️  Default admin user already exists")


def create_test_users():
    """Create test users for development"""
    test_users = [
        {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'password': 'password123',
            'balance': 500.0
        },
        {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'jane@example.com',
            'password': 'password123',
            'balance': 750.0
        }
    ]
    
    for user_data in test_users:
        existing_user = User.query.filter_by(email=user_data['email']).first()
        
        if not existing_user:
            user = User(
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                email=user_data['email'],
                role='user',
                status='active'
            )
            user.set_password(user_data['password'])
            db.session.add(user)
            db.session.flush()
            
            # Create wallet
            wallet = Wallet(
                user_id=user.id,
                wallet_id=generate_unique_id('QP'),
                balance=user_data['balance']
            )
            db.session.add(wallet)
    
    try:
        db.session.commit()
        print("✅ Test users created successfully")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Failed to create test users: {str(e)}")