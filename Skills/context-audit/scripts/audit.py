#!/usr/bin/env python3
"""Context file audit script"""
import os
import json

CONTEXT_FILES = {
    "AGENTS.md": "/home/workspace/AGENTS.md",
    "SOUL.md": "/home/workspace/SOUL.md", 
    "USER.md": None,  # Not in workspace
    "MEMORY.md": None,
    "HEARTBEAT.md": None,
}

def count_tokens(text):
    return len(text.split())

def audit_file(path, name):
    if not path or not os.path.exists(path):
        return {"file": name, "status": "not_found", "current": 0, "projected": 0, "savings": 0}
    
    with open(path) as f:
        content = f.read()
    
    current = count_tokens(content)
    
    # Simple heuristics
    issues = []
    projected = current
    
    # Check for verbose sections
    if current > 500:
        issues.append("Long file - consider splitting")
        projected = int(current * 0.7)  # Assume 30% reduction
    
    # Check for skills that could be extracted
    if "Skills Installed" in content:
        issues.append("Skill list should be in skills, not context")
        projected -= 50
    
    return {
        "file": name,
        "status": "ok",
        "current": current,
        "projected": projected,
        "savings": current - projected,
        "issues": issues
    }

print("=== Context Audit Report ===\n")
total_current = 0
total_projected = 0

for name, path in CONTEXT_FILES.items():
    result = audit_file(path, name)
    print(f"FILE: {result['file']}")
    print(f"  Current: {result['current']} tokens")
    if result['issues']:
        print(f"  Issues: {', '.join(result['issues'])}")
    print(f"  Projected: {result['projected']} tokens")
    print(f"  Savings: {result['savings']} tokens ({result['savings']/max(result['current'],1)*100:.0f}%)")
    print()
    total_current += result['current']
    total_projected += result['projected']

print(f"TOTAL: {total_current} -> {total_projected} tokens")
print(f"SAVINGS: {total_current - total_projected} tokens ({(total_current-total_projected)/max(total_current,1)*100:.0f}%)")