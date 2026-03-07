# iHhashi Project Memory

## ⚠️ PIVOT HISTORY

**iHhashi evolved from Boober** (a ride-hailing app like Uber/Bolt):
- **Boober** was the original project - taxi/ride-hailing for South Africa
- **Pivot Date**: 2026-02-25
- **Why**: Food delivery has lower regulatory barriers, faster path to revenue in SA market
- **What Changed**: Same tech stack, same team, different use case
- **Legacy Files**: Old Boober files exist in `/home/workspace/Boober/` - these are archived, NOT the current project

**Current Project: iHhashi** (food delivery like Uber Eats/Order.in)
- Repository: `/home/workspace/iHhashi/`
- Focus: Food delivery, not ride-hailing

---

## Project Overview
Delivery platform for South Africa, inspired by Ele.me.
- **Started**: 2026-02-25
- **Tech Stack**: FastAPI + MongoDB (backend), React + Tailwind (frontend)
- **Version**: 1.0.0 (Referral & Rewards System)

## Architecture

### Three User Types
1. **Customers** - Browse merchants, order, track delivery
2. **Vendors/Merchants** - Manage menu, receive orders, analytics
3. **Delivery Servicemen** - Accept deliveries, navigate, earn

### Database Models
- User (email, phone, role, location)
- Merchant (name, category, menu, hours, location)
- Order (items, status, delivery address, tracking)
- Rider (vehicle, status, location, earnings)
- Verification (Blue Horse system)
- Account (warnings, suspension, termination)

## South Africa Specific
- Currency: ZAR (R)
- Local food: Kota, Bunny Chow, Gatsby, Braai
- All 9 provinces supported
- **Languages**: English, Zulu, Sotho, Afrikaans, Tswana, Xhosa
- VAT: 15%

---

## ✅ FEATURES IMPLEMENTED (v0.2.0)

### Blue Horse Verification System
- **Vendor Verification**: ID, company registration, business license, proof of address
- **Delivery Serviceman Verification**: ID, license, vehicle registration, number plate
- **Customer Light KYC**: ID verification
- **Verification Levels**: 0=unverified, 1=basic, 2=full (Blue Horse), 3=premium
- **Ranking Boost**: Verified vendors appear higher in search

### Multi-Modal Delivery
- **Transport Options**: Car, Motorcycle, Scooter, Bicycle, On-foot
- **Competitive Pricing**: Delivery servicemen set their own rates
- **Inclusive**: Supports those without vehicles (bicycle, walking)

### Account Management
- **45-Day Free Trial**: All new users get free access
- **Warning System**: 3 warnings = automatic suspension
- **Termination Rules**: Criminal activity = permanent termination
- **Suspension Appeals**: 30-day window

### Tipping System
- **0% Platform Fee**: 100% of tips go to delivery servicemen
- Optional tipping on delivery completion

### Product Template
- Up to 5 images per product
- Price with VAT inclusive
- Description, category, availability
- Ratings and reviews

### Reviews & Comments
- All users can read and comment
- Vendors can respond to reviews
- Star ratings (1-5)

### Error Tracking
- **GlitchTip Integration**: Open-source Sentry alternative
- **DSN**: https://25a5585d096a411495f93126742fbf73@app.glitchtip.com/20760
- **Security Endpoint**: https://app.glitchtip.com/api/20760/security/?glitchtip_key=25a5585d096a411495f93126742fbf73

### Language Support
- English (en)
- Zulu/isiZulu (zu)
- Sotho/Sesotho (st)
- Afrikaans (af)
- Tswana/Setswana (tn)
- Xhosa/isiXhosa (xh)

### Infrastructure
- **Docker Compose**: Full stack with MongoDB, Redis, GlitchTip
- **GitHub Actions**: CI/CD pipeline with lint, test, build, deploy
- **Rate Limiting**: slowapi for API protection
- **Analytics**: PostHog integration

---

## 📁 KEY FILES

### Backend
- `backend/app/main.py` - FastAPI app with GlitchTip
- `backend/app/config.py` - Settings with all new features
- `backend/app/models/verification.py` - Blue Horse system
- `backend/app/models/account.py` - Warning/termination logic
- `backend/app/models/delivery.py` - Multi-modal delivery, tipping
- `backend/app/routes/vendors.py` - Vendor verification routes
- `backend/app/routes/delivery_servicemen.py` - Serviceman routes

### Frontend
- `frontend/src/App.tsx` - Splash screen, GlitchTip init
- `frontend/src/components/SplashScreen.tsx` - Logo display
- `frontend/src/components/LanguageSelector.tsx` - Language switcher
- `frontend/public/logo.png` - iHhashi logo

