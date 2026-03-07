"""Mermaid diagram generator."""

from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from pathlib import Path
import re

from .parser import ParsedFile, ClassDefinition, FunctionDefinition, RelationshipType


@dataclass
class DiagramConfig:
    """Configuration for Mermaid diagram generation."""
    direction: str = "TD"  # TD, LR, RL, BT
    theme: str = "default"  # default, dark, forest, neutral
    show_private: bool = False
    show_methods: bool = True
    show_attributes: bool = True
    max_classes: int = 50
    max_methods_per_class: int = 10


class MermaidGenerator:
    """Generates Mermaid diagrams from parsed code."""
    
    def __init__(self, config: Optional[DiagramConfig] = None):
        self.config = config or DiagramConfig()
    
    def generate_class_diagram(self, parsed_files: List[ParsedFile],
                               title: Optional[str] = None) -> str:
        """Generate a Mermaid class diagram."""
        lines = ["classDiagram"]
        
        if title:
            lines.insert(0, f"---\ntitle: {title}\n---")
        
        # Collect all classes
        all_classes: Dict[str, ClassDefinition] = {}
        for pf in parsed_files:
            for cls in pf.classes:
                all_classes[cls.name] = cls
        
        # Limit classes if needed
        if len(all_classes) > self.config.max_classes:
            # Keep most referenced classes
            referenced = self._get_most_referenced(parsed_files, self.config.max_classes)
            all_classes = {k: v for k, v in all_classes.items() if k in referenced}
        
        # Generate class definitions
        for name, cls in all_classes.items():
            lines.extend(self._generate_class_def(cls))
        
        # Generate relationships
        relationships = self._extract_relationships(parsed_files, all_classes)
        for rel in relationships:
            lines.append(self._format_relationship(rel))
        
        return '\n'.join(lines)
    
    def generate_sequence_diagram(self, parsed_files: List[ParsedFile],
                                  entry_point: str,
                                  max_depth: int = 5,
                                  title: Optional[str] = None) -> str:
        """Generate a Mermaid sequence diagram from code flow."""
        lines = ["sequenceDiagram"]
        
        if title:
            lines.insert(0, f"---\ntitle: {title}\n---")
        
        # Find participants (classes/modules involved)
        participants = self._find_participants(parsed_files, entry_point)
        
        for p in participants:
            lines.append(f"    participant {self._sanitize_id(p)}")
        
        # Generate sequence from function calls
        sequences = self._extract_call_sequence(parsed_files, entry_point, max_depth)
        for seq in sequences:
            lines.append(f"    {seq}")
        
        return '\n'.join(lines)
    
    def generate_component_diagram(self, parsed_files: List[ParsedFile],
                                   title: Optional[str] = None) -> str:
        """Generate a Mermaid component diagram."""
        lines = ["graph TB"]
        
        if title:
            lines.insert(0, f"---\ntitle: {title}\n---")
        
        # Group by module/package
        modules: Dict[str, List[ParsedFile]] = {}
        for pf in parsed_files:
            module_name = self._get_module_name(pf.path)
            if module_name not in modules:
                modules[module_name] = []
            modules[module_name].append(pf)
        
        # Generate subgraphs for each module
        for module, files in modules.items():
            lines.append(f"    subgraph {self._sanitize_id(module)}")
            
            for pf in files:
                node_id = self._sanitize_id(Path(pf.path).stem)
                lines.append(f"        {node_id}[{Path(pf.path).name}]")
            
            lines.append("    end")
        
        # Generate dependencies between modules
        dependencies = self._extract_module_dependencies(parsed_files)
        for source, target in dependencies:
            lines.append(f"    {self._sanitize_id(source)} --> {self._sanitize_id(target)}")
        
        return '\n'.join(lines)
    
    def generate_er_diagram(self, parsed_files: List[ParsedFile],
                           entities: Optional[List[str]] = None,
                           title: Optional[str] = None) -> str:
        """Generate a Mermaid ER diagram from data classes/models."""
        lines = ["erDiagram"]
        
        if title:
            lines.insert(0, f"---\ntitle: {title}\n---")
        
        # Find data classes/entities
        entities_data = self._extract_entities(parsed_files, entities)
        
        for entity_name, attributes, relationships in entities_data:
            lines.append(f"    {self._sanitize_id(entity_name)} {{")
            
            for attr in attributes:
                attr_type = attr.type_annotation or "string"
                attr_name = attr.name
                lines.append(f"        {self._map_type(attr_type)} {attr_name}")
            
            lines.append("    }")
            
            # Add relationships
            for rel_target, rel_type in relationships:
                cardinality = self._map_relationship_type(rel_type)
                lines.append(f"    {self._sanitize_id(entity_name)} {cardinality} {self._sanitize_id(rel_target)} : has")
        
        return '\n'.join(lines)
    
    def generate_state_diagram(self, state_machine_class: ClassDefinition,
                               title: Optional[str] = None) -> str:
        """Generate a Mermaid state diagram from a state machine class."""
        lines = ["stateDiagram-v2"]
        
        if title:
            lines.insert(0, f"---\ntitle: {title}\n---")
        
        # Extract states and transitions from methods
        states = set()
        transitions = []
        
        for method in state_machine_class.methods:
            # Look for state transition patterns
            state_info = self._extract_state_info(method)
            if state_info:
                from_state, to_state, event = state_info
                states.add(from_state)
                states.add(to_state)
                transitions.append((from_state, to_state, event))
        
        # Generate state diagram
        for state in states:
            lines.append(f"    {self._sanitize_id(state)}")
        
        for from_state, to_state, event in transitions:
            lines.append(f"    {self._sanitize_id(from_state)} --> {self._sanitize_id(to_state)} : {event}")
        
        return '\n'.join(lines)
    
    def generate_flowchart(self, function: FunctionDefinition,
                          title: Optional[str] = None) -> str:
        """Generate a Mermaid flowchart from a function."""
        lines = ["flowchart TD"]
        
        if title:
            lines.insert(0, f"---\ntitle: {title}\n---")
        
        # Simple flowchart: Start -> Function -> Return
        func_id = self._sanitize_id(function.name)
        
        lines.append(f"    Start([Start]) --> {func_id}[{function.name}]")
        
        # Add parameter nodes
        prev_node = func_id
        for i, param in enumerate(function.parameters[:5]):  # Limit params
            param_id = f"{func_id}_param_{i}"
            lines.append(f"    {prev_node} --> {param_id}[{param.name}]")
            prev_node = param_id
        
        lines.append(f"    {prev_node} --> End([End])")
        
        return '\n'.join(lines)
    
    def _generate_class_def(self, cls: ClassDefinition) -> List[str]:
        """Generate Mermaid class definition."""
        lines = []
        class_id = self._sanitize_id(cls.name)
        
        # Start class definition
        lines.append(f"class {class_id} {")
        
        # Add attributes
        if self.config.show_attributes:
            for attr in cls.attributes:
                if not attr.name.startswith('_') or self.config.show_private:
                    type_str = f"{attr.type_annotation} " if attr.type_annotation else ""
                    lines.append(f"    {type_str}{attr.name}")
        
        # Add methods
        if self.config.show_methods:
            for method in cls.methods[:self.config.max_methods_per_class]:
                if not method.name.startswith('_') or self.config.show_private:
                    visibility = self._get_visibility(method)
                    params = ", ".join(p.name for p in method.parameters[:4])
                    if len(method.parameters) > 4:
                        params += "..."
                    return_type = f" {method.return_type}" if method.return_type else ""
                    lines.append(f"    {visibility}{method.name}({params}){return_type}")
        
        lines.append("}")
        
        # Add inheritance
        for parent in cls.parent_classes:
            lines.append(f"{self._sanitize_id(parent)} <|-- {class_id}")
        
        # Add interface implementations
        for interface in cls.implemented_interfaces:
            lines.append(f"{self._sanitize_id(interface)} <|.. {class_id} : implements")
        
        return lines
    
    def _extract_relationships(self, parsed_files: List[ParsedFile],
                               classes: Dict[str, ClassDefinition]) -> List[tuple]:
        """Extract relationships between classes."""
        relationships = []
        class_names = set(classes.keys())
        
        for pf in parsed_files:
            for rel in pf.relationships:
                from_name, to_name, rel_type = rel
                if to_name in class_names or from_name in class_names:
                    relationships.append(rel)
        
        # Detect composition/association from attributes
        for name, cls in classes.items():
            for attr in cls.attributes:
                if attr.type_annotation:
                    for other_name in class_names:
                        if other_name != name and other_name in attr.type_annotation:
                            relationships.append((name, other_name, RelationshipType.COMPOSITION))
        
        return relationships
    
    def _format_relationship(self, rel: tuple) -> str:
        """Format a relationship for Mermaid."""
        from_name, to_name, rel_type = rel
        from_id = self._sanitize_id(from_name)
        to_id = self._sanitize_id(to_name)
        
        if rel_type == RelationshipType.INHERITS:
            return f"{to_id} <|-- {from_id}"
        elif rel_type == RelationshipType.IMPLEMENTS:
            return f"{to_id} <|.. {from_id}"
        elif rel_type == RelationshipType.COMPOSITION:
            return f"{from_id} *-- {to_id}"
        elif rel_type == RelationshipType.ASSOCIATION:
            return f"{from_id} --> {to_id}"
        else:
            return f"{from_id} ..> {to_id}"
    
    def _get_most_referenced(self, parsed_files: List[ParsedFile], limit: int) -> Set[str]:
        """Get the most referenced classes."""
        reference_count: Dict[str, int] = {}
        
        for pf in parsed_files:
            for cls in pf.classes:
                reference_count[cls.name] = reference_count.get(cls.name, 0)
            
            for rel in pf.relationships:
                _, to_name, _ = rel
                reference_count[to_name] = reference_count.get(to_name, 0) + 1
        
        sorted_classes = sorted(reference_count.items(), key=lambda x: x[1], reverse=True)
        return set(name for name, _ in sorted_classes[:limit])
    
    def _find_participants(self, parsed_files: List[ParsedFile], 
                          entry_point: str) -> List[str]:
        """Find participants in a sequence."""
        participants = set()
        
        for pf in parsed_files:
            # Add module name
            participants.add(Path(pf.path).stem)
            
            # Add classes
            for cls in pf.classes:
                participants.add(cls.name)
        
        return list(participants)[:20]  # Limit participants
    
    def _extract_call_sequence(self, parsed_files: List[ParsedFile],
                               entry_point: str, max_depth: int) -> List[str]:
        """Extract function call sequence."""
        sequences = []
        
        # Find entry point
        entry_func = None
        for pf in parsed_files:
            for func in pf.functions:
                if func.name == entry_point:
                    entry_func = func
                    break
            if entry_func:
                break
        
        if entry_func:
            sequences.append(f"Note over {entry_func.name}: Entry point")
        
        return sequences
    
    def _get_module_name(self, file_path: str) -> str:
        """Extract module name from file path."""
        path = Path(file_path)
        
        # Try to find package root
        parts = list(path.parts)
        for i, part in enumerate(parts):
            if part in ('src', 'lib', 'app', 'packages'):
                return parts[i + 1] if i + 1 < len(parts) else path.parent.name
        
        return path.parent.name
    
    def _extract_module_dependencies(self, parsed_files: List[ParsedFile]) -> List[tuple]:
        """Extract dependencies between modules."""
        dependencies = []
        
        for pf in parsed_files:
            source_module = self._get_module_name(pf.path)
            
            for imp in pf.imports:
                target_module = imp.module.split('.')[0]
                if target_module and target_module != source_module:
                    dependencies.append((source_module, target_module))
        
        return list(set(dependencies))
    
    def _extract_entities(self, parsed_files: List[ParsedFile],
                         entity_filter: Optional[List[str]]) -> List[tuple]:
        """Extract entity definitions for ER diagram."""
        entities = []
        
        for pf in parsed_files:
            for cls in pf.classes:
                # Check if this is an entity (dataclass, has id field, etc.)
                is_entity = cls.is_dataclass or any(
                    attr.name in ('id', 'pk', 'uuid') for attr in cls.attributes
                )
                
                if entity_filter and cls.name not in entity_filter:
                    continue
                
                if is_entity or not entity_filter:
                    relationships = []
                    for attr in cls.attributes:
                        if attr.type_annotation:
                            # Look for references to other classes
                            for other_cls in pf.classes:
                                if other_cls.name != cls.name and other_cls.name in attr.type_annotation:
                                    relationships.append((other_cls.name, "FK"))
                    
                    entities.append((cls.name, cls.attributes, relationships))
        
        return entities
    
    def _extract_state_info(self, method: FunctionDefinition) -> Optional[tuple]:
        """Extract state transition info from a method."""
        # Look for patterns like: transition_to, set_state, etc.
        state_patterns = [
            r'to[_\s](\w+)',
            r'set[_\s]state[_\s]?(?:to)?[_\s]?(\w+)',
            r'transition[_\s]?(?:to)?[_\s]?(\w+)',
        ]
        
        for pattern in state_patterns:
            match = re.search(pattern, method.name, re.IGNORECASE)
            if match:
                to_state = match.group(1)
                from_state = "current"  # Default
                return (from_state, to_state, method.name)
        
        return None
    
    def _sanitize_id(self, name: str) -> str:
        """Sanitize a name for use as Mermaid ID."""
        sanitized = re.sub(r'[^\w]', '_', name)
        if sanitized[0].isdigit():
            sanitized = '_' + sanitized
        return sanitized
    
    def _get_visibility(self, method: FunctionDefinition) -> str:
        """Get Mermaid visibility notation."""
        if method.name.startswith('__'):
            return "-"  # Private
        elif method.name.startswith('_'):
            return "#"  # Protected
        elif method.is_static:
            return "$"  # Static
        else:
            return "+"  # Public
    
    def _map_type(self, type_name: str) -> str:
        """Map type to ER diagram type."""
        type_lower = type_name.lower()
        
        if 'int' in type_lower or 'number' in type_lower:
            return "int"
        elif 'float' in type_lower or 'decimal' in type_lower or 'double' in type_lower:
            return "float"
        elif 'bool' in type_lower:
            return "bool"
        elif 'date' in type_lower or 'time' in type_lower:
            return "date"
        elif 'list' in type_lower or 'array' in type_lower:
            return "array"
        else:
            return "string"
    
    def _map_relationship_type(self, rel_type: str) -> str:
        """Map relationship type to ER notation."""
        if rel_type == "FK":
            return "||--o|"
        return "||--||"
    
    def save_diagram(self, diagram: str, output_path: str):
        """Save diagram to a file."""
        Path(output_path).write_text(diagram)
    
    def generate_diagram_with_styling(self, diagram_type: str,
                                      parsed_files: List[ParsedFile],
                                      output_path: str,
                                      title: Optional[str] = None):
        """Generate a diagram with embedded styling."""
        if diagram_type == "class":
            diagram = self.generate_class_diagram(parsed_files, title)
        elif diagram_type == "sequence":
            diagram = self.generate_sequence_diagram(parsed_files, "main", title=title)
        elif diagram_type == "component":
            diagram = self.generate_component_diagram(parsed_files, title)
        elif diagram_type == "er":
            diagram = self.generate_er_diagram(parsed_files, title=title)
        else:
            raise ValueError(f"Unknown diagram type: {diagram_type}")
        
        # Add styling
        styled = f"""%%{{init: {{'theme': '{self.config.theme}'}}}}%%
{diagram}
"""
        
        self.save_diagram(styled, output_path)
        return output_path