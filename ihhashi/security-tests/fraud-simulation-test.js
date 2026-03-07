// Fraud Simulation Test Suite for iHhashi Platform
// Comprehensive security testing using K6

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Counter } from 'k6/metrics';

// Metrics
const fraudDetectedRate = new Rate('fraud_detected');
const securityBypassRate = new Rate('security_bypass');
const blockedAttempts = new Counter('blocked_attempts');
const successfulAttacks = new Counter('successful_attacks');

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API = `${BASE_URL}/api`;

export const options = {
  scenarios: {
    // Test rate limiting
    rateLimiting: {
      executor: 'constant-vus',
      vus: 10,
      duration: '2m',
      exec: 'testRateLimiting',
    },
    
    // Test authentication attacks
    authAttacks: {
      executor: 'per-vu-iterations',
      vus: 5,
      iterations: 100,
      exec: 'testAuthenticationBypass',
      startTime: '2m',
    },
    
    // Test order manipulation
    orderFraud: {
      executor: 'per-vu-iterations',
      vus: 5,
      iterations: 50,
      exec: 'testOrderFraud',
      startTime: '4m',
    },
    
    // Test payment manipulation
    paymentFraud: {
      executor: 'per-vu-iterations',
      vus: 3,
      iterations: 30,
      exec: 'testPaymentFraud',
      startTime: '6m',
    },
    
    // Test input validation
    injectionAttacks: {
      executor: 'per-vu-iterations',
      vus: 5,
      iterations: 50,
      exec: 'testInjectionAttacks',
      startTime: '7m',
    },
    
    // Test session hijacking
    sessionAttacks: {
      executor: 'per-vu-iterations',
      vus: 5,
      iterations: 30,
      exec: 'testSessionAttacks',
      startTime: '9m',
    },
  },
  
  thresholds: {
    fraud_detected: ['rate>0.9'], // 90% of fraud should be detected
    security_bypass: ['rate<0.01'], // Less than 1% bypass rate
    blocked_attempts: ['count>100'], // Should block many attempts
    successful_attacks: ['count<5'], // Very few successful attacks
  },
};

// ============================================
// TEST 1: Rate Limiting
// ============================================
export function testRateLimiting() {
  let blocked = 0;
  let success = 0;
  
  // Brute force login attempts
  for (let i = 0; i < 20; i++) {
    const response = http.post(`${API}/auth/login`, {
      username: `victim@example.com`,
      password: `password${i}`,
    });
    
    if (response.status === 429) {
      blocked++;
      blockedAttempts.add(1);
    } else if (response.status === 401) {
      success++; // Expected for wrong password
    } else if (response.status === 200) {
      successfulAttacks.add(1);
    }
  }
  
  fraudDetectedRate.add(blocked > 0);
  sleep(1);
  
  // Test registration spam
  blocked = 0;
  for (let i = 0; i < 15; i++) {
    const response = http.post(`${API}/auth/register`, {
      email: `spam${i}@test.com`,
      password: 'TestPass123!',
      full_name: 'Spam User',
      phone: `+27${Math.floor(Math.random() * 1000000000)}`,
    });
    
    if (response.status === 429) {
      blocked++;
      blockedAttempts.add(1);
    }
  }
  
  fraudDetectedRate.add(blocked > 0);
}