### Infrastructure
- `docker-compose.yml` - Full stack deployment
- `.github/workflows/ci-cd.yml` - GitHub Actions pipeline

### Documentation
- `docs/TERMS_OF_SERVICE.md` - Full ToS with rules
- `backend/.env.example` - Environment template

---

## Play Store Preparation (2026-02-26)

### Build Outputs
- ✅ Debug APK: `ihhashi-debug.apk` (3.6MB)
- ✅ Release APK (unsigned): `ihhashi-release-unsigned.apk` (2.9MB)
- ✅ Signed release APK: `ihhashi-release-signed.apk` (2.9MB) - Ready for Play Store

### Listing Status (All Complete)
- ✅ App name: iHhashi - Food Delivery SA
- ✅ Short description
- ✅ Full description  
- ✅ Keywords
- ✅ Screenshots (4 images, 2160x3840 each)
- ✅ App icon
- ✅ Privacy policy URL
- ✅ Support URL
- ✅ Category: Food & Drink
- ✅ Age rating: Everyone
- ✅ Signed release APK (2.9MB) - Ready for Play Store

### Files
- APKs: `/home/workspace/iHhashi/*.apk`
- Screenshots: `/home/workspace/iHhashi/docs/screenshots/`
- Listing docs: `/home/workspace/iHhashi/docs/PLAY_STORE_LISTING.md`

## ✅ FEATURES IMPLEMENTED (v0.3.0)

### Payment Scheduling (v0.3.0)
- **Payout Day**: Every Sunday at 11:11 AM SAST
- **Who Gets Paid**: All verified delivery servicemen and drivers
- **Minimum Payout**: R100 (accumulated weekly earnings)
- **Automatic Processing**: Background scheduler handles all payouts
- **Bank Integration**: Paystack transfer to SA banks (FNB, Capitec, Standard Bank, etc.)

### Inclusive Delivery Transport (v0.3.0)
- **Standard Options**: Car, Motorcycle, Scooter, Bicycle, On-foot
- **Inclusive Options**:
  - Wheelchair - Users with wheelchairs are welcome delivery partners
  - Running - For fitness enthusiasts
  - Rollerblade - Alternative eco-friendly transport
- **Competitive Pricing**: Each serviceman sets their own rates

### Database Seeding (v0.3.0)
- **Script**: `backend/scripts/seed_database.py`
- **Sample Data**: Admin user, 7 delivery servicemen (all transport types), 3 merchants
- **Run**: `cd backend && python -m scripts.seed_database`

---

## ✅ FEATURES IMPLEMENTED (v0.4.0)

### Vendor Referral System (v0.4.0)
- **Referral Bonus**: +2 FREE DAYS per successful vendor referral
- **Maximum Bonus**: 90 extra days (3 months total possible)
- **How It Works**: 
  1. Vendor gets unique referral code (format: IH-V-XXXXXX)
  2. New vendor signs up using the code
  3. Referrer's trial is extended by 2 days automatically
- **Tracking**: Referrals tracked in AccountRecord model
- **API**: `/api/v1/referrals/*` and `/api/v1/vendors/apply`

### Customer iHhashi Coins Rewards (v0.4.0)
- **Virtual Currency**: "iHhashi Coins" earned through referrals and activity
- **Referral Rewards**:
  - Referrer: 50 iHhashi Coins per successful referral
  - New customer: 25 iHhashi Coins welcome bonus
- **Redemption Options**:
  - 100 coins = Free delivery
  - 150 coins = R15 discount
  - 300 coins = R30 discount
- **Coin Value**: 1 iHhashi Coin = 10 cents (R0.10)

### Customer Tier System (v0.4.0)
Based on successful referrals:
- **Bronze** (1-5): 5% off, Standard support 🥉
- **Silver** (6-15): 10% off, 1 free delivery/month, Priority support 🥈
- **Gold** (16-50): 15% off, 2 free deliveries/month, VIP support, Early access 🥇
- **Platinum** (51+): 20% off, Unlimited free delivery, Dedicated manager 💎

### API Endpoints Added (v0.4.0)
- `/api/v1/referrals/*` - General referral operations
- `/api/v1/customer-rewards/*` - Customer rewards dashboard, tier info, coin redemption
- Vendor application now accepts `referral_code` parameter

### New Models (v0.4.0)
- `ReferralCode` - Unique referral codes for users
- `Referral` - Referral tracking records
- `VendorReferralStats` - Vendor referral statistics
- `CustomerRewardAccount` - Customer rewards and tier tracking
- `CoinTransaction` - iHhashi Coin transaction history
- `RewardRedemption` - Reward redemption records

