# Frontend Builder AGENTS.md
## Implementation Protocol & Memory

### MANDATORY: Pre-Build Search

**Before generating ANY component:**

1. **Search `../shared/knowledge/patterns/ui/`**
   - Check for existing similar components
   - Load design system tokens (colors, spacing, typography)
   - Review animation patterns

2. **Read `../shared/memory/component-library.md`**
   - Check what's already built (avoid duplication)
   - Note component versions and dependencies
   - Verify no naming conflicts

3. **Check `../shared/memory/browser-issues.md`**
   - Review known browser quirks
   - Load polyfills if needed
   - Note CSS workarounds

### Component Generation Process

**Input:** Tech spec (from Architect) + component requirements

**Output Structure:**
```typescript
// Component with full lifecycle
export interface ComponentProps {
  // Explicit, documented
}

export function Component({ ...props }: ComponentProps) {
  // Implementation
  // - State management
  // - Effects
  // - Event handlers
  // - Error boundaries
}

// Storybook story
export const Default = { ... }
export const Loading = { ... }
export const Error = { ... }
export const Mobile = { ... }
```

**Code Standards:**
- TypeScript strict mode
- Export types explicitly
- JSDoc for complex props
- Error boundary wrapper

### Capacitor-Specific Rules

**When track = capacitor:**

1. **Preserve existing web code:**
   - Never modify original React components
   - Create `mobile/` wrapper directory
   - Import and wrap web components

2. **Native bridge integration:**
   - Use Capacitor plugins for native features
   - Fallback gracefully if permission denied
   - Test on actual device (not just emulator)

3. **Platform quirks:**
   - iOS: Status bar handling, safe areas
   - Android: Back button, hardware variants
   - Log to `memory/capacitor-issues.md`

### Testing Checklist

**Before marking complete:**

- [ ] Renders without errors (Chrome, Firefox, Safari)
- [ ] Mobile responsive (iPhone SE → iPhone Pro Max)
- [ ] Keyboard navigation works
- [ ] Screen reader announces correctly
- [ ] Loading state implemented
- [ ] Error state implemented
- [ ] Empty state implemented
- [ ] Storybook stories written

**Record results in `memory/component-tests.md`**

### Coordination with Backend

**API integration:**
- Read API spec from Architect's tech spec
- Generate TypeScript interfaces from OpenAPI
- Handle loading/error states for every endpoint
- Implement optimistic updates where appropriate

**Type sharing:**
- Import types from shared package
- Never duplicate type definitions
- Update shared types if backend changes

### Performance Memory

**Track in `memory/performance-benchmarks.md`:**
- First Contentful Paint (target: <1.5s)
- Time to Interactive (target: <3.5s)
- Bundle size per route (code splitting)
- Re-render frequency (React DevTools)

**Optimization patterns:**
- `React.memo` for pure components
- `useMemo` for expensive calculations
- `useCallback` for stable references
- Dynamic imports for routes

---
*"The UI is the product. Everything else is implementation detail."*
