# iHhashi API Reference v2

## Base URL
```
Production: https://api.ihhashi.app
Development: http://localhost:8000
```

## Authentication
All protected endpoints require Bearer token:
```
Authorization: Bearer <supabase_jwt_token>
```

---

## Orders API (`/api/v2/orders`)

### Create Order
```http
POST /api/v2/orders
```

**Request Body:**
```json
{
  "store_id": "store-uuid",
  "items": [
    {"product_id": "prod-uuid", "quantity": 2}
  ],
  "delivery_address_id": "address-uuid",
  "payment_method": "cash",
  "buyer_notes": "Ring doorbell twice"
}
```

**Response:**
```json
{
  "order_id": "order-uuid",
  "status": "pending",
  "subtotal": 150.00,
  "base_delivery_fee": 35.00,
  "estimated_delivery_minutes": 45,
  "message": "Order created. Waiting for store confirmation and rider bids."
}
```

### Get Order
```http
GET /api/v2/orders/{order_id}
```

### Track Order (Real-time)
```http
GET /api/v2/orders/{order_id}/track
```

### Update Order Status
```http
PUT /api/v2/orders/{order_id}/status
```

**Request Body:**
```json
{
  "status": "delivered",
  "notes": "Left at door",
  "lat": -26.2041,
  "lng": 28.0473
}
```

### Rider Bidding

#### Submit Bid
```http
POST /api/v2/orders/{order_id}/bid
```

**Request Body:**
```json
{
  "order_id": "order-uuid",
  "bid_amount": 30.00,
  "estimated_minutes": 25,
  "message": "I'm nearby!"
}
```

#### Accept Rider Bid
```http
POST /api/v2/orders/{order_id}/accept-rider?rider_id=rider-uuid
```

---

## Merchants API (`/api/v2/merchants`)

### Search Merchants
```http
GET /api/v2/merchants
  ?lat=-26.2041
  &lng=28.0473
  &radius_km=5
  &category=restaurant
  &open_now=true
```

**Response:**
```json
{
  "merchants": [
    {
      "id": "merchant-uuid",
      "name": "Spaza Express",
      "category": "grocery",
      "distance_km": 1.2,
      "is_open": true,
      "rating": 4.5
    }
  ],
  "total": 15
}
```

### Get Merchant Menu
```http
GET /api/v2/merchants/{merchant_id}/menu
```

### Get Merchant Products
```http
GET /api/v2/merchants/{merchant_id}/products
  ?category_id=cat-uuid
  &search=bread
  &min_price=10
  &max_price=100
```

### Create Merchant
```http
POST /api/v2/merchants
```

**Request Body:**
```json
{
  "name": "My Store",
  "category": "retail",
  "address_line1": "123 Main Street",
  "city": "Johannesburg",
  "latitude": -26.2041,
  "longitude": 28.0473,
  "phone": "+27821234567",
  "email": "store@example.com"
}
```

---

## Riders API (`/api/v2/riders`)

### Get Profile
```http
GET /api/v2/riders/profile
```

### Create Profile
```http
POST /api/v2/riders/profile
```

**Request Body:**
```json
{
  "name": "John Doe",
  "phone": "+27821234567",
  "vehicle_type": "motorcycle",
  "vehicle_plate": "CA123456",
  "bank_name": "FNB",
  "bank_account_number": "1234567890",
  "bank_account_name": "John Doe"
}
```

### Update Status & Location
```http
PUT /api/v2/riders/status
```

**Request Body:**
```json
{
  "lat": -26.2041,
  "lng": 28.0473,
  "status": "available"
}
```

### Get Available Orders
```http
GET /api/v2/riders/orders/available?radius_km=3
```

### Accept Order
```http
POST /api/v2/riders/orders/{order_id}/accept
  ?delivery_fee=35.00
  &estimated_minutes=25
```

### Get Earnings
```http
GET /api/v2/riders/earnings?period=today
```

**Response:**
```json
{
  "period": "today",
  "total_orders": 8,
  "total_distance_km": 24.5,
  "total_earnings": 280.00,
  "total_tips": 45.00,
  "pending_payout": 325.00
}
```

---

## Payments API (`/api/payments`)

### Initialize Payment
```http
POST /api/payments/initialize
```

### Verify Payment
```http
GET /api/payments/verify/{reference}
```

### Webhook
```http
POST /api/payments/webhook
```

Handled events:
- `charge.success`
- `transfer.success`
- `transfer.failed`
- `charge.refunded`

---

## WebSocket Endpoints

### Order Tracking
```
ws://api.ihhashi.app/ws/track/{order_id}
```

Messages:
```json
{"type": "connected"}
{"type": "rider_location", "lat": -26.2, "lng": 28.0}
{"type": "status_update", "status": "in_transit"}
```

### Rider Connection
```
ws://api.ihhashi.app/ws/rider/{rider_id}
```

Messages:
```json
{"type": "location_update", "lat": -26.2, "lng": 28.0, "order_id": "..."}
{"type": "new_order", "order": {...}}
```

---

## Nduna Chatbot (`/api/nduna`)

### Chat
```http
POST /api/nduna/chat
```

**Request Body:**
```json
{
  "message": "Where is my order?",
  "language": "en",
  "context": {"order_id": "..."}
}
```

**Response:**
```json
{
  "response": "Let me check your order status...",
  "language": "en",
  "detected_intent": "track_order",
  "suggested_actions": ["View order status", "Contact rider"]
}
```

### Supported Languages
- `en` - English
- `zu` - isiZulu
- `xh` - isiXhosa
- `af` - Afrikaans
- `st` - Sesotho
- `tn` - Setswana
- `ts` - Xitsonga
- `ve` - Tshivenda
- `ss` - siSwati
- `nr` - isiNdebele
- `nso` - Sepedi

### Translate
```http
POST /api/nduna/translate
```

---

## Error Responses

All errors follow this format:
```json
{
  "detail": "Error message here"
}
```

Common status codes:
- `400` - Bad Request (validation error)
- `401` - Unauthorized (missing/invalid token)
- `403` - Forbidden (no permission)
- `404` - Not Found
- `500` - Internal Server Error

---

## Rate Limits

- General API: 100 requests/minute
- WebSocket: 10 messages/second
- Nduna Chat: 20 messages/minute
