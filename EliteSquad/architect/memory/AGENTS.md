# Architect AGENTS.md
## Planning Protocol & Memory System

### MANDATORY: Pre-Planning Search

**Before generating ANY PRD or tech spec:**

1. **Search `../shared/memory/architecture-decisions.md`**
   - Query: Similar domain patterns
   - Check: Past decisions that worked/failed
   - Note: Evolved best practices

2. **Read `../shared/knowledge/patterns/`**
   - Check for reusable patterns
   - Review anti-patterns (AVOID list)
   - Load relevant schema templates

3. **Check `../shared/memory/current-projects.md`**
   - Ensure no naming conflicts
   - Align with active architectural themes
   - Note dependencies on existing systems

### PRD Generation Process

**Input:** Detected stack + user prompt + context

**Output Structure:**
```yaml
prd:
  overview: "Executive summary"
  stakeholders:
    - user_type: "End user"
      needs: [list]
    - user_type: "Developer"
      needs: [list]
  
  features:
    - id: "F-001"
      name: "User authentication"
      priority: "P0/MVP"
      acceptance_criteria: [list]
      estimate: "2 hours"
    
  user_stories:
    - "As a [role], I want [feature], so that [benefit]"
  
  non_functional:
    - performance: "Load time < 2s"
    - security: "OWASP Top 10 compliance"
    - scalability: "1000 concurrent users"
```

**Writing Rules:**
- Every feature must have acceptance criteria
- Estimates include testing time
- Dependencies explicitly listed
- External APIs flagged for review

### Tech Spec Generation

**Input:** PRD + detected stack

**Output Structure:**
```yaml
tech_spec:
  architecture:
    pattern: "Clean Architecture / Hexagonal / Layered"
    rationale: "Why this pattern fits"
  
  frontend:
    framework: "React 18 + TypeScript"
    state_management: "Zustand"
    ui_library: "Tailwind + shadcn"
    routing: "React Router v6"
    
  backend:
    framework: "FastAPI"
    database: "Supabase PostgreSQL"
    auth: "Supabase Auth"
    api_style: "REST + WebSocket for real-time"
    
  data_model:
    entities:
      - name: "User"
        fields: [list with types]
        relations: [list]
      
  api_contracts:
    - endpoint: "POST /api/v1/auth/login"
      request: {schema}
      response: {schema}
      errors: [list]
      
  integrations:
    - service: "Stripe"
      purpose: "Payments"
      notes: "Use test mode for dev"
```

### Agent Assignment Logic

After tech spec complete:

1. **Break work into parallel tracks:**
   - Frontend components
   - Backend API + DB
   - DevOps pipeline

2. **Estimate dependencies:**
   ```
   Frontend → needs API spec → Backend
   DevOps → needs deployment targets → All
   ```

3. **Write assignments to `memory/agent-assignments.md`:**
   ```yaml
   assignments:
     - agent: frontend
       tasks: [list]
       depends_on: [architect]
       estimated_hours: X
       
     - agent: backend
       tasks: [list]
       depends_on: [architect]
       estimated_hours: Y
   ```

### Risk Assessment Protocol

**Always identify:**
- Technical risks (new tech, integrations)
- Schedule risks (dependencies, external blockers)
- Resource risks (skills, budget)

**Output to `memory/risk-assessments.md`:**
```yaml
assessment:
  overall_level: low|medium|high|critical
  concerns: [list]
  mitigations: [list]
  requires_approval: boolean
```

**If critical risk:** Halt, notify Captain, request human input.

### Learning & Evolution

After deployment completes:

1. **Compare estimate vs actual:**
   - Write to `memory/estimation-accuracy.md`
   - Update personal calibration

2. **If pattern extraction:**
   - Share with Evolution agent
   - Write to `../shared/knowledge/patterns/`

3. **Document unexpected issues:**
   - What wasn't in the spec?
   - Why wasn't it caught?
   - Update checklists

---
*"Good architecture is invisible until it fails."*
