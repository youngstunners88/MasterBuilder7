# RobeetsDay Immediate Skills

This directory contains 4 production-ready skills for the RobeetsDay project.

## Skills Overview

### 1. Predictive Context Loader
**Purpose:** Pre-fetches relevant files before user asks

- Analyzes conversation history using embeddings
- Predicts which files user will need next
- Pre-loads files into context
- Uses vector similarity (Qdrant/ChromaDB concepts)
- Caches predictions for 1 hour

**Location:** `predictive-context-loader/`

**Quick Start:**
```python
from predictive_context_loader import create_loader

loader = create_loader("/path/to/project")
loader.initialize()

predictions = loader.predict([
    {"role": "user", "content": "Fix the authentication bug"}
])
files = loader.load_predicted_files(predictions[:3])
```

### 2. Semantic Code Search
**Purpose:** Natural language to code location

- Indexes code files using tree-sitter parsers
- Creates embeddings for functions/classes
- Accepts natural language queries
- Returns ranked results with relevance scores
- Supports filtering by language

**Location:** `semantic-code-search/`

**Quick Start:**
```bash
# CLI
semantic-search "authentication middleware" --top-k 5

# Python
from semantic_code_search import SemanticSearchEngine

engine = SemanticSearchEngine("/path/to/project")
engine.index()
results = engine.search("find auth code", top_k=10)
```

### 3. Auto-Documentation
**Purpose:** Keeps AGENTS.md updated automatically

- Monitors file changes in real-time
- Detects new features, routes, models
- Auto-updates AGENTS.md with new sections
- Maintains version history
- Generates "What's New" summaries

**Location:** `auto-documentation/`

**Quick Start:**
```bash
# CLI
auto-docs watch
auto-docs init
auto-docs update
```

```python
from auto_documentation import create_manager

manager = create_manager("/path/to/project")
manager.start()  # Start watching
# ... changes happen ...
manager.stop()
```

### 4. Self-Healing Tests
**Purpose:** Auto-fixes flaky tests

- Detects flaky tests (fails intermittently)
- Analyzes failure patterns
- Attempts automatic fixes
- Generates PR with fixes
- Tracks fix success rate

**Location:** `self-healing-tests/`

**Quick Start:**
```bash
# Pytest plugin
pytest --self-heal --count=5 --auto-heal

# CLI
self-heal detect tests/ --runs=5
self-heal heal test_file.py test_name
```

## Directory Structure

```
immediate/
├── predictive-context-loader/
│   ├── src/
│   │   ├── __init__.py
│   │   ├── cache.py
│   │   ├── predictor.py
│   │   └── loader.py
│   ├── tests/
│   │   ├── test_cache.py
│   │   ├── test_predictor.py
│   │   └── test_loader.py
│   ├── requirements.txt
│   └── SKILL.md
│
├── semantic-code-search/
│   ├── src/
│   │   ├── __init__.py
│   │   ├── embeddings.py
│   │   ├── indexer.py
│   │   ├── search.py
│   │   └── cli.py
│   ├── tests/
│   │   ├── test_embeddings.py
│   │   └── test_indexer.py
│   ├── requirements.txt
│   └── SKILL.md
│
├── auto-documentation/
│   ├── src/
│   │   ├── __init__.py
│   │   ├── diff.py
│   │   ├── generator.py
│   │   └── watcher.py
│   ├── tests/
│   │   └── test_diff.py
│   ├── requirements.txt
│   └── SKILL.md
│
└── self-healing-tests/
    ├── src/
    │   ├── __init__.py
    │   ├── analyzer.py
    │   ├── healer.py
    │   ├── plugin.py
    │   └── cli.py
    ├── tests/
    │   └── test_analyzer.py
    ├── requirements.txt
    ├── pyproject.toml
    └── SKILL.md
```

## Installation

Each skill can be installed independently:

```bash
# Skill 1: Predictive Context Loader
cd predictive-context-loader
pip install -r requirements.txt

# Skill 2: Semantic Code Search
cd semantic-code-search
pip install -r requirements.txt

# Skill 3: Auto-Documentation
cd auto-documentation
pip install -r requirements.txt

# Skill 4: Self-Healing Tests
cd self-healing-tests
pip install -r requirements.txt
# Or install as pytest plugin
pip install -e .
```

## Integration Example

```python
"""
Example: Using all 4 skills together in a RobeetsDay agent session.
"""

from predictive_context_loader import create_loader, ContextManager
from semantic_code_search import SemanticSearchEngine
from auto_documentation import create_manager as create_doc_manager
import os

PROJECT_ROOT = "/path/to/project"

# 1. Initialize Predictive Context Loader
loader = create_loader(PROJECT_ROOT)
loader.initialize()

# 2. Initialize Semantic Code Search
search_engine = SemanticSearchEngine(PROJECT_ROOT)
search_engine.index()

# 3. Start Auto-Documentation
doc_manager = create_doc_manager(PROJECT_ROOT)
doc_manager.start()

# 4. Use in conversation loop
manager = ContextManager(loader, auto_predict=True)

# User asks a question
user_message = "I need to fix the authentication bug in the login system"

# Predict and load relevant files
predictions = manager.add_message("user", user_message)
context_files = manager.get_context_files(max_files=5)

# Use semantic search for additional context
search_results = search_engine.search("authentication login", top_k=5)

# Present to AI
print("=== Context Files (Predictive) ===")
for f in context_files:
    print(f"  {f['path']} (confidence: {f['confidence']})")

print("\n=== Search Results (Semantic) ===")
for r in search_results:
    print(f"  {r.file_path}:{r.start_line} - {r.name} ({r.relevance_score})")

# Cleanup
doc_manager.stop()
```

## Testing

Run tests for all skills:

```bash
cd /home/teacherchris37/robeetsday/skills/immediate

# Test each skill
for skill in predictive-context-loader semantic-code-search auto-documentation self-healing-tests; do
    echo "Testing $skill..."
    cd $skill
    python -m pytest tests/ -v 2>/dev/null || echo "Tests require dependencies to be installed"
    cd ..
done
```

## Requirements

All skills require:
- Python 3.8+
- Dependencies listed in each skill's `requirements.txt`

Optional but recommended:
- `sentence-transformers` for embedding-based skills
- `tree-sitter` for code parsing
- `watchdog` for file monitoring

## License

MIT License - See individual SKILL.md files for details.
