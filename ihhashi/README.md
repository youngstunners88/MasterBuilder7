# iHhashi

**Delivery platform for South Africa** - Food, groceries, fruits & vegetables, and personal courier services.

Inspired by Ele.me, built for Mzansi. 🇿🇦

## Features

- 🍽️ **Food Delivery** - Restaurants, takeaways, local SA food (Kota, Bunny Chow, Gatsby)
- 🛒 **Groceries** - Supermarkets, spaza shops
- 🥬 **Fresh Produce** - Fruits & vegetables
- 📦 **Courier Services** - Packages, documents, parcels
- 🚗 **Multi-Modal Delivery** - Car, motorcycle, scooter, bicycle, on-foot, wheelchair, rollerblade
- 🔵 **Blue Horse Verification** - Trust system for vendors and delivery partners
- 🪙 **iHhashi Coins** - Customer rewards and referral bonuses
- 🤖 **Nduna Intelligence** - AI-powered ETA and route optimization
- 🗺️ **Route Memory** - Driver knowledge capture for better ETAs
- 🏆 **Community** - Driver reputation and badges
- 🇿🇦 **South African** - All 9 provinces, ZAR currency, local languages

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI, MongoDB, Redis |
| **Frontend** | React, Tailwind CSS, Capacitor |
| **Mobile** | Android (Capacitor), PWA |
| **Auth** | Supabase (Phone OTP) |
| **Payments** | Paystack, Yoco |
| **Maps** | Google Maps |
| **Analytics** | PostHog |
| **Errors** | GlitchTip |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB 7.0
- Redis 7

### Development Setup

```bash
# Clone the repository
git clone https://github.com/yourorg/ihhashi.git
cd ihhashi

# Backend setup
cd backend
cp .env.example .env
# Edit .env with your values
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend setup (new terminal)
cd frontend
cp .env.example .env
# Edit .env with your values
npm install
npm run dev
```

### Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Project Structure

```
ihhashi/
├── backend/
│   ├── app/
│   │   ├── models/        # Database models
│   │   │   ├── account.py        # Warning/suspension system
│   │   │   ├── buyer.py          # Buyer model
│   │   │   ├── community.py      # Driver reputation, badges
│   │   │   ├── customer_rewards.py # Hashi Coins, tiers
│   │   │   ├── delivery.py       # Multi-modal delivery, tipping
│   │   │   ├── driver.py         # Driver model
│   │   │   ├── order.py          # Order model
│   │   │   ├── pricing_intelligence.py # Pricing analytics
│   │   │   ├── product.py        # Product model
│   │   │   ├── referral.py       # Referral system
│   │   │   ├── refund.py         # Refund processing
│   │   │   ├── route_memory.py   # Driver route knowledge
│   │   │   ├── trip.py           # Trip tracking
│   │   │   ├── user.py           # User model
│   │   │   └── verification.py   # Blue Horse verification
│   │   ├── routes/        # API endpoints (see API section)
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic
│   │   └── middleware/    # Rate limiting, security
│   ├── scripts/
│   │   ├── migrations/    # Database migrations
│   │   └── seed_database.py
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   │   ├── Home.tsx           # Main home page
│   │   │   ├── HomePage.tsx       # Alternative home page
│   │   │   ├── CartPage.tsx       # Shopping cart
│   │   │   ├── MerchantPage.tsx   # Merchant view
│   │   │   ├── MerchantDashboard.tsx # Merchant dashboard
│   │   │   ├── RiderDashboard.tsx # Rider dashboard
│   │   │   ├── OrdersPage.tsx     # Orders page
│   │   │   ├── ProfilePage.tsx    # Profile page
│   │   │   ├── auth/Auth.tsx      # Authentication
│   │   │   ├── catalog/Products.tsx # Product catalog
│   │   │   ├── admin/             # Admin pages
│   │   │   ├── cart/              # Cart components
│   │   │   ├── orders/            # Order pages
│   │   │   └── profile/           # Profile pages
│   │   ├── hooks/         # Custom hooks
│   │   ├── lib/           # API client, utilities
│   │   └── styles/        # CSS/Tailwind
│   ├── public/
│   ├── package.json
│   └── Dockerfile
├── assets/
│   └── nduna/             # Nduna bot assets
├── content/
│   └── marketing/         # Marketing content
├── deployment/
│   ├── vercel.json        # Vercel configuration
│   ├── render.yaml        # Render blueprint
│   ├── docker-compose.prod.yml
│   └── nginx/             # Nginx configs
├── docs/
│   ├── PLAY_STORE_LISTING.md
│   ├── TERMS_OF_SERVICE.md
│   └── screenshots/
├── legal/
│   └── kimi-prompt-business-docs.md
├── marketing/
│   └── meta-ads/          # Automated Meta Ads management
├── ihhashi-coin/            # Hashi Coin rewards system
├── videos/                # Marketing videos
├── swarm-reports/         # Swarm deployment reports
└── docker-compose.yml     # Development compose
```

