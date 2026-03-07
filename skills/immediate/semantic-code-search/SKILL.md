# Semantic Code Search

Natural language to code location using tree-sitter parsers and semantic embeddings.

## Overview

Semantic Code Search lets you find code in your project using natural language queries like "authentication middleware" or "database connection pool". It uses tree-sitter to parse code structure and embeddings to understand semantics.

## Installation

```bash
cd .kimi/skills/semantic-code-search
pip install -r requirements.txt
```

## Quick Start

### CLI Usage

```bash
# Search for code
semantic-search "authentication middleware"

# Search with filters
semantic-search "user login" --language python --type function

# Find similar code
semantic-search similar src/auth.py authenticate

# Find definition
semantic-search definition UserManager

# Show statistics
semantic-search stats
```

### Python API

```python
from semantic_code_search import SemanticSearchEngine

# Initialize and index
engine = SemanticSearchEngine("/path/to/project")
engine.index()

# Search
results = engine.search("authentication middleware", top_k=10)

for result in results:
    print(f"{result.file_path}:{result.start_line} - {result.name}")
    print(f"  Relevance: {result.relevance_score}")
    print(f"  {result.signature}")
```

## Features

- **Natural Language Queries**: Search using plain English descriptions
- **Multi-Language Support**: Python, JavaScript, TypeScript, Rust, Go, Java
- **Semantic Understanding**: Uses embeddings to understand code meaning
- **Tree-Sitter Parsing**: Accurate code structure extraction
- **Smart Filters**: Filter by language, element type, file path
- **Query Expansion**: Expands queries with synonyms for better results
- **Similar Code Finding**: Find similar implementations

## Supported Languages

| Language | Extensions | Parser |
|----------|------------|--------|
| Python | .py | tree-sitter-python |
| JavaScript | .js, .jsx | tree-sitter-javascript |
| TypeScript | .ts, .tsx | tree-sitter-typescript |
| Rust | .rs | tree-sitter-rust |
| Go | .go | tree-sitter-go |
| Java | .java | tree-sitter-java |

## CLI Reference

### search

```bash
semantic-search search [OPTIONS] QUERY

Options:
  -k, --top-k INTEGER      Number of results [default: 10]
  -l, --language TEXT      Filter by language
  -t, --type TEXT          Filter by element type
  -f, --file TEXT          Filter by file path pattern
  -m, --min-score FLOAT    Minimum relevance score [default: 0.0]
  -e, --expand             Expand query with synonyms
  -c, --show-code          Show full code content
  -v, --verbose            Enable verbose output
```

**Examples:**

```bash
# Basic search
semantic-search "user authentication"

# Find test files
semantic-search "test user login" --type function

# Find in specific language
semantic-search "database connection" --language python

# Find in specific directory
semantic-search "API handler" --file src/routes/

# High confidence results only
semantic-search "encryption" --min-score 0.7
```

### similar

Find code elements similar to a given one.

```bash
semantic-search similar [OPTIONS] FILE_PATH SYMBOL_NAME

Options:
  --line INTEGER    Line number of the symbol
  -k, --top-k INTEGER  Number of results [default: 5]
```

**Example:**

```bash
semantic-search similar src/auth.py authenticate --top-k 10
```

### definition

Find where a symbol is defined.

```bash
semantic-search definition SYMBOL
```

**Example:**

```bash
semantic-search definition UserManager
```

### index

Force reindex the project.

```bash
semantic-search index [--languages python,javascript]
```

### stats

Show indexing statistics.

```bash
semantic-search stats
```

## Python API Reference

### SemanticSearchEngine

Main search engine class.

```python
from semantic_code_search import SemanticSearchEngine

engine = SemanticSearchEngine(project_root="/path/to/project")
```

#### Methods

**`index(languages=None)`**

Index the project. Call before searching.

```python
engine.index()  # Index all supported languages
engine.index(languages=['python', 'javascript'])  # Index specific languages
```

**`search(query, top_k=10, **filters)`**

Search for code elements.

```python
results = engine.search(
    "authentication middleware",
    top_k=10,
    language_filter='python',
    type_filter='function',
    min_score=0.5
)
```

**`search_with_expansion(query, top_k=10, **filters)`**

Search with query expansion using synonyms.

```python
results = engine.search_with_expansion(
    "auth",  # Expands to: auth, authentication, login, etc.
    top_k=10
)
```

**`find_similar(file_path, name, start_line, top_k=5)`**

Find similar code elements.

```python
similar = engine.find_similar(
    "src/auth.py",
    "authenticate",
    42,
    top_k=5
)
```

