"""
Tests for BusinessLogicExtractor.
"""

import pytest
from src.extractor import BusinessLogicExtractor, RuleType


class TestBusinessLogicExtractor:
    """Test cases for BusinessLogicExtractor."""
    
    def setup_method(self):
        self.extractor = BusinessLogicExtractor()
    
    def test_extract_validation_rule(self):
        """Test extracting validation rules."""
        code = """
def process_order(order):
    if order.amount <= 0:
        raise ValueError("Amount must be positive")
    return order
"""
        result = self.extractor.extract(code, "orders.py")
        
        validation_rules = [r for r in result.rules if r.rule_type == RuleType.VALIDATION]
        assert len(validation_rules) > 0
    
    def test_extract_calculation_rule(self):
        """Test extracting calculation rules."""
        code = """
def calculate_total(items):
    total = sum(item.price * item.quantity for item in items)
    return total * 1.08  # Add tax
"""
        result = self.extractor.extract(code, "orders.py")
        
        calc_rules = [r for r in result.rules if r.rule_type == RuleType.CALCULATION]
        assert len(calc_rules) > 0
    
    def test_extract_entity(self):
        """Test extracting domain entities."""
        code = """
class Customer:
    def __init__(self, id, name, email):
        self.id = id
        self.name = name
        self.email = email
"""
        result = self.extractor.extract(code, "models.py")
        
        assert len(result.entities) > 0
        assert result.entities[0].name == "Customer"
    
    def test_extract_entity_attributes(self):
        """Test extracting entity attributes."""
        code = """
from dataclasses import dataclass

@dataclass
class Product:
    id: str
    name: str
    price: float
"""
        result = self.extractor.extract(code, "models.py")
        
        if result.entities:
            product = result.entities[0]
            assert product.name == "Product"
            attr_names = [a["name"] for a in product.attributes]
            assert "id" in attr_names
            assert "name" in attr_names
    
    def test_extract_workflow_rule(self):
        """Test extracting workflow rules."""
        code = """
def process_order(order):
    if order.status == "pending":
        validate_order(order)
        charge_payment(order)
        order.status = "processing"
    elif order.status == "processing":
        ship_order(order)
        order.status = "shipped"
"""
        result = self.extractor.extract(code, "workflow.py")
        
        workflow_rules = [r for r in result.rules if r.rule_type == RuleType.WORKFLOW]
        assert len(workflow_rules) > 0
    
    def test_extract_access_control_rule(self):
        """Test extracting access control rules."""
        code = """
def delete_user(user_id, current_user):
    if not current_user.is_admin:
        raise PermissionError("Admin required")
    # Delete logic
"""
        result = self.extractor.extract(code, "auth.py")
        
        access_rules = [r for r in result.rules if r.rule_type == RuleType.ACCESS_CONTROL]
        assert len(access_rules) > 0
    
    def test_generate_documentation(self):
        """Test documentation generation."""
        code = """
class Order:
    def apply_discount(self):
        if self.amount > 1000:
            return self.amount * 0.9
        return self.amount
"""
        result = self.extractor.extract(code, "orders.py")
        doc = self.extractor.generate_documentation(result)
        
        assert "# Business Logic Documentation" in doc
        assert "Order" in doc
    
    def test_looks_like_business_rule(self):
        """Test business rule detection."""
        assert self.extractor._looks_like_business_rule("amount > 100")
        assert self.extractor._looks_like_business_rule("status == 'approved'")
        assert not self.extractor._looks_like_business_rule("x == y")
    
    def test_calculate_confidence(self):
        """Test confidence calculation."""
        from src.extractor import BusinessRule, RuleType
        
        rules = [
            BusinessRule(
                name="rule1",
                rule_type=RuleType.VALIDATION,
                description="Test",
                conditions=[],
                actions=[],
                source_file="test.py",
                line_start=1,
                line_end=2,
                confidence=0.9,
            ),
            BusinessRule(
                name="rule2",
                rule_type=RuleType.VALIDATION,
                description="Test",
                conditions=[],
                actions=[],
                source_file="test.py",
                line_start=3,
                line_end=4,
                confidence=0.7,
            )
        ]
        
        confidence = self.extractor._calculate_confidence(rules, [])
        assert confidence == 0.8


class TestRuleType:
    """Test cases for RuleType enum."""
    
    def test_rule_types(self):
        """Test all rule types exist."""
        assert RuleType.VALIDATION
        assert RuleType.CALCULATION
        assert RuleType.WORKFLOW
        assert RuleType.ACCESS_CONTROL
        assert RuleType.NOTIFICATION
        assert RuleType.TRANSFORMATION
        assert RuleType.CONSTRAINT