## API Endpoints

### Core Routes

| Route | File | Description |
|-------|------|-------------|
| `/api/v1/auth/*` | `auth.py` | Authentication (phone OTP via Supabase) |
| `/api/v1/users/*` | `users.py` | User management and profiles |
| `/api/v1/addresses/*` | `addresses.py` | Address management |
| `/api/v1/orders/*` | `orders.py` | Order creation and management |
| `/api/v1/payments/*` | `payments.py` | Payment processing (Paystack, Yoco) |
| `/api/v1/tracking/*` | `tracking.py` | Real-time delivery tracking |
| `/api/v1/websocket/*` | `websocket.py` | WebSocket connections |

### Marketplace Routes

| Route | File | Description |
|-------|------|-------------|
| `/api/v1/merchants/*` | `merchants.py` | Vendor/merchant management |
| `/api/v1/vendors/*` | `vendors.py` | Vendor-specific operations |
| `/api/v1/products/*` | `products.py` | Product catalog |
| `/api/v1/refunds/*` | `refunds.py` | Refund processing |

### Delivery Routes

| Route | File | Description |
|-------|------|-------------|
| `/api/v1/delivery-servicemen/*` | `delivery_servicemen.py` | Delivery partner management |
| `/api/v1/riders/*` | `riders.py` | Rider operations |
| `/api/v1/trips/*` | `trips.py` | Trip tracking |

### Route Memory System (Phases 1-4)

| Route | File | Description |
|-------|------|-------------|
| `/api/route-memory/*` | `route_memory.py` | Driver knowledge capture |
| `/api/v1/pricing-intelligence/*` | `pricing_intelligence.py` | Pricing analytics and alerts |
| `/api/v1/community/*` | `community.py` | Driver reputation and badges |
| `/api/v1/nduna-intelligence/*` | `nduna_intelligence.py` | AI-powered ETA and routes |

### Rewards & Referrals

| Route | File | Description |
|-------|------|-------------|
| `/api/v1/referrals/*` | `referrals.py` | Referral code management |
| `/api/v1/customer-rewards/*` | `customer_rewards.py` | iHhashi Coins, tiers, redemption |

### AI Assistant

| Route | File | Description |
|-------|------|-------------|
| `/api/v1/nduna/*` | `nduna.py` | Nduna chatbot endpoints |

### Quantum Dispatch System (Phase 5)

| Route | File | Description |
|-------|------|-------------|
| `/api/v1/quantum-dispatch/*` | `quantum_dispatch.py` | Quantum route optimization, A/B testing |
| `/quantum/*` | `quantum_orchestrator.py` | Quantum routing orchestration for Nduna Bot |

**Quantum Dispatch Endpoints:**
- `GET /api/v1/quantum-dispatch/status` - System status
- `POST /api/v1/quantum-dispatch/optimize` - Optimize single route
- `POST /api/v1/quantum-dispatch/ab-test` - Run A/B test (quantum vs classical)
- `GET /api/v1/quantum-dispatch/stats` - Performance statistics
- `POST /api/v1/quantum-dispatch/batch-ab-test` - Batch A/B testing

**Quantum Orchestrator Endpoints:**
- `POST /quantum/optimize-routes` - Multi-driver route optimization
- `POST /quantum/optimize-route-async` - Async route optimization
- `POST /quantum/optimize-multi-stop` - Multi-stop route planning
- `GET /quantum/status/{task_id}` - Check async task status
- `GET /quantum/stats` - Optimization statistics
- `GET /quantum/health` - Health check

## Backend Services

Business logic layer in `backend/app/services/`:

