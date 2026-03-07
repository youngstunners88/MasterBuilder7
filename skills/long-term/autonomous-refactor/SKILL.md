# Skill 10: Autonomous Refactoring Agent

Continuously improves codebase quality by identifying code smells and applying automated refactorings.

## Overview

The Autonomous Refactoring Agent analyzes code, detects quality issues, applies safe refactorings, and manages the refactoring lifecycle including PR creation.

## Installation

```bash
cd .kimi/skills/autonomous-refactor
pip install -r requirements.txt
```

## Quick Start

```python
from autonomous_refactor import CodeSmellDetector, Refactorer

# Detect code smells
detector = CodeSmellDetector()
smells = detector.detect(code, "example.py")

# Apply refactorings
refactorer = Refactorer()
refactorings = refactorer.refactor_all(code, smells, "example.py")

# Review results
for r in refactorings:
    print(f"Applied: {r.description}")
```

## Examples

### Example 1: Detect Code Smells

```python
from autonomous_refactor import CodeSmellDetector

code = """
def process_order(order, customer, shipping, billing, discount, tax_rate):
    if order.status == "pending":
        if customer.is_active:
            if order.amount > 100:
                if discount > 0:
                    final_amount = order.amount * (1 - discount)
                    if final_amount > 0:
                        return final_amount * (1 + tax_rate)
    return None
"""

detector = CodeSmellDetector()
smells = detector.detect(code, "orders.py")

for smell in smells:
    print(f"[{smell.severity}] {smell.smell_type.name}: {smell.message}")
    for suggestion in smell.suggestions:
        print(f"  → {suggestion}")
```

**Output:**
```
[HIGH] LONG_METHOD: Method 'process_order' is 12 lines
  → Extract helper methods
  → Consider using the Extract Method pattern
[HIGH] TOO_MANY_PARAMETERS: Method 'process_order' has 6 parameters
  → Introduce a parameter object
[MEDIUM] DEEP_NESTING: Method 'process_order' has nesting depth of 5
  → Use early returns to reduce nesting
```

### Example 2: Auto-Refactor

```python
from autonomous_refactor import Refactorer, RefactoringValidator

refactorer = Refactorer()
refactorings = refactorer.refactor_all(code, smells, "orders.py")

# Validate changes
validator = RefactoringValidator()
for r in refactorings:
    result = validator.validate(r, code)
    print(f"{r.description}: {result.is_valid}")
```

### Example 3: Create Refactoring PR

```python
from autonomous_refactor import PRCreator

pr_creator = PRCreator(repo_path="/path/to/repo")
metadata = pr_creator.create_refactoring_pr(
    refactorings=refactorings,
    base_branch="main",
    auto_create=False  # Set to True to actually create PR
)

print(f"Branch: {metadata.branch_name}")
print(f"Title: {metadata.title}")
print(f"Labels: {metadata.labels}")
```

## Detected Code Smells

### Critical
- **Syntax Errors** - Code that won't compile

### High Priority
- **Long Method** - Methods over 50 lines
- **God Class** - Classes with too many responsibilities
- **Deep Nesting** - Nesting depth over 3 levels
- **Complex Conditional** - Cyclomatic complexity over 10

### Medium Priority
- **Long Class** - Classes over 300 lines
- **Too Many Parameters** - Methods with over 5 parameters
- **Duplicate Code** - Similar code blocks

### Low Priority
- **Missing Docstring** - Undocumented functions/classes
- **Magic Numbers** - Unnamed numeric constants
- **Data Class** - Classes that should use @dataclass
- **Unused Import** - Import statements not used

## Refactoring Operations

### Available Refactorings

| Refactoring | Smell Types | Breaking Change |
|-------------|-------------|-----------------|
| Extract Method | Long Method | No |
| Introduce Parameter Object | Too Many Parameters | Yes |
| Add Docstring | Missing Docstring | No |
| Remove Unused Import | Unused Import | No |
| Replace Magic Numbers | Magic Number | No |
| Simplify Conditional | Deep Nesting | No |
| Convert to Dataclass | Data Class | No |

### Learning from Rejections

```python
# Track rejected refactorings
refactorer.history.reject(refactoring, reason="Breaks API compatibility")

# Later, check success rate
success_rate = refactorer.history.get_success_rate()
print(f"Success rate: {success_rate:.0%}")
```

## Configuration

### Custom Thresholds

```python
detector = CodeSmellDetector(thresholds={
    "max_method_lines": 30,
    "max_class_lines": 200,
    "max_parameters": 4,
    "max_nesting_depth": 2,
})
```

### Refactoring Plan

```python
# Generate a refactoring plan with effort estimates
plan = refactorer.generate_refactoring_plan(
    smells=smells,
    max_effort_hours=4.0
)

print(f"Planned: {plan['planned_refactorings']} refactorings")
print(f"Total effort: {plan['total_effort_hours']:.1f} hours")
```

## API Reference

### CodeSmellDetector

```python
class CodeSmellDetector:
    def detect(self, code: str, filename: str, language: str = "python") -> List[CodeSmell]
    def detect_in_project(self, project_path: Path) -> Dict[str, List[CodeSmell]]
    def detect_duplicates(self, files: Dict[str, str]) -> List[CodeSmell]
    def generate_report(self, smells: List[CodeSmell]) -> str
```

### Refactorer

```python
class Refactorer:
    def refactor(self, code: str, smell: CodeSmell, filename: str) -> Optional[Refactoring]
    def refactor_all(self, code: str, smells: List[CodeSmell], filename: str) -> List[Refactoring]
    def generate_refactoring_plan(self, smells: List[CodeSmell], max_effort_hours: float) -> Dict
```

### PRCreator

```python
class PRCreator:
    def create_refactoring_pr(self, refactorings: List[Refactoring], base_branch: str, auto_create: bool) -> PRMetadata
    def save_refactoring_history(self, output_path: Path)
    def generate_refactoring_report(self, project_path: Path) -> str
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Refactoring Check
on: [push, pull_request]

jobs:
  refactor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -r .kimi/skills/autonomous-refactor/requirements.txt
      - run: python -m autonomous_refactor.ci_check
```

### Pre-commit Hook

```yaml
# .pre-commit-hooks.yaml
- repo: local
  hooks:
    - id: code-smell-check
      name: Check for code smells
      entry: python -m autonomous_refactor.pre_commit
      language: python
```

## Reporting

### Generate Project Report

```python
pr_creator = PRCreator()
report = pr_creator.generate_refactoring_report(
    project_path=Path("/path/to/project"),
    output_path=Path("refactoring-report.md")
)
```

### Sample Report Output

```markdown
# Refactoring Report

## Summary
- Total refactorings applied: 15
- Total refactorings rejected: 3
- Success rate: 83%

## By File
### models.py
- Applied: 5
- Rejected: 1
- Success rate: 83%

**Applied refactorings:**
- ADD_DOCSTRING: Added docstring to 'User'
- REMOVE_UNUSED_IMPORT: Removed unused import: 'json'
```

## Testing

```bash
pytest tests/ -v
```

## Architecture

```
autonomous-refactor/
├── src/
│   ├── detector.py      # Code smell detection
│   ├── refactorer.py    # Refactoring application
│   ├── validator.py     # Change validation
│   └── pr_creator.py    # PR creation
├── tests/
│   ├── test_detector.py
│   └── test_refactorer.py
├── SKILL.md
└── requirements.txt
```
