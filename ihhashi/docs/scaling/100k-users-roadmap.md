# iHhashi 100K Users Scaling Roadmap

## Current State Assessment

### Architecture Overview
- **Backend**: FastAPI (Python)
- **Database**: MongoDB (single instance)
- **Cache**: Redis (single instance)
- **Frontend**: React + Vite
- **Deployment**: Docker containers

### Current Capacity Estimates
- Single MongoDB instance: ~10K concurrent users
- Single Redis instance: ~50K ops/sec
- Single backend instance: ~1K requests/sec
- Current architecture supports: **~5K-10K users**

---

## Scaling Phases

### Phase 1: Foundation (0 → 10K users)
**Timeline: Month 1-2**
**Cost: ~$200-500/month**

#### Database Optimization
- [ ] Create all necessary indexes
  ```javascript
  // Users collection
  db.users.createIndex({ email: 1 }, { unique: true })
  db.users.createIndex({ phone: 1 }, { unique: true })
  
  // Orders collection
  db.orders.createIndex({ buyer_id: 1, created_at: -1 })
  db.orders.createIndex({ status: 1, created_at: -1 })
  db.orders.createIndex({ rider_id: 1, status: 1 })
  db.orders.createIndex({ "delivery_info.location": "2dsphere" })
  
  // Drivers collection
  db.drivers.createIndex({ current_location: "2dsphere" })
  db.drivers.createIndex({ status: 1 })
  
  // Products collection
  db.products.createIndex({ store_id: 1, category: 1 })
  db.products.createIndex({ store_id: 1, active: 1 })
  ```

#### Caching Strategy
- [ ] Implement Redis caching
  ```python
  # Cache frequently accessed data
  - Store details (TTL: 5 minutes)
  - Product catalog (TTL: 5 minutes)
  - User sessions (TTL: 1 hour)
  - Rate limit counters
  ```

- [ ] Add caching decorator
  ```python
  from functools import wraps
  import json
  
  def cache_result(ttl_seconds=300):
      def decorator(func):
          @wraps(func)
          async def wrapper(*args, **kwargs):
              cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
              cached = await redis.get(cache_key)
              if cached:
                  return json.loads(cached)
              result = await func(*args, **kwargs)
              await redis.setex(cache_key, ttl_seconds, json.dumps(result))
              return result
          return wrapper
      return decorator
  ```

#### Backend Optimization
- [ ] Enable connection pooling
  ```python
  # MongoDB connection pool
  client = AsyncIOMotorClient(
      MONGODB_URL,
      maxPoolSize=100,
      minPoolSize=10,
      maxIdleTimeMS=45000,
      waitQueueTimeoutMS=5000,
  )
  ```

- [ ] Implement request compression
- [ ] Add response caching headers
- [ ] Optimize JSON serialization (orjson)

#### Infrastructure
- [ ] Move to managed MongoDB (Atlas) or set up replica set
- [ ] Use managed Redis (Upstash, Redis Cloud) or cluster
- [ ] Set up CDN for static assets
- [ ] Implement health checks for auto-scaling

**Estimated Capacity After Phase 1: 10K users**

---

### Phase 2: Horizontal Scaling (10K → 30K users)
**Timeline: Month 2-4**
**Cost: ~$500-1,500/month**

#### Database Replication
- [ ] Set up MongoDB replica set (3 nodes)
  ```
  - 1 Primary (read/write)
  - 2 Secondaries (read replicas)
  ```

- [ ] Configure read preferences
  ```python
  # Read from secondaries for non-critical queries
  db.orders.find(...).read_preference(ReadPreference.SECONDARY_PREFERRED)
  ```

- [ ] Enable MongoDB sharding preparation
  - Choose shard key: `buyer_id` for orders
  - Create sharded collections (when needed)

#### Backend Clustering
- [ ] Deploy multiple backend instances
  ```yaml
  # docker-compose.prod.yml
  backend:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 2G
  ```

- [ ] Set up load balancer (nginx/HAProxy)
  ```nginx
  upstream backend {
      least_conn;
      server backend-1:8000;
      server backend-2:8000;
      server backend-3:8000;
  }
  ```

- [ ] Implement sticky sessions for WebSocket connections
  ```nginx
  upstream websocket {
      ip_hash;
      server backend-1:8000;
      server backend-2:8000;
  }
  ```

#### Redis Clustering
- [ ] Set up Redis Sentinel or Redis Cluster
  ```
  - 3 master nodes
  - 3 replica nodes
  - Automatic failover
  ```