| Service | File | Description |
|---------|------|-------------|
| **Auth** | `auth.py` | Authentication utilities, token validation |
| **Delivery Fee** | `delivery_fee.py` | Dynamic delivery fee calculation based on distance, time, demand |
| **File Upload** | `file_upload.py` | File handling for verification documents, product images |
| **Matching** | `matching.py` | Order-driver matching algorithm, proximity-based dispatch |
| **Payout Scheduler** | `payout_scheduler.py` | Sunday 11:11 AM SAST automatic payouts to delivery partners |
| **Paystack** | `paystack.py` | Paystack payment integration for SA banks (FNB, Capitec, etc.) |
| **Quantum Dispatch** | `quantum_dispatch.py` | Quantum route optimization service, A/B testing framework |
| **Route Optimizer** | `route_optimizer.py` | Classical TSP solver, route planning algorithms |
| **Telegram Bot** | `telegram_bot.py` | Nduna bot integration, customer support automation |

## Frontend Hooks

Custom React hooks in `frontend/src/hooks/`:

| Hook | File | Description |
|------|------|-------------|
| **useCart** | `useCart.ts` | Shopping cart state management, add/remove items |
| **useDataSaver** | `useDataSaver.ts` | Data saver mode detection for South African users |
| **useLoadShedding** | `useLoadShedding.ts` | Load shedding status detection (Eskom integration) |
| **usePostHog** | `usePostHog.ts` | Analytics tracking with PostHog |
| **useSupabase** | `useSupabase.ts` | Authentication state with Supabase phone OTP |

## Frontend Components

Key components in `frontend/src/components/`:

| Component | File | Description |
|-----------|------|-------------|
| **Header** | `Header.tsx` | App header with navigation, language toggle |
| **CategoryBar** | `CategoryBar.tsx` | Food/grocery category navigation |
| **MerchantCard** | `MerchantCard.tsx` | Restaurant/store card with ratings, delivery info |
| **PaymentSelector** | `PaymentSelector.tsx` | Paystack/Yoco payment method selector |
| **LanguageSelector** | `LanguageSelector.tsx` | SA language picker (Zulu, Sotho, Afrikaans, etc.) |
| **LanguageToggle** | `LanguageToggle.tsx` | Compact language toggle button |
| **SplashScreen** | `SplashScreen.tsx` | App loading screen with iHhashi logo |

## Route Memory System

A driver knowledge capture system for improved ETAs and route suggestions.

### Phase 1: Route Memory ✅
- Submit actual delivery times
- Driver insights (shortcuts, avoid areas)
- Route feedback (smooth/ok/delayed)

### Phase 2: Pricing Intelligence ✅
- Pricing gap detection
- Conversion by tier analysis
- Churn tracking
- Revenue vs forecast

### Phase 3: Community ✅
- Insight validation (upvotes, confirmations)
- Driver reputation (Newcomer → Legend)
- Local knowledge maps
- Badge system

### Phase 4: Nduna Integration ✅
- ETA calculation with route memory
- Best route suggestions
- Driver alerts
- Performance analytics

## Customer Rewards

### iHhashi Coins
- Virtual currency earned through referrals and activity
- 1 iHhashi Coin = R0.10
- Referral: 50 coins per successful referral
- Welcome bonus: 25 coins for new customers

### Redemption Options
- 100 coins = Free delivery
- 150 coins = R15 discount
- 300 coins = R30 discount

### Customer Tiers
| Tier | Referrals | Benefits |
|------|-----------|----------|
| 🥉 Bronze | 1-5 | 5% off, Standard support |
| 🥈 Silver | 6-15 | 10% off, 1 free delivery/month |
| 🥇 Gold | 16-50 | 15% off, 2 free deliveries/month |
| 💎 Platinum | 51+ | 20% off, Unlimited free delivery |

## Vendor Referral System

- +2 FREE DAYS per successful vendor referral
- Maximum 90 extra days (3 months)
- Unique referral codes (IH-V-XXXXXX format)

## Deployment

### Option 1: Render (Recommended)

1. **Push to GitHub**
   ```bash
   git push origin main
   ```