// ============================================
// TEST 2: Authentication Bypass
// ============================================
export function testAuthenticationBypass() {
  // Test with invalid tokens
  const invalidTokens = [
    'invalid.token.here',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c',
    '', // Empty token
    'null',
    'undefined',
  ];
  
  for (const token of invalidTokens) {
    const response = http.get(`${API}/auth/me`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    
    const isBlocked = response.status === 401 || response.status === 403;
    check(response, {
      'invalid token rejected': (r) => isBlocked,
    });
    
    if (!isBlocked) {
      successfulAttacks.add(1);
      securityBypassRate.add(1);
    }
    
    fraudDetectedRate.add(isBlocked);
  }
  
  // Test with expired tokens (if we can generate them)
  // Test with tampered payloads
  const tamperedPayload = btoa(JSON.stringify({ sub: 'admin', role: 'admin', exp: 9999999999 }));
  const tamperedToken = `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.${tamperedPayload}.fake_signature`;
  
  const tamperedResponse = http.get(`${API}/auth/me`, {
    headers: { 'Authorization': `Bearer ${tamperedToken}` },
  });
  
  const tamperedBlocked = tamperedResponse.status === 401 || tamperedResponse.status === 403;
  fraudDetectedRate.add(tamperedBlocked);
  
  if (!tamperedBlocked) {
    successfulAttacks.add(1);
  }
  
  sleep(0.5);
}

// ============================================
// TEST 3: Order Fraud
// ============================================
export function testOrderFraud() {
  // Attempt to access other users' orders
  const fakeOrderIds = [
    '507f1f77bcf86cd799439011', // Valid ObjectId format
    '507f1f77bcf86cd799439012',
    '507f1f77bcf86cd799439013',
  ];
  
  for (const orderId of fakeOrderIds) {
    const response = http.get(`${API}/orders/${orderId}`, {
      headers: { 'Authorization': 'Bearer invalid_token' },
    });
    
    const isBlocked = response.status === 401 || response.status === 403 || response.status === 404;
    check(response, {
      'unauthorized order access blocked': (r) => isBlocked,
    });
    
    if (!isBlocked) {
      successfulAttacks.add(1);
      securityBypassRate.add(1);
    }
    
    fraudDetectedRate.add(isBlocked);
  }
  
  // Test order manipulation
  const manipulations = [
    // Negative quantities
    { items: [{ product_id: 'prod1', quantity: -5 }], delivery_address_id: 'addr1', store_id: 'store1', payment_method: 'card' },
    // Zero amount
    { items: [{ product_id: 'prod1', quantity: 0 }], delivery_address_id: 'addr1', store_id: 'store1', payment_method: 'card' },
    // Huge quantity (stock exhaustion)
    { items: [{ product_id: 'prod1', quantity: 999999 }], delivery_address_id: 'addr1', store_id: 'store1', payment_method: 'card' },
    // Price manipulation (shouldn't be client-controllable)
    { items: [{ product_id: 'prod1', quantity: 1, price: 0.01 }], delivery_address_id: 'addr1', store_id: 'store1', payment_method: 'card' },
  ];
  
  for (const orderData of manipulations) {
    const response = http.post(`${API}/orders/`, JSON.stringify(orderData), {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer test_token',
      },
    });
    
    const isBlocked = response.status === 400 || response.status === 401 || response.status === 422;
    check(response, {
      'order manipulation blocked': (r) => isBlocked,
    });
    
    if (!isBlocked && response.status !== 404) {
      successfulAttacks.add(1);
    }
    
    fraudDetectedRate.add(isBlocked);
  }
  
  sleep(0.5);
}

// ============================================
// TEST 4: Payment Fraud
// ============================================
export function testPaymentFraud() {
  // Test callback URL manipulation (open redirect)
  const maliciousCallbacks = [
    'https://evil.com/steal-data',
    'javascript:alert(1)',
    'http://localhost:8000/api/payments/webhook', // Internal URL
    'file:///etc/passwd',
  ];
  
  for (const callback of maliciousCallbacks) {
    const response = http.post(`${API}/payments/initialize`, JSON.stringify({
      amount: 100,
      callback_url: callback,
    }), {
      headers: { 'Content-Type': 'application/json' },
    });
    
    const isBlocked = response.status === 400 || response.status === 401 || response.status === 403;
    check(response, {
      'malicious callback blocked': (r) => isBlocked,
    });
    
    if (!isBlocked && response.status !== 404) {
      successfulAttacks.add(1);
    }
    
    fraudDetectedRate.add(isBlocked);
  }
  
  // Test amount manipulation
  const amounts = [-100, 0, 0.01, 999999999];
  
  for (const amount of amounts) {
    const response = http.post(`${API}/payments/initialize`, JSON.stringify({
      amount: amount,
      callback_url: 'https://ihhashi.app/payment/callback',
    }), {
      headers: { 'Content-Type': 'application/json' },
    });
    
    const isBlocked = response.status === 400 || response.status === 422;
    fraudDetectedRate.add(isBlocked);
  }
  
  // Test webhook replay attacks
  const fakeWebhookData = {
    event: 'charge.success',
    data: {
      reference: 'fake-reference-123',
      amount: 10000,
      status: 'success',
    },
  };
  
  // Send same webhook multiple times
  for (let i = 0; i < 5; i++) {
    const response = http.post(`${API}/payments/webhook`, JSON.stringify(fakeWebhookData), {
      headers: {
        'Content-Type': 'application/json',
        'X-Paystack-Signature': 'fake_signature',
      },
    });
    
    // Should be idempotent - no double processing
    check(response, {
      'webhook processed idempotently': (r) => r.status < 500,
    });
  }
  
  sleep(0.5);
}