#### Background Tasks
- [ ] Implement Celery for async tasks
  ```python
  # tasks.py
  @celery_app.task
  def process_order_notification(order_id):
      # Send notifications
      # Update stats
      pass
  ```

- [ ] Add task queue (Redis/RabbitMQ)
- [ ] Set up Celery workers (3-5 workers)

**Estimated Capacity After Phase 2: 30K users**

---

### Phase 3: Advanced Scaling (30K → 60K users)
**Timeline: Month 4-6**
**Cost: ~$1,500-3,000/month**

#### Database Sharding
- [ ] Enable MongoDB sharding
  ```javascript
  // Enable sharding for orders collection
  sh.enableSharding("ihhashi")
  sh.shardCollection("ihhashi.orders", { "buyer_id": 1 })
  
  // Enable sharding for users
  sh.shardCollection("ihhashi.users", { "region": 1, "_id": 1 })
  ```

- [ ] Add 2 more shard servers
- [ ] Implement zone sharding for geographic distribution

#### Geographic Distribution
- [ ] Multi-region deployment
  ```
  - Primary region: Johannesburg
  - Secondary region: Cape Town (for Cape Town users)
  ```

- [ ] Geographic routing
  ```
  Cape Town users → Cape Town cluster
  Johannesburg users → Johannesburg cluster
  ```

#### Advanced Caching
- [ ] Implement multi-layer caching
  ```
  L1: Application-level (in-memory)
  L2: Redis (shared)
  L3: CDN (static content)
  ```

- [ ] Cache warming strategies
- [ ] Cache invalidation patterns

#### Event-Driven Architecture
- [ ] Implement event bus (Kafka/Redis Streams)
  ```python
  # Order events
  OrderCreated → NotifyMerchant
  OrderPickedUp → NotifyBuyer
  OrderDelivered → UpdateStats
  ```

- [ ] Event sourcing for critical flows
- [ ] CQRS for read-heavy operations

#### Monitoring & Observability
- [ ] Distributed tracing (Jaeger/Zipkin)
- [ ] Advanced APM
- [ ] Capacity planning dashboards
- [ ] Predictive scaling

**Estimated Capacity After Phase 3: 60K users**

---

### Phase 4: Global Scale (60K → 100K+ users)
**Timeline: Month 6-12**
**Cost: ~$3,000-8,000/month**

#### Microservices Migration
- [ ] Extract services from monolith
  ```
  - auth-service (authentication)
  - order-service (order management)
  - payment-service (payments)
  - delivery-service (driver matching)
  - notification-service (SMS, push, email)
  - analytics-service (metrics, reporting)
  ```

- [ ] Service mesh (Istio/Linkerd)
- [ ] API Gateway (Kong/Traefik)

#### Database Per Service
- [ ] Separate databases by service
  ```
  auth-service → PostgreSQL (ACID for auth)
  order-service → MongoDB (flexible schema)
  analytics-service → ClickHouse (OLAP)
  ```

- [ ] Data synchronization strategies
- [ ] Saga pattern for distributed transactions

#### Kubernetes Deployment
- [ ] Migrate to Kubernetes
  ```yaml
  # Horizontal Pod Autoscaler
  apiVersion: autoscaling/v2
  kind: HorizontalPodAutoscaler
  metadata:
    name: backend-hpa
  spec:
    scaleTargetRef:
      apiVersion: apps/v1
      kind: Deployment
      name: backend
    minReplicas: 3
    maxReplicas: 20
    metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
  ```

- [ ] Auto-scaling policies
- [ ] Rolling deployments
- [ ] Blue-green deployments

#### Edge Computing
- [ ] Edge locations for low-latency
  ```
  - Cloudflare Workers for API edge
  - Edge caching
  - Geographic load balancing
  ```

#### AI/ML Integration
- [ ] Predictive demand forecasting
- [ ] Dynamic pricing
- [ ] Optimal route calculation
- [ ] Fraud detection ML models

**Estimated Capacity After Phase 4: 100K+ users**

---

## Infrastructure Cost Estimates

### Phase 1 (0-10K users)
| Service | Provider | Monthly Cost |
|---------|----------|--------------|
| Backend (2 vCPU, 4GB) | Render/Railway | $50-100 |
| MongoDB (M10) | Atlas | $60-150 |
| Redis (500MB) | Upstash | $50 |
| CDN | Cloudflare | $20-50 |
| Monitoring | Sentry + Prometheus | $50-100 |
| **Total** | | **$230-450** |

