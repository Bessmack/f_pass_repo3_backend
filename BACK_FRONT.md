# Complete Money Transfer App - Setup & Installation Guide

## 📁 Backend Structure (Complete)

```
backend/
├── __init__.py                 ✅ Provided
├── config.py                   ✅ Provided
├── run.py                      ✅ Provided
├── .env                        ✅ Provided
├── requirements.txt            ✅ Provided
├── models/
│   ├── __init__.py            ✅ Provided
│   ├── user.py                ✅ Provided
│   ├── wallet.py              ✅ Provided
│   ├── transaction.py         ✅ Provided
│   └── beneficiary.py         ✅ Provided
├── routes/
│   ├── __init__.py            ✅ Provided
│   ├── auth_routes.py         ✅ Provided
│   ├── user_routes.py         ✅ Provided
│   ├── wallet_routes.py       ✅ Provided
│   ├── transaction_routes.py  ✅ Provided
│   ├── beneficiary_routes.py  ✅ Provided
│   └── admin_routes.py        ✅ Provided
└── utils/
    ├── __init__.py            ✅ Provided
    ├── helpers.py             ✅ Provided
    ├── decorators.py          ✅ Provided
    └── seed.py                ✅ Provided
```

## 🚀 Backend Setup Instructions

### Step 1: Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Step 2: Create .env File

Create `.env` file in backend root with the provided content.

### Step 3: Run Backend

```bash
python run.py
```

Backend will start on: http://localhost:5000

## 📁 Frontend Structure

```
frontend/
├── src/
│   ├── App.jsx                     ✅ Already provided
│   ├── App.css                     ✅ Already provided
│   ├── main.jsx                    ✅ Already provided
│   ├── services/
│   │   └── api.js                  ✅ Just provided (use fetch)
│   ├── context/
│   │   └── AuthContext.jsx         ✅ Previously provided
│   ├── components/
│   │   ├── Navbar.jsx              ✅ Already provided
│   │   ├── UserTopNavbar.jsx       ✅ Already provided
│   │   ├── UserBottomNavbar.jsx    ✅ Already provided
│   │   ├── Footer.jsx              ✅ Already provided
│   │   ├── Stats.jsx               ✅ Already provided
│   │   ├── AdminDashboard.jsx      ✅ Already provided
│   │   ├── AdminOverview.jsx       ✅ Already provided
│   │   ├── AdminTransactions.jsx   ✅ Already provided
│   │   ├── AdminUsers.jsx          ✅ Already provided
│   │   └── AdminWallets.jsx        ✅ Already provided
│   └── pages/
│       ├── Login.jsx               ✅ Previously corrected
│       ├── Logout.jsx              ✅ Already provided
│       ├── Profile.jsx             ✅ Already provided
│       ├── UserHomePage.jsx        ✅ Previously corrected
│       ├── UserAddFunds.jsx        ✅ Previously corrected
│       ├── UserSendMoney.jsx       ✅ Already provided
│       ├── UserHistory.jsx         ✅ Already provided
│       ├── UserWallet.jsx          ✅ Already provided
│       ├── UserContacts.jsx        ✅ Already provided
│       ├── UserProfile.jsx         ✅ Already provided
│       └── AddBeneficiary.jsx      ✅ Already provided
├── .env                            ✅ Already provided
├── index.html                      ✅ Already provided
├── package.json                    (Create if needed)
└── vite.config.js                  (Create if needed)
```

## 🔧 Frontend Setup Instructions

### Step 1: Install Dependencies

```bash
cd frontend
npm install react react-dom react-router-dom
npm install -D vite @vitejs/plugin-react
```

### Step 2: Replace api.js

Replace `src/services/api.js` with the fetch-based version I just provided above.

### Step 3: Update Other Service Files

Since we're now using the main `api.js` file, you can delete these old service files:
- `src/services/authService.js`
- `src/services/walletService.js`
- `src/services/transactionService.js`
- `src/services/userService.js`
- `src/services/adminService.js`
- `src/services/beneficiaryService.js`

### Step 4: Update Imports in Components

Update all components to use the new API:

