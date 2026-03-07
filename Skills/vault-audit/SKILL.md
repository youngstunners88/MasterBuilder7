---
name: vault-audit
description: "Analyze Obsidian vaults: find orphan notes, broken links, duplicate content, suggest MOCs, normalize tags."
metadata:
  author: youngstunners.zo.computer
---

# Vault Audit Skill

Analyze and organize Obsidian knowledge vaults.

## Commands

### Scan vault for issues
```bash
find /path/to/vault -name "*.md" -exec grep -l "link" {} \;
```

### Generate MOC (Map of Content)
- Find notes with common tags/links
- Group by topic clusters

### Tag normalization
- Find duplicate tags (#ml, #ML, #machine-learning)
- Suggest consolidation

### Orphan detection
- Find notes with no inbound links
- Suggest linking opportunities

## Usage
Point me at your Obsidian vault path and I'll audit it.