# MasterBuilder7 Monitoring Stack

Complete observability solution for the MasterBuilder7 8-agent build system.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        MONITORING STACK                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Metrics          Logs            Traces          Alerts            │
│   ┌─────────┐     ┌─────────┐    ┌─────────┐    ┌─────────────┐    │
│   │Prometheus│◀────│  Loki   │    │  Tempo  │───▶│Alertmanager │    │
│   │ Server  │     │ Server  │    │ Server  │    │   Server    │    │
│   └────┬────┘     └────┬────┘    └────┬────┘    └──────┬──────┘    │
│        │               │              │                │           │
│   ┌────▼────┐     ┌────▼────┐    ┌────▼────┐           │           │
│   │  Agent  │     │Promtail │    │OTEL Col.│◀──────────┘           │
│   │Exporters│     │  Agent  │    │         │                       │
│   └────┬────┘     └────┬────┘    └────┬────┘                       │
│        │               │              │                             │
│   ┌────▼───────────────▼──────────────▼────┐                        │
│   │           MasterBuilder7 Agents         │                        │
│   │  Meta-Router → Frontend → Testing → ... │                        │
│   └─────────────────────────────────────────┘                        │
│                                                                      │
│   Visualization: Grafana Dashboards                                  │
│   - Agent Overview                                                   │
│   - Build Metrics                                                    │
│   - Cost Tracking                                                    │
│   - Health Monitoring                                                │
└─────────────────────────────────────────────────────────────────────┘
```

## Components

| Component | Version | Purpose | Port |
|-----------|---------|---------|------|
| Prometheus | v2.47.0 | Metrics collection & alerting | 9090 |
| Grafana | v10.1.2 | Visualization & dashboards | 3000 |
| Loki | v2.9.0 | Log aggregation | 3100 |
| Tempo | v2.3.0 | Distributed tracing | 3200 |
| Alertmanager | v0.26.0 | Alert routing | 9093 |
| OpenTelemetry Collector | v0.85.0 | Unified telemetry collection | 8888 |
| Node Exporter | v1.6.1 | System metrics | 9100 |
| cAdvisor | v0.47.2 | Container metrics | 8080 |
| Promtail | v2.9.0 | Log collection | 9080 |
| Blackbox Exporter | v0.24.0 | Endpoint probing | 9115 |
| Pushgateway | v1.6.2 | Batch metric push | 9091 |

## Quick Start

### 1. Start the Stack

```bash
cd /home/teacherchris37/MasterBuilder7/monitoring

# Create network if it doesn't exist
docker network create masterbuilder7_default 2>/dev/null || true

# Start all services
docker-compose -f docker-compose.monitoring.yml up -d

# Or start specific services
docker-compose -f docker-compose.monitoring.yml up -d prometheus grafana
```

### 2. Access Services

| Service | URL | Default Credentials |
|---------|-----|---------------------|
| Grafana | http://localhost:3000 | admin/admin |
| Prometheus | http://localhost:9090 | - |
| Alertmanager | http://localhost:9093 | - |
| Loki | http://localhost:3100 | - |
| Tempo | http://localhost:3200 | - |

### 3. Stop the Stack

```bash
docker-compose -f docker-compose.monitoring.yml down

# To also remove volumes (WARNING: data loss)
docker-compose -f docker-compose.monitoring.yml down -v
```

## Dashboards

### Agent Overview (`mb7-agent-overview`)
- Real-time status of all 8 agents
- CPU/Memory usage per agent
- Request rates and queue depth
- Health scores visualization

### Build Metrics (`mb7-build-metrics`)
- Build success/failure rates
- Build duration histograms
- Queue depth trends
- Build status distribution

### Cost Tracking (`mb7-cost-tracking`)
- Daily/monthly cost tracking
- Cost per build analysis
- Budget utilization
- Cost forecasts

### Health Monitoring (`mb7-health-monitoring`)
- System health overview
- Error rate analysis
- Response time percentiles
- Infrastructure metrics

## Alerting

### Alert Rules (alerts.yml)

| Alert | Severity | Condition |
|-------|----------|-----------|
| AgentDown | Critical | Agent not reporting for 1m |
| AgentHealthCheckFailed | Critical | Health score < 50% |
| BuildFailureRateHigh | Critical | > 15% failure rate |
| QueueDepthHigh | Warning | Queue depth > 100 |
| DailyBudgetExceeded | Warning | Daily cost > budget |
| ErrorRateHigh | Critical | Error rate > 5% |
| DiskSpaceLow | Critical | Disk usage > 90% |

### Notification Channels

Configure in `alertmanager.yml`:
- Email
- Slack
- PagerDuty
- Webhooks
- Telegram (optional)

Set environment variables in `.env`:
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
PAGERDUTY_SERVICE_KEY=...
SMTP_HOST=smtp.gmail.com:587
SMTP_USER=...
SMTP_PASSWORD=...
```

## Metrics Reference

