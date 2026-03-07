# 🛡️ Security & Concurrency Remediation Plan
**iHhashi Backend - Prioritized Action Plan**
*Generated: 2026-02-27*
*Agents: ShieldGuard + BugHunter + DocMaster + Obsidian*

---

## 🔴 CRITICAL: Concurrency Issues (Fix Immediately)

### C1. Race Condition in Stock Management
**File:** `backend/app/routes/orders.py`
**Issue:** Stock check and order creation are separate operations - allows overselling
**Risk:** Customers can order out-of-stock items, inventory corruption

**Fix:**
```python
# Use atomic find_one_and_update with condition
result = await products_col.find_one_and_update(
    {
        "_id": safe_object_id(item["product_id"]),
        "store_id": order_data.store_id,
        "stock_quantity": {"$gte": item["quantity"]}  # Atomic check
    },
    {"$inc": {"stock_quantity": -item["quantity"]}},
    return_document=True
)
if not result:
    raise HTTPException(status_code=400, detail="Insufficient stock")
```

### C2. Non-Atomic Order Creation
**File:** `backend/app/routes/orders.py`
**Issue:** Multiple DB operations without transaction - partial failures possible
**Risk:** Orphaned data, inconsistent state

**Fix:** Use MongoDB transactions for order creation

---

## 🟠 HIGH PRIORITY: Security Issues

### S1. Order Tracking Authentication (Medium)
**File:** `backend/app/routes/websocket.py`
**Issue:** `/ws/track/{order_id}` accepts unauthenticated connections
**Risk:** Order enumeration attack

**Fix:** Require authentication or order token for tracking

### S2. Missing Rate Limiting (Medium)
**Files:** `orders.py`, `riders.py`
**Issue:** Critical endpoints lack rate limiting
**Risk:** Order spam, API abuse

**Fix:** Add `@limiter.limit("20/minute")` decorators

---

## 🟡 MEDIUM PRIORITY: Input Validation

### S3. Location Coordinate Validation (Low)
**File:** `backend/app/routes/websocket.py`
**Issue:** No validation on lat/lng values
**Fix:** Validate latitude (-90 to 90) and longitude (-180 to 180)

### S4. Order Quantity Limits (Low)
**File:** `backend/app/routes/orders.py`
**Issue:** No max quantity per item
**Fix:** Add max quantity validation (e.g., 99 per item)

### S5. Buyer Notes Sanitization (Low)
**File:** `backend/app/routes/orders.py`
**Issue:** No length limit or sanitization
**Fix:** Add max length (500 chars) and strip HTML

---

## 📋 File-by-File Changes

| File | Changes | Priority |
|------|---------|----------|
| `routes/orders.py` | Atomic stock ops, transactions, rate limits, quantity limits | 🔴 Critical |
| `routes/websocket.py` | Auth for tracking, location validation | 🟠 High |
| `routes/riders.py` | Rate limiting | 🟠 High |
| `models/order.py` | Add quantity constraints | 🟡 Medium |
| `middleware/rate_limit.py` | Add order_rate_limit decorator | 🟡 Medium |

---

## ✅ Implementation Order

1. **Phase 1 (Critical):** Fix concurrency in orders.py
   - Atomic stock decrement
   - MongoDB transactions for order creation
   - Add idempotency key support

2. **Phase 2 (High):** Security hardening
   - Authenticate order tracking WebSocket
   - Add rate limiting to all critical endpoints

3. **Phase 3 (Medium):** Input validation
   - Coordinate validation
   - Quantity limits
   - Notes sanitization

---

## 🧪 Testing Requirements (BugHunter)

1. Concurrency tests: Simultaneous order creation for same product
2. Rate limit tests: Verify 429 responses after limit exceeded
3. Auth tests: Verify unauthenticated tracking is blocked
4. Input validation: Boundary tests for coordinates and quantities

---

*Coordinated by Agent Orchestra - ShieldGuard, BugHunter, DocMaster, Obsidian*
