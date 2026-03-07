---
name: capture-lessons
description: Document lessons learned during task execution
metadata:
  author: youngstunners.zo.computer

## Purpose
Follow "Capture Lessons" principle from workflow rules

## When to Use
After completing any significant task:
- Building a game
- Creating a skill
- Fixing a bug
- Learning something new

## How to Capture
Update /home/workspace/AGENTS.md with:
1. What worked
2. What didn't work
3. What to do differently next time
4. Any useful commands/discovery

## Format
```markdown
## Lessons Learned - [Date]
- ✅ [What worked]
- ❌ [What didn't]
- 💡 [Improvement idea]
- 🔧 [Useful command]
```

## Example
## Lessons Learned - Feb 24, 2026
- ✅ Created 40+ zo.space routes successfully
- ❌ Some routes didn't build - needed to check get_space_errors
- 💡 Always test routes with curl after creating
- 🔧 Use update_space_route with public=true for all games