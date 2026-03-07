# Production Monitoring Checklist for iHhashi

## Pre-Launch Monitoring Setup

### 1. Infrastructure Monitoring

#### MongoDB
- [ ] **Metrics to collect:**
  - Connection count (alert if > 80% of max connections)
  - Query execution time (p95 < 100ms)
  - Index usage statistics
  - Disk usage (alert at 80%)
  - Memory usage
  - Replication lag (if using replica sets)
  
- [ ] **Tools:**
  - MongoDB Atlas built-in monitoring (if using Atlas)
  - MongoDB Compass for index analysis
  - Prometheus exporter: `mongodb_exporter`
  
- [ ] **Alerts:**
  ```
  - Connection pool exhausted
  - Query timeout (> 5s)
  - Disk usage > 80%
  - Replication lag > 10s
  ```

#### Redis
- [ ] **Metrics to collect:**
  - Memory usage (alert at 80%)
  - Connection count
  - Hit/miss ratio (target > 90%)
  - Evicted keys
  - Blocked clients
  
- [ ] **Tools:**
  - Redis CLI: `redis-cli --stat`
  - Redis Exporter for Prometheus
  
- [ ] **Alerts:**
  ```
  - Memory usage > 80%
  - Hit ratio < 70%
  - Connection limit reached
  ```

#### Application Server
- [ ] **Metrics to collect:**
  - CPU usage (alert at 80%)
  - Memory usage (alert at 85%)
  - Disk I/O
  - Network throughput
  - Process count
  
- [ ] **Tools:**
  - Prometheus Node Exporter
  - Grafana dashboards
  - New Relic / Datadog (optional)
  
- [ ] **Alerts:**
  ```
  - CPU > 80% for 5 minutes
  - Memory > 85% for 5 minutes
  - Disk usage > 85%
  - Process crashes
  ```

### 2. Application Monitoring

#### FastAPI Backend
- [ ] **APM Setup:**
  - [ ] Sentry/GlitchTip for error tracking (already configured)
  - [ ] Request tracing
  - [ ] Database query logging
  
- [ ] **Custom Metrics:**
  ```python
  # Add to app/main.py
  from prometheus_fastapi_instrumentator import Instrumentator
  
  Instrumentator().instrument(app).expose(app)
  ```
  
- [ ] **Key Metrics:**
  - Request rate (requests/second)
  - Response time (p50, p95, p99)
  - Error rate (target < 1%)
  - Active WebSocket connections
  - Background task queue depth

- [ ] **Logging:**
  ```python
  # Structured logging format
  {
    "timestamp": "2024-01-15T10:30:00Z",
    "level": "INFO",
    "request_id": "abc-123",
    "user_id": "user-456",
    "endpoint": "/api/orders",
    "method": "POST",
    "status_code": 201,
    "duration_ms": 145,
    "message": "Order created successfully"
  }
  ```

- [ ] **Health Checks:**
  - [ ] `/health` endpoint (exists)
  - [ ] `/ready` endpoint (Kubernetes readiness)
  - [ ] Database connectivity check
  - [ ] Redis connectivity check
  - [ ] External API connectivity (Paystack)

### 3. Business Metrics

#### Order Metrics
- [ ] Orders per minute/hour
- [ ] Order value distribution
- [ ] Order status breakdown
- [ ] Average delivery time
- [ ] Order cancellation rate (target < 5%)
- [ ] Failed orders by reason

#### User Metrics
- [ ] Active users (DAU/MAU)
- [ ] Registration rate
- [ ] Login success rate
- [ ] Session duration
- [ ] User retention (D1, D7, D30)

#### Payment Metrics
- [ ] Payment success rate (target > 95%)
- [ ] Payment volume (ZAR/hour)
- [ ] Refund rate (target < 2%)
- [ ] Average transaction value
- [ ] Payment method distribution

#### Delivery Metrics
- [ ] Average pickup time
- [ ] Average delivery time
- [ ] Rider utilization rate
- [ ] Customer rating distribution
- [ ] Delivery success rate

### 4. Security Monitoring

#### Rate Limiting
- [ ] Track rate limit hits per endpoint
- [ ] Alert on sudden spikes
- [ ] Log suspicious patterns

#### Authentication
- [ ] Failed login attempts (alert on spike)
- [ ] Password reset requests
- [ ] Token refresh failures
- [ ] Concurrent sessions per user

