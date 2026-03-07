# Evolution AGENTS.md
## Pattern Extraction & Knowledge Building Protocol

### MANDATORY: Post-Deployment Analysis

**After EVERY deployment (success or failure):**

1. **Read deployment log** from `../shared/memory/deployments/`
2. **Analyze timeline:**
   - Estimated duration vs actual
   - Bottlenecks identified
   - Agent coordination issues
3. **Extract outcomes:**
   - Success metrics
   - Failure modes
   - User feedback

### Pattern Extraction Process

**Step 1: Code Pattern Mining**
```python
def extract_code_patterns(deployment):
    patterns = []
    
    # Analyze generated code
    for file in deployment.output_files:
        # AST parsing for structure
        # Similarity detection
        # Reusable component identification
        
        if is_reusable(file):
            patterns.append({
                "type": "component",
                "name": extract_name(file),
                "structure": extract_structure(file),
                "context": deployment.context,
                "success": deployment.success
            })
    
    return patterns
```

**Step 2: Architecture Pattern Recognition**
- What system design was chosen?
- Why was it effective (or not)?
- Can it be generalized?
- Document to `../shared/knowledge/patterns/architecture/`

**Step 3: Process Optimization**
- Which agents worked well together?
- Where were handoffs smooth? Where rough?
- What checks caught issues early?
- What was redundant?

### Knowledge Base Updates

**Write to `../shared/knowledge/`:**

**Successful Patterns:**
```yaml
pattern_id: "auth-flow-jwt-v1"
source_deployment: "uuid"
extracted_date: ISO8601
context: "Mobile app auth with Supabase"
components:
  - "LoginForm.tsx"
  - "useAuth.ts"
  - "AuthGuard.tsx"
rationale: "Clean separation, reusable hooks"
success_rate: 0.94
usage_count: 12
```

**Anti-Patterns (AVOID):**
```yaml
anti_pattern: "nested-tenary-jsx"
issue: "Unreadable, hard to maintain"
solution: "Use early returns or component extraction"
example_bad: "..."
example_good: "..."
first_seen: ISO8601
```

**Process Improvements:**
```yaml
improvement_id: "parallel-testing"
observation: "Sequential testing adds 15 min"
solution: "Run unit + integration in parallel"
result: "-10 min build time"
applied_to: ["frontend", "backend"]
```

### Agent SOUL Updates

**Quarterly Review:**
1. Analyze agent performance metrics
2. Identify knowledge gaps
3. Update SOUL.md with new learnings
4. Add skills to AGENTS.md
5. Refine decision rules

**Example Update:**
```markdown
# Added to Frontend Builder SOUL.md

### New Learning (2024-03)
"Capacitor camera plugin has iOS permission quirks.
Always test on physical device, not just emulator."
```

### Success Rate Tracking

**Per Track:**
```yaml
capacitor:
  deployments: 47
  successful: 44
  failed: 3
  success_rate: 0.936
  avg_duration: "3.2 hours"
  
flutter:
  deployments: 23
  successful: 19
  failed: 4
  success_rate: 0.826
  avg_duration: "2.8 hours"
```

**If success rate drops:**
1. Analyze recent failures
2. Identify common causes
3. Update agent training
4. Require additional verification

### Insight Generation

**Weekly Digest (written to `memory/insights/weekly.md`):**
```markdown
# Week of 2024-03-01

## Key Insights

1. **Capacitor deployments 15% faster** when using 
   pre-built native plugins vs. custom bridges.
   
2. **Guardian security scans** catching 2.3x more 
   issues when run BEFORE vs. AFTER full build.
   
3. **Meta-Router confidence** drops below 80% when
   repos have >3 framework indicators (hybrid apps).
   Human routing recommended.

## Recommendations

- [ ] Update Meta-Router to flag hybrid apps
- [ ] Move security scans earlier in pipeline
- [ ] Document Capacitor plugin selection guide
```

### Knowledge Sharing with Other Agents

**Daily Sync:**
1. Query: "What did we learn yesterday?"
2. Format: Insight + Source + Confidence
3. Distribute to relevant agents' memory
4. Update shared pattern library

**Example Distribution:**
```
To: Frontend Builder
Subject: Pattern - Responsive Grid

Extracted from: iHhashi dashboard
Pattern: CSS Grid with auto-fit + minmax
Use when: 3+ column layouts
Avoid: When IE11 support required
```

---
*"The system learns so the humans don't have to repeat."*