**Example for UserHomePage.jsx:**
```javascript
import { walletAPI, transactionAPI } from '../services/api';

// Instead of:
// import walletService from '../services/walletService';

// Use:
const fetchWallet = async () => {
  const response = await walletAPI.getWallet();
  return response.wallet;
};
```

## 📦 Complete package.json for Frontend

```json
{
  "name": "money-transfer-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "react-icons": "^4.12.0",
    "lucide-react": "^0.263.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.1",
    "vite": "^5.0.8"
  }
}
```

## 📝 vite.config.js

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    open: true
  }
})
```

## 🔑 Key Changes Made

### Backend:
1. ✅ Added `success: true` to all successful responses
2. ✅ Fixed wallet balance updates
3. ✅ Added sender/receiver names to transactions
4. ✅ Improved error handling and logging
5. ✅ Fixed CORS configuration
6. ✅ Added comprehensive validation

### Frontend:
1. ✅ Replaced Axios with native Fetch API
2. ✅ Centralized API calls in `services/api.js`
3. ✅ Fixed AuthContext to properly manage state
4. ✅ Added automatic token refresh
5. ✅ Improved error handling
6. ✅ Fixed transaction display

## 🧪 Testing Workflow

### 1. Start Backend
```bash
cd backend
python run.py
```

### 2. Start Frontend
```bash
cd frontend
npm run dev
```

### 3. Test Registration
- Go to http://localhost:5173
- Click "Sign Up"
- Register with:
  - First Name: Test
  - Last Name: User
  - Email: test@example.com
  - Password: password123

### 4. Test Add Funds
- After login, click "Add Funds"
- Add $100
- Verify balance updates

### 5. Test Send Money
- Register another user
- Login as first user
- Send money to second user
- Check transaction history

### 6. Test Admin
- Login with:
  - Email: admin@example.com
  - Password: admin123
  - Role: Admin
- View dashboard statistics
- Manage users and wallets

## 🔍 Troubleshooting

### Backend Issues

**Port 5000 already in use:**
```bash
# Change port in run.py
app.run(port=5001)
```

**Database errors:**
```bash
# Delete and recreate database
rm money_transfer.db
python run.py
```

### Frontend Issues

**CORS errors:**
- Verify backend is running
- Check CORS_ORIGINS in backend .env
- Ensure frontend URL matches

**Token expired:**
```javascript
// Clear browser storage
localStorage.clear()
// Login again
```

**API not connecting:**
- Check VITE_API_URL in frontend .env
- Verify backend is running on correct port
- Check browser console for errors

## 📊 API Endpoints Reference

### Authentication
- `POST /api/auth/register` - Register
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Get current user

### Wallet
- `GET /api/wallet` - Get wallet
- `POST /api/wallet/add-funds` - Add funds

### Transactions
- `POST /api/transactions/send` - Send money
- `GET /api/transactions` - Get transactions
- `GET /api/transactions/:id` - Get transaction

### Users
- `GET /api/users/profile` - Get profile
- `PUT /api/users/profile` - Update profile
- `GET /api/users` - Get all users

### Admin (Requires Admin Role)
- `GET /api/admin/users` - List users
- `GET /api/admin/wallets` - List wallets
- `POST /api/admin/wallets/:id/adjust` - Adjust wallet
- `GET /api/admin/transactions` - List transactions
- `GET /api/admin/stats` - Get statistics

## ✅ Verification Checklist

- [ ] Backend starts without errors
- [ ] Frontend starts without errors
- [ ] Can register new user
- [ ] Can login successfully
- [ ] Wallet balance displays
- [ ] Can add funds
- [ ] Can send money
- [ ] Transaction history shows
- [ ] Admin can access dashboard
- [ ] Admin can manage users
- [ ] Logout works properly

## 🎉 Success!

Your money transfer app should now be fully functional with:
- ✅ User registration and authentication
- ✅ Wallet management
- ✅ Money transfers
- ✅ Transaction history
- ✅ Admin dashboard
- ✅ Real-time balance updates

For any issues, check:
1. Browser console (F12)
2. Backend terminal output
3. Network tab in browser DevTools