# Skill 12: Business Logic Extractor

Understands what code does, not just how. Extracts business rules, domain entities, and generates human-readable documentation.

## Overview

The Business Logic Extractor analyzes source code to identify:
- Business rules and constraints
- Domain entities and their relationships
- Data flows through the system
- Decision trees from conditional logic

## Installation

```bash
cd .kimi/skills/business-logic-extractor
pip install -r requirements.txt
```

## Quick Start

```python
from business_logic_extractor import BusinessLogicExtractor

# Initialize extractor
extractor = BusinessLogicExtractor()

# Extract from code
code = """
class Order:
    def __init__(self, amount, customer):
        self.amount = amount
        self.customer = customer
    
    def apply_discount(self):
        if self.customer.is_vip:
            return self.amount * 0.9
        if self.amount > 1000:
            return self.amount * 0.95
        return self.amount
"""

result = extractor.extract(code, "orders.py")

# Review extracted rules
for rule in result.rules:
    print(f"Rule: {rule.name}")
    print(f"  {rule.description}")
```

## Examples

### Example 1: Extract Business Rules

```python
code = """
def process_payment(order, payment_method):
    # Validate order
    if order.status != "pending":
        raise ValueError("Order must be pending")
    
    # Check amount limits
    if order.amount > 10000:
        require_manager_approval(order)
    
    # Apply payment method rules
    if payment_method == "credit_card":
        if order.amount < 5:
            raise ValueError("Minimum amount for credit card is $5")
        process_credit_card(order)
    elif payment_method == "wire":
        if order.amount < 100:
            raise ValueError("Minimum amount for wire is $100")
        process_wire(order)
    
    order.status = "paid"
    notify_customer(order.customer, "Payment processed")
"""

result = extractor.extract(code, "payment.py")

for rule in result.rules:
    print(f"\n[{rule.rule_type.value.upper()}] {rule.name}")
    print(f"  {rule.description}")
    if rule.conditions:
        print("  Conditions:")
        for c in rule.conditions:
            print(f"    - {c}")
```

**Output:**
```
[VALIDATION] validate_order_status
  Rule 'validate_order_status': When order.status != "pending", then raise ValueError
  Conditions:
    - order.status != "pending"

[CONSTRAINT] check_amount_limits
  Rule 'check_amount_limits': When order.amount > 10000, then require_manager_approval
  Conditions:
    - order.amount > 10000

[VALIDATION] credit_card_minimum
  Rule 'credit_card_minimum': When payment_method == "credit_card" AND order.amount < 5
  Conditions:
    - payment_method == "credit_card"
    - order.amount < 5
```

### Example 2: Extract Domain Model

```python
code = """
@dataclass
class Product:
    id: str
    name: str
    price: float
    stock: int
    
    def is_available(self, quantity: int) -> bool:
        return self.stock >= quantity
    
    def reserve(self, quantity: int):
        if not self.is_available(quantity):
            raise OutOfStockError()
        self.stock -= quantity

class Customer:
    def __init__(self, id: str, email: str, tier: str = "bronze"):
        self.id = id
        self.email = email
        self.tier = tier
        self.orders = []
    
    def can_order(self, amount: float) -> bool:
        max_amount = {"bronze": 1000, "silver": 5000, "gold": 10000}
        return amount <= max_amount.get(self.tier, 1000)
"""

result = extractor.extract(code, "models.py")

for entity in result.entities:
    print(f"\nEntity: {entity.name}")
    for attr in entity.attributes:
        print(f"  - {attr['name']}: {attr['type']}")
```

**Output:**
```
Entity: Product
  - id: str
  - name: str
  - price: float
  - stock: int

Entity: Customer
  - id: str
  - email: str
  - tier: str
```

### Example 3: Generate Documentation

```python
from business_logic_extractor import BusinessDocumenter, DocumentationConfig

config = DocumentationConfig(
    format="markdown",
    include_code_references=True,
    include_diagrams=True,
    project_name="E-Commerce System",
    company_name="Acme Corp",
)

documenter = BusinessDocumenter(config)
doc = documenter.generate(result)

# Save to file
documenter.generate(result, output_path=Path("business-logic.md"))
```

### Example 4: Project-Wide Extraction

```python
from pathlib import Path

project_path = Path("/path/to/project")
results = extractor.extract_from_project(project_path)

all_rules = []
all_entities = []

for filepath, result in results.items():
    all_rules.extend(result.rules)
    all_entities.extend(result.entities)

print(f"Total rules found: {len(all_rules)}")
print(f"Total entities found: {len(all_entities)}")

# Generate consolidated documentation
combined = ExtractionResult(
    rules=all_rules,
    entities=all_entities,
    data_flows=[],
    decision_trees=[],
    summary=f"Extracted from {len(results)} files",
    confidence=sum(r.confidence for r in all_rules) / len(all_rules) if all_rules else 0,
)

documenter.generate(combined, output_path=Path("project-documentation.md"))
```

