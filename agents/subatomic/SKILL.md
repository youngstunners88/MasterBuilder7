# Sub-atomic Agent Templates

Micro-agent templates for specialized tasks.

## Overview

**Platform**: Distributed System
**Status**: Experimental
**Scale**: 2-50 agents

## Agent Types

| Agent | Role | Docker Image |
|-------|------|--------------|
| Extractor | Data extraction | subatomic-extract |
| Validator | Data validation | subatomic-validate |
| Enricher | Data enrichment | subatomic-enrich |
| Formatter | Data formatting | subatomic-format |
| Notifier | Notifications | subatomic-notify |

## Usage

```bash
# Deploy swarm
docker-compose -f agents/subatomic/docker-compose.yml up --scale extractor=5

# Submit task
curl -X POST http://localhost:8080/tasks \
  -d '{"type": "extract", "data": [...]}'
```

## Configuration

```yaml
swarm:
  min: 2
  max: 50
  scale_threshold:
    cpu: 70
    memory: 80
```