---

## 🔧 INFRASTRUCTURE

### Error Tracking
- **GlitchTip** (NOT Sentry): Open-source error tracking
- **DSN**: https://25a5585d096a411495f93126742fbf73@app.glitchtip.com/20760

### Authentication
- **Supabase**: Phone OTP authentication
- **Hook**: `useSupabase.ts` for auth state management

### Language Support (i18n)
- **Package**: react-i18next
- **Languages**: English, Zulu, Sotho, Afrikaans, Tswana, Xhosa

---

## 🧠 ROUTE MEMORY SYSTEM

A driver knowledge capture and intelligence system for improved ETAs and route suggestions.

### Phase 1: Foundation ✅ COMPLETE
- Database models: `route_memory.py`
- API endpoints: `/api/route-memory/*`
- Submit actual time records
- Submit driver insights (shortcuts, avoid areas, road work)
- Submit route feedback (smooth/ok/delayed)
- Query route intelligence

### Phase 2: Pricing Intelligence ✅ COMPLETE
- Models: `pricing_intelligence.py`
- API endpoints: `/api/v1/pricing-intelligence/*`
- Pricing gap detection and tracking
- Conversion by tier analysis
- Churn by offer tracking
- Daily revenue vs forecast
- Pre-built query plans:
  - `windowed_price_deltas`
  - `underperforming_tiers`
  - `churn_streaks`
  - `revenue_variance_alerts`
- Reporter template: `/api/v1/pricing-intelligence/report`

### Phase 3: Community ✅ COMPLETE
- Models: `community.py`
- API endpoints: `/api/v1/community/*`
- Insight validation system (upvotes, downvotes, confirmations)
- Driver reputation scoring (Newcomer → Scout → Navigator → Expert → Legend)
- Local knowledge map (geographic clustering of insights)
- Badge system (First Light, Shortcut King, Safety Scout, etc.)
- Leaderboard

### Phase 4: Nduna Integration ✅ COMPLETE
- API endpoints: `/api/v1/nduna-intelligence/*`
- ETA calculation with route memory data
- Best route suggestions based on community knowledge
- Community insight alerts for drivers
- Driver performance analytics
- Context provider for Nduna chatbot
- Analytics dashboard data

### Key Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/route-memory/actual-time` | Submit delivery time data |
| `POST /api/route-memory/insights` | Submit driver insight |
| `POST /api/route-memory/feedback` | Submit route feedback |
| `GET /api/v1/nduna-intelligence/eta` | Calculate ETA with route memory |
| `GET /api/v1/nduna-intelligence/suggest-route` | Get best route suggestions |
| `GET /api/v1/community/reputation/{driver_id}` | Get driver reputation |
| `GET /api/v1/pricing-intelligence/report` | Get pricing intelligence report |

---

## 💰 REFUNDS & DISPUTES FRONTEND (v0.5.0)

### Overview
Complete customer-facing refund system integrated with South African Consumer Protection Act (CPA) compliance.

### Components Created

| Component | Purpose |
|-----------|---------|
| `OrderCard` | Display order with expandable details, status badges, and refund/track actions |
| `RefundRequestModal` | Multi-item refund selection with reason, explanation, and evidence upload |
| `RefundStatusCard` | Track refund status with AI decision display and deadline countdown |
| `OrdersPage` | Tab-based view (Active/Past/Refunds) with full order management |

### Features
- **Order History**: View all orders with status filtering
- **Refund Request**: Select specific items for partial or full refund
- **CPA Compliance**: 10 business day deadline enforcement displayed
- **AI Moderation**: Shows AI recommendation and confidence score
- **Evidence Upload**: Support for photo/document URLs
- **Status Tracking**: Real-time refund status with color-coded badges

### File Locations
- `frontend/src/components/order/OrderCard.tsx`
- `frontend/src/components/order/RefundRequestModal.tsx`
- `frontend/src/components/order/RefundStatusCard.tsx`
- `frontend/src/pages/OrdersPage.tsx`
- `frontend/src/types/order.ts`

### Next Steps
- [ ] Add refund details page (`/refunds/:id`)
- [ ] Add merchant refund management view
- [ ] Add push notifications for refund status changes
- [ ] Integrate with actual evidence file upload (currently URL-based)

---

## 🚀 QUANTUM DISPATCH SYSTEM (v0.5.0)

### Overview
Quantum-enhanced route optimization using D-Wave Leap API for quantum annealing.

