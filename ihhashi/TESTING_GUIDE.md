# iHhashi Testing Guide

## Backend Tests

### Running Tests

```bash
cd backend

# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run with verbose output
pytest -v

# Run only unit tests (skip integration)
pytest -m unit

# Run without slow tests
pytest -m "not slow"
```

### Test Structure

```
backend/tests/
├── conftest.py              # Test fixtures and configuration
├── test_auth.py             # Authentication tests
├── test_orders.py           # Order management tests
├── test_payments.py         # Payment processing tests
├── test_referrals.py        # Referral system tests
├── test_customer_rewards.py # Customer rewards tests
├── test_merchants.py        # Merchant operations tests
├── test_websocket.py        # WebSocket connection tests
└── test_utils.py            # Test utilities
```

### Fixtures Available

- `test_user` - Standard buyer user
- `test_merchant` - Merchant user
- `test_driver` - Driver user with driver profile
- `test_admin` - Admin user
- `test_customer` - Customer for rewards testing
- `test_store` - Store/merchant
- `test_product` - Product
- `test_order` - Order with items
- `buyer_auth_headers`, `merchant_auth_headers`, etc. - Auth headers
- `mock_paystack` - Mocked Paystack service
- `mock_redis` - Mocked Redis

## Frontend Tests

### Running Tests

```bash
cd frontend

# Run tests
npm test

# Run in watch mode
npm run test:watch

# Run with coverage
npm run test:coverage

# Run E2E tests
npm run test:e2e
```

### Test Structure

```
frontend/src/__tests__/
├── setup.ts                 # Test setup and mocks
├── components/
│   ├── SplashScreen.test.tsx
│   ├── Header.test.tsx
│   ├── LanguageSelector.test.tsx
│   ├── MerchantCard.test.tsx
│   └── CategoryBar.test.tsx
└── hooks/
    └── useCart.test.ts
```

## Writing New Tests

### Backend Test Template

```python
import pytest
from httpx import AsyncClient
from fastapi import status

class TestFeature:
    @pytest.mark.asyncio
    async def test_specific_feature(
        self,
        async_client: AsyncClient,
        test_user,
        buyer_auth_headers
    ):
        response = await async_client.get(
            "/api/v1/endpoint",
            headers=buyer_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "expected_field" in data
```

### Frontend Test Template

```typescript
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Component } from '../../components/Component';

describe('Component', () => {
  it('renders correctly', () => {
    render(<Component />);
    expect(screen.getByText('Expected Text')).toBeInTheDocument();
  });
});
```

## CI/CD Integration

Tests run automatically on:
- Pull requests
- Pushes to main branch
- Release tags

See `.github/workflows/ci-cd.yml` for configuration.
