# Architecture Overview

> System architecture for iHhashi delivery platform

---

## High-Level Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Customer  │     │   Merchant  │     │    Rider    │
│    Mobile   │     │   Dashboard │     │    Mobile   │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                    ┌──────▼──────┐
                    │   FastAPI   │
                    │   Backend   │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐ ┌───▼───┐ ┌──────▼──────┐
       │   MongoDB   │ │Supabase│ │  PostHog   │
       │   (Data)    │ │(Auth)  │ │(Analytics) │
       └─────────────┘ └────────┘ └─────────────┘
```

---

## Frontend Stack

### Framework
- **React 18** with TypeScript
- **Vite** for build tooling
- **Tailwind CSS** for styling

### Mobile
- **Capacitor** for native wrapper
- **Android** target (app-id: com.ihhashi.delivery)

### Key Dependencies
- `@supabase/supabase-js` - Auth
- `posthog-js` - Analytics
- `react-router-dom` - Routing

---

## Backend Stack

### Framework
- **FastAPI** (Python)
- **Uvicorn** ASGI server

### Database
- **MongoDB** for data storage
- **Supabase** for authentication

### Key Endpoints
- `/auth` - Authentication routes
- `/users` - User management
- `/merchants` - Merchant operations
- `/orders` - Order processing
- `/riders` - Rider management

---

## Data Models

### User
```python
{
    "email": str,
    "phone": str,
    "role": "customer" | "merchant" | "rider",
    "location": {
        "lat": float,
        "lng": float
    }
}
```

### Merchant
```python
{
    "name": str,
    "category": str,
    "menu": [...],
    "hours": {...},
    "location": {...}
}
```

### Order
```python
{
    "items": [...],
    "status": "pending" | "confirmed" | "preparing" | "ready" | "delivered",
    "delivery_address": {...},
    "tracking": {...}
}
```

### Rider
```python
{
    "vehicle": "bike" | "car" | "scooter",
    "status": "available" | "busy" | "offline",
    "location": {...},
    "earnings": float
}
```

---

## Authentication Flow

1. User signs up with email/phone
2. Supabase handles auth
3. JWT token issued
4. Token stored locally
5. Token sent with API requests

---

## Deployment

- **Frontend**: Play Store (Android)
- **Backend**: Cloud provider (TBD)
- **Database**: MongoDB Atlas
- **Auth**: Supabase Cloud

---

#iHhashi #architecture