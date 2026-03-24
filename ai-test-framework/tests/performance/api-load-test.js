import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');

// Test configuration
export const options = {
  stages: [
    { duration: '1m', target: 10 },   // Ramp up to 10 users
    { duration: '3m', target: 50 },   // Ramp up to 50 users
    { duration: '5m', target: 100 },  // Stay at 100 users
    { duration: '2m', target: 0 },    // Ramp down to 0
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests must complete below 500ms
    http_req_failed: ['rate<0.01'],    // Error rate must be less than 1%
    errors: ['rate<0.1'],              // Custom error rate must be less than 10%
  },
};

const BASE_URL = __ENV.API_URL || 'http://localhost:3000';

export default function () {
  // Test 1: Health check
  let healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, {
    'health status is 200': (r) => r.status === 200,
  }) || errorRate.add(1);

  // Test 2: Get users
  let usersRes = http.get(`${BASE_URL}/api/v1/users`);
  check(usersRes, {
    'users status is 200': (r) => r.status === 200,
    'users response time < 200ms': (r) => r.timings.duration < 200,
  }) || errorRate.add(1);

  // Test 3: Get products
  let productsRes = http.get(`${BASE_URL}/api/v1/products`);
  check(productsRes, {
    'products status is 200': (r) => r.status === 200,
    'products has data': (r) => JSON.parse(r.body).length > 0,
  }) || errorRate.add(1);

  // Test 4: Create order (POST request)
  let orderPayload = JSON.stringify({
    userId: Math.floor(Math.random() * 1000),
    items: [
      { productId: 1, quantity: 2 },
      { productId: 2, quantity: 1 },
    ],
  });

  let orderRes = http.post(`${BASE_URL}/api/v1/orders`, orderPayload, {
    headers: { 'Content-Type': 'application/json' },
  });

  check(orderRes, {
    'order status is 201': (r) => r.status === 201,
    'order has ID': (r) => JSON.parse(r.body).id !== undefined,
  }) || errorRate.add(1);

  // Think time between iterations
  sleep(Math.random() * 3 + 1); // Random sleep between 1-4 seconds
}

export function handleSummary(data) {
  return {
    'api-performance-results.json': JSON.stringify(data, null, 2),
    stdout: JSON.stringify(data.metrics, null, 2),
  };
}
