# Auto-Documentation

Keeps AGENTS.md updated automatically by monitoring file changes in real-time.

## Overview

The Auto-Documentation skill watches your codebase for changes, detects new features/routes/models, and automatically updates AGENTS.md with accurate, up-to-date documentation.

## Installation

```bash
cd .kimi/skills/auto-documentation
pip install -r requirements.txt
```

## Quick Start

### CLI Usage

```bash
# Start watching for changes
auto-docs watch

# Generate initial AGENTS.md
auto-docs init

# Force update now
auto-docs update

# Show status
auto-docs status

# Generate What's New summary
auto-docs whats-new
```

### Python API

```python
from auto_documentation import create_manager

# Create and start manager
manager = create_manager("/path/to/project")
manager.start()

# Let it run...

# Stop when done
manager.stop()
```

## Features

- **Real-time Monitoring**: Watches files for changes using watchdog
- **Change Detection**: Detects new features, routes, models, bug fixes
- **Impact Assessment**: Classifies changes by impact level (critical/high/medium/low)
- **Auto-updates**: Updates AGENTS.md automatically
- **Version History**: Maintains version history of changes
- **What's New**: Generates "What's New" summaries
- **Smart Filtering**: Ignores generated files and dependencies

## How It Works

```
┌──────────────────────────────────────────────────────────────┐
│                    Auto-Documentation                         │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  File Change → DiffAnalyzer → CodeChange → AGENTSMDGenerator │
│      ↑                                                           │
│  Watchdog                                                    │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

1. **File Watcher** monitors project files using `watchdog`
2. **Diff Analyzer** detects what changed and categorizes it
3. **Generator** updates AGENTS.md with new information
4. **What's New Generator** creates summaries of recent changes

## CLI Reference

### watch

Start watching files for changes.

```bash
auto-docs watch [OPTIONS]

Options:
  --debounce FLOAT    Debounce time in seconds [default: 2.0]
  --interval INTEGER  Update interval in seconds [default: 60]
  --no-auto-update    Don't auto-update, just watch
```

**Examples:**

```bash
# Start watching
auto-docs watch

# Faster updates
auto-docs watch --debounce 1.0 --interval 30

# Watch only, don't auto-update
auto-docs watch --no-auto-update
```

### init

Generate initial AGENTS.md.

```bash
auto-docs init [--output PATH]
```

### update

Force immediate documentation update.

```bash
auto-docs update
```

### status

Show watcher and documentation status.

```bash
auto-docs status
```

### whats-new

Generate What's New summary.

```bash
auto-docs whats-new [--since DATE]
```

## Python API Reference

### AutoDocumentationManager

Main manager class for auto-documentation.

```python
from auto_documentation import AutoDocumentationManager

manager = AutoDocumentationManager(
    project_root="/path/to/project",
    agents_md_path=Path("/path/to/AGENTS.md"),
    auto_update=True,
    update_interval=60
)
```

#### Methods

**`start()`**

Start monitoring and auto-updating.

```python
manager.start()
```

**`stop()`**

Stop monitoring.

```python
manager.stop()
```

**`force_update()`**

Force immediate documentation update.

```python
manager.force_update()
```

**`get_status()`**

Get current status.

```python
status = manager.get_status()
print(f"Files tracked: {status['watcher_stats']['files_tracked']}")
```

**`generate_initial()`**

Generate initial AGENTS.md.

```python
manager.generate_initial()
```

### DocumentationWatcher

Lower-level file watcher.

```python
from auto_documentation import DocumentationWatcher

def on_changes(changes):
    for change in changes:
        print(f"Detected: {change.description}")

watcher = DocumentationWatcher(
    project_root="/path/to/project",
    on_change=on_changes,
    debounce_seconds=2.0
)

watcher.start()
# ... watch ...
watcher.stop()
```

#### Methods

**`get_change_history(n=10)`**

Get recent change batches.

```python
batches = watcher.get_change_history(n=5)
for batch in batches:
    print(f"{batch.timestamp}: {len(batch.changes)} changes")
```

**`get_all_changes()`**

Get all accumulated changes.

```python
all_changes = watcher.get_all_changes()
```

**`get_stats()`**

Get watcher statistics.

```python
stats = watcher.get_stats()
print(f"Tracked: {stats['files_tracked']}, Changes: {stats['total_changes']}")
```

### DiffAnalyzer

Analyzes code changes.

```python
from auto_documentation import DiffAnalyzer

analyzer = DiffAnalyzer()

# Analyze a file change
changes = analyzer.analyze_file_changes(
    file_path=Path("src/auth.py"),
    old_content="def old_auth(): pass",
    new_content="def authenticate(): pass"
)

