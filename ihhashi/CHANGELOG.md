# Changelog

All notable changes to iHhashi will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-03-01

### Added - Nduna Chatbot Enhancements

#### Product Browsing with Function Calling
- **Added** Groq function calling support to Nduna chatbot
- **Added** `search_merchants` function - search stores, restaurants, pharmacies by query/category/city
- **Added** `search_products` function - search products and menu items across all merchants
- **Added** `get_merchant_menu` function - get full catalog for a specific merchant
- **Added** automatic function execution when users ask about food, groceries, or products
- **Enhanced** system prompts to instruct AI on when to use browsing functions

#### Voice Input Support
- **Added** `/nduna/voice` endpoint - transcribe audio using Groq Whisper (whisper-large-v3-turbo)
- **Added** `/nduna/voice/chat` endpoint - transcribe and get AI response in one call
- **Added** support for multiple audio formats: mp3, mp4, mpeg, mpga, m4a, wav, webm
- **Perfect** for Telegram voice messages integration

#### New Browse Endpoints
- **Added** `GET /nduna/browse/merchants` - direct merchant browsing API
- **Added** `GET /nduna/browse/products` - direct product browsing API  
- **Added** `GET /nduna/browse/{merchant_id}/menu` - get merchant catalog

#### Improved Suggestions
- **Enhanced** quick reply suggestions for store/grocery queries
- **Added** context-aware suggestions for different merchant types

### Technical Details
- Uses Groq's Llama 3.3 70B for chat with tool calling
- Uses Groq's Whisper Large V3 Turbo for fast transcription
- Maintains key rotation for rate limit resilience (up to 19 Groq keys)
- All 7 South African languages supported (en, zu, xh, af, st, tn, so)

### Files Changed
- `backend/app/routes/nduna.py` - Complete overhaul with function calling and voice support

## [0.4.2] - 2026-02-27

### Security (Critical Fixes from Security Review)

#### Backend Security Fixes
- **Removed** dangerous `RequestValidationMiddleware` - naive SQL/XSS pattern matching causes false positives
- **Kept** proper protection via FastAPI/Pydantic validation + Motor's injection-safe MongoDB operations

#### Frontend Authentication Fixes
- **Fixed** frontend authentication to use Bearer token authentication (JWT) instead of broken CSRF logic
- **Updated** API interceptor to read `access_token` from localStorage and send as `Authorization: Bearer {token}`
- **Updated** login/register to store tokens in localStorage from backend response
- **Updated** logout to clear both `access_token` and `refresh_token` from localStorage
- **Removed** CSRF token logic entirely (not needed for Bearer token auth)

#### Analytics Security Fixes
- **Fixed** hardcoded PostHog API key in `frontend/src/lib/posthog.ts`
- **Added** environment variable validation - only initialize if `VITE_POSTHOG_KEY` is properly configured
- **Added** protection against placeholder/invalid keys

### Files Changed
- `backend/app/middleware/security.py` - Removed dangerous RequestValidationMiddleware
- `frontend/src/lib/api.ts` - Fixed Bearer token authentication
- `frontend/src/lib/posthog.ts` - Removed hardcoded key, added env validation

## [0.4.1] - 2026-02-27

### Security (Remediation from ShieldGuard Audit)

#### Critical Concurrency Fix
- **Fixed** race condition in order creation that allowed overselling (atomic stock management)
- **Added** `find_one_and_update` pattern for atomic stock decrement with condition check
- **Added** rollback mechanism for partial order failures
- **Added** stock restoration on order cancellation

#### WebSocket Security Hardening
- **Fixed** unauthenticated access to order tracking WebSocket endpoint
- **Added** JWT token validation before accepting connections
- **Added** access control verification (buyer/rider/merchant/admin only)
- **Added** proper WebSocket close codes (4001=auth required, 4003=unauthorized, 4004=not found)

#### Rate Limiting (All Endpoints)
- **Added** rate limiting to all order endpoints (10-60/min based on sensitivity)
- **Added** rate limiting to all rider endpoints (10-120/min for location updates)
- **Added** `order_rate_limit` decorator to middleware

#### Input Validation
- **Added** coordinate validation for latitude (-90 to 90) and longitude (-180 to 180)
- **Added** speed validation (0-200 km/h) and heading validation (0-360 degrees)
- **Added** quantity limits (max 99 per item)
- **Added** buyer notes sanitization (HTML stripping, max 500 chars)

### Files Changed
- `backend/app/routes/orders.py` - Atomic operations, rate limiting, input validation
- `backend/app/routes/websocket.py` - Authentication, coordinate validation
- `backend/app/routes/riders.py` - Rate limiting on all endpoints
- `backend/app/middleware/rate_limit.py` - New order_rate_limit decorator

## [0.4.0] - 2026-02-27

