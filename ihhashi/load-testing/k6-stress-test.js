// K6 Load Testing Script for iHhashi Platform
// Comprehensive stress test covering all critical endpoints

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const orderLatency = new Trend('order_latency');
const authLatency = new Trend('auth_latency');
const paymentLatency = new Trend('payment_latency');
const trackingLatency = new Trend('tracking_latency');
const activeUsers = new Counter('active_users');

// Configuration - UPDATE THESE FOR YOUR ENVIRONMENT
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_V1 = `${BASE_URL}/api`;
const API_V2 = `${BASE_URL}/api/v2`;

// Test data
const TEST_USERS = [
  { email: 'buyer1@test.com', password: 'TestPass123!' },
  { email: 'buyer2@test.com', password: 'TestPass123!' },
  { email: 'merchant1@test.com', password: 'TestPass123!' },
  { email: 'driver1@test.com', password: 'TestPass123!' },
];

// Scenarios
export const options = {
  scenarios: {
    // 1. Smoke test - verify system works under minimal load
    smoke: {
      executor: 'constant-vus',
      vus: 5,
      duration: '1m',
      tags: { test_type: 'smoke' },
      exec: 'smokeTest',
    },
    
    // 2. Load test - normal expected load
    load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 50 },   // Ramp up to 50 users
        { duration: '5m', target: 50 },   // Stay at 50 users
        { duration: '2m', target: 100 },  // Ramp up to 100 users
        { duration: '5m', target: 100 },  // Stay at 100 users
        { duration: '2m', target: 0 },    // Ramp down
      ],
      tags: { test_type: 'load' },
      exec: 'normalUserFlow',
    },
    
    // 3. Stress test - find breaking point
    stress: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 200 },  // Ramp up
        { duration: '3m', target: 200 },  // Stay
        { duration: '2m', target: 400 },  // Push harder
        { duration: '3m', target: 400 },  // Stay
        { duration: '2m', target: 600 },  // Push to limit
        { duration: '3m', target: 600 },  // Stay
        { duration: '5m', target: 0 },    // Recovery
      ],
      tags: { test_type: 'stress' },
      exec: 'aggressiveUserFlow',
      startTime: '15m', // Start after load test
    },
    
    // 4. Spike test - sudden traffic burst
    spike: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '10s', target: 0 },
        { duration: '30s', target: 500 }, // Sudden spike
        { duration: '1m', target: 500 },  // Stay spiked
        { duration: '30s', target: 0 },   // Drop
        { duration: '2m', target: 0 },    // Recovery
      ],
      tags: { test_type: 'spike' },
      exec: 'browsingFlow',
      startTime: '35m',
    },
    
    // 5. Soak test - extended duration
    soak: {
      executor: 'constant-vus',
      vus: 50,
      duration: '1h',
      tags: { test_type: 'soak' },
      exec: 'normalUserFlow',
      startTime: '40m',
    },
  },
  
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'], // 95% under 500ms, 99% under 1s
    errors: ['rate<0.05'], // Less than 5% errors
    order_latency: ['p(95)<800'],
    auth_latency: ['p(95)<300'],
    payment_latency: ['p(95)<1000'],
    tracking_latency: ['p(95)<200'],
    http_req_failed: ['rate<0.05'],
  },
};

// Helper functions
function getRandomUser() {
  return TEST_USERS[Math.floor(Math.random() * TEST_USERS.length)];
}

function login(user) {
  const startTime = new Date();
  const response = http.post(`${API_V1}/auth/login`, {
    username: user.email,
    password: user.password,
  });
  authLatency.add(new Date() - startTime);
  
  check(response, {
    'login successful': (r) => r.status === 200,
    'has access token': (r) => r.json('access_token') !== undefined,
  });
  
  return response.json('access_token');
}

function authenticatedRequest(method, url, token, body = null) {
  const params = {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  };
  
  if (body) {
    return http[method](url, JSON.stringify(body), params);
  }
  return http[method](url, params);
}

