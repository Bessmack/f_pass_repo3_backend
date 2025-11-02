# Money Transfer Backend API

A Flask-based REST API for a money transfer application with user authentication, wallet management, and transaction processing.

## Features

- 🔐 User Authentication - JWT-based authentication with registration and login
- 💰 Wallet Management - Digital wallet system for each user
- 💸 Money Transfers - Send money between users with transaction fees
- 👥 Beneficiary Management - Save and manage frequent recipients
- 📊 Admin Dashboard - Administrative functions for user and transaction management
- 🔒 Security - Password hashing, JWT tokens, and role-based access control

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment (recommended)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run the application:
```bash
python app.py
```

The API will be available at `http://localhost:5000`

## Default Admin Credentials

- Email: admin@example.com
- Password: admin123

**⚠️ Important: Change these credentials immediately after first login in production!**

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user (requires authentication)

### User Profile
- `GET /api/users/profile` - Get user profile
- `PUT /api/users/profile` - Update user profile
- `POST /api/users/change-password` - Change password

### Wallet
- `GET /api/wallet` - Get user wallet
- `POST /api/wallet/add-funds` - Add funds to wallet

### Transactions
- `POST /api/transactions/send` - Send money to another user
- `GET /api/transactions` - Get user transactions
- `GET /api/transactions/<id>` - Get transaction details

### Beneficiaries
- `GET /api/beneficiaries` - Get all beneficiaries
- `POST /api/beneficiaries` - Add new beneficiary
- `GET /api/beneficiaries/<id>` - Get beneficiary details
- `PUT /api/beneficiaries/<id>` - Update beneficiary
- `DELETE /api/beneficiaries/<id>` - Delete beneficiary

### Admin
- `GET /api/admin/users` - Get all users (admin only)
- `GET /api/admin/stats` - Get system statistics (admin only)

## Transaction Fees

- Transaction fee: 0.5% of amount
- Minimum transaction: $1.00
- Maximum transaction: $10,000.00

## Security Features

- Password hashing with Bcrypt
- JWT token-based authentication
- Role-based access control (User/Admin)
- CORS protection
- SQL injection prevention via ORM

## Database Schema

### Users Table
- id, first_name, last_name, email, password_hash
- phone, country, address, city, zip_code
- role, status, created_at, updated_at

### Wallets Table
- id, user_id, wallet_id, balance, currency
- status, created_at, updated_at

### Transactions Table
- id, transaction_id, sender_id, receiver_id
- amount, fee, total_amount, type, status
- note, created_at

### Beneficiaries Table
- id, user_id, name, email, phone
- relationship, beneficiary_user_id, created_at

## Testing

You can test the API using:
- Postman
- cURL
- Python requests library
- Frontend application

Example cURL request:
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}'
```

## Production Deployment

For production deployment with Gunicorn:
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Production Checklist
- ✅ Change default admin credentials
- ✅ Set strong SECRET_KEY and JWT_SECRET_KEY
- ✅ Use PostgreSQL instead of SQLite
- ✅ Enable HTTPS
- ✅ Set FLASK_ENV=production
- ✅ Configure proper CORS origins
- ✅ Set up proper logging
- ✅ Use environment variables for sensitive data

## License

MIT License