### Features
- **Quantum Route Optimization**: Uses D-Wave hybrid solvers for CVRP
- **A/B Testing**: Compare quantum vs classical routing performance
- **Automatic Fallback**: Falls back to OR-Tools if quantum unavailable
- **Statistics Dashboard**: Track quantum win rates and improvements

### Key Files
- `backend/app/services/quantum_dispatch.py` - Quantum dispatcher service
- `backend/app/routes/quantum_dispatch.py` - API endpoints
- `docs/QUANTUM_DISPATCH_SETUP.md` - Setup guide

### API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/quantum-dispatch/status` | Check quantum configuration |
| `POST /api/v1/quantum-dispatch/optimize` | Optimize route with quantum |
| `POST /api/v1/quantum-dispatch/ab-test` | Run A/B test comparison |
| `GET /api/v1/quantum-dispatch/stats` | Get A/B test statistics |
| `POST /api/v1/quantum-dispatch/batch-ab-test` | Run multiple tests |

### Performance Benchmarks
Based on industry studies:
- UPS + IonQ: 24% better routing
- Amazon + Zapata AI: Significant improvements
- DHL + Rigetti: 31% improvement

### Setup
1. Sign up at https://cloud.dwavesys.com/leap/ (free tier: 1 min QPU/month)
2. Get API token from https://cloud.dwavesys.com/leap/api/
3. Set `DWAVE_API_TOKEN` environment variable
4. Restart backend

See `docs/QUANTUM_DISPATCH_SETUP.md` for detailed instructions.

---

## 💰 REFUND & DISPUTE SYSTEM (v0.6.0)

### Overview
Comprehensive refund and dispute management compliant with South African Consumer Protection Act (CPA) 68 of 2008 and Electronic Communications and Transactions Act (ECTA) 25 of 2002.

### Features
- **Customer Refunds**: Submit, track, and manage refund requests
- **Merchant Portal**: Respond to refunds, view pending requests
- **Dispute System**: Escalate rejected refunds to disputes
- **AI Moderation**: Automated refund assessment with fraud detection
- **Admin Dashboard**: Full oversight of all refunds and disputes
- **CPA Compliance**: 10 business day resolution window, automatic deadline tracking

### Key Files
- `backend/app/models/refund.py` - Refund, Dispute, and AI Moderation models
- `backend/app/routes/refunds.py` - All refund and dispute API endpoints

### API Endpoints

#### Customer Endpoints
| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/refunds/request` | Submit a refund request |
| `GET /api/v1/refunds/my-requests` | Get customer's refund requests |
| `GET /api/v1/refunds/{id}` | Get refund details |
| `POST /api/v1/refunds/{id}/evidence` | Add evidence to refund |
| `GET /api/v1/refunds/summary/customer` | Customer refund dashboard summary |

#### Merchant Endpoints
| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/refunds/merchant/pending` | Get pending refund requests |
| `POST /api/v1/refunds/{id}/merchant-response` | Accept or dispute refund |
| `GET /api/v1/refunds/summary/merchant` | Merchant refund summary |

#### Dispute Endpoints
| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/refunds/{id}/dispute` | Open a dispute |
| `GET /api/v1/refunds/disputes/my` | Get user's disputes |
| `POST /api/v1/refunds/disputes/{id}/message` | Add message to dispute |

#### Admin/Moderator Endpoints
| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/refunds/admin/refunds` | List all refunds |
| `GET /api/v1/refunds/admin/disputes` | List all disputes |
| `POST /api/v1/refunds/admin/disputes/{id}/resolve` | Resolve a dispute |
| `POST /api/v1/refunds/{id}/ai-review` | Get AI moderation analysis |

### Refund Reasons (CPA Compliant)
- Defective goods (s56)
- Not as described (s55)
- Wrong item delivered
- Missing items
- Damaged in transit
- Late delivery (s19)
- Food safety concerns
- Allergen issues
- Counterfeit goods
- Price errors

### AI Moderation Factors
- Customer refund history
- Merchant reliability score
- Evidence quality assessment
- Fraud risk scoring
- Similar case outcomes

### Frontend Components
- `RefundRequestModal.tsx` - Submit refund requests
- `RefundStatusCard.tsx` - Display refund status
- `RefundsPage.tsx` - Customer refund dashboard

---

## 🤖 AGENT SYNCHRONIZATION

### Keeping Agents Updated
When iHhashi is updated, run the sync skill to update all agent knowledge bases:
```bash
bun /home/workspace/Skills/ihhashi-sync/scripts/sync.ts
```