#### Fraud Detection
- [ ] Multiple orders from same device/IP
- [ ] Rapid account creation
- [ ] Unusual order patterns
- [ ] Payment anomalies
- [ ] Location spoofing detection

### 5. Third-Party Services

#### Paystack
- [ ] Webhook delivery success
- [ ] API response times
- [ ] Payment failures by type
- [ ] Refund processing time

#### SMS/Email (if configured)
- [ ] Delivery success rate
- [ ] Bounce rate
- [ ] Cost per message

### 6. Frontend Monitoring

#### Performance
- [ ] Core Web Vitals
  - LCP (Largest Contentful Paint) < 2.5s
  - FID (First Input Delay) < 100ms
  - CLS (Cumulative Layout Shift) < 0.1
  
- [ ] JavaScript errors
- [ ] API call failures
- [ ] Page load time by route

#### Tools
- [ ] Google Analytics 4
- [ ] Sentry Browser SDK
- [ ] LogRocket (optional for session replay)

### 7. Alerting Configuration

#### Critical Alerts (immediate response)
```
- Database down
- Redis down
- API error rate > 10%
- Payment webhook failures
- Security breach detected
- SSL certificate expiring
```

#### High Priority (response within 1 hour)
```
- API latency p95 > 2s
- Error rate > 5%
- Disk usage > 85%
- Memory usage > 90%
- Payment success rate < 90%
```

#### Medium Priority (response within 4 hours)
```
- API latency p95 > 1s
- Disk usage > 75%
- Slow database queries
- Rate limit threshold approaching
```

#### Low Priority (response within 24 hours)
```
- Certificate expiring in 30 days
- Disk usage > 65%
- Non-critical feature errors
```

### 8. Dashboard Setup

#### Operations Dashboard
```
- System health status
- Current active users
- Orders in progress
- API response times
- Error rate trend
- Infrastructure metrics
```

#### Business Dashboard
```
- Daily revenue
- Order count
- Active riders
- Customer satisfaction
- Top merchants
- Geographic distribution
```

#### Security Dashboard
```
- Failed login attempts
- Rate limit hits
- Blocked requests
- Suspicious activities
- API key usage
```

### 9. Log Management

#### Log Retention
- [ ] Application logs: 30 days
- [ ] Access logs: 90 days
- [ ] Security logs: 1 year
- [ ] Audit logs: 7 years (if required by law)

#### Log Aggregation
- [ ] Configure Loki (already set up at localhost:3100)
- [ ] Set up log rotation
- [ ] Create retention policies

### 10. Backup & Recovery

#### Database Backups
- [ ] Daily automated backups
- [ ] Weekly backup verification
- [ ] Backup retention: 30 days
- [ ] Point-in-time recovery enabled

#### Disaster Recovery
- [ ] RTO (Recovery Time Objective): 1 hour
- [ ] RPO (Recovery Point Objective): 15 minutes
- [ ] Documented runbook for common incidents
- [ ] Tested recovery procedure (quarterly)

### 11. Compliance & Auditing

- [ ] GDPR compliance checks
- [ ] POPIA compliance (South Africa)
- [ ] PCI DSS compliance (if handling cards directly)
- [ ] Audit log for sensitive operations
- [ ] Data retention policies documented

### 12. Monitoring Tools Stack

| Purpose | Tool | Status |
|---------|------|--------|
| Metrics | Prometheus | To Set Up |
| Visualization | Grafana | To Set Up |
| Logging | Loki | ✅ Available |
| Error Tracking | GlitchTip/Sentry | ✅ Configured |
| APM | Sentry Performance | To Enable |
| Uptime | UptimeRobot/Pingdom | To Set Up |
| Real User Monitoring | Sentry/GA4 | To Set Up |

### Quick Start Commands

```bash
# Check all services health
curl http://localhost:8000/health

# View recent errors in Loki
curl -G "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={filename="/dev/shm/ihhashi-backend.log"} |~ "error"' \
  --data-urlencode "start=$(date -d '1 hour ago' +%s)000000000" \
  --data-urlencode "end=$(date +%s)000000000" | jq

# Monitor MongoDB
docker exec ihhashi-mongo mongosh --eval "db.serverStatus().connections"

# Monitor Redis
docker exec ihhashi-redis redis-cli INFO stats
```

---

## Post-Incident Checklist

After any incident:
- [ ] Incident documented in runbook
- [ ] Root cause identified
- [ ] Fix implemented
- [ ] Monitoring improved to catch future occurrences
- [ ] Team notified of learnings
- [ ] Customer communication sent (if needed)