## Features

### Rule Types

| Type | Description | Example |
|------|-------------|---------|
| VALIDATION | Input/constraint checking | `if age < 18: raise Error` |
| CALCULATION | Business calculations | `total = price * quantity` |
| WORKFLOW | Process orchestration | `if status == "pending": process()` |
| ACCESS_CONTROL | Permission checks | `if user.is_admin: allow()` |
| NOTIFICATION | Alerts/messages | `send_email(customer)` |
| TRANSFORMATION | Data conversion | `format_date(timestamp)` |
| CONSTRAINT | Business limits | `if amount > max: reject()` |

### Decision Trees

The extractor builds decision trees from nested conditionals:

```python
if customer.vip:
    if order.amount > 1000:
        discount = 0.20
    else:
        discount = 0.10
else:
    discount = 0.05
```

**Extracted Tree:**
```
IF: customer.vip
  THEN IF: order.amount > 1000
    THEN: discount = 0.20
    ELSE: discount = 0.10
  ELSE: discount = 0.05
```

### Data Flow Detection

Automatically detects:
- HTTP API calls (fetch, axios, requests)
- Database operations (save, update, query)
- Message sending (notifications, events)
- File I/O operations

## API Reference

### BusinessLogicExtractor

```python
class BusinessLogicExtractor:
    def extract(self, code: str, filename: str, language: str = "python") -> ExtractionResult
    def extract_from_file(self, filepath: Path) -> ExtractionResult
    def extract_from_project(self, project_path: Path) -> Dict[str, ExtractionResult]
    def generate_documentation(self, result: ExtractionResult) -> str
```

### BusinessDocumenter

```python
class BusinessDocumenter:
    def generate(self, result: ExtractionResult, output_path: Optional[Path] = None) -> str
    def export_to_format(self, result: ExtractionResult, format_type: str, output_path: Path) -> Path
```

### ExtractionResult

```python
@dataclass
class ExtractionResult:
    rules: List[BusinessRule]
    entities: List[DomainEntity]
    data_flows: List[DataFlow]
    decision_trees: List[DecisionNode]
    summary: str
    confidence: float
```

## Rule Parser

### Parse Natural Language Rules

```python
from business_logic_extractor import RuleParser

parser = RuleParser()

text = """
If the customer is a VIP and the order amount exceeds $1000,
then apply a 20% discount and send a thank you email.
"""

rules = parser.parse_from_text(text)
for rule in rules:
    print(f"Parsed: {rule.name}")
    for cond in rule.conditions:
        print(f"  Condition: {cond.left_operand} {cond.operator} {cond.right_operand}")
```

### Decision Tables

```python
# Convert rules to decision table
table = parser.to_decision_table(rules)

print("Conditions:", table["conditions"])
for rule_row in table["rules"]:
    print(f"Rule: {rule_row['rule_name']}")
    print(f"  When: {rule_row['conditions']}")
    print(f"  Then: {rule_row['actions']}")
```

### Generate Pseudo-Code

```python
# Generate executable pseudo-code
for rule in parsed_rules:
    code = parser.to_pseudo_code(rule, language="python")
    print(code)
```

## Documentation Formats

### Markdown (default)

```python
config = DocumentationConfig(format="markdown")
```

### HTML

```python
config = DocumentationConfig(format="html")
```

### JSON

```python
documenter.export_to_format(result, "json", Path("rules.json"))
```

### YAML

```python
documenter.export_to_format(result, "yaml", Path("rules.yaml"))
```

## Configuration

### DocumentationConfig

```python
@dataclass
class DocumentationConfig:
    format: str = "markdown"           # markdown, html, json, yaml
    include_code_references: bool = True
    include_diagrams: bool = True
    include_decision_tables: bool = True
    style: str = "professional"        # professional, technical, simple
    company_name: Optional[str] = None
    project_name: Optional[str] = None
    version: str = "1.0"
```

## Testing

```bash
pytest tests/ -v
```

## Architecture

```
business-logic-extractor/
├── src/
│   ├── extractor.py      # Business logic extraction
│   ├── rule_parser.py    # Rule parsing and structuring
│   └── documenter.py     # Documentation generation
├── tests/
│   ├── test_extractor.py
│   └── test_documenter.py
├── SKILL.md
└── requirements.txt
```

## Use Cases

1. **Legacy Code Documentation** - Document undocumented systems
2. **Knowledge Transfer** - Help new team members understand business logic
3. **Compliance Audits** - Extract rules for regulatory review
4. **Refactoring Planning** - Understand dependencies before changes
5. **Business-IT Alignment** - Generate docs for business stakeholders