### Agent Metrics
```
# Up/Down status
up{job="agent-metrics", agent_name="meta-router"}

# Health score (0-100)
agent_health_score{agent_name="meta-router"}

# Request rate
rate(agent_requests_total[5m])

# Error rate
rate(agent_errors_total[5m])

# Response duration
histogram_quantile(0.95, rate(agent_response_duration_ms_bucket[5m]))

# Resource usage
agent_cpu_usage_percent{agent_name="meta-router"}
agent_memory_usage_bytes{agent_name="meta-router"}

# Active builds
agent_active_builds{agent_name="meta-router"}
```

### Build Metrics
```
# Build counts
build_total{status="success"}
build_total{status="failed"}

# Build duration
build_duration_seconds_bucket{le="300"}

# Queue depth
build_queue_depth

# Processing time
queue_processing_duration_seconds
```

### Cost Metrics
```
# Daily cost
cost_daily_total_usd
cost_daily_budget_usd

# Monthly cost
cost_monthly_running_total_usd

# Cost per agent
cost_agent_total_usd{agent_name="meta-router"}

# Hourly cost
cost_hourly_usd
```

## Instrumenting Your Application

### Python (FastAPI)
```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import FastAPI
from opentelemetry import trace

app = FastAPI()

# Metrics
REQUESTS = Counter('agent_requests_total', 'Total requests', ['agent_name'])
ERRORS = Counter('agent_errors_total', 'Total errors', ['agent_name', 'error_type'])
DURATION = Histogram('agent_response_duration_ms', 'Response time', ['agent_name'])
HEALTH = Gauge('agent_health_score', 'Health score', ['agent_name'])
ACTIVE_BUILDS = Gauge('agent_active_builds', 'Active builds', ['agent_name'])

# Tracing
tracer = trace.get_tracer(__name__)

@app.get("/build")
async def build():
    with tracer.start_as_current_span("build") as span:
        span.set_attribute("agent.name", "meta-router")
        REQUESTS.labels(agent_name="meta-router").inc()
        # ... build logic
```

### Go
```go
import (
    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promauto"
)

var (
    requests = promauto.NewCounterVec(prometheus.CounterOpts{
        Name: "agent_requests_total",
        Help: "Total requests",
    }, []string{"agent_name"})
)
```

### Node.js
```javascript
const client = require('prom-client');

const requests = new client.Counter({
  name: 'agent_requests_total',
  help: 'Total requests',
  labelNames: ['agent_name']
});

requests.inc({ agent_name: 'meta-router' });
```

## Log Format

Structured JSON logs for Loki:
```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "info",
  "message": "Build completed successfully",
  "agent_name": "meta-router",
  "build_id": "build-123",
  "trace_id": "abc123",
  "duration_ms": 5000,
  "status": "success"
}
```

## Tracing

OpenTelemetry trace context:
```python
from opentelemetry import trace
from opentelemetry.propagate import inject

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("process-build") as span:
    span.set_attribute("agent.name", agent_name)
    span.set_attribute("build.id", build_id)
    
    # Add events
    span.add_event("build-started")
    
    # Add error
    if error:
        span.record_exception(error)
        span.set_status(trace.Status(trace.StatusCode.ERROR))
```

## Maintenance

### Data Retention

| Component | Default Retention | Config Location |
|-----------|------------------|-----------------|
| Prometheus | 30 days, 50GB | prometheus.yml |
| Loki | 30 days | loki-config.yml |
| Tempo | 7 days | tempo-config.yml |
| Alertmanager | 120 hours | docker-compose.yml |

### Backup

```bash
# Backup Prometheus data
docker run --rm -v mb7_prometheus-data:/data -v $(pwd):/backup alpine tar czf /backup/prometheus-backup.tar.gz -C /data .

# Backup Grafana dashboards
docker run --rm -v mb7_grafana-data:/data -v $(pwd):/backup alpine tar czf /backup/grafana-backup.tar.gz -C /data .
```

### Health Checks

```bash
# Check all services
docker-compose -f docker-compose.monitoring.yml ps

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check Grafana health
curl http://localhost:3000/api/health

# Check Loki ready
curl http://localhost:3100/ready
```

## Troubleshooting

### No metrics showing
1. Check agent exporters are running: `curl http://agent:8000/metrics`
2. Verify Prometheus targets: http://localhost:9090/targets
3. Check network connectivity between containers

### No logs in Loki
1. Check Promtail is running: `docker logs mb7-promtail`
2. Verify log file paths in promtail-config.yml
3. Check Loki is receiving: `curl http://localhost:3100/loki/api/v1/label/job/values`

### Traces not appearing
1. Verify Tempo receivers are configured
2. Check OTLP endpoint: `curl http://localhost:4318/v1/traces`
3. Enable debug logging in OTel Collector

### Alerts not firing
1. Check alert rules: http://localhost:9090/rules
2. Verify Alertmanager is receiving: http://localhost:9093/api/v2/status
3. Check alertmanager.yml routing configuration

## Security Considerations

1. **Change default passwords** in docker-compose.yml
2. **Use TLS** for external access
3. **Restrict network access** to monitoring ports
4. **Regular updates** of all components
5. **Audit logs** for access and changes

## License

Part of MasterBuilder7 - MIT License
