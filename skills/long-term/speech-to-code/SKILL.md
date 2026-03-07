# Skill 9: Code Synthesis from Speech

Convert natural language descriptions into complete, production-ready code.

## Overview

The Speech-to-Code skill transforms spoken or written descriptions into working implementations. It understands FastAPI, React, Node.js, Flask, and generic Python patterns.

## Installation

```bash
cd .kimi/skills/speech-to-code
pip install -r requirements.txt
```

## Quick Start

```python
from speech_to_code import CodeSynthesizer, SynthesisRequest

# Initialize synthesizer
synthesizer = CodeSynthesizer()

# Create a request
request = SynthesisRequest(
    description="Build me a login system with JWT authentication",
    language="python",
    framework="fastapi",
    include_tests=True,
    include_auth=True,
)

# Synthesize code
result = synthesizer.synthesize(request)

# Access generated files
for filename, content in result.files.items():
    print(f"=== {filename} ===")
    print(content)
```

## Examples

### Example 1: FastAPI CRUD API

```python
request = SynthesisRequest(
    description="Create a REST API for managing products with name, price, and stock",
    framework="fastapi",
)
result = synthesizer.synthesize(request)
```

**Output:**
- `models.py` - Pydantic models for Product
- `routes.py` - CRUD endpoints
- `main.py` - FastAPI app setup
- `requirements.txt` - Dependencies

### Example 2: React Component

```python
request = SynthesisRequest(
    description="Build a user profile component with name, email, and avatar",
    framework="react",
)
result = synthesizer.synthesize(request)
```

**Output:**
- `UserProfile.jsx` - React component
- `App.jsx` - Main app integration
- `package.json` - Dependencies

### Example 3: With Authentication

```python
request = SynthesisRequest(
    description="User registration and login API",
    framework="fastapi",
    include_auth=True,
    include_validation=True,
)
result = synthesizer.synthesize(request)
```

**Output:**
- Auth routes with JWT
- Password hashing
- Token validation middleware
- User models

## Features

### Automatic Framework Detection

```python
# Detects "fastapi" from keywords
request = SynthesisRequest(
    description="Create API endpoints for order management",
    # framework is auto-detected as "fastapi"
)
```

### Entity Extraction

Automatically extracts entities from descriptions:
- "Create a product with name and price" → Product entity
- "User login system" → User entity
- "Order processing" → Order entity

### CRUD Operation Detection

Recognizes operations from keywords:
- Create: "create", "add", "new", "register"
- Read: "get", "fetch", "retrieve", "list"
- Update: "update", "edit", "modify"
- Delete: "delete", "remove", "destroy"

### Template Engine

Use templates for common patterns:

```python
from speech_to_code import TemplateEngine

engine = TemplateEngine()

# Render a template
code = engine.render_template("fastapi_crud", 
    entity="Product",
    entity_lower="product",
    fields="name: str\n    price: float",
    create_fields="name: str\n    price: float",
    update_fields="name: Optional[str]\n    price: Optional[float]"
)
```

## API Reference

### CodeSynthesizer

```python
class CodeSynthesizer:
    def synthesize(self, request: SynthesisRequest) -> SynthesisResult
    def _detect_framework(self, description: str) -> Optional[str]
    def _parse_requirements(self, description: str) -> Dict[str, Any]
```

### SynthesisRequest

```python
@dataclass
class SynthesisRequest:
    description: str          # Natural language description
    language: str = "python"  # Target language
    framework: Optional[str]  # "fastapi", "react", "node", etc.
    include_tests: bool = True
    include_auth: bool = False
    include_validation: bool = True
    target_directory: Optional[str]
    context: Optional[Dict]   # Additional context
```

### SynthesisResult

```python
@dataclass
class SynthesisResult:
    files: Dict[str, str]           # Generated files
    tests: Dict[str, str]           # Test files
    dependencies: List[str]         # Required dependencies
    setup_instructions: List[str]   # Setup steps
    validation_results: Dict        # Validation output
    estimated_complexity: str       # Simple/Medium/Complex
```

## Supported Frameworks

| Framework | Language | Features |
|-----------|----------|----------|
| FastAPI | Python | CRUD, Auth, Validation |
| React | JavaScript/JSX | Components, Hooks |
| Node.js | JavaScript | Express, Mongoose |
| Flask | Python | Routes, Models |
| Django | Python | Models, Views |

## Validation

Code is automatically validated:

```python
from speech_to_code import CodeValidator

validator = CodeValidator()
result = validator.validate(code, "python")

print(result.is_valid)  # True/False
print(result.issues)    # List of issues
```

## Testing

```bash
pytest tests/
```

## Architecture

```
speech-to-code/
├── src/
│   ├── synthesizer.py      # Main synthesis logic
│   ├── template_engine.py  # Template management
│   └── validator.py        # Code validation
├── tests/
│   ├── test_synthesizer.py
│   └── test_validator.py
├── SKILL.md
└── requirements.txt
```

## Extending

Add custom templates:

```python
from speech_to_code import CodeTemplate

template = CodeTemplate(
    name="custom_api",
    language="python",
    template="""
def {{function_name}}({{args}}):
    {{body}}
""",
    placeholders=["function_name", "args", "body"],
    description="Custom API template"
)

engine.add_template(template)
```
