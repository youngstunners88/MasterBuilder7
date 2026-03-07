# iHhashi - Delivery for South Africa

A delivery platform inspired by Ele.me, built for the South African market.

## Features

- **Rider App**: Browse merchants, order food/groceries, track deliveries
- **Merchant Dashboard**: Manage menu, receive orders, track analytics
- **Rider Dashboard**: Accept deliveries, navigate, track earnings

## Tech Stack

### Backend
- **FastAPI** - Python web framework
- **MongoDB** - Database (via Motor async driver)
- **JWT** - Authentication
- **Pydantic** - Data validation

### Frontend
- **React 18** - UI library
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Vite** - Build tool
- **React Router** - Navigation

## Project Structure

```
iHhashi/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app entry
│   │   ├── config.py        # Settings
│   │   ├── database.py      # MongoDB connection
│   │   ├── routes/          # API endpoints
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── merchants.py
│   │   │   ├── orders.py
│   │   │   └── riders.py
│   │   └── services/        # Business logic
│   │       └── auth.py
│   ├── models/              # Pydantic models
│   │   ├── user.py
│   │   ├── merchant.py
│   │   ├── order.py
│   │   └── rider.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/      # Reusable UI
│   │   ├── pages/           # Page components
│   │   ├── hooks/           # Custom hooks
│   │   ├── utils/           # Utilities
│   │   ├── styles/          # CSS
│   │   └── App.tsx
│   ├── package.json
│   └── tailwind.config.js
└── docs/
    └── README.md
```

## Getting Started

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Start MongoDB (if not running)
# mongod --dbpath /path/to/data

# Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install  # or: bun install

# Run dev server
npm run dev  # or: bun run dev
```

## API Endpoints

### Auth
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login (returns JWT)
- `GET /api/auth/me` - Get current user

### Users
- `GET /api/users/profile` - Get user profile
- `PUT /api/users/profile` - Update profile
- `GET /api/users/orders` - Get user orders

### Merchants
- `GET /api/merchants` - List merchants (with filters)
- `GET /api/merchants/{id}` - Get merchant details
- `GET /api/merchants/{id}/menu` - Get merchant menu
- `POST /api/merchants` - Create merchant (auth required)

### Orders
- `POST /api/orders` - Create order
- `GET /api/orders/{id}` - Get order details
- `GET /api/orders/{id}/track` - Real-time tracking
- `PUT /api/orders/{id}/status` - Update status

### Riders
- `GET /api/riders/profile` - Rider profile
- `PUT /api/riders/status` - Update availability
- `GET /api/riders/orders/available` - Available orders
- `POST /api/riders/orders/{id}/accept` - Accept delivery
- `GET /api/riders/earnings` - Earnings summary

## South Africa Specific

- **Currency**: ZAR (R)
- **Payment Methods**: 
  - Cash on delivery
  - Card (Stripe)
  - Mobile money (planned)
- **Provinces**: All 9 provinces supported
- **Local Food Categories**:
  - Kota (Soweto sandwich)
  - Bunny Chow (Durban)
  - Gatsby (Cape Town)
  - Braai

## Next Steps

1. **Database**: Set up MongoDB Atlas or local instance
2. **Authentication**: Implement full JWT flow
3. **Geolocation**: Add Google Maps or OpenStreetMap
4. **Payments**: Integrate Stripe for card payments
5. **Notifications**: Add push notifications
6. **Testing**: Write unit and integration tests
7. **Deployment**: Deploy to Zo or cloud provider

## Environment Variables

```env
# Backend (.env)
MONGODB_URL=mongodb://localhost:27017
DB_NAME=ihhashi
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```
