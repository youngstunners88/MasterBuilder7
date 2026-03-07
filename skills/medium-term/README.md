# Medium-Term Skills (5-8) - RobeetsDay Project

This directory contains four production-ready, fully implemented skills for the RobeetsDay project.

## Skills Overview

### Skill 5: Multi-Repo Intelligence
**Directory:** `skill5-multi-repo-intelligence/`

Understands relationships across multiple repositories.

- **Indexer** (`src/indexer.py`): Indexes local and GitHub repositories
- **Dependency Mapper** (`src/dependency_mapper.py`): Maps cross-repo dependencies
- **Graph** (`src/graph.py`): Visualizes repo relationships as interactive graphs
- **Alerter** (`src/alerter.py`): Detects and alerts on breaking changes

**Key Features:**
- Multi-repository indexing and search
- Dependency mapping (imports, APIs, shared libraries)
- Interactive HTML/Mermaid visualizations
- Breaking change detection with baselines
- GitHub issues integration

### Skill 6: Visual Architecture Generator
**Directory:** `skill6-visual-architecture/`

Creates diagrams automatically from code.

- **Parser** (`src/parser.py`): Parses Python/JS/TS/Rust/Go code
- **Mermaid Generator** (`src/mermaid_gen.py`): Generates Mermaid diagrams
- **C4 Generator** (`src/c4_gen.py`): Creates C4 Model diagrams
- **Renderer** (`src/renderer.py`): Renders to SVG/PNG/PDF/HTML

**Key Features:**
- Class diagrams with inheritance
- Sequence and component diagrams
- C4 Model (Context, Container, Component, Code)
- Multiple output formats (SVG, PNG, PDF, HTML)
- Tree-sitter based parsing

### Skill 7: Security Oracle
**Directory:** `skill7-security-oracle/`

Proactive vulnerability detection and remediation.

- **Scanner** (`src/scanner.py`): Multi-scanner security analysis
- **Reporter** (`src/reporter.py`): HTML/SARIF/Markdown reports
- **Remediator** (`src/remediator.py`): Automated fix suggestions
- **Rules** (`src/rules/`): Custom detection rules

**Key Features:**
- Semgrep, Bandit integration
- Secret detection (API keys, tokens, passwords)
- Dependency vulnerability scanning
- Automated remediation suggestions
- CVSS scoring and GitHub issue creation

### Skill 8: Performance Prophet
**Directory:** `skill8-performance-prophet/`

Predicts bottlenecks before deployment.

- **Profiler** (`src/profiler.py`): CPU and memory profiling
- **Query Analyzer** (`src/query_analyzer.py`): N+1 detection
- **Predictor** (`src/predictor.py`): Scaling bottleneck prediction
- **Optimizer** (`src/optimizer.py`): Performance optimization suggestions

**Key Features:**
- cProfile integration
- Database query analysis
- ML-based bottleneck prediction
- Load test scenario generation (Locust)
- Automated optimization plans

## Quick Start

Each skill can be used independently:

```bash
# Skill 5: Multi-Repo Intelligence
cd skill5-multi-repo-intelligence
python examples/basic_usage.py

# Skill 6: Visual Architecture
cd skill6-visual-architecture
python examples/generate_diagrams.py

# Skill 7: Security Oracle
cd skill7-security-oracle
python examples/scan_repository.py

# Skill 8: Performance Prophet
cd skill8-performance-prophet
python examples/profile_and_predict.py
```

## Installation

Each skill has its own `requirements.txt`:

```bash
cd skill5-multi-repo-intelligence
pip install -r requirements.txt

cd skill6-visual-architecture
pip install -r requirements.txt

cd skill7-security-oracle
pip install -r requirements.txt

cd skill8-performance-prophet
pip install -r requirements.txt
```

## Testing

Run tests for each skill:

```bash
cd skill5-multi-repo-intelligence
pytest tests/

cd skill6-visual-architecture
pytest tests/

cd skill7-security-oracle
pytest tests/

cd skill8-performance-prophet
pytest tests/
```

## Directory Structure

```
medium-term/
├── README.md
├── skill5-multi-repo-intelligence/
│   ├── requirements.txt
│   ├── SKILL.md
│   ├── src/
│   │   ├── __init__.py
│   │   ├── indexer.py
│   │   ├── dependency_mapper.py
│   │   ├── graph.py
│   │   └── alerter.py
│   ├── tests/
│   │   └── test_indexer.py
│   └── examples/
│       └── basic_usage.py
├── skill6-visual-architecture/
│   ├── requirements.txt
│   ├── SKILL.md
│   ├── src/
│   │   ├── __init__.py
│   │   ├── parser.py
│   │   ├── mermaid_gen.py
│   │   ├── c4_gen.py
│   │   └── renderer.py
│   ├── tests/
│   │   └── test_parser.py
│   └── examples/
│       └── generate_diagrams.py
├── skill7-security-oracle/
│   ├── requirements.txt
│   ├── SKILL.md
│   ├── src/
│   │   ├── __init__.py
│   │   ├── scanner.py
│   │   ├── reporter.py
│   │   ├── remediator.py
│   │   └── rules/
│   │       ├── sql_injection.yaml
│   │       ├── secrets.yaml
│   │       └── xss.yaml
│   ├── tests/
│   │   └── test_scanner.py
│   └── examples/
│       └── scan_repository.py
└── skill8-performance-prophet/
    ├── requirements.txt
    ├── SKILL.md
    ├── src/
    │   ├── __init__.py
    │   ├── profiler.py
    │   ├── query_analyzer.py
    │   ├── predictor.py
    │   └── optimizer.py
    ├── tests/
    │   └── test_profiler.py
    └── examples/
        └── profile_and_predict.py
```

## Integration

These skills are designed to work together:

```python
# Example: Complete workflow
from skill5_multi_repo_intelligence import RepoIndexer
from skill6_visual_architecture import CodeParser, MermaidGenerator
from skill7_security_oracle import SecurityScanner
from skill8_performance_prophet import Profiler, QueryAnalyzer

# 1. Index repositories
indexer = RepoIndexer()
indexer.add_local_repo("./src")

# 2. Parse and visualize
parser = CodeParser()
parsed = parser.parse_directory("./src")
mermaid = MermaidGenerator()
diagram = mermaid.generate_class_diagram(parsed)

# 3. Security scan
scanner = SecurityScanner()
security_result = scanner.scan("./src")

# 4. Performance analysis
profiler = Profiler()
profile_result = profiler.profile_function(main)
```

## License

MIT - RobeetsDay Project