**`save(output_dir)` / `load(input_dir)`**

Save and load index for caching.

```python
engine.save(".kimi/semantic-search")
engine.load(".kimi/semantic-search")
```

### SearchResult

Result of a search query.

```python
result: SearchResult

result.name           # Name of the element
result.element_type   # function, class, method, etc.
result.file_path      # Relative file path
result.start_line     # Starting line number
result.end_line       # Ending line number
result.relevance_score # Semantic similarity score (0-1)
result.signature      # Code signature if available
result.docstring      # Documentation if available
result.content_preview # Preview of code content
result.parent         # Parent class/module
```

### CodeNavigator

Advanced navigation using semantic search.

```python
from semantic_code_search import CodeNavigator

navigator = CodeNavigator(engine)

# Find definition
definition = navigator.find_definition("UserManager")

# Find usages
usages = navigator.find_usages("authenticate")

# Find related code
related = navigator.find_related("src/auth.py", "login", 42)

# Explore file contents
file_contents = navigator.explore_file("src/models.py")
```

## Query Tips

### Effective Queries

1. **Be specific**: "JWT token validation" > "auth stuff"
2. **Use domain terms**: "ORM model" rather than "database thing"
3. **Mention patterns**: "singleton pattern implementation"
4. **Include return types**: "function that returns User object"

### Query Expansion

The search automatically expands common programming terms:

| Term | Expands To |
|------|-----------|
| auth | authentication, login, authorize, credential |
| db | database, storage, persistence, ORM, model |
| api | endpoint, route, controller, handler, REST |
| ui | interface, component, view, frontend |
| test | spec, unittest, pytest, verify, assert |

### Filtering

Combine filters for precise results:

```python
# Find Python test functions about authentication
results = engine.search(
    "authentication",
    language_filter='python',
    type_filter='function',
    file_filter='test_'
)
```

## Configuration

### Environment Variables

```bash
# Use specific embedding model
export SEMANTIC_SEARCH_MODEL="microsoft/codebert-base"

# Device for embeddings (cpu/cuda)
export SEMANTIC_SEARCH_DEVICE="cpu"
```

### Custom Models

```python
from semantic_code_search import SemanticSearchEngine, EmbeddingManager

# Use custom embedding model
embedding_manager = EmbeddingManager(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    device="cuda"
)

engine = SemanticSearchEngine(
    project_root="/path/to/project",
    embedding_manager=embedding_manager
)
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   SemanticSearchEngine                       │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │TreeSitterIndexer │  │EmbeddingManager  │                │
│  │  - Parse code    │  │  - Create embeds │                │
│  │  - Extract funcs │  │  - Similarity    │                │
│  │  - Extract classes│  │  - Query expand  │                │
│  └──────────────────┘  └──────────────────┘                │
├─────────────────────────────────────────────────────────────┤
│  Search Methods:                                            │
│  - search()        - Basic semantic search                  │
│  - search_with_expansion() - With synonyms                  │
│  - find_similar()  - Find similar code                      │
└─────────────────────────────────────────────────────────────┘
```

## Performance

- Initial indexing: ~2-5 seconds per 1000 files
- Search latency: <200ms
- Memory usage: ~100MB per 10,000 code elements
- Incremental indexing: Not yet supported (planned)

## Testing

```bash
# Run tests
pytest tests/

# Run specific test file
pytest tests/test_indexer.py

# Run with coverage
pytest tests/ --cov=semantic_code_search --cov-report=html
```

## Examples

### Example 1: Find Authentication Code

```python
results = engine.search("JWT authentication middleware", top_k=5)

for r in results:
    print(f"{r.file_path}:{r.start_line} {r.name}")
    print(f"  Score: {r.relevance_score}")
    if r.signature:
        print(f"  {r.signature}")
```

### Example 2: Find All API Endpoints

```python
results = engine.search(
    "API endpoint route handler",
    type_filter='function',
    top_k=20
)
```

### Example 3: Find Similar Implementations

```python
# Find code similar to your UserService class
similar = engine.find_similar(
    "src/services/user.py",
    "UserService",
    15,  # line number
    top_k=10
)

for s in similar:
    print(f"Similar: {s.file_path} - {s.name} ({s.relevance_score})")
```

### Example 4: Explore a File

```python
navigator = CodeNavigator(engine)

# Get all elements in a file
contents = navigator.explore_file("src/models.py")

for elem in contents:
    print(f"[{elem.element_type}] {elem.name}")
    if elem.docstring:
        print(f"  Docs: {elem.docstring[:100]}")
```

## License

MIT