for change in changes:
    print(f"{change.change_type.value}: {change.description}")
```

#### Change Types

- `NEW_FEATURE` - New functionality added
- `BUGFIX` - Bug fix
- `REFACTOR` - Code restructuring
- `DEPRECATED` - Deprecated functionality
- `REMOVED` - Removed functionality
- `UNKNOWN` - Could not determine type

### AGENTSMDGenerator

Generates AGENTS.md content.

```python
from auto_documentation import AGENTSMDGenerator, DiffAnalyzer

generator = AGENTSMDGenerator("/path/to/project")

# Generate new content
analyzer = DiffAnalyzer()
changes = []  # Get changes from somewhere

content = generator.generate(changes)
# or update existing
current_content = Path("AGENTS.md").read_text()
updated = generator.update(changes, preserve_existing=True)

generator.save(updated)
```

### WhatsNewGenerator

Generates "What's New" summaries.

```python
from auto_documentation import WhatsNewGenerator

generator = WhatsNewGenerator()

whats_new = generator.generate(changes)
print(whats_new)
```

## Configuration

### Environment Variables

```bash
# Custom AGENTS.md path
export AGENTS_MD_PATH="docs/AGENTS.md"

# Update interval
export AUTO_DOCS_INTERVAL=120

# Debounce time
export AUTO_DOCS_DEBOUNCE=3.0
```

### Custom Templates

You can provide a custom Jinja2 template for AGENTS.md:

```python
from auto_documentation import AGENTSMDGenerator

custom_template = """
# My Project

## Changes
{% for change in changes %}
- {{ change.description }}
{% endfor %}
"""

generator = AGENTSMDGenerator(
    project_root="/path/to/project",
    template=custom_template
)
```

## Change Detection

### Detected Change Types

The system detects these types of changes:

| Type | Pattern | Example |
|------|---------|---------|
| Function | `def name():` | New API endpoint |
| Class | `class Name:` | New model |
| Route | `@app.get()` | New URL route |
| Model | `class X(Model)` | Database model |
| Bugfix | `fix` in code | Error handling |

### Impact Levels

Changes are classified by impact:

- **Critical**: Auth, security, database schema, breaking changes
- **High**: Config, public API, models, services
- **Medium**: Utils, internal code
- **Low**: Private methods, comments

## Examples

### Example 1: Basic Usage

```python
from auto_documentation import create_manager
import time

# Create manager
manager = create_manager("/home/user/myproject")

# Start watching
manager.start()

print("Watching for changes... Press Ctrl+C to stop")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    manager.stop()
```

### Example 2: Custom Handler

```python
from auto_documentation import DocumentationWatcher, DiffAnalyzer

def on_changes(changes):
    print(f"Detected {len(changes)} changes:")
    for change in changes:
        print(f"  [{change.impact_level}] {change.element_type}: {change.name}")
        print(f"    {change.description}")

watcher = DocumentationWatcher(
    project_root="/path/to/project",
    on_change=on_changes,
    debounce_seconds=1.0
)

watcher.start()
```

### Example 3: Manual Updates

```python
from auto_documentation import AGENTSMDGenerator, DiffAnalyzer
import os

# Watch without auto-update
manager = create_manager("/path/to/project", auto_update=False)
manager.start()

# Periodically check and update
while True:
    time.sleep(300)  # Every 5 minutes
    
    stats = manager.watcher.get_stats()
    if stats['pending_changes'] > 0:
        print(f"Processing {stats['pending_changes']} changes...")
        manager.force_update()
```

### Example 4: Generate What's New

```python
from auto_documentation import WhatsNewGenerator, DiffAnalyzer

analyzer = DiffAnalyzer()
generator = WhatsNewGenerator()

# Simulate changes (normally from watcher)
changes = [
    # ... changes from watcher
]

whats_new = generator.generate(changes)
Path("WHATS_NEW.md").write_text(whats_new)
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     AutoDocumentationManager                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐ │
│  │Documentation    │  │DiffAnalyzer      │  │AGENTSMDGenerator│ │
│  │Watcher          │  │  - analyze()     │  │  - generate()   │ │
│  │  - watch()      │  │  - categorize()  │  │  - update()     │ │
│  │  - detect()     │  │  - get_summary() │  │  - save()       │ │
│  └─────────────────┘  └──────────────────┘  └─────────────────┘ │
│                                                                  │
│  ┌─────────────────┐  ┌──────────────────┐                       │
│  │WhatsNewGenerator│  │FileState         │                       │
│  │  - generate()   │  │  - track()       │                       │
│  └─────────────────┘  └──────────────────┘                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest tests/ --cov=auto_documentation --cov-report=html
```

## License

MIT