### Phase 2 (10K-30K users)
| Service | Provider | Monthly Cost |
|---------|----------|--------------|
| Backend (3 instances) | Render/Railway | $150-300 |
| MongoDB (M20 + replica) | Atlas | $200-400 |
| Redis Cluster | Redis Cloud | $100-200 |
| Load Balancer | Cloudflare/Render | $50-100 |
| Celery Workers | Render/Railway | $50-100 |
| **Total** | | **$550-1,100** |

### Phase 3 (30K-60K users)
| Service | Provider | Monthly Cost |
|---------|----------|--------------|
| Backend (5 instances) | Kubernetes | $300-500 |
| MongoDB (Sharded M30) | Atlas | $500-800 |
| Redis Cluster (Pro) | Redis Cloud | $200-400 |
| Event Bus (Kafka) | Confluent | $200-400 |
| Multi-region | Multi-cloud | $300-500 |
| **Total** | | **$1,500-2,600** |

### Phase 4 (60K-100K+ users)
| Service | Provider | Monthly Cost |
|---------|----------|--------------|
| Kubernetes Cluster | GKE/EKS | $500-1,000 |
| Databases (multiple) | Managed | $800-1,500 |
| Redis Enterprise | Redis Cloud | $400-800 |
| Service Mesh + Gateway | Kong/Cloudflare | $200-400 |
| ML Infrastructure | Vertex AI/SageMaker | $500-1,000 |
| Global CDN + Edge | Cloudflare Enterprise | $300-500 |
| Monitoring (Full Stack) | Datadog/New Relic | $300-800 |
| **Total** | | **$3,000-6,000** |

---

## Key Performance Targets

| Metric | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|--------|---------|---------|---------|---------|
| Concurrent Users | 1K | 5K | 15K | 30K |
| Requests/second | 100 | 500 | 2,000 | 5,000 |
| API Latency (p95) | <500ms | <300ms | <200ms | <100ms |
| Order Processing | 10/min | 50/min | 200/min | 500/min |
| Uptime SLA | 99% | 99.5% | 99.9% | 99.95% |
| Recovery Time | 1hr | 30min | 10min | 5min |

---

## Team Scaling Recommendations

### Phase 1 (0-10K)
- 1 Backend Developer
- 1 Frontend Developer
- 0.5 DevOps

### Phase 2 (10K-30K)
- 2 Backend Developers
- 1 Frontend Developer
- 1 DevOps Engineer
- 0.5 Data Engineer

### Phase 3 (30K-60K)
- 3 Backend Developers
- 2 Frontend Developers
- 1 DevOps Engineer
- 1 Data Engineer
- 1 SRE

### Phase 4 (60K-100K+)
- 5 Backend Developers
- 3 Frontend Developers
- 2 DevOps/SRE
- 2 Data Engineers
- 1 Platform Engineer
- 1 Security Engineer

---

## Quick Wins (Implement Now)

1. **Enable MongoDB indexes** (immediate 10x improvement)
2. **Add Redis caching for hot paths** (immediate 5x improvement)
3. **Implement connection pooling** (immediate 3x improvement)
4. **Add CDN for static assets** (immediate latency improvement)
5. **Enable gzip compression** (immediate bandwidth savings)
6. **Set up monitoring dashboards** (visibility into issues)
7. **Implement rate limiting** (protect against abuse)
8. **Add health checks** (enable auto-restart)

---

## Migration Checklist

### Before Each Phase
- [ ] Backup all data
- [ ] Test migration in staging
- [ ] Prepare rollback plan
- [ ] Notify users of maintenance window
- [ ] Have on-call engineer ready

### After Each Phase
- [ ] Verify all services operational
- [ ] Check performance metrics
- [ ] Monitor error rates
- [ ] Update documentation
- [ ] Conduct load test

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Database failure | Replica set with automatic failover |
| Redis failure | Redis Sentinel for HA |
| Backend overload | Auto-scaling + load shedding |
| Payment gateway down | Queue payments, retry later |
| Geographic outage | Multi-region deployment |
| Data loss | Backups every 6 hours + point-in-time recovery |
| Security breach | Regular audits, encryption at rest |

---

## Contact & Resources

- **MongoDB Atlas Support**: https://support.mongodb.com
- **Render Support**: https://render.com/support
- **Redis Cloud Support**: https://redis.com/support
- **Cloudflare Support**: https://support.cloudflare.com

---

*Last Updated: February 2026*
*Review Schedule: Quarterly*
