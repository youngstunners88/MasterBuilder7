"""
Business Documenter: Generates human-readable documentation from extracted rules.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .extractor import ExtractionResult, BusinessRule, DomainEntity, DataFlow, DecisionNode
from .rule_parser import ParsedRule, RuleParser


@dataclass
class DocumentationConfig:
    """Configuration for documentation generation."""
    format: str = "markdown"  # markdown, html, pdf, docx
    include_code_references: bool = True
    include_diagrams: bool = True
    include_decision_tables: bool = True
    style: str = "professional"  # professional, technical, simple
    company_name: Optional[str] = None
    project_name: Optional[str] = None
    version: str = "1.0"


class BusinessDocumenter:
    """
    Generates various types of business documentation.
    """
    
    def __init__(self, config: Optional[DocumentationConfig] = None):
        self.config = config or DocumentationConfig()
        self.rule_parser = RuleParser()
    
    def generate(
        self, 
        result: ExtractionResult,
        output_path: Optional[Path] = None
    ) -> str:
        """
        Generate documentation from extraction result.
        
        Args:
            result: Extraction result
            output_path: Optional path to save documentation
            
        Returns:
            Generated documentation as string
        """
        if self.config.format == "markdown":
            doc = self._generate_markdown(result)
        elif self.config.format == "html":
            doc = self._generate_html(result)
        else:
            doc = self._generate_markdown(result)
        
        if output_path:
            output_path.write_text(doc)
        
        return doc
    
    def _generate_markdown(self, result: ExtractionResult) -> str:
        """Generate Markdown documentation."""
        lines = []
        
        # Header
        lines.extend(self._generate_header())
        
        # Executive Summary
        lines.extend(self._generate_executive_summary(result))
        
        # Business Rules
        if result.rules:
            lines.extend(self._generate_rules_section(result.rules))
        
        # Domain Model
        if result.entities:
            lines.extend(self._generate_domain_section(result.entities))
        
        # Data Flows
        if result.data_flows:
            lines.extend(self._generate_data_flow_section(result.data_flows))
        
        # Decision Trees
        if result.decision_trees:
            lines.extend(self._generate_decision_trees_section(result.decision_trees))
        
        # Decision Tables
        if self.config.include_decision_tables and result.rules:
            lines.extend(self._generate_decision_tables(result.rules))
        
        # Appendix
        lines.extend(self._generate_appendix(result))
        
        return '\n'.join(lines)
    
    def _generate_header(self) -> List[str]:
        """Generate document header."""
        lines = []
        
        project = self.config.project_name or "Project"
        company = self.config.company_name
        
        lines.append(f"# {project} - Business Logic Documentation")
        lines.append("")
        
        if company:
            lines.append(f"**{company}**")
            lines.append("")
        
        lines.append(f"Version: {self.config.version}")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"Extraction Confidence: {result.confidence:.0%}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        return lines
    
    def _generate_executive_summary(self, result: ExtractionResult) -> List[str]:
        """Generate executive summary."""
        lines = [
            "## Executive Summary",
            "",
            "This document describes the business logic extracted from the codebase.",
            "",
            "### Overview",
            "",
            f"- **Business Rules:** {len(result.rules)}",
            f"- **Domain Entities:** {len(result.entities)}",
            f"- **Data Flows:** {len(result.data_flows)}",
            f"- **Decision Points:** {len(result.decision_trees)}",
            "",
        ]
        
        # Group rules by type
        from .extractor import RuleType
        by_type = {}
        for rule in result.rules:
            rule_type = rule.rule_type.value
            by_type[rule_type] = by_type.get(rule_type, 0) + 1
        
        if by_type:
            lines.extend(["### Rules by Category", ""])
            for rule_type, count in sorted(by_type.items()):
                lines.append(f"- **{rule_type.replace('_', ' ').title()}:** {count}")
            lines.append("")
        
        return lines
    
    def _generate_rules_section(self, rules: List[BusinessRule]) -> List[str]:
        """Generate business rules section."""
        lines = [
            "## Business Rules",
            "",
            "This section documents all business rules extracted from the code.",
            "",
        ]
        
        # Group by type
        from .extractor import RuleType
        for rule_type in RuleType:
            type_rules = [r for r in rules if r.rule_type == rule_type]
            if type_rules:
                lines.extend([
                    f"### {rule_type.value.replace('_', ' ').title()} Rules",
                    "",
                ])
                
                for i, rule in enumerate(type_rules, 1):
                    lines.extend([
                        f"#### {i}. {rule.name}",
                        "",
                        rule.description,
                        "",
                    ])
                    
                    if rule.conditions:
                        lines.append("**Conditions:**")
                        for cond in rule.conditions:
                            lines.append(f"- {cond}")
                        lines.append("")
                    
                    if rule.actions:
                        lines.append("**Actions:**")
                        for action in rule.actions:
                            lines.append(f"- {action}")
                        lines.append("")
                    
                    if self.config.include_code_references:
                        lines.append(f"*Source: `{rule.source_file}:{rule.line_start}`*")
                        lines.append("")
                    
                    lines.append("---")
                    lines.append("")
        
        return lines
    
    def _generate_domain_section(self, entities: List[DomainEntity]) -> List[str]:
        """Generate domain model section."""
        lines = [
            "## Domain Model",
            "",
            "This section describes the key domain entities and their relationships.",
            "",
        ]
        
        for entity in entities:
            lines.extend([
                f"### {entity.name}",
                "",
            ])
            
            if entity.attributes:
                lines.extend([
                    "**Attributes:**",
                    "",
                    "| Name | Type |",
                    "|------|------|",
                ])
                for attr in entity.attributes:
                    attr_type = attr.get('type', 'unknown')
                    lines.append(f"| `{attr['name']}` | {attr_type} |")
                lines.append("")
            
            if entity.relationships:
                lines.extend([
                    "**Relationships:**",
                    "",
                ])
                for rel in entity.relationships:
                    lines.append(f"- {rel}")
                lines.append("")
            
            if entity.business_rules:
                lines.extend([
                    "**Associated Rules:**",
                    "",
                ])
                for rule in entity.business_rules[:5]:
                    lines.append(f"- {rule}")
                if len(entity.business_rules) > 5:
                    lines.append(f"- *... and {len(entity.business_rules) - 5} more*")
                lines.append("")
            
            if self.config.include_code_references:
                lines.append(f"*Source: `{entity.source_file}:{entity.line_number}`*")
                lines.append("")
            
            lines.append("---")
            lines.append("")
        
        return lines
    
    def _generate_data_flow_section(self, flows: List[DataFlow]) -> List[str]:
        """Generate data flow section."""
        lines = [
            "## Data Flows",
            "",
            "This section documents how data flows through the system.",
            "",
        ]
        
        if self.config.include_diagrams:
            lines.extend([
                "### Flow Diagram",
                "",
                "```mermaid",
                "graph LR",
            ])
            
            seen = set()
            for flow in flows[:30]:  # Limit to avoid huge diagrams
                source = flow.source.split('/')[-1].replace('.', '_')
                target = flow.target.replace('.', '_').replace('/', '_')
                edge_id = f"{source}_{target}"
                
                if edge_id not in seen:
                    lines.append(f"    {source}[{flow.source.split('/')[-1]}] -->|{flow.data_type}| {target}[{flow.target}]")
                    seen.add(edge_id)
            
            lines.extend([
                "```",
                "",
            ])
        
        lines.extend([
            "### Flow Details",
            "",
            "| Source | Target | Data Type |",
            "|--------|--------|-----------|",
        ])
        
        for flow in flows:
            source = flow.source.split('/')[-1]
            target = flow.target if len(flow.target) < 40 else flow.target[:37] + "..."
            lines.append(f"| {source} | {target} | {flow.data_type} |")
        
        lines.append("")
        
        return lines
    
    def _generate_decision_trees_section(self, trees: List[DecisionNode]) -> List[str]:
        """Generate decision trees section."""
        lines = [
            "## Decision Trees",
            "",
            "This section visualizes complex decision logic.",
            "",
        ]
        
        for i, tree in enumerate(trees, 1):
            lines.extend([
                f"### Decision Tree {i}",
                "",
                "```",
            ])
            lines.extend(self._format_decision_tree(tree))
            lines.extend([
                "```",
                "",
            ])
        
        return lines
    
    def _format_decision_tree(
        self, 
        node: DecisionNode, 
        indent: int = 0,
        prefix: str = ""
    ) -> List[str]:
        """Format a decision tree as text."""
        lines = []
        spacing = "  " * indent
        
        if node.condition:
            lines.append(f"{spacing}{prefix}IF: {node.condition}")
        
        if node.true_branch:
            if isinstance(node.true_branch, DecisionNode):
                lines.extend(self._format_decision_tree(node.true_branch, indent + 1, "THEN "))
            else:
                lines.append(f"{spacing}  THEN: {node.true_branch}")
        
        if node.false_branch:
            if isinstance(node.false_branch, DecisionNode):
                lines.extend(self._format_decision_tree(node.false_branch, indent + 1, "ELSE "))
            else:
                lines.append(f"{spacing}  ELSE: {node.false_branch}")
        
        if node.action:
            lines.append(f"{spacing}  ACTION: {node.action}")
        
        return lines
    
    def _generate_decision_tables(self, rules: List[BusinessRule]) -> List[str]:
        """Generate decision tables from rules."""
        lines = [
            "## Decision Tables",
            "",
            "This section provides tabular views of decision logic.",
            "",
        ]
        
        # Parse rules and create tables
        parsed_rules = []
        for rule in rules:
            parsed = self._parse_business_rule(rule)
            if parsed:
                parsed_rules.append(parsed)
        
        if parsed_rules:
            table = self.rule_parser.to_decision_table(parsed_rules)
            
            lines.extend([
                "### Summary Table",
                "",
            ])
            
            # Header
            conditions = table["conditions"]
            header = ["Rule"] + conditions + ["Actions", "Priority"]
            lines.append("| " + " | ".join(header) + " |")
            lines.append("|" + "|".join(["---"] * len(header)) + "|")
            
            # Rows
            for rule_row in table["rules"]:
                row = [rule_row["rule_name"]]
                for cond in conditions:
                    if cond in rule_row["conditions"]:
                        cond_info = rule_row["conditions"][cond]
                        cell = f"{cond_info['operator']} {cond_info['value']}"
                    else:
                        cell = "-"
                    row.append(cell)
                
                actions = "; ".join(rule_row["actions"][:2])
                if len(rule_row["actions"]) > 2:
                    actions += "..."
                row.append(actions)
                row.append(rule_row["priority"])
                
                lines.append("| " + " | ".join(row) + " |")
            
            lines.append("")
        
        return lines
    
    def _parse_business_rule(self, rule: BusinessRule) -> Optional[ParsedRule]:
        """Convert BusinessRule to ParsedRule."""
        conditions = []
        for cond_text in rule.conditions:
            cond = self.rule_parser.parse_from_condition(cond_text)
            if cond:
                conditions.append(cond)
        
        return ParsedRule(
            name=rule.name,
            description=rule.description,
            conditions=conditions,
            actions=rule.actions,
            priority=self._map_confidence_to_priority(rule.confidence),
        )
    
    def _map_confidence_to_priority(self, confidence: float) -> Any:
        """Map confidence score to priority."""
        from .rule_parser import RulePriority
        if confidence >= 0.9:
            return RulePriority.HIGH
        elif confidence >= 0.7:
            return RulePriority.MEDIUM
        else:
            return RulePriority.LOW
    
    def _generate_appendix(self, result: ExtractionResult) -> List[str]:
        """Generate appendix."""
        lines = [
            "## Appendix",
            "",
            "### Files Analyzed",
            "",
        ]
        
        files = set()
        for rule in result.rules:
            files.add(rule.source_file)
        for entity in result.entities:
            files.add(entity.source_file)
        
        for f in sorted(files):
            lines.append(f"- `{f}`")
        
        lines.extend([
            "",
            "### Methodology",
            "",
            "This documentation was automatically generated by analyzing",
            "the codebase to extract:",
            "",
            "1. **Business Rules** - Logic that enforces business constraints",
            "2. **Domain Entities** - Core business objects and their attributes",
            "3. **Data Flows** - How information moves through the system",
            "4. **Decision Points** - Conditional logic and branching",
            "",
            "The extraction process uses static code analysis to identify",
            "patterns and structures that represent business logic.",
            "",
            "### Confidence Levels",
            "",
            "- **High (80%+)**: Strong confidence in extraction accuracy",
            "- **Medium (60-80%)**: Moderate confidence, may need review",
            "- **Low (<60%)**: Low confidence, requires manual verification",
            "",
        ])
        
        return lines
    
    def _generate_html(self, result: ExtractionResult) -> str:
        """Generate HTML documentation."""
        # Convert markdown to HTML (simplified)
        markdown = self._generate_markdown(result)
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Business Logic Documentation</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        h1, h2, h3, h4 {{
            color: #2c3e50;
            margin-top: 30px;
        }}
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Consolas', monospace;
        }}
        pre {{
            background: #f4f4f4;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background: #2c3e50;
            color: white;
        }}
        tr:nth-child(even) {{
            background: #f9f9f9;
        }}
        hr {{
            border: none;
            border-top: 1px solid #eee;
            margin: 30px 0;
        }}
    </style>
</head>
<body>
    <pre>{markdown}</pre>
</body>
</html>"""
        
        return html
    
    def export_to_format(
        self, 
        result: ExtractionResult, 
        format_type: str,
        output_path: Path
    ) -> Path:
        """
        Export documentation to various formats.
        
        Args:
            result: Extraction result
            format_type: Output format (markdown, html, json, yaml)
            output_path: Output file path
            
        Returns:
            Path to generated file
        """
        if format_type == "markdown":
            content = self._generate_markdown(result)
        elif format_type == "html":
            content = self._generate_html(result)
        elif format_type == "json":
            import json
            content = json.dumps(self._result_to_dict(result), indent=2)
        elif format_type == "yaml":
            import yaml
            content = yaml.dump(self._result_to_dict(result))
        else:
            content = self._generate_markdown(result)
        
        output_path.write_text(content)
        return output_path
    
    def _result_to_dict(self, result: ExtractionResult) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "confidence": result.confidence,
            "summary": result.summary,
            "rules": [
                {
                    "name": r.name,
                    "type": r.rule_type.value,
                    "description": r.description,
                    "conditions": r.conditions,
                    "actions": r.actions,
                    "source_file": r.source_file,
                    "confidence": r.confidence,
                }
                for r in result.rules
            ],
            "entities": [
                {
                    "name": e.name,
                    "attributes": e.attributes,
                    "business_rules": e.business_rules,
                }
                for e in result.entities
            ],
        }
