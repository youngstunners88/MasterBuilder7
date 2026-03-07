"""C4 Model diagram generator."""

from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from pathlib import Path
import re

from .parser import ParsedFile, ClassDefinition, ImportInfo


@dataclass
class C4Element:
    """Base class for C4 model elements."""
    id: str
    name: str
    description: str = ""
    tags: Set[str] = field(default_factory=set)


@dataclass
class C4Person(C4Element):
    """C4 Person element."""
    pass


@dataclass
class C4System(C4Element):
    """C4 Software System element."""
    technology: str = ""


@dataclass
class C4Container(C4Element):
    """C4 Container element."""
    technology: str = ""
    system_id: str = ""


@dataclass
class C4Component(C4Element):
    """C4 Component element."""
    technology: str = ""
    container_id: str = ""


@dataclass
class C4Relationship:
    """C4 Relationship element."""
    source: str
    target: str
    description: str = ""
    technology: str = ""


class C4Generator:
    """Generates C4 Model diagrams from parsed code."""
    
    def __init__(self):
        self.systems: Dict[str, C4System] = {}
        self.containers: Dict[str, C4Container] = {}
        self.components: Dict[str, C4Component] = {}
        self.people: Dict[str, C4Person] = {}
        self.relationships: List[C4Relationship] = []
    
    def analyze_codebase(self, parsed_files: List[ParsedFile], 
                        system_name: str = "System") -> 'C4Generator':
        """Analyze a codebase and build C4 model."""
        # Create system
        system = C4System(
            id="system",
            name=system_name,
            description=f"The {system_name} software system"
        )
        self.systems[system.id] = system
        
        # Group files by module/directory
        modules = self._group_by_module(parsed_files)
        
        # Create containers for each module
        for module_name, files in modules.items():
            container = C4Container(
                id=self._sanitize_id(module_name),
                name=module_name,
                description=f"{module_name} module",
                technology=self._detect_container_technology(files),
                system_id=system.id
            )
            self.containers[container.id] = container
            
            # Create components for classes
            for pf in files:
                for cls in pf.classes:
                    component = C4Component(
                        id=self._sanitize_id(f"{container.id}_{cls.name}"),
                        name=cls.name,
                        description=f"Class: {cls.name}",
                        technology=pf.language,
                        container_id=container.id,
                        tags={"class", cls.name.lower()}
                    )
                    self.components[component.id] = component
        
        # Extract relationships from imports and references
        self._extract_relationships(parsed_files)
        
        return self
    
    def generate_context_diagram(self, title: str = "System Context") -> str:
        """Generate C4 Level 1: System Context diagram."""
        lines = [
            "C4Context",
            f"title {title}",
            ""
        ]
        
        # Add person (user)
        user = C4Person(
            id="user",
            name="User",
            description="A user of the system"
        )
        self.people[user.id] = user
        lines.append(f'Person({user.id}, "{user.name}", "{user.description}")')
        
        # Add systems
        for sys in self.systems.values():
            lines.append(f'System({sys.id}, "{sys.name}", "{sys.description}")')
        
        # Add external systems (from imports)
        external_systems = self._get_external_systems()
        for ext in external_systems:
            lines.append(f'System_Ext({ext.id}, "{ext.name}", "{ext.description}")')
        
        # Add relationships
        lines.append(f'Rel({user.id}, system, "Uses")')
        
        for rel in self.relationships:
            if rel.source in self.systems or rel.target in self.systems:
                lines.append(f'Rel({rel.source}, {rel.target}, "{rel.description}")')
        
        return '\n'.join(lines)
    
    def generate_container_diagram(self, title: str = "Container Diagram") -> str:
        """Generate C4 Level 2: Container diagram."""
        lines = [
            "C4Container",
            f"title {title}",
            ""
        ]
        
        # Add person
        if 'user' in self.people:
            user = self.people['user']
            lines.append(f'Person({user.id}, "{user.name}", "{user.description}")')
        
        # Add system boundary
        if self.systems:
            system = list(self.systems.values())[0]
            lines.append(f'System_Boundary({system.id}_boundary, "{system.name}") {{')
            
            # Add containers
            for container in self.containers.values():
                lines.append(f'    Container({container.id}, "{container.name}", "{container.technology}", "{container.description}")')
            
            lines.append("}")
        
        # Add external systems
        external_systems = self._get_external_systems()
        for ext in external_systems:
            lines.append(f'System_Ext({ext.id}, "{ext.name}", "{ext.description}")')
        
        # Add relationships
        for rel in self.relationships:
            if rel.source in self.containers or rel.target in self.containers:
                lines.append(f'Rel({rel.source}, {rel.target}, "{rel.description}")')
        
        return '\n'.join(lines)
    
    def generate_component_diagram(self, container_id: str,
                                   title: Optional[str] = None) -> str:
        """Generate C4 Level 3: Component diagram for a specific container."""
        if container_id not in self.containers:
            raise ValueError(f"Container {container_id} not found")
        
        container = self.containers[container_id]
        title = title or f"Component diagram for {container.name}"
        
        lines = [
            "C4Component",
            f'title {title}',
            ""
        ]
        
        # Add container boundary
        lines.append(f'Container_Boundary({container_id}_boundary, "{container.name}") {{')
        
        # Add components in this container
        components_in_container = [
            c for c in self.components.values() 
            if c.container_id == container_id
        ]
        
        for comp in components_in_container:
            lines.append(f'    Component({comp.id}, "{comp.name}", "{comp.technology}", "{comp.description}")')
        
        lines.append("}")
        
        # Add relationships between components
        component_ids = {c.id for c in components_in_container}
        for rel in self.relationships:
            if rel.source in component_ids and rel.target in component_ids:
                lines.append(f'Rel({rel.source}, {rel.target}, "{rel.description}")')
        
        return '\n'.join(lines)
    
    def generate_code_diagram(self, class_name: str) -> str:
        """Generate C4 Level 4: Code diagram for a specific class."""
        # Find the component
        component = None
        for comp in self.components.values():
            if comp.name == class_name:
                component = comp
                break
        
        if not component:
            raise ValueError(f"Class {class_name} not found")
        
        lines = [
            "classDiagram",
            f"title Code diagram for {class_name}",
            ""
        ]
        
        # This would require access to the original parsed file
        # For now, create a simple placeholder
        lines.append(f"class {class_name} {{")
        lines.append("    +method()")
        lines.append("}")
        
        return '\n'.join(lines)
    
    def generate_dynamic_diagram(self, scenario: str, steps: List[tuple]) -> str:
        """Generate C4 Dynamic diagram."""
        lines = [
            "C4Dynamic",
            f'title {scenario}',
            ""
        ]
        
        # Add all elements involved
        involved_elements = set()
        for source, target, _ in steps:
            involved_elements.add(source)
            involved_elements.add(target)
        
        for elem_id in involved_elements:
            if elem_id in self.containers:
                container = self.containers[elem_id]
                lines.append(f'Container({container.id}, "{container.name}", "{container.technology}")')
            elif elem_id in self.components:
                component = self.components[elem_id]
                lines.append(f'Component({component.id}, "{component.name}", "{component.technology}")')
        
        # Add sequence
        for i, (source, target, description) in enumerate(steps, 1):
            lines.append(f'Rel({source}, {target}, "{i}. {description}")')
        
        return '\n'.join(lines)
    
    def generate_deployment_diagram(self, environment: str = "Production") -> str:
        """Generate C4 Deployment diagram."""
        lines = [
            "C4Deployment",
            f'title Deployment Diagram for {environment}',
            ""
        ]
        
        # Add deployment nodes
        lines.append(f'Deployment_Node(env, "{environment}", "Environment") {{')
        lines.append('    Deployment_Node(server, "Application Server", "Ubuntu 22.04") {{')
        
        # Add containers as deployment artifacts
        for container in self.containers.values():
            lines.append(f'        Container({container.id}, "{container.name}", "{container.technology}")')
        
        lines.append('    }')
        lines.append('}')
        
        return '\n'.join(lines)
    
    def _group_by_module(self, parsed_files: List[ParsedFile]) -> Dict[str, List[ParsedFile]]:
        """Group parsed files by module/directory."""
        modules: Dict[str, List[ParsedFile]] = {}
        
        for pf in parsed_files:
            module_name = self._get_module_name(pf.path)
            if module_name not in modules:
                modules[module_name] = []
            modules[module_name].append(pf)
        
        return modules
    
    def _get_module_name(self, file_path: str) -> str:
        """Extract module name from file path."""
        path = Path(file_path)
        parts = list(path.parts)
        
        # Common source directory patterns
        for i, part in enumerate(parts):
            if part in ('src', 'lib', 'app', 'packages', 'services'):
                if i + 1 < len(parts):
                    return parts[i + 1]
        
        return path.parent.name
    
    def _detect_container_technology(self, files: List[ParsedFile]) -> str:
        """Detect the primary technology used in a container."""
        languages: Dict[str, int] = {}
        
        for pf in files:
            lang = pf.language
            languages[lang] = languages.get(lang, 0) + 1
        
        if languages:
            return max(languages.items(), key=lambda x: x[1])[0]
        return "Unknown"
    
    def _extract_relationships(self, parsed_files: List[ParsedFile]):
        """Extract relationships from parsed files."""
        for pf in parsed_files:
            source_module = self._sanitize_id(self._get_module_name(pf.path))
            
            # Extract from imports
            for imp in pf.imports:
                target_parts = imp.module.split('.')
                if len(target_parts) > 0:
                    target_module = self._sanitize_id(target_parts[0])
                    if target_module != source_module and target_module in self.containers:
                        rel = C4Relationship(
                            source=source_module,
                            target=target_module,
                            description=f"imports {imp.module}",
                            technology="import"
                        )
                        self.relationships.append(rel)
            
            # Extract from class relationships
            for cls in pf.classes:
                source_comp = self._sanitize_id(f"{source_module}_{cls.name}")
                
                for parent in cls.parent_classes:
                    # Find which container has this parent class
                    for other_pf in parsed_files:
                        other_module = self._sanitize_id(self._get_module_name(other_pf.path))
                        for other_cls in other_pf.classes:
                            if other_cls.name == parent:
                                target_comp = self._sanitize_id(f"{other_module}_{parent}")
                                rel = C4Relationship(
                                    source=source_comp,
                                    target=target_comp,
                                    description="inherits",
                                    technology="inheritance"
                                )
                                self.relationships.append(rel)
    
    def _get_external_systems(self) -> List[C4System]:
        """Get external systems from imports."""
        external = []
        seen = set()
        
        for rel in self.relationships:
            if rel.target not in self.containers and rel.target not in self.components:
                if rel.target not in seen:
                    seen.add(rel.target)
                    external.append(C4System(
                        id=rel.target,
                        name=rel.target.replace('_', ' ').title(),
                        description=f"External system: {rel.target}",
                        technology=rel.technology
                    ))
        
        return external
    
    def _sanitize_id(self, name: str) -> str:
        """Sanitize a name for use as ID."""
        sanitized = re.sub(r'[^\w]', '_', name)
        if sanitized and sanitized[0].isdigit():
            sanitized = '_' + sanitized
        return sanitized
    
    def to_plantuml(self) -> str:
        """Convert C4 model to PlantUML format."""
        lines = [
            "@startuml",
            "!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml",
            ""
        ]
        
        # Add elements
        for person in self.people.values():
            lines.append(f'Person({person.id}, "{person.name}", "{person.description}")')
        
        for system in self.systems.values():
            lines.append(f'System({system.id}, "{system.name}", "{system.description}")')
        
        for container in self.containers.values():
            lines.append(f'Container({container.id}, "{container.name}", "{container.technology}", "{container.description}")')
        
        # Add relationships
        for rel in self.relationships:
            lines.append(f'Rel({rel.source}, {rel.target}, "{rel.description}")')
        
        lines.append("")
        lines.append("@enduml")
        
        return '\n'.join(lines)
    
    def save_model(self, output_path: str):
        """Save the C4 model as JSON."""
        import json
        
        model = {
            'systems': [
                {'id': s.id, 'name': s.name, 'description': s.description}
                for s in self.systems.values()
            ],
            'containers': [
                {'id': c.id, 'name': c.name, 'technology': c.technology, 
                 'description': c.description, 'system_id': c.system_id}
                for c in self.containers.values()
            ],
            'components': [
                {'id': c.id, 'name': c.name, 'technology': c.technology,
                 'description': c.description, 'container_id': c.container_id}
                for c in self.components.values()
            ],
            'relationships': [
                {'source': r.source, 'target': r.target, 
                 'description': r.description, 'technology': r.technology}
                for r in self.relationships
            ]
        }
        
        Path(output_path).write_text(json.dumps(model, indent=2))
    
    def generate_all_levels(self, output_dir: str):
        """Generate all C4 level diagrams."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Level 1: Context
        context = self.generate_context_diagram()
        (output_dir / "level1_context.puml").write_text(self.to_plantuml())
        
        # Level 2: Container
        container = self.generate_container_diagram()
        (output_dir / "level2_container.mmd").write_text(container)
        
        # Level 3: Components for each container
        for container_id in self.containers.keys():
            component = self.generate_component_diagram(container_id)
            (output_dir / f"level3_component_{container_id}.mmd").write_text(component)
        
        # Level 4: Code diagrams for key classes
        for component in list(self.components.values())[:10]:
            code = self.generate_code_diagram(component.name)
            (output_dir / f"level4_code_{component.name}.mmd").write_text(code)
        
        # Save model
        self.save_model(output_dir / "c4_model.json")
        
        return output_dir