// ============================================
// TEST 5: Injection Attacks
// ============================================
export function testInjectionAttacks() {
  // SQL/NoSQL Injection attempts
  const injectionPayloads = [
    { email: "admin' OR '1'='1", password: "anything" },
    { email: "admin'; DROP TABLE users; --", password: "test" },
    { email: { "$gt": "" }, password: { "$gt": "" } }, // NoSQL injection
    { email: { "$ne": null }, password: { "$ne": null } },
    { email: "admin", password: { "$regex": ".*" } },
  ];
  
  for (const payload of injectionPayloads) {
    const response = http.post(`${API}/auth/login`, payload);
    
    const isBlocked = response.status === 401 || response.status === 400 || response.status === 422;
    check(response, {
      'injection attack blocked': (r) => isBlocked,
    });
    
    if (!isBlocked && response.status === 200) {
      successfulAttacks.add(1);
      securityBypassRate.add(1);
    }
    
    fraudDetectedRate.add(isBlocked);
  }
  
  // XSS attempts
  const xssPayloads = [
    '<script>alert("XSS")</script>',
    '<img src=x onerror=alert(1)>',
    'javascript:alert(1)',
    '<svg onload=alert(1)>',
  ];
  
  for (const xss of xssPayloads) {
    const response = http.post(`${API}/auth/register`, {
      email: 'test@test.com',
      password: 'TestPass123!',
      full_name: xss,
      phone: '+27123456789',
    });
    
    // Check if payload is reflected in response
    const reflects = response.body.includes(xss);
    if (reflects) {
      successfulAttacks.add(1);
      securityBypassRate.add(1);
    }
    
    fraudDetectedRate.add(!reflects);
  }
  
  sleep(0.5);
}

// ============================================
// TEST 6: Session Attacks
// ============================================
export function testSessionAttacks() {
  // Test token fixation
  const oldToken = 'old_session_token_123';
  
  // Try to use token after "logout"
  const logoutResponse = http.post(`${API}/auth/logout`, {}, {
    headers: { 'Authorization': `Bearer ${oldToken}` },
  });
  
  // Try to use the same token again
  const reuseResponse = http.get(`${API}/auth/me`, {
    headers: { 'Authorization': `Bearer ${oldToken}` },
  });
  
  const isBlocked = reuseResponse.status === 401 || reuseResponse.status === 403;
  fraudDetectedRate.add(isBlocked);
  
  // Test concurrent session handling
  // Login multiple times with same credentials
  const tokens = [];
  for (let i = 0; i < 3; i++) {
    const response = http.post(`${API}/auth/login`, {
      username: 'test@test.com',
      password: 'TestPass123!',
    });
    
    if (response.status === 200) {
      tokens.push(response.json('access_token'));
    }
    sleep(0.1);
  }
  
  // All tokens should work or only the latest should work
  let validTokens = 0;
  for (const token of tokens) {
    const checkResponse = http.get(`${API}/auth/me`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    if (checkResponse.status === 200) validTokens++;
  }
  
  // If all tokens are valid, consider it a potential issue
  // (depends on your security policy - some systems allow concurrent sessions)
  
  sleep(0.5);
}

// Helper function for base64 encoding
function btoa(str) {
  return Buffer.from(str).toString('base64');
}

// Run with: k6 run fraud-simulation-test.js
