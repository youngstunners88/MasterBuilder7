"""
Business Logic Extractor: Extracts business rules from code.
"""

import ast
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class RuleType(Enum):
    """Types of business rules."""
    VALIDATION = "validation"
    CALCULATION = "calculation"
    WORKFLOW = "workflow"
    ACCESS_CONTROL = "access_control"
    NOTIFICATION = "notification"
    INTEGRATION = "integration"
    TRANSFORMATION = "transformation"
    CONSTRAINT = "constraint"


@dataclass
class DomainEntity:
    """A domain entity extracted from code."""
    name: str
    attributes: List[Dict[str, Any]]
    relationships: List[Dict[str, str]]
    business_rules: List[str]
    source_file: str
    line_number: int


@dataclass
class DataFlow:
    """A data flow between components."""
    source: str
    target: str
    data_type: str
    transformation: Optional[str]
    conditions: List[str]
    source_file: str


@dataclass
class BusinessRule:
    """A business rule extracted from code."""
    name: str
    rule_type: RuleType
    description: str
    conditions: List[str]
    actions: List[str]
    source_file: str
    line_start: int
    line_end: int
    confidence: float
    related_entities: List[str] = field(default_factory=list)


@dataclass
class DecisionNode:
    """A node in a decision tree."""
    condition: str
    true_branch: Optional[Any]
    false_branch: Optional[Any]
    action: Optional[str]


@dataclass
class ExtractionResult:
    """Result of business logic extraction."""
    rules: List[BusinessRule]
    entities: List[DomainEntity]
    data_flows: List[DataFlow]
    decision_trees: List[DecisionNode]
    summary: str
    confidence: float


