# iHhashi

> **Delivery platform for South Africa** - Groceries, Food, Fruits, Vegetables, Dairy Products, and Personal Courier Services

**Started**: 2026-02-25
**Status**: Development
**Repository**: `/home/workspace/iHhashi`

---

## ⚠️ IMPORTANT CLARIFICATION

**iHhashi IS:**
- Grocery delivery (supermarkets, spaza shops)
- Food delivery (restaurants, takeaways)
- Fresh produce delivery (fruits, vegetables)
- Dairy product delivery (milk, cheese, yogurt, etc.)
- Personal courier services (packages, documents, parcels)

**iHhashi is NOT:**
- ❌ A taxi/ride-hailing app
- ❌ A passenger transport service
- ❌ Related to Boober or any taxi platform

---

## Quick Links

- [[Architecture Overview]] - System architecture and tech stack
- [[User Types]] - Customers, Merchants, Riders
- [[API Reference]] - Backend API endpoints
- [[Sprint Backlog]] - Current and planned work
- [[Daily Log]] - Development log

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React + TypeScript + Tailwind CSS |
| Backend | FastAPI (Python) |
| Database | MongoDB |
| Mobile | Capacitor (Android) |
| Auth | Supabase + JWT |
| Analytics | PostHog |

---

## Project Structure

```
iHhashi/
├── frontend/          # React + Capacitor app
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── lib/
│   └── android/
├── backend/           # FastAPI server
│   ├── app/
│   │   ├── routes/
│   │   ├── models/
│   │   └── services/
│   └── tests/
└── docs/              # Documentation
```

---

## Current Status

- ✅ Project scaffolded
- ✅ Models defined
- ✅ Routes stubbed
- ✅ Frontend UI started
- ✅ Debug APK built
- ⏳ Database connection
- ⏳ Auth implementation
- ⏳ Real functionality

---

## South Africa Specific

- **Currency**: ZAR (R)
- **Local foods**: Kota, Bunny Chow, Gatsby, Braai
- **Coverage**: All 9 provinces

---

## Next Steps

1. Set up MongoDB (Atlas or local)
2. Implement JWT auth fully
3. Add geolocation (Google Maps/OpenStreetMap)
4. Integrate Stripe payments
5. Push notifications
6. Testing
7. Deployment

---

#iHhashi #project