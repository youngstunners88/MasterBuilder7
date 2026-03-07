"""
Rule Parser: Parses and structures business rules.
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class RulePriority(Enum):
    """Priority levels for business rules."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ParsedCondition:
    """A parsed condition."""
    left_operand: str
    operator: str
    right_operand: str
    negated: bool = False


@dataclass
class ParsedRule:
    """A parsed and structured business rule."""
    name: str
    description: str
    conditions: List[ParsedCondition]
    actions: List[str]
    priority: RulePriority
    effective_date: Optional[str] = None
    expiration_date: Optional[str] = None
    version: str = "1.0"
    owner: Optional[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class RuleParser:
    """
    Parses natural language and code into structured business rules.
    """
    
    # Operators and their variations
    OPERATORS = {
        "equals": ["=", "==", "===", "equals", "is", "equal to"],
        "not_equals": ["!=", "!==", "not equals", "is not", "not equal to"],
        "greater_than": [">", "greater than", "more than", "exceeds"],
        "less_than": ["<", "less than", "fewer than", "below"],
        "greater_equal": [">=", "greater than or equal", "at least"],
        "less_equal": ["<=", "less than or equal", "at most"],
        "contains": ["in", "contains", "includes", "has"],
        "not_contains": ["not in", "does not contain", "excludes"],
        "starts_with": ["starts with", "begins with"],
        "ends_with": ["ends with", "ends with"],
        "matches": ["matches", "conforms to", "satisfies"],
    }
    
    # Priority indicators
    PRIORITY_INDICATORS = {
        RulePriority.CRITICAL: ["must", "required", "critical", "mandatory", "shall"],
        RulePriority.HIGH: ["should", "important", "high priority", "strongly recommended"],
        RulePriority.MEDIUM: ["may", "can", "recommended", "normal"],
        RulePriority.LOW: ["could", "optional", "low priority", "if possible"],
    }
    
    def __init__(self):
        self.operator_patterns = self._compile_operator_patterns()
    
    def _compile_operator_patterns(self) -> Dict[str, re.Pattern]:
        """Compile operator patterns for matching."""
        patterns = {}
        for op_name, variations in self.OPERATORS.items():
            escaped = [re.escape(v) for v in variations]
            pattern = r'\s*(' + '|'.join(escaped) + r')\s*'
            patterns[op_name] = re.compile(pattern, re.IGNORECASE)
        return patterns
    
    def parse_from_text(self, text: str) -> List[ParsedRule]:
        """
        Parse business rules from natural language text.
        
        Args:
            text: Natural language text describing rules
            
        Returns:
            List of parsed rules
        """
        rules = []
        
        # Split into potential rule statements
        statements = self._split_into_statements(text)
        
        for statement in statements:
            rule = self._parse_statement(statement)
            if rule:
                rules.append(rule)
        
        return rules
    
    def parse_from_condition(self, condition: str) -> Optional[ParsedCondition]:
        """
        Parse a single condition string.
        
        Args:
            condition: Condition string (e.g., "age > 18")
            
        Returns:
            ParsedCondition or None
        """
        # Check for negation
        negated = False
        clean_condition = condition
        if condition.startswith("not ") or condition.startswith("!"):
            negated = True
            clean_condition = condition[4:] if condition.startswith("not ") else condition[1:]
        
        # Try to match operators
        for op_name, pattern in self.operator_patterns.items():
            match = pattern.search(clean_condition)
            if match:
                parts = pattern.split(clean_condition, maxsplit=1)
                if len(parts) == 2:
                    return ParsedCondition(
                        left_operand=parts[0].strip(),
                        operator=match.group(1),
                        right_operand=parts[1].strip(),
                        negated=negated,
                    )
        
        # Default: treat as boolean check
        return ParsedCondition(
            left_operand=clean_condition,
            operator="is_truthy",
            right_operand="true",
            negated=negated,
        )
    
    def parse_code_condition(self, condition: str, language: str = "python") -> Optional[ParsedCondition]:
        """
        Parse a condition from code.
        
        Args:
            condition: Code condition string
            language: Programming language
            
        Returns:
            ParsedCondition or None
        """
        # Normalize the condition
        normalized = condition.strip()
        
        # Handle common patterns
        if language == "python":
            return self._parse_python_condition(normalized)
        elif language in ["javascript", "typescript"]:
            return self._parse_js_condition(normalized)
        
        return self.parse_from_condition(normalized)
    
    def _parse_python_condition(self, condition: str) -> Optional[ParsedCondition]:
        """Parse a Python condition."""
        # Handle 'in' operator
        match = re.match(r'(\w+)\s+in\s+(.+)', condition)
        if match:
            return ParsedCondition(
                left_operand=match.group(1),
                operator="in",
                right_operand=match.group(2),
            )
        
        # Handle comparisons
        match = re.match(r'(.+?)\s*(==|!=|<=|>=|<|>)\s*(.+)', condition)
        if match:
            return ParsedCondition(
                left_operand=match.group(1).strip(),
                operator=match.group(2),
                right_operand=match.group(3).strip(),
            )
        
        # Handle 'is None' / 'is not None'
        match = re.match(r'(.+?)\s+is\s+(not\s+)?None', condition)
        if match:
            return ParsedCondition(
                left_operand=match.group(1).strip(),
                operator="is_not" if match.group(2) else "is",
                right_operand="None",
            )
        
        # Boolean condition
        return ParsedCondition(
            left_operand=condition,
            operator="is_truthy",
            right_operand="True",
        )
    
    def _parse_js_condition(self, condition: str) -> Optional[ParsedCondition]:
        """Parse a JavaScript condition."""
        # Handle strict equality
        match = re.match(r'(.+?)\s*(===|!==|==|!=|<=|>=|<|>)\s*(.+)', condition)
        if match:
            return ParsedCondition(
                left_operand=match.group(1).strip(),
                operator=match.group(2),
                right_operand=match.group(3).strip(),
            )
        
        # Handle 'includes'
        match = re.match(r'(.+?)\.includes\((.+?)\)', condition)
        if match:
            return ParsedCondition(
                left_operand=match.group(2).strip(),
                operator="in",
                right_operand=match.group(1).strip(),
            )
        
        return ParsedCondition(
            left_operand=condition,
            operator="is_truthy",
            right_operand="true",
        )
    
    def _split_into_statements(self, text: str) -> List[str]:
        """Split text into potential rule statements."""
        # Split by periods, but keep abbreviations
        text = re.sub(r'\.(?=[a-z])', '. ', text)  # Space after period if followed by lowercase
        
        # Split sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Filter and clean
        statements = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10 and self._looks_like_rule(sentence):
                statements.append(sentence)
        
        return statements
    
    def _looks_like_rule(self, text: str) -> bool:
        """Check if text looks like a business rule."""
        rule_indicators = [
            "if", "when", "must", "should", "required", "cannot",
            "must not", "should not", "only", "always", "never",
        ]
        return any(indicator in text.lower() for indicator in rule_indicators)
    
    def _parse_statement(self, statement: str) -> Optional[ParsedRule]:
        """Parse a single statement into a rule."""
        # Try to extract condition and action
        # Pattern: "If [condition], then [action]" or "When [condition], [action]"
        
        patterns = [
            r'(?:if|when)\s+(.+?),?\s*(?:then)?\s*(.+?)(?:\.|$)',
            r'(.+?)\s+must\s+(.+?)(?:\.|$)',
            r'(.+?)\s+should\s+(.+?)(?:\.|$)',
            r'(.+?)\s+cannot\s+(.+?)(?:\.|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, statement, re.IGNORECASE)
            if match:
                condition_text = match.group(1).strip()
                action_text = match.group(2).strip()
                
                # Parse conditions
                conditions = self._parse_conditions(condition_text)
                
                # Determine priority
                priority = self._determine_priority(statement)
                
                # Generate name
                name = self._generate_rule_name(statement, conditions)
                
                return ParsedRule(
                    name=name,
                    description=statement,
                    conditions=conditions,
                    actions=[action_text],
                    priority=priority,
                )
        
        return None
    
    def _parse_conditions(self, condition_text: str) -> List[ParsedCondition]:
        """Parse conditions from text."""
        conditions = []
        
        # Split by AND/OR
        parts = re.split(r'\s+(?:and|&&)\s+', condition_text, flags=re.IGNORECASE)
        
        for part in parts:
            condition = self.parse_from_condition(part.strip())
            if condition:
                conditions.append(condition)
        
        return conditions
    
    def _determine_priority(self, text: str) -> RulePriority:
        """Determine rule priority from text."""
        text_lower = text.lower()
        
        for priority, indicators in self.PRIORITY_INDICATORS.items():
            if any(indicator in text_lower for indicator in indicators):
                return priority
        
        return RulePriority.MEDIUM
    
    def _generate_rule_name(
        self, 
        statement: str, 
        conditions: List[ParsedCondition]
    ) -> str:
        """Generate a rule name from statement."""
        # Use first few words
        words = statement.split()[:5]
        name = '_'.join(w.lower() for w in words if w.isalnum())
        name = re.sub(r'[^a-z0-9_]', '_', name)
        return name or "unnamed_rule"
    
    def to_decision_table(self, rules: List[ParsedRule]) -> Dict[str, Any]:
        """
        Convert rules to a decision table format.
        
        Args:
            rules: List of parsed rules
            
        Returns:
            Decision table structure
        """
        # Collect all unique conditions
        all_conditions = set()
        for rule in rules:
            for cond in rule.conditions:
                all_conditions.add(cond.left_operand)
        
        conditions = sorted(all_conditions)
        
        # Build table rows
        rows = []
        for rule in rules:
            row = {
                "rule_name": rule.name,
                "conditions": {},
                "actions": rule.actions,
                "priority": rule.priority.value,
            }
            
            for cond in rule.conditions:
                row["conditions"][cond.left_operand] = {
                    "operator": cond.operator,
                    "value": cond.right_operand,
                    "negated": cond.negated,
                }
            
            rows.append(row)
        
        return {
            "conditions": conditions,
            "rules": rows,
        }
    
    def to_pseudo_code(self, rule: ParsedRule, language: str = "python") -> str:
        """
        Convert a parsed rule to pseudo-code.
        
        Args:
            rule: Parsed rule
            language: Target language style
            
        Returns:
            Pseudo-code string
        """
        lines = [f"# Rule: {rule.name}", f"# {rule.description}"]
        
        if language == "python":
            # Build condition
            if rule.conditions:
                condition_parts = []
                for cond in rule.conditions:
                    op = cond.operator
                    if op == "is_truthy":
                        part = cond.left_operand
                    elif op in ["in", "contains"]:
                        part = f"{cond.left_operand} in {cond.right_operand}"
                    else:
                        part = f"{cond.left_operand} {op} {cond.right_operand}"
                    
                    if cond.negated:
                        part = f"not ({part})"
                    condition_parts.append(part)
                
                condition = " and ".join(condition_parts)
                lines.append(f"if {condition}:")
                
                for action in rule.actions:
                    lines.append(f"    {action}")
        
        elif language == "sql":
            # Generate SQL WHERE clause
            if rule.conditions:
                where_parts = []
                for cond in rule.conditions:
                    op_map = {
                        "equals": "=",
                        "not_equals": "!=",
                        "greater_than": ">",
                        "less_than": "<",
                        "contains": "LIKE",
                    }
                    sql_op = op_map.get(cond.operator, cond.operator)
                    where_parts.append(f"{cond.left_operand} {sql_op} {cond.right_operand}")
                
                where_clause = " AND ".join(where_parts)
                lines.append(f"WHERE {where_clause}")
        
        return "\n".join(lines)
    
    def validate_rule(self, rule: ParsedRule) -> List[str]:
        """
        Validate a parsed rule for common issues.
        
        Args:
            rule: Rule to validate
            
        Returns:
            List of validation warnings
        """
        warnings = []
        
        # Check for vague conditions
        for cond in rule.conditions:
            if len(cond.left_operand) < 3:
                warnings.append(f"Condition operand '{cond.left_operand}' is very short")
            if len(cond.right_operand) < 2:
                warnings.append(f"Condition value '{cond.right_operand}' is very short")
        
        # Check for missing actions
        if not rule.actions:
            warnings.append("Rule has no actions")
        
        # Check for contradictory conditions
        if len(rule.conditions) > 1:
            # Simple check: same operand with different operators
            operands = {}
            for cond in rule.conditions:
                if cond.left_operand in operands:
                    warnings.append(
                        f"Multiple conditions on '{cond.left_operand}' - check for contradictions"
                    )
                operands[cond.left_operand] = cond
        
        return warnings