class BusinessLogicExtractor:
    """
    Extracts business rules, entities, and flows from code.
    """
    
    # Keywords that indicate business logic
    BUSINESS_KEYWORDS = {
        "validation": ["validate", "check", "verify", "ensure", "assert", "require"],
        "calculation": ["calculate", "compute", "sum", "total", "amount", "price", "cost"],
        "workflow": ["process", "workflow", "stage", "status", "approve", "reject"],
        "access": ["permission", "authorize", "access", "role", "admin", "user"],
        "notification": ["notify", "email", "send", "alert", "message"],
        "transformation": ["transform", "convert", "parse", "format", "serialize"],
        "constraint": ["limit", "restrict", "max", "min", "constraint", "boundary"],
    }
    
    # Entity naming patterns
    ENTITY_PATTERNS = [
        r'class\s+(\w+)(?:Model|Entity|Domain)?',
        r'dataclass\s+(\w+)',
        r'type\s+(\w+)\s*=',
        r'interface\s+(\w+)',
    ]
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    def extract_from_file(self, filepath: Path) -> ExtractionResult:
        """Extract business logic from a file."""
        code = filepath.read_text()
        language = self._detect_language(filepath.suffix)
        return self.extract(code, str(filepath), language)
    
    def extract(
        self, 
        code: str, 
        filename: str,
        language: str = "python"
    ) -> ExtractionResult:
        """
        Extract business logic from code.
        
        Args:
            code: Source code
            filename: File path
            language: Programming language
            
        Returns:
            ExtractionResult with extracted business logic
        """
        rules = []
        entities = []
        data_flows = []
        decision_trees = []
        
        if language == "python":
            rules.extend(self._extract_python_rules(code, filename))
            entities.extend(self._extract_python_entities(code, filename))
            decision_trees.extend(self._extract_python_decisions(code, filename))
        elif language in ["javascript", "typescript"]:
            rules.extend(self._extract_js_rules(code, filename))
            entities.extend(self._extract_js_entities(code, filename))
        
        # Language-agnostic extraction
        data_flows.extend(self._extract_data_flows(code, filename))
        
        # Generate summary
        summary = self._generate_summary(rules, entities, data_flows)
        
        # Calculate confidence
        confidence = self._calculate_confidence(rules, entities)
        
        return ExtractionResult(
            rules=rules,
            entities=entities,
            data_flows=data_flows,
            decision_trees=decision_trees,
            summary=summary,
            confidence=confidence,
        )
    
    def extract_from_project(self, project_path: Path) -> Dict[str, ExtractionResult]:
        """Extract business logic from an entire project."""
        results = {}
        
        for file_path in project_path.rglob("*"):
            if file_path.is_file() and self._is_source_file(file_path):
                try:
                    result = self.extract_from_file(file_path)
                    if result.rules or result.entities:
                        results[str(file_path)] = result
                except Exception as e:
                    print(f"Failed to extract from {file_path}: {e}")
        
        return results
    
    def _extract_python_rules(self, code: str, filename: str) -> List[BusinessRule]:
        """Extract business rules from Python code."""
        rules = []
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                # Extract validation rules
                if isinstance(node, ast.FunctionDef):
                    rule = self._extract_rule_from_function(node, filename)
                    if rule:
                        rules.append(rule)
                
                # Extract rules from if statements
                elif isinstance(node, ast.If):
                    rule = self._extract_rule_from_if(node, filename)
                    if rule:
                        rules.append(rule)
                
                # Extract rules from assert statements
                elif isinstance(node, ast.Assert):
                    rule = self._extract_rule_from_assert(node, filename)
                    if rule:
                        rules.append(rule)
        
        except SyntaxError:
            pass
        
        return rules
    
    def _extract_rule_from_function(
        self, 
        func: ast.FunctionDef, 
        filename: str
    ) -> Optional[BusinessRule]:
        """Extract a business rule from a function."""
        func_name = func.name.lower()
        
        # Determine rule type from function name
        rule_type = None
        for type_name, keywords in self.BUSINESS_KEYWORDS.items():
            if any(kw in func_name for kw in keywords):
                rule_type = RuleType(type_name)
                break
        
        if not rule_type:
            return None
        
        # Extract conditions from function body
        conditions = []
        actions = []
        
        for stmt in func.body:
            if isinstance(stmt, ast.If):
                condition_str = self._ast_to_string(stmt.test)
                conditions.append(condition_str)
                
                # Extract action from if body
                if stmt.body:
                    action = self._ast_to_string(stmt.body[0])
                    actions.append(action)
            elif isinstance(stmt, ast.Assert):
                conditions.append(self._ast_to_string(stmt.test))
            elif isinstance(stmt, ast.Return):
                actions.append(f"returns {self._ast_to_string(stmt.value)}")
        
        if not conditions and not actions:
            return None
        
        return BusinessRule(
            name=func.name,
            rule_type=rule_type,
            description=self._generate_rule_description(func.name, conditions, actions),
            conditions=conditions,
            actions=actions,
            source_file=filename,
            line_start=func.lineno,
            line_end=func.end_lineno or func.lineno,
            confidence=0.8,
        )
    
    def _extract_rule_from_if(
        self, 
        node: ast.If, 
        filename: str
    ) -> Optional[BusinessRule]:
        """Extract a business rule from an if statement."""
        condition = self._ast_to_string(node.test)
        
        # Check if this looks like a business rule
        is_business_rule = self._looks_like_business_rule(condition)
        
        if not is_business_rule:
            return None
        
        # Extract actions
        actions = []
        for stmt in node.body:
            action_str = self._ast_to_string(stmt)
            actions.append(action_str)
        
        return BusinessRule(
            name=f"rule_at_line_{node.lineno}",
            rule_type=RuleType.CONSTRAINT,
            description=f"If {condition}, then execute actions",
            conditions=[condition],
            actions=actions,
            source_file=filename,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            confidence=0.6,
        )
    
    def _extract_rule_from_assert(
        self, 
        node: ast.Assert, 
        filename: str
    ) -> Optional[BusinessRule]:
        """Extract a business rule from an assert statement."""
        condition = self._ast_to_string(node.test)
        
        return BusinessRule(
            name=f"assertion_at_line_{node.lineno}",
            rule_type=RuleType.VALIDATION,
            description=f"Must satisfy: {condition}",
            conditions=[condition],
            actions=[],
            source_file=filename,
            line_start=node.lineno,
            line_end=node.lineno,
            confidence=0.9,
        )
    
    def _extract_python_entities(self, code: str, filename: str) -> List[DomainEntity]:
        """Extract domain entities from Python code."""
        entities = []
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    entity = self._extract_entity_from_class(node, filename)
                    if entity:
                        entities.append(entity)
        
        except SyntaxError:
            pass
        
        return entities
    
    def _extract_entity_from_class(
        self, 
        cls: ast.ClassDef, 
        filename: str
    ) -> Optional[DomainEntity]:
        """Extract a domain entity from a class."""
        attributes = []
        relationships = []
        business_rules = []
        
        for item in cls.body:
            if isinstance(item, ast.AnnAssign):  # Typed attribute
                attr_name = item.target.id if isinstance(item.target, ast.Name) else str(item.target)
                attr_type = self._ast_to_string(item.annotation) if item.annotation else "Any"
                attributes.append({
                    "name": attr_name,
                    "type": attr_type,
                })
            elif isinstance(item, ast.FunctionDef):
                # Check if method implements a business rule
                rule = self._extract_rule_from_function(item, filename)
                if rule:
                    business_rules.append(rule.description)
        
        # Skip utility classes without attributes
        if not attributes and len(business_rules) < 2:
            return None
        
        return DomainEntity(
            name=cls.name,
            attributes=attributes,
            relationships=relationships,
            business_rules=business_rules,
            source_file=filename,
            line_number=cls.lineno,
        )
    
    def _extract_python_decisions(self, code: str, filename: str) -> List[DecisionNode]:
        """Extract decision trees from Python code."""
        decisions = []
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.If):
                    decision = self._build_decision_tree(node)
                    if decision:
                        decisions.append(decision)
        
        except SyntaxError:
            pass
        
        return decisions
    
    def _build_decision_tree(self, node: ast.If) -> Optional[DecisionNode]:
        """Build a decision tree from an if statement."""
        condition = self._ast_to_string(node.test)
        
        # Build true branch
        true_branch = None
        if len(node.body) == 1 and isinstance(node.body[0], ast.If):
            true_branch = self._build_decision_tree(node.body[0])
        elif node.body:
            action = self._ast_to_string(node.body[0])
            true_branch = DecisionNode(
                condition="",
                true_branch=None,
                false_branch=None,
                action=action,
            )
        
        # Build false branch (elif/else)
        false_branch = None
        if node.orelse:
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                false_branch = self._build_decision_tree(node.orelse[0])
            else:
                action = self._ast_to_string(node.orelse[0])
                false_branch = DecisionNode(
                    condition="",
                    true_branch=None,
                    false_branch=None,
                    action=action,
                )
        
        return DecisionNode(
            condition=condition,
            true_branch=true_branch,
            false_branch=false_branch,
            action=None,
        )
    
    def _extract_js_rules(self, code: str, filename: str) -> List[BusinessRule]:
        """Extract business rules from JavaScript code."""
        rules = []
        
        # Pattern-based extraction for JS
        # Function declarations
        func_pattern = r'(?:async\s+)?function\s+(\w+)\s*\([^)]*\)\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}'
        
        for match in re.finditer(func_pattern, code, re.DOTALL):
            func_name = match.group(1)
            func_body = match.group(2)
            
            rule_type = self._determine_rule_type(func_name)
            if rule_type:
                conditions = self._extract_conditions_from_js(func_body)
                actions = self._extract_actions_from_js(func_body)
                
                rules.append(BusinessRule(
                    name=func_name,
                    rule_type=rule_type,
                    description=self._generate_rule_description(func_name, conditions, actions),
                    conditions=conditions,
                    actions=actions,
                    source_file=filename,
                    line_start=code[:match.start()].count('\n') + 1,
                    line_end=code[:match.end()].count('\n') + 1,
                    confidence=0.7,
                ))
        
        return rules
    
    def _extract_js_entities(self, code: str, filename: str) -> List[DomainEntity]:
        """Extract domain entities from JavaScript code."""
        entities = []
        
        # Class declarations
        class_pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?\s*\{([^}]*)\}'
        
        for match in re.finditer(class_pattern, code, re.DOTALL):
            class_name = match.group(1)
            class_body = match.group(3)
            
            # Extract properties
            attributes = []
            prop_pattern = r'this\.(\w+)\s*=\s*([^;]+);'
            for prop_match in re.finditer(prop_pattern, class_body):
                attributes.append({
                    "name": prop_match.group(1),
                    "type": "inferred",
                })
            
            entities.append(DomainEntity(
                name=class_name,
                attributes=attributes,
                relationships=[],
                business_rules=[],
                source_file=filename,
                line_number=code[:match.start()].count('\n') + 1,
            ))
        
        return entities
    
    def _extract_data_flows(self, code: str, filename: str) -> List[DataFlow]:
        """Extract data flows from code."""
        flows = []
        
        # Look for API calls, database operations, etc.
        patterns = [
            (r'(?:fetch|axios|request)\s*\(\s*["\']([^"\']+)["\']', "HTTP API"),
            (r'\.save\s*\(|\.create\s*\(|\.update\s*\(', "Database"),
            (r'\.send\s*\(|emit\s*\(', "Message"),
            (r'read_file|write_file|open\s*\(', "File"),
        ]
        
        for pattern, flow_type in patterns:
            for match in re.finditer(pattern, code, re.IGNORECASE):
                line_num = code[:match.start()].count('\n') + 1
                flows.append(DataFlow(
                    source=filename,
                    target=match.group(1) if match.groups() else flow_type,
                    data_type=flow_type,
                    transformation=None,
                    conditions=[],
                    source_file=filename,
                ))
        
        return flows
    
    def _looks_like_business_rule(self, condition: str) -> bool:
        """Check if a condition looks like a business rule."""
        business_indicators = [
            "amount", "price", "total", "limit", "max", "min",
            "status", "role", "permission", "valid", "required",
            "age", "date", "expired", "approved", "active",
        ]
        return any(indicator in condition.lower() for indicator in business_indicators)
    
    def _determine_rule_type(self, name: str) -> Optional[RuleType]:
        """Determine rule type from name."""
        name_lower = name.lower()
        for type_name, keywords in self.BUSINESS_KEYWORDS.items():
            if any(kw in name_lower for kw in keywords):
                return RuleType(type_name)
        return None
    
    def _extract_conditions_from_js(self, code: str) -> List[str]:
        """Extract conditions from JavaScript code."""
        conditions = []
        
        # Find if statements
        if_pattern = r'if\s*\(([^)]+)\)'
        for match in re.finditer(if_pattern, code):
            conditions.append(match.group(1).strip())
        
        return conditions
    
    def _extract_actions_from_js(self, code: str) -> List[str]:
        """Extract actions from JavaScript code."""
        actions = []
        
        # Find return statements
        return_pattern = r'return\s+([^;]+);'
        for match in re.finditer(return_pattern, code):
            actions.append(f"returns {match.group(1).strip()}")
        
        return actions
    
    def _generate_rule_description(
        self, 
        name: str, 
        conditions: List[str], 
        actions: List[str]
    ) -> str:
        """Generate a human-readable rule description."""
        parts = [f"Rule '{name}':"]
        
        if conditions:
            parts.append(f"When {' AND '.join(conditions)},")
        
        if actions:
            parts.append(f"then {'; '.join(actions)}")
        
        return " ".join(parts)
    
    def _ast_to_string(self, node: ast.AST) -> str:
        """Convert an AST node to a string representation."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Compare):
            left = self._ast_to_string(node.left)
            ops = []
            for op in node.ops:
                if isinstance(op, ast.Eq):
                    ops.append("==")
                elif isinstance(op, ast.NotEq):
                    ops.append("!=")
                elif isinstance(op, ast.Lt):
                    ops.append("<")
                elif isinstance(op, ast.LtE):
                    ops.append("<=")
                elif isinstance(op, ast.Gt):
                    ops.append(">")
                elif isinstance(op, ast.GtE):
                    ops.append(">=")
                elif isinstance(op, ast.In):
                    ops.append("in")
                elif isinstance(op, ast.Is):
                    ops.append("is")
            comparators = [self._ast_to_string(c) for c in node.comparators]
            return f"{left} {' '.join(ops)} {' '.join(comparators)}"
        elif isinstance(node, ast.BoolOp):
            op_str = " and " if isinstance(node.op, ast.And) else " or "
            values = [self._ast_to_string(v) for v in node.values]
            return op_str.join(values)
        elif isinstance(node, ast.Call):
            func = self._ast_to_string(node.func)
            args = [self._ast_to_string(a) for a in node.args]
            return f"{func}({', '.join(args)})"
        elif isinstance(node, ast.Attribute):
            value = self._ast_to_string(node.value)
            return f"{value}.{node.attr}"
        elif isinstance(node, ast.BinOp):
            left = self._ast_to_string(node.left)
            right = self._ast_to_string(node.right)
            op_map = {
                ast.Add: "+",
                ast.Sub: "-",
                ast.Mult: "*",
                ast.Div: "/",
                ast.Mod: "%",
            }
            op = op_map.get(type(node.op), "?")
            return f"{left} {op} {right}"
        elif isinstance(node, ast.UnaryOp):
            operand = self._ast_to_string(node.operand)
            if isinstance(node.op, ast.Not):
                return f"not {operand}"
            elif isinstance(node.op, ast.USub):
                return f"-{operand}"
        elif isinstance(node, list):
            return "; ".join(self._ast_to_string(item) for item in node)
        elif node is None:
            return "None"
        else:
            return str(node)
    
    def _detect_language(self, extension: str) -> str:
        """Detect language from file extension."""
        mapping = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
        }
        return mapping.get(extension, "python")
    
    def _is_source_file(self, path: Path) -> bool:
        """Check if file is a source code file."""
        return path.suffix in ['.py', '.js', '.jsx', '.ts', '.tsx']
    
    def _generate_summary(
        self, 
        rules: List[BusinessRule], 
        entities: List[DomainEntity],
        flows: List[DataFlow]
    ) -> str:
        """Generate a summary of extracted business logic."""
        lines = [
            f"Extracted {len(rules)} business rules from {len(set(r.source_file for r in rules))} files.",
            f"Identified {len(entities)} domain entities.",
            f"Found {len(flows)} data flows.",
        ]
        
        # Group rules by type
        by_type = {}
        for rule in rules:
            rule_type = rule.rule_type.value
            by_type[rule_type] = by_type.get(rule_type, 0) + 1
        
        if by_type:
            lines.append("\nRules by type:")
            for rule_type, count in sorted(by_type.items()):
                lines.append(f"  - {rule_type}: {count}")
        
        # List entities
        if entities:
            lines.append("\nDomain entities:")
            for entity in entities[:10]:  # Limit to first 10
                lines.append(f"  - {entity.name} ({len(entity.attributes)} attributes)")
        
        return "\n".join(lines)
    
    def _calculate_confidence(
        self, 
        rules: List[BusinessRule], 
        entities: List[DomainEntity]
    ) -> float:
        """Calculate overall extraction confidence."""
        if not rules and not entities:
            return 0.0
        
        all_confidences = [r.confidence for r in rules]
        return sum(all_confidences) / len(all_confidences) if all_confidences else 0.5
    
    def generate_documentation(self, result: ExtractionResult) -> str:
        """Generate structured documentation from extraction result."""
        lines = [
            "# Business Logic Documentation",
            "",
            "## Overview",
            "",
            result.summary,
            "",
            f"_Extraction confidence: {result.confidence:.0%}_",
            "",
        ]
        
        # Business Rules
        if result.rules:
            lines.extend(["## Business Rules", ""])
            
            for rule_type in RuleType:
                type_rules = [r for r in result.rules if r.rule_type == rule_type]
                if type_rules:
                    lines.extend([f"### {rule_type.value.replace('_', ' ').title()}", ""])
                    for rule in type_rules:
                        lines.extend([
                            f"#### {rule.name}",
                            "",
                            rule.description,
                            "",
                        ])
                        if rule.conditions:
                            lines.extend(["**Conditions:**", ""])
                            for cond in rule.conditions:
                                lines.append(f"- {cond}")
                            lines.append("")
                        if rule.actions:
                            lines.extend(["**Actions:**", ""])
                            for action in rule.actions:
                                lines.append(f"- {action}")
                            lines.append("")
                        lines.append(f"*Source: {rule.source_file}:{rule.line_start}*")
                        lines.append("")
        
        # Domain Entities
        if result.entities:
            lines.extend(["## Domain Model", ""])
            
            for entity in result.entities:
                lines.extend([
                    f"### {entity.name}",
                    "",
                ])
                
                if entity.attributes:
                    lines.extend(["**Attributes:**", ""])
                    for attr in entity.attributes:
                        lines.append(f"- `{attr['name']}`: {attr['type']}")
                    lines.append("")
                
                if entity.relationships:
                    lines.extend(["**Relationships:**", ""])
                    for rel in entity.relationships:
                        lines.append(f"- {rel}")
                    lines.append("")
                
                if entity.business_rules:
                    lines.extend(["**Business Rules:**", ""])
                    for rule in entity.business_rules[:5]:
                        lines.append(f"- {rule}")
                    lines.append("")
        
        # Data Flows
        if result.data_flows:
            lines.extend(["## Data Flows", ""])
            
            for flow in result.data_flows[:20]:  # Limit
                lines.append(f"- {flow.source} → {flow.target} ({flow.data_type})")
            lines.append("")
        
        return '\n'.join(lines)
