"""
Tests for RuleParser.
"""

import pytest
from src.rule_parser import RuleParser, RulePriority, ParsedCondition


class TestRuleParser:
    """Test cases for RuleParser."""
    
    def setup_method(self):
        self.parser = RuleParser()
    
    def test_parse_from_text_simple(self):
        """Test parsing simple rule from text."""
        text = "If the amount is greater than 100, then apply discount."
        rules = self.parser.parse_from_text(text)
        
        assert len(rules) > 0
        assert rules[0].name == "if_the_amount"
    
    def test_parse_from_text_multiple(self):
        """Test parsing multiple rules from text."""
        text = """
If the customer is VIP, give 20% discount.
If the order amount exceeds $1000, require approval.
"""
        rules = self.parser.parse_from_text(text)
        
        assert len(rules) >= 2
    
    def test_parse_condition_simple(self):
        """Test parsing simple condition."""
        condition = "age > 18"
        parsed = self.parser.parse_from_condition(condition)
        
        assert parsed.left_operand == "age"
        assert parsed.operator == ">"
        assert parsed.right_operand == "18"
    
    def test_parse_condition_with_in(self):
        """Test parsing 'in' condition."""
        condition = "status in ['active', 'pending']"
        parsed = self.parser.parse_from_condition(condition)
        
        assert parsed.left_operand == "status"
        assert parsed.operator == "in"
    
    def test_parse_condition_negated(self):
        """Test parsing negated condition."""
        condition = "not is_active"
        parsed = self.parser.parse_from_condition(condition)
        
        assert parsed.negated is True
        assert "is_active" in parsed.left_operand
    
    def test_parse_python_condition(self):
        """Test parsing Python condition."""
        condition = "x == 5"
        parsed = self.parser._parse_python_condition(condition)
        
        assert parsed.left_operand == "x"
        assert parsed.operator == "=="
        assert parsed.right_operand == "5"
    
    def test_parse_python_condition_is_none(self):
        """Test parsing 'is None' condition."""
        condition = "user is None"
        parsed = self.parser._parse_python_condition(condition)
        
        assert parsed.operator == "is"
        assert parsed.right_operand == "None"
    
    def test_determine_priority_critical(self):
        """Test detecting critical priority."""
        text = "The system must validate all inputs"
        priority = self.parser._determine_priority(text)
        assert priority == RulePriority.CRITICAL
    
    def test_determine_priority_high(self):
        """Test detecting high priority."""
        text = "Users should be notified of errors"
        priority = self.parser._determine_priority(text)
        assert priority == RulePriority.HIGH
    
    def test_determine_priority_low(self):
        """Test detecting low priority."""
        text = "This could be implemented later"
        priority = self.parser._determine_priority(text)
        assert priority == RulePriority.LOW
    
    def test_to_decision_table(self):
        """Test converting rules to decision table."""
        from src.rule_parser import ParsedRule
        
        rules = [
            ParsedRule(
                name="vip_discount",
                description="VIP discount rule",
                conditions=[
                    ParsedCondition("customer.tier", "equals", "VIP")
                ],
                actions=["apply 20% discount"],
                priority=RulePriority.HIGH,
            ),
            ParsedRule(
                name="bulk_discount",
                description="Bulk order discount",
                conditions=[
                    ParsedCondition("order.amount", ">", "1000")
                ],
                actions=["apply 10% discount"],
                priority=RulePriority.MEDIUM,
            )
        ]
        
        table = self.parser.to_decision_table(rules)
        
        assert "conditions" in table
        assert "rules" in table
        assert len(table["rules"]) == 2
    
    def test_to_pseudo_code_python(self):
        """Test generating Python pseudo-code."""
        from src.rule_parser import ParsedRule
        
        rule = ParsedRule(
            name="test_rule",
            description="Test rule",
            conditions=[
                ParsedCondition("age", ">=", "18")
            ],
            actions=["allow_access()"],
            priority=RulePriority.HIGH,
        )
        
        code = self.parser.to_pseudo_code(rule, "python")
        assert "if" in code
        assert "age" in code
        assert "allow_access" in code
    
    def test_validate_rule(self):
        """Test rule validation."""
        from src.rule_parser import ParsedRule
        
        rule = ParsedRule(
            name="x",
            description="Test",
            conditions=[
                ParsedCondition("x", ">", "y")
            ],
            actions=[],
            priority=RulePriority.MEDIUM,
        )
        
        warnings = self.parser.validate_rule(rule)
        assert len(warnings) > 0  # Should warn about no actions
        assert any("no actions" in w.lower() for w in warnings)
    
    def test_split_into_statements(self):
        """Test splitting text into statements."""
        text = "If A then B. If C then D."
        statements = self.parser._split_into_statements(text)
        
        assert len(statements) >= 1
