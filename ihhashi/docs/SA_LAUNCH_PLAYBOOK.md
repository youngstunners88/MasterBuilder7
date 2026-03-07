# South Africa Launch Playbook for iHhashi

## Pre-Launch Checklist (Feb 26-27)

### Security Hardening (2 hours)
- [x] Create secure config in `backend/app/core/config.py`
- [x] Add security middleware (headers, request validation)
- [x] Create docker-compose.yml for local dev
- [x] Create CI/CD pipeline (.github/workflows/ci.yml)
- [ ] Verify .env has real values (not placeholders)
- [ ] Change default MongoDB password
- [ ] Generate new SECRET_KEY (32+ chars)
- [ ] Add rate limiting to all auth endpoints

### Database & Infrastructure (3 hours)
- [ ] Set up MongoDB Atlas cluster (free tier)
- [ ] Configure Redis on Render/Railway
- [ ] Deploy backend to Render.com (free tier)
- [ ] Deploy frontend to Vercel/Netlify
- [ ] Configure custom domain (if available)

### Testing (2 hours)
- [ ] Test all API endpoints with Postman/curl
- [ ] Test payment flow (Paystack test mode)
- [ ] Test order creation → rider notification
- [ ] Test WebSocket tracking
- [ ] Test on Android device (APK)

---

## Feb 28 Launch Day

### Morning (8:00 - 12:00)
1. **Deploy to Production**
   ```bash
   # Backend
   cd backend
   render deploy
   
   # Frontend
   cd frontend
   npm run build
   # Upload to hosting
   ```

2. **Generate Android APK**
   ```bash
   cd frontend
   npx cap add android
   npx cap build android
   # APK at: android/app/build/outputs/apk/
   ```

3. **Create Landing Page**
   - Link to APK download
   - WhatsApp contact for support
   - Basic feature list

### Afternoon (12:00 - 17:00)
4. **Beta User Recruitment**
   - Post in local Facebook groups
   - Share on WhatsApp status
   - Target: 20 beta users
   - Focus on one suburb (e.g., Sandton, Rosebank)

5. **Manual Order Testing**
   - Process 5-10 test orders
   - Collect voice note feedback
   - Track issues in Sprint Backlog

---

## March 1-7: Week 1

### Daily Tasks
- Monitor error logs (GlitchTip)
- Respond to user feedback within 2 hours
- Fix top 3 bugs each day

### Development
- [ ] Add order status tracking UI
- [ ] Improve rider location updates
- [ ] Add Push notifications (Firebase)
- [ ] Implement offline mode caching

### Growth
- [ ] Recruit 5 beta merchants
- [ ] Onboard 10 more riders
- [ ] Create referral program (R50 credit)

---

## South Africa Specific Considerations

### Payment Methods
- **Primary**: Paystack (card, EFT, USSD)
- **Secondary**: Yoco (card present)
- **Future**: Momnt (BNPL for larger orders)

### Network Resilience
- Offline mode for order viewing
- Compressed API responses (gzip)
- Retry logic with exponential backoff
- Data-saver mode toggle

### Language Support
- English (default)
- Zulu
- Xhosa
- Afrikaans
- Sotho
- Tswana
- (Nduna chatbot supports all 11 official languages)

### Delivery Zones (Phase 1)
- Gauteng: Sandton, Rosebank, Fourways
- Focus on high-density areas first
- Expand to suburbs as riders sign up

---

## Marketing Strategy

### Digital (Free)
- WhatsApp status updates
- Facebook marketplace posts
- Local community groups
- University campus boards

### Offline (Low Cost)
- Flyers at taxi ranks (R200)
- Stickers at spaza shops
- Word of mouth via riders

### Partnerships
- Partner with 3-5 local restaurants
- Offer free delivery for first week
- 20% off for referral signups

---

## Support Infrastructure

### Customer Support
- WhatsApp: +27 XX XXX XXXX
- Response time: <2 hours (8am-8pm)
- Use Nduna chatbot for basic queries

### Rider Support
- WhatsApp group for active riders
- Daily payout reconciliation
- Incident reporting form

### Merchant Support
- Onboarding call (15 min)
- WhatsApp for order issues
- Weekly performance report

---

## Key Metrics to Track

### Launch Week
- DAU (Daily Active Users): Target 50
- Orders completed: Target 100
- Average order value: Target R150
- Delivery time: Target <45 min
- Customer satisfaction: Target 4.5/5

### Week 1-4
- Retention rate: Target 40%
- Rider signups: Target 20
- Merchant signups: Target 10
- Revenue: Target R5,000

---

## Emergency Contacts

### Technical Issues
- Backend down: Check Render logs
- Database issues: MongoDB Atlas
- Payment failures: Paystack dashboard

### Business Issues
- Rider disputes: WhatsApp support
- Merchant complaints: Scheduled call
- Legal questions: Consult lawyer

---

## Post-Launch Priorities (March 8+)

### Must Have
1. Bug fixes from beta feedback
2. Basic order tracking UI
3. Push notifications
4. Rider earnings dashboard

### Nice to Have
1. Subscription model (R99/month free delivery)
2. Scheduled deliveries
3. Group orders
4. Loyalty points

### Future (April+)
1. iOS app
2. Enterprise API
3. Franchise model
4. Expansion to Cape Town, Durban

---

## Notes

- Keep it simple for launch - perfection is the enemy of shipped
- Focus on one suburb, one user segment first
- Collect feedback religiously
- Iterate fast based on real usage

**Remember**: A buggy app with 100 users beats a perfect app with 0 users.
