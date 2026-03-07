# Predictive Context Loader

Pre-fetches relevant files before the user asks for them by analyzing conversation history using embeddings and vector similarity.

## Overview

The Predictive Context Loader analyzes your conversation with the AI, predicts which files you'll likely need next, and pre-loads them into context. This reduces latency and improves response quality.

## Installation

```bash
cd .kimi/skills/predictive-context-loader
pip install -r requirements.txt
```

## Quick Start

```python
from predictive_context_loader import create_loader

# Create and initialize loader
loader = create_loader("/path/to/project")
loader.initialize()

# Predict files based on conversation
conversation = [
    {"role": "user", "content": "I need to fix the authentication bug in the login system"}
]

predictions = loader.predict(conversation)

# Load predicted files into context
files = loader.load_predicted_files(predictions[:3])

for file in files:
    print(f"Loaded: {file['path']} (confidence: {file['confidence']})")
```

## Features

- **Embedding-based Analysis**: Uses sentence transformers to understand conversation context
- **Vector Similarity Search**: Finds semantically similar files using cosine similarity
- **Intelligent Caching**: 1-hour TTL cache for predictions, persistent embedding cache
- **File Type Detection**: Automatically categorizes and prioritizes relevant file types
- **Confidence Scoring**: Each prediction includes confidence and reasoning

## API Reference

### PredictiveContextLoader

Main class for predictive loading.

```python
loader = PredictiveContextLoader(
    project_root="/path/to/project",
    cache_ttl=3600,          # 1 hour default
    cache_max_size=1000,      # Max cached predictions
    enable_logging=True
)
```

#### Methods

**`initialize(file_patterns=None)`**
Indexes the project files. Call before making predictions.

```python
loader.initialize(file_patterns=['**/*.py', '**/*.js'])
```

**`predict(conversation_history, context=None, top_k=10, use_cache=True)`**
Predict which files will be needed.

```python
predictions = loader.predict([
    {"role": "user", "content": "Fix the auth bug"},
    {"role": "assistant", "content": "I'll help..."}
], top_k=5)
```

Returns list of `PredictionResult`:
- `file_path`: Relative path to file
- `relevance_score`: Similarity score (0-1)
- `confidence`: Prediction confidence (0-1)
- `reason`: Why this file was predicted
- `predicted_action`: Likely action (read/edit/create/test)

**`load_predicted_files(predictions, max_files=5, confidence_threshold=0.5)`**
Load content of predicted files.

```python
files = loader.load_predicted_files(predictions, max_files=3)
for f in files:
    print(f['content'])  # Full file content
```

### ContextManager

Manages conversation context for interactive sessions.

```python
from predictive_context_loader import ContextManager

manager = ContextManager(loader, auto_predict=True)

# Add message and auto-predict
predictions = manager.add_message("user", "I need to update the user model")

# Get loaded files
files = manager.get_context_files(max_files=5)
```

## Configuration

### Environment Variables

```bash
# Optional: Use custom embedding model
export PCL_EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"

# Optional: Cache location
export PCL_CACHE_DIR=".kimi/cache"
```

### Caching

Two-level caching system:

1. **Prediction Cache**: Caches prediction results (1 hour TTL)
2. **Embedding Cache**: Caches file embeddings (7 days TTL)

```python
# Check cache stats
stats = loader.get_cache_stats()
print(f"Cached predictions: {stats['active_entries']}")

# Clear cache
loader.clear_cache()  # All
loader.clear_cache("auth")  # Pattern match
```

## Examples

### Example 1: Find Authentication Code

```python
conversation = [
    {"role": "user", "content": "Where is the JWT authentication handled?"}
]

predictions = loader.predict(conversation, top_k=5)

for p in predictions:
    print(f"{p.file_path}: {p.confidence} - {p.reason}")
    # Output: src/auth/jwt.py: 0.92 - Matches requested file type: code; Semantic similarity match
```

### Example 2: Fix Bug Workflow

```python
# User reports a bug
manager.add_message("user", "The login is broken, getting 500 errors")

# Get predicted files (likely auth, routes, error handlers)
files = manager.get_context_files(max_files=5)

# Present to AI
for file in files:
    print(f"--- {file['path']} ---")
    print(file['content'][:1000])  # First 1000 chars
```

### Example 3: Async Usage

```python
import asyncio

async def main():
    loader = create_loader("/path/to/project")
    loader.initialize()
    
    predictions = await loader.predict_async(conversation)
    files = await loader.load_predicted_files_async(predictions[:3])
    
    return files

files = asyncio.run(main())
```

### Example 4: Export Predictions

```python
# Export for debugging or sharing
json_output = loader.export_predictions(
    predictions, 
    output_path=Path("predictions.json")
)
```

## CLI Usage

```bash
# Predict files for a query
python -m predictive_context_loader predict "fix authentication bug" --top-k 5

# Export predictions to JSON
python -m predictive_context_loader export --output predictions.json

# Show cache stats
python -m predictive_context_loader stats

# Clear cache
python -m predictive_context_loader clear-cache
```

## Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest tests/ --cov=predictive_context_loader --cov-report=html
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   PredictiveContextLoader                    │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Predictor  │  │PredictionCache│  │EmbeddingCache│      │
│  └──────┬───────┘  └──────────────┘  └──────────────┘      │
│         │                                                   │
│  ┌──────▼───────┐  ┌──────────────┐                        │
│  │Conversation  │  │FileIndexer   │                        │
│  │ Analyzer     │  │              │                        │
│  └──────────────┘  └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

## Performance

- Initial indexing: ~1-2 seconds per 100 files
- Prediction latency: <100ms
- Cache hit rate: Typically 60-80% for similar queries

## License

MIT
