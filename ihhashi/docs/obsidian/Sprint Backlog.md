# Sprint Backlog

## Current Sprint: Production Readiness

### ✅ Completed (2026-02-26)

#### Security Hardening
- [x] Secure config in `backend/app/core/config.py`
- [x] Security middleware (headers, request validation, timing)
- [x] Webhook signature verification
- [x] Updated .gitignore with secrets protection
- [x] Security scan (ShieldGuard) - 0 critical issues

#### Orders Routes
- [x] Create order with competitive bidding
- [x] Track order (REST + WebSocket)
- [x] Update order status with transitions
- [x] Rider bid submission
- [x] Customer bid acceptance

#### Merchants Routes
- [x] Search with geolocation
- [x] Filter by category/city/area
- [x] Business hours + "open now"
- [x] Menu with categories
- [x] Product search
- [x] Reviews system

#### Riders Routes
- [x] Profile CRUD
- [x] Status/location updates
- [x] Available orders near rider
- [x] Accept orders
- [x] Earnings calculation
- [x] Earnings history
- [x] Performance stats

#### Payments
- [x] Webhook handling (all events)
- [x] Database updates on payment
- [x] Idempotent processing

#### Real-time Tracking
- [x] WebSocket server
- [x] Order tracking room
- [x] Rider location updates
- [x] User notifications

#### Nduna Chatbot
- [x] All 11 SA languages
- [x] Groq API integration
- [x] Intent detection
- [x] Translation

#### Infrastructure
- [x] Docker Compose for local development
- [x] Backend Dockerfile
- [x] Frontend Dockerfile (dev)
- [x] CI/CD pipeline (GitHub Actions)
- [x] .env.example with all required variables

#### Documentation
- [x] SA Launch Playbook created
- [x] Step-by-step Feb 28 launch guide
- [x] South Africa specific considerations

---

### 🔄 In Progress

#### Frontend Integration
- [ ] Competitive bidding UI
- [ ] Rider selection screen
- [ ] Real-time tracking map
- [ ] Nduna chat interface

#### Push Notifications
- [ ] FCM setup
- [ ] APNs setup
- [ ] Notification templates

---

### 📋 Backlog

#### High Priority
- [ ] Load testing (WebSocket connections)
- [ ] API rate limiting per user
- [ ] Order cancellation flow
- [ ] Refund processing

#### Medium Priority
- [ ] Merchant dashboard analytics
- [ ] Rider performance reports
- [ ] Customer order history
- [ ] Favorite merchants/riders

#### Low Priority
- [ ] Promo code system
- [ ] Loyalty points
- [ ] Referral program
- [ ] Scheduled deliveries

---

## Velocity Tracking

| Date | Points Completed | Notes |
|------|-----------------|-------|
| 2026-02-26 | 42 | All core routes implemented |

---

## Dependencies

### External Services
- ✅ MongoDB (database)
- ✅ Supabase (auth)
- ✅ Paystack (payments)
- ✅ Groq (Nduna chatbot)

### Still Needed
- [ ] FCM project setup
- [ ] APNs certificates
- [ ] Sentry project (using GlitchTip)

---

## Risks

1. **WebSocket Scalability** - May need Redis pub/sub for multi-instance
2. **Groq Rate Limits** - 7 keys rotation should handle load
3. **Payment Webhook Security** - Signature verification critical

---

## Definition of Done

- [x] Code written
- [x] API documented
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Code reviewed
- [ ] Deployed to staging