This automatically updates:
1. **Nduna Bot** - Telegram bot knowledge base (`/home/workspace/mosta-agent/knowledge-base.json`)
2. **Marketing OpenClaw** - Marketing prompts (`/home/workspace/mosta-agent/prompts/marketing-prompts.md`)

### When to Sync
- New features added/removed
- Business logic changes (pricing, payments, verification)
- New user types or roles
- Marketing messaging updates
- Any significant app update

### Rule
Zo has a rule to automatically run this sync whenever iHhashi is updated.

---

## 📊 META ADS AUTOMATION

### Overview
Autonomous Meta Ads management system for iHhashi marketing.

### Location
`marketing/meta-ads/` in the iHhashi repository

### Daily Workflow
1. **Health Check** - Assess overall account health
2. **Fatigue Detection** - Find ads with audience fatigue (frequency > 3.5)
3. **Auto-Pause** - Stop campaigns bleeding money (CPA > 2.5x target)
4. **Budget Optimization** - Shift spend to top performers
5. **Copy Generation** - Create variations from winners
6. **Morning Brief** - Telegram summary
7. **GitHub Issues** - Create issues for findings

### Quick Start
```bash
# Full autonomous cycle
bun marketing/meta-ads/scripts/autonomous.ts --execute --telegram

# Individual scripts
bun marketing/meta-ads/scripts/health-check.ts
bun marketing/meta-ads/scripts/fatigue-detector.ts
bun marketing/meta-ads/scripts/auto-pause.ts
bun marketing/meta-ads/scripts/budget-optimizer.ts
bun marketing/meta-ads/scripts/copy-generator.ts
bun marketing/meta-ads/scripts/morning-brief.ts
```

### Required Secrets (Zo Settings > Advanced)
- `META_AD_ACCOUNT_ID` - Meta ad account ID
- `META_ACCESS_TOKEN` - Marketing API token
- `META_PAGE_ID` - Facebook Page ID
- `META_INSTAGRAM_ACCOUNT_ID` - Instagram account (optional)
- `META_TARGET_CPA` - Target CPA (default: $5)
- `GITHUB_TOKEN` - For issue creation (optional)

### GitHub Issues Integration
- Fatigue warnings → `ads-fatigue` label
- Paused bleeders → `ads-critical` label
- Budget suggestions → `ads-budget` label
- Copy ideas → `ads-copy` label

View issues: https://github.com/youngstunners88/ihhashi/issues?q=is:issue+is:open+label:ads

### Safety Features
- All new ads start paused
- Auto-pause requires 48hrs poor performance
- Budget shifts capped at 20%/day
- All actions logged with timestamps
- Telegram approval for major changes

---

## ⚡ QUANTUM MERCHANT ONBOARDING (v0.7.0)

### Overview
AI-powered instant merchant profile creation from business name, location, or website URL.

### Capabilities
- **URL Extraction**: Paste any website URL → complete merchant profile
- **Business Name Extraction**: "Nando's Sandton City" → auto-populated profile
- **Google Maps Extraction**: Maps link → full business data + hours
- **Menu Intelligence**: Auto-extract menus from websites, PDFs, social media
- **Social Enrichment**: Pull photos, hours, contact from social profiles

### Extraction Sources
| Source | Method | Accuracy |
|--------|--------|----------|
| Website | FireCrawl + LLM | 95%+ |
| Google Maps | Apify scraper | 90%+ |
| Business Name | Search + Scrape | 75%+ |
| Social Media | API + Scraping | 85%+ |

### Required Secrets (Zo Settings > Advanced)
- `FIRECRAWL_API_KEY` - Get from https://firecrawl.dev
- `APIFY_API_TOKEN` - Get from https://apify.com

### API Endpoints
| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/quantum-onboarding/start` | Start extraction job |
| `GET /api/v1/quantum-onboarding/{job_id}/status` | Check status |
| `GET /api/v1/quantum-onboarding/{job_id}/preview` | Preview extracted data |
| `POST /api/v1/quantum-onboarding/{job_id}/confirm` | Confirm and create merchant |

### Skill: quantum-extractor
Zo has a built-in skill for quantum extraction:
```bash
# Extract from URL
bun /home/workspace/Skills/quantum-extractor/scripts/extract.ts \
  --url "https://restaurant.com" --type merchant

# Extract from business name
bun /home/workspace/Skills/quantum-extractor/scripts/extract.ts \
  --name "Nando's" --location "Sandton"

# Batch extraction
bun /home/workspace/Skills/quantum-extractor/scripts/batch.ts \
  --input businesses.csv --output results.json
```

### Documentation
See `docs/QUANTUM_MERCHANT_ONBOARDING.md` for full implementation details.