// Scenario: Smoke test
export function smokeTest() {
  // Health check
  const health = http.get(`${BASE_URL}/health`);
  check(health, {
    'health check OK': (r) => r.status === 200,
    'database healthy': (r) => r.json('database.status') === 'healthy',
  });
  
  // Root endpoint
  const root = http.get(`${BASE_URL}/`);
  check(root, {
    'root OK': (r) => r.status === 200,
    'has version': (r) => r.json('version') !== undefined,
  });
  
  sleep(1);
}

// Scenario: Normal user flow
export function normalUserFlow() {
  activeUsers.add(1);
  const user = getRandomUser();
  
  // 1. Login
  const token = login(user);
  if (!token) {
    errorRate.add(1);
    return;
  }
  sleep(1);
  
  // 2. Get profile
  const profile = authenticatedRequest('get', `${API_V1}/auth/me`, token);
  check(profile, { 'profile fetched': (r) => r.status === 200 });
  sleep(0.5);
  
  // 3. Browse products/stores
  const stores = http.get(`${API_V1}/vendors/stores`);
  check(stores, { 'stores fetched': (r) => r.status === 200 });
  sleep(1);
  
  // 4. Get orders
  const orders = authenticatedRequest('get', `${API_V1}/orders/`, token);
  check(orders, { 'orders fetched': (r) => r.status === 200 });
  sleep(0.5);
  
  // 5. Track an order (simulated)
  const startTime = new Date();
  const tracking = http.get(`${API_V1}/orders/test-order-123/track`);
  trackingLatency.add(new Date() - startTime);
  check(tracking, { 'tracking OK': (r) => r.status === 200 || r.status === 404 });
  sleep(1);
  
  // 6. Logout
  const logout = authenticatedRequest('post', `${API_V1}/auth/logout`, token);
  check(logout, { 'logout OK': (r) => r.status === 200 });
  
  activeUsers.add(-1);
  sleep(2);
}

// Scenario: Aggressive user flow
export function aggressiveUserFlow() {
  const user = getRandomUser();
  
  // Rapid-fire operations
  const token = login(user);
  if (!token) return;
  
  // Create orders rapidly
  for (let i = 0; i < 3; i++) {
    const startTime = new Date();
    const order = authenticatedRequest('post', `${API_V1}/orders/`, token, {
      store_id: 'store-test-123',
      items: [
        { product_id: 'prod-1', quantity: 1 },
      ],
      delivery_address_id: 'addr-1',
      payment_method: 'card',
    });
    orderLatency.add(new Date() - startTime);
    
    check(order, {
      'order created': (r) => r.status === 201 || r.status === 404 || r.status === 400,
    });
    
    sleep(0.5);
  }
  
  // Check WebSocket connection capability
  // Note: K6 doesn't natively support WebSockets in the same way,
  // but we can test the handshake endpoint
  const ws = http.get(`${BASE_URL}/ws/tracking/test-order`);
  check(ws, { 'ws endpoint reachable': (r) => r.status < 500 });
  
  sleep(1);
}

// Scenario: Browsing flow (read-heavy)
export function browsingFlow() {
  // No auth needed for browsing
  const stores = http.get(`${API_V1}/vendors/stores`);
  check(stores, { 'stores OK': (r) => r.status === 200 });
  
  const products = http.get(`${API_V1}/products/`);
  check(products, { 'products OK': (r) => r.status === 200 });
  
  const health = http.get(`${BASE_URL}/health`);
  check(health, { 'health OK': (r) => r.status === 200 });
  
  sleep(0.5);
}

// Teardown - called once after all scenarios
export function teardown() {
  console.log('Load test completed. Check metrics for results.');
}

// Run with: k6 run k6-stress-test.js
// Or with custom config: k6 run --env BASE_URL=https://api.ihhashi.app k6-stress-test.js
