# User Types

> Three primary user types in iHhashi

---

## 1. Customers

### Capabilities
- Browse merchants by category/location
- View menus and item details
- Add items to cart
- Place orders
- Track delivery in real-time
- Rate merchants and riders
- View order history

### Key Features
- Location-based merchant discovery
- Search and filter
- Favorites
- Payment integration
- Push notifications

---

## 2. Merchants

### Capabilities
- Manage menu (add/edit/remove items)
- Receive and process orders
- Update order status
- View analytics
- Manage operating hours
- Handle promotions

### Dashboard Features
- Order queue
- Sales analytics
- Popular items
- Customer ratings
- Revenue tracking

---

## 3. Riders

### Capabilities
- Accept/reject delivery requests
- Navigate to pickup/delivery
- Update delivery status
- View earnings
- Manage availability

### App Features
- Map integration
- Order queue
- Earnings dashboard
- Delivery history
- Availability toggle

---

## User Flow

```
Customer              Merchant              Rider
   │                     │                     │
   ├─ Browse ───────────►│                     │
   │                     │                     │
   ├─ Place Order ──────►│                     │
   │                     │                     │
   │                     ├─ Confirm ──────────►│
   │                     │                     │
   │                     ├─ Prepare            │
   │                     │                     │
   │                     ├─ Ready ────────────►│
   │                     │                     │
   │◄────────────────────┼─────────────────────┤
   │       Delivered     │                     │
```

---

#iHhashi #users