2. **Create Render Account**
   - Go to [render.com](https://render.com)
   - Connect your GitHub repository

3. **Deploy using Blueprint**
   - Create a new Blueprint
   - Select your repository
   - Render will detect `deployment/render.yaml`

4. **Set Environment Variables**
   - Set all `sync: false` variables in Render dashboard
   - See `backend/.env.example` for full list

5. **Deploy Frontend to Vercel** (see Option 2)

### Option 2: Vercel + Render

**Frontend (Vercel):**

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
cd frontend
vercel --prod
```

**Backend (Render):**
Follow Option 1 steps, or deploy manually:
1. Create a new Web Service
2. Connect GitHub repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Option 3: Self-Hosted (Docker)

```bash
# Copy environment file
cp backend/.env.example .env

# Edit with production values
nano .env

# Deploy with Docker Compose
docker-compose -f deployment/docker-compose.prod.yml up -d

# View logs
docker-compose -f deployment/docker-compose.prod.yml logs -f

# Run migrations
docker-compose -f deployment/docker-compose.prod.yml exec backend \
  python -m scripts.migrations.migrate --up
```

### SSL Certificates (Let's Encrypt)

```bash
# Initial certificate request
docker-compose -f deployment/docker-compose.prod.yml run --rm certbot \
  certonly --webroot --webroot-path /var/www/certbot \
  -d ihhashi.co.za -d www.ihhashi.co.za -d api.ihhashi.co.za

# Certificates auto-renew via certbot container
```

## Environment Setup

### Required Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | JWT signing key | ✅ |
| `MONGODB_URL` | MongoDB connection string | ✅ |
| `REDIS_URL` | Redis connection string | ✅ |
| `SUPABASE_URL` | Supabase project URL | ✅ |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | ✅ |
| `PAYSTACK_SECRET_KEY` | Paystack secret key | ✅ |
| `GOOGLE_MAPS_API_KEY` | Google Maps API key | ✅ |

### Optional Environment Variables

| Variable | Description |
|----------|-------------|
| `GLITCHTIP_DSN` | Error tracking DSN |
| `POSTHOG_API_KEY` | Analytics key |
| `FIREBASE_*` | Push notifications |
| `TWILIO_*` | SMS notifications |
| `TELEGRAM_BOT_TOKEN` | Telegram bot |

See `backend/.env.example` and `frontend/.env.example` for complete lists.

## Database Migrations

```bash
# View migration status
python -m scripts.migrations.migrate --status

# Apply pending migrations
python -m scripts.migrations.migrate --up

# Rollback last migration
python -m scripts.migrations.migrate --down

# Create a new migration
python -m scripts.migrations.migrate --create "add_new_field"
```

## Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v
```

### Frontend Tests

```bash
cd frontend

# Run tests
npm test

# Run with coverage
npm test -- --coverage

# Run e2e tests
npm run test:e2e
```

### Type Checking

```bash
# Backend
cd backend
mypy app

# Frontend
cd frontend
npm run typecheck
```

## API Documentation

Once the backend is running, access the API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Mobile App (Android)

### Build Debug APK

```bash
cd frontend
npm run build
npx cap sync android
cd android
./gradlew assembleDebug
```

### Build Release APK

```bash
# Build and sign release
cd frontend/android
./gradlew assembleRelease

# APK location: frontend/android/app/build/outputs/apk/release/
```

### Play Store

See `docs/PLAY_STORE_LISTING.md` for store listing details.

## Monitoring

### Health Endpoints

- `GET /health` - Basic health check
- `GET /` - API info

### Error Tracking

Errors are tracked via GlitchTip:
- DSN: Configure `GLITCHTIP_DSN` environment variable
- Dashboard: https://app.glitchtip.com

### Analytics

User behavior tracked via PostHog:
- Configure `POSTHOG_API_KEY`
- Dashboard: https://app.posthog.com

## Security

- **Rate Limiting**: API protected with slowapi
- **CORS**: Configurable allowed origins
- **JWT**: Secure token-based authentication
- **Input Validation**: Pydantic schemas
- **Helmet Headers**: Security headers in responses

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

Proprietary - All rights reserved.

## Support

- **Website**: https://ihhashi.co.za
- **Email**: support@ihhashi.co.za
- **Play Store**: [iHhashi - Food Delivery SA](https://play.google.com/store/apps/details?id=za.co.ihhashi)

---

Built with ❤️ in South Africa
