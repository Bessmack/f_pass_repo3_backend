from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from datetime import timedelta
import os

# Initialize extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()

def create_app(config_name='development'):
    app = Flask(__name__)
    
    # Handle Render PostgreSQL database URL
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Fix for Render's PostgreSQL URL format
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        print("✅ Using PostgreSQL database from DATABASE_URL")
    else:
        # Fallback for local development
        from config import config
        app.config.from_object(config[config_name])
        print(f"✅ Using database from config: {config_name}")
    
    # Load other configuration from config.py
    from config import config
    if not database_url:  # Only use config file if no DATABASE_URL
        app.config.from_object(config[config_name])
    
    # Set other essential configs
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', app.config.get('SECRET_KEY', 'fallback-secret'))
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', app.config.get('JWT_SECRET_KEY', 'fallback-jwt-secret'))
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize CORS
    CORS(app, 
         resources={r"/api/*": {
             "origins": os.environ.get('CORS_ORIGINS', 'http://localhost:5173').split(','),
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization"],
             "expose_headers": ["Content-Type", "Authorization"],
             "supports_credentials": True,
             "max_age": 3600
         }})
    
    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    
    # Register blueprints (your existing code)
    from routes import (
        auth_routes, user_routes, wallet_routes, transaction_routes, 
        beneficiary_routes, admin_routes, receipt_routes, notification_routes
    )

    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(user_routes.bp)
    app.register_blueprint(wallet_routes.bp)
    app.register_blueprint(transaction_routes.bp)
    app.register_blueprint(beneficiary_routes.bp)
    app.register_blueprint(admin_routes.bp)
    app.register_blueprint(receipt_routes.bp)
    app.register_blueprint(notification_routes.bp)
    
    # Add health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return {'status': 'healthy', 'message': 'API is running'}, 200
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return {'error': 'Internal server error'}, 500
    
    # Create tables
    with app.app_context():
        try:
            db.create_all()
            from utils.seed import create_default_admin
            create_default_admin()
            print("✅ Database tables created successfully")
        except Exception as e:
            print(f"❌ Database error: {str(e)}")
            # Don't raise error, just log it
    
    return app