### Security (Critical Fixes from Security Audit)

#### Webhook Idempotency & Replay Protection
- **Added** unique index on `payment_webhooks.event_id` to prevent duplicate webhook processing
- **Added** `DuplicateKeyError` handling in webhook handler to silently ignore replayed webhooks
- **Added** Paystack verification call before marking payments as success (prevents fraud)

#### Concurrency & Atomic Operations
- **Added** atomic `find_and_lock_rider` method using `find_one_and_update` pattern
- **Added** `locked_at` timestamp for rider locks with TTL auto-release (10 minutes)
- **Fixed** race condition in rider assignment that could cause double-assignment

#### WebSocket Authentication
- **Added** JWT authentication to all WebSocket endpoints (`/ws/track`, `/ws/rider`, `/ws/user`)
- **Added** token validation on connect with proper error codes (4001=auth required, 4003=unauthorized)
- **Added** user/rider identity verification to prevent impersonation

#### Rate Limiting
- **Added** Redis-backed rate limiting for production scaling
- **Added** specialized rate limit decorators: `payment_rate_limit`, `webhook_rate_limit`
- **Fixed** in-memory rate limiter that resets on process restart

### Database Indexes
- **Added** `riders.location` 2dsphere geo index for location queries
- **Added** `riders.locked_at` TTL index (600 seconds) for auto-releasing stuck locks
- **Added** `payment_webhooks.event_id` unique index for idempotency
- **Added** `payment_webhooks.received_at` index for log queries

### Testing
- **Added** `test_concurrent_matching.py` - Tests for atomic rider assignment
- **Added** `test_webhook_replay.py` - Tests for webhook idempotency protection
- **Added** tests verifying TTL index behavior for stale locks

### CI/CD
- **Added** smoke-test job that verifies backend health before production deployment
- **Changed** deploy-production to depend on smoke-test (not just docker-build)
- **Added** Docker health check with curl to `/health` endpoint

### Changed
- Updated payments webhook handler with idempotent updates (`status != success` check)
- Updated rate limiter to use Redis storage URI from settings

## [0.3.0] - 2026-02-27

### Added
- **Payment Scheduling**: Automatic weekly payouts every Sunday at 11:11 AM SAST for verified delivery servicemen
- **Inclusive Transport Options**: Added wheelchair, running, and rollerblade delivery options
- **Database Seeding**: Sample data script with admin, 7 delivery servicemen, and 3 merchants
- **Multi-Modal Delivery**: Full support for car, motorcycle, scooter, bicycle, and on-foot delivery

### Changed
- Updated README with comprehensive deployment instructions
- Enhanced Play Store listing with all required assets

## [0.2.0] - 2026-02-26

### Added
- **Blue Horse Verification System**: Comprehensive ID, company, and vehicle verification
- **Multi-Modal Delivery**: Support for various transport types (car, motorcycle, scooter, bicycle, on-foot)
- **Account Management**: 45-day free trial, warning system, suspension/termination logic
- **Tipping System**: 0% platform fee on tips - 100% goes to delivery servicemen
- **Product Templates**: Up to 5 images per product, VAT-inclusive pricing
- **Reviews & Comments**: Star ratings (1-5), vendor responses
- **Language Support**: English, Zulu, Sotho, Afrikaans, Tswana, Xhosa
- **GlitchTip Integration**: Open-source error tracking
- **PostHog Integration**: User behavior analytics
- **GitHub Actions CI/CD**: Automated lint, test, build, deploy pipelines
- **Rate Limiting**: slowapi for API protection

### Changed
- Pivot from Boober (ride-hailing) to iHhashi (food delivery)
- Database models updated for delivery-focused operations

## [0.1.0] - 2026-02-25

### Added
- Initial project scaffold
- FastAPI backend with MongoDB
- React + Tailwind frontend
- Capacitor for Android mobile app
- Supabase authentication (Phone OTP)
- Basic order, merchant, and rider models

---

## Version History

| Version | Date | Status |
|---------|------|--------|
| 0.4.2 | 2026-02-27 | Current |
| 0.4.1 | 2026-02-27 | Released |
| 0.4.0 | 2026-02-27 | Released |
| 0.3.0 | 2026-02-27 | Released |
| 0.2.0 | 2026-02-26 | Released |
| 0.1.0 | 2026-02-25 | Initial Release |

## Upcoming (Planned)

- [ ] Paystack payment integration
- [ ] Yoco payment integration  
- [ ] Google Maps integration
- [ ] Push notifications (Firebase)
- [ ] SMS notifications (Twilio)
- [ ] Telegram bot enhancements
- [ ] Real-time WebSocket tracking
- [ ] Advanced analytics dashboard

---

*Maintained by DocMaster - iHhashi Documentation Agent*
