# Skill 11: Cross-Language Polyglot

Seamlessly translate code between Python, JavaScript, TypeScript, Rust, Go, and more.

## Overview

The Polyglot skill translates code between programming languages while maintaining semantic equivalence and using idiomatic patterns in the target language.

## Installation

```bash
cd .kimi/skills/polyglot
pip install -r requirements.txt
```

## Quick Start

```python
from polyglot import PolyglotTranslator, TranslationRequest, Language

# Initialize translator
translator = PolyglotTranslator()

# Create translation request
request = TranslationRequest(
    source_code="""
def calculate_total(items):
    total = 0
    for item in items:
        total += item.price * item.quantity
    return total
""",
    source_language=Language.PYTHON,
    target_language=Language.JAVASCRIPT,
)

# Translate
result = translator.translate(request)
print(result.target_code)
```

## Examples

### Example 1: Python to JavaScript

```python
python_code = """
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
    
    def greet(self):
        return f"Hello, {self.name}!"

users = [User("Alice", "alice@example.com")]
for user in users:
    print(user.greet())
"""

request = TranslationRequest(
    source_code=python_code,
    source_language=Language.PYTHON,
    target_language=Language.JAVASCRIPT,
)

result = translator.translate(request)
print(result.target_code)
```

**Output:**
```javascript
class User {
    constructor(name, email) {
        this.name = name;
        this.email = email;
    }
    
    greet() {
        return `Hello, ${this.name}!`;
    }
}

const users = [new User("Alice", "alice@example.com")];
for (const user of users) {
    console.log(user.greet());
}
```

### Example 2: Python to Rust

```python
python_code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""

request = TranslationRequest(
    source_code=python_code,
    source_language=Language.PYTHON,
    target_language=Language.RUST,
)

result = translator.translate(request)
```

**Output:**
```rust
fn factorial(n: i64) -> i64 {
    if n <= 1 {
        return 1;
    }
    n * factorial(n - 1)
}
```

### Example 3: JavaScript to Python

```javascript
const data = users
    .filter(u => u.active)
    .map(u => ({ name: u.name, email: u.email }))
    .sort((a, b) => a.name.localeCompare(b.name));
```

**Translated:**
```python
data = sorted(
    [{"name": u.name, "email": u.email} for u in users if u.active],
    key=lambda x: x["name"]
)
```

### Example 4: Batch Translation

```python
from pathlib import Path

files = [
    (Path("src/models.py"), Path("dist/models.js")),
    (Path("src/utils.py"), Path("dist/utils.js")),
]

results = translator.batch_translate(files, Language.JAVASCRIPT)

for source, result in results.items():
    print(f"{source}: {len(result.warnings)} warnings")
```

## Features

### Language Support

| Source | Target | Confidence |
|--------|--------|------------|
| Python | JavaScript | 85% |
| JavaScript | Python | 85% |
| Python | TypeScript | 80% |
| Python | Rust | 70% |
| Python | Go | 70% |
| JavaScript | TypeScript | 95% |

### Semantic Preservation

The translator maintains:
- Control flow semantics
- Variable scope behavior
- Function/method signatures
- Error handling patterns
- Data structure operations

### Idiomatic Output

```python
# Python
squares = [x**2 for x in range(10) if x % 2 == 0]
```

```javascript
// JavaScript (idiomatic)
const squares = Array.from({length: 10}, (_, x) => x)
    .filter(x => x % 2 === 0)
    .map(x => x ** 2);
```

### Validation

```python
from polyglot import TranslationValidator

validator = TranslationValidator()
validation = validator.validate(request, result)

print(f"Valid: {validation.is_valid}")
print(f"Semantic preservation: {validation.semantic_preservation:.0%}")
for warning in validation.warnings:
    print(f"⚠️ {warning}")
```

## Type Mappings

### Python to JavaScript

| Python | JavaScript |
|--------|------------|
| `int` | `number` |
| `str` | `string` |
| `list` | `Array` |
| `dict` | `Object` |
| `None` | `null` |
| `True/False` | `true/false` |

### Python to Rust

| Python | Rust |
|--------|------|
| `int` | `i64` |
| `float` | `f64` |
| `str` | `String` |
| `list` | `Vec` |
| `dict` | `HashMap` |
| `None` | `Option` |

### Python to Go

| Python | Go |
|--------|-----|
| `int` | `int` |
| `str` | `string` |
| `list` | `[]interface{}` |
| `dict` | `map[string]interface{}` |
| `None` | `nil` |

## Function Mappings

### Python ↔ JavaScript

| Python | JavaScript |
|--------|------------|
| `print()` | `console.log()` |
| `len()` | `.length` |
| `range(n)` | `Array.from({length: n}, (_, i) => i)` |
| `list.append()` | `.push()` |
| `dict.get()` | `obj[key] ?? default` |
| `key in dict` | `dict.hasOwnProperty(key)` |

## API Reference

### PolyglotTranslator

```python
class PolyglotTranslator:
    def translate(self, request: TranslationRequest) -> TranslationResult
    def translate_file(self, source_path: Path, target_path: Path, target_language: Language) -> TranslationResult
    def batch_translate(self, files: List[Tuple[Path, Path]], target_language: Language) -> Dict[str, TranslationResult]
```

### TranslationRequest

```python
@dataclass
class TranslationRequest:
    source_code: str
    source_language: Language
    target_language: Language
    preserve_comments: bool = True
    preserve_docstrings: bool = True
    target_style: Optional[str] = None  # "idiomatic" or "literal"
    context: Optional[Dict[str, Any]] = None
```

### TranslationResult

```python
@dataclass
class TranslationResult:
    target_code: str
    source_language: Language
    target_language: Language
    warnings: List[str]
    info: List[str]
    dependencies: List[str]
    confidence: float
    partial_translation: bool
```

## Advanced Usage

### Custom Translation Patterns

```python
from polyglot.translator import TranslationPatterns

class CustomPatterns(TranslationPatterns):
    def translate(self, request):
        # Custom translation logic
        pass

# Register custom patterns
translator.patterns["custom"] = CustomPatterns()
```

### Context-Aware Translation

```python
request = TranslationRequest(
    source_code=code,
    source_language=Language.PYTHON,
    target_language=Language.JAVASCRIPT,
    context={
        "is_async": True,
        "use_types": True,
        "module_name": "userService",
    }
)
```

## Testing

```bash
pytest tests/ -v
```

## Limitations

- Complex metaprogramming may not translate accurately
- Language-specific features (e.g., Python decorators) need manual adjustment
- Memory management (Rust) and ownership need review
- Performance characteristics may differ

## Architecture

```
polyglot/
├── src/
│   ├── translator.py      # Main translation logic
│   └── validator.py       # Translation validation
├── tests/
│   ├── test_translator.py
│   └── test_validator.py
├── SKILL.md
└── requirements.txt
```
