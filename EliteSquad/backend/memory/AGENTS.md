# Backend Builder AGENTS.md
## API & Database Implementation Protocol

### MANDATORY: Pre-Implementation Search

**Before writing ANY endpoint:**

1. **Read `../shared/memory/api-contracts.md`**
   - Load existing API patterns
   - Check version compatibility
   - Note deprecated endpoints

2. **Search `../shared/knowledge/patterns/database/`**
   - Load schema templates
   - Review migration patterns
   - Check for reusable models

3. **Check `../shared/memory/security-incidents.md`**
   - Review past vulnerabilities
   - Load security checklists
   - Verify compliance requirements

### API Implementation Process

**From Tech Spec → Code:**

**Step 1: OpenAPI Spec First**
```yaml
# Write to memory/api-draft.yaml
paths:
  /api/v1/resource:
    get:
      summary: "Get resource"
      parameters: [...]
      responses:
        200:
          content:
            application/json:
              schema: {...}
```

**Step 2: Generate Types**
```bash
# Generate TypeScript from OpenAPI
openapi-typescript memory/api-draft.yaml --output types/api.ts
```

**Step 3: Implement Handler**
```python
@app.get("/api/v1/resource")
async def get_resource(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Authorization check
    # 2. Input validation (Pydantic)
    # 3. Database query
    # 4. Business logic
    # 5. Response formatting
    # 6. Logging
    pass
```

**Step 4: Verify with Guardian**
- Security scan
- Load test
- Contract compliance check

### Database Schema Protocol

**Migration Rules:**
1. Migrations are additive only (in production)
2. Each migration has:
   - `upgrade()` function
   - `downgrade()` function (rollback)
   - `test_data()` fixture
3. Test migrations on copy of production data

**Schema Design Checklist:**
- [ ] Primary keys (UUID or auto-increment)
- [ ] Foreign key constraints
- [ ] Indexes on query columns
- [ ] Timestamps (created_at, updated_at)
- [ ] Soft delete (deleted_at) if applicable
- [ ] Enum constraints where appropriate
- [ ] JSON columns for flexible data (documented)

**Write to `memory/schema-decisions.md`:**
```yaml
table_name: "users"
rationale: "Central auth entity"
indexes:
  - email (unique, for login)
  - created_at (for sorting)
tradeoffs: "UUID vs int - chose UUID for privacy"
```

### Coordination with Frontend

**Type Sharing:**
```
backend/types/ → shared package → frontend/src/types/
```

**Mock Server:**
- Provide mocks within 30 minutes of spec
- Frontend builds against mocks immediately
- Implement real endpoints in parallel
- Switch from mocks to real when ready

**API Versioning:**
- URL versioning: `/api/v1/`, `/api/v2/`
- Deprecation headers: `Sunset: [date]`
- Migration guides in `memory/api-migrations.md`

### Performance & Scale

**Query Optimization:**
- EXPLAIN ANALYZE every query
- N+1 detection (automatic)
- Query result caching (Redis)
- Pagination on all list endpoints

**Load Testing:**
- k6 scripts in `tests/load/`
- Target: 1000 req/s per endpoint
- Record in `memory/performance-tests.md`

**Database Connection Pool:**
- Size: (cores * 2) + effective_spindle_count
- Timeout: 30s
- Max overflow: 10

### Error Handling

**Standard Response Format:**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Field 'email' is required",
    "field": "email",
    "request_id": "uuid-for-tracing"
  }
}
```

**Log Levels:**
- ERROR: 5xx errors, security incidents
- WARN: 4xx errors, slow queries (>1s)
- INFO: Successful auth, important state changes
- DEBUG: Detailed request/response (dev only)

---
*"APIs are promises. Keep them."*
