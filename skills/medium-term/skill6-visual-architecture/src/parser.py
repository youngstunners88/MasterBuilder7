"""Code parser for extracting architecture information."""

import re
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

from tree_sitter import Language, Parser, Tree, Node
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjs
import tree_sitter_typescript as tsts
import tree_sitter_rust as tsrust


class RelationshipType(Enum):
    INHERITS = "inherits"
    IMPLEMENTS = "implements"
    USES = "uses"
    CALLS = "calls"
    IMPORTS = "imports"
    COMPOSITION = "composition"
    ASSOCIATION = "association"


@dataclass
class Parameter:
    name: str
    type_annotation: Optional[str] = None
    default_value: Optional[str] = None


@dataclass
class FunctionDefinition:
    name: str
    parameters: List[Parameter]
    return_type: Optional[str] = None
    is_async: bool = False
    is_static: bool = False
    is_private: bool = False
    decorators: List[str] = field(default_factory=list)
    docstring: Optional[str] = None
    start_line: int = 0
    end_line: int = 0


@dataclass
class ClassDefinition:
    name: str
    methods: List[FunctionDefinition] = field(default_factory=list)
    attributes: List[Parameter] = field(default_factory=list)
    parent_classes: List[str] = field(default_factory=list)
    implemented_interfaces: List[str] = field(default_factory=list)
    is_abstract: bool = False
    is_dataclass: bool = False
    decorators: List[str] = field(default_factory=list)
    docstring: Optional[str] = None
    start_line: int = 0
    end_line: int = 0


@dataclass
class ImportInfo:
    module: str
    names: List[str] = field(default_factory=list)
    is_relative: bool = False
    alias: Optional[str] = None


@dataclass
class ModuleInfo:
    name: str
    classes: List[ClassDefinition] = field(default_factory=list)
    functions: List[FunctionDefinition] = field(default_factory=list)
    imports: List[ImportInfo] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)


@dataclass
class ParsedFile:
    path: str
    language: str
    module: ModuleInfo
    classes: List[ClassDefinition] = field(default_factory=list)
    functions: List[FunctionDefinition] = field(default_factory=list)
    imports: List[ImportInfo] = field(default_factory=list)
    relationships: List[tuple] = field(default_factory=list)  # (from, to, type)


class CodeParser:
    """Parses code files to extract architectural information."""
    
    LANGUAGE_MAP = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.rs': 'rust',
        '.go': 'go',
        '.java': 'java',
    }
    
    def __init__(self):
        self.parsers: Dict[str, Parser] = {}
        self._init_parsers()
    
    def _init_parsers(self):
        """Initialize tree-sitter parsers."""
        try:
            self.parsers['python'] = Parser(tspython.language())
        except Exception:
            pass
        
        try:
            self.parsers['javascript'] = Parser(tsjs.language())
        except Exception:
            pass
        
        try:
            self.parsers['typescript'] = Parser(tsts.language_typescript())
        except Exception:
            pass
        
        try:
            self.parsers['rust'] = Parser(tsrust.language())
        except Exception:
            pass
    
    def parse_file(self, file_path: str | Path) -> Optional[ParsedFile]:
        """Parse a single file and extract architectural information."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            return None
        
        language = self._detect_language(file_path)
        if not language or language not in self.parsers:
            # Fall back to regex-based parsing
            return self._parse_with_regex(file_path, language)
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return None
        
        parser = self.parsers[language]
        tree = parser.parse(content.encode())
        
        if language == 'python':
            return self._parse_python(tree, content, str(file_path))
        elif language in ('javascript', 'typescript'):
            return self._parse_js_ts(tree, content, str(file_path), language)
        elif language == 'rust':
            return self._parse_rust(tree, content, str(file_path))
        
        return None
    
    def _detect_language(self, file_path: Path) -> Optional[str]:
        """Detect language from file extension."""
        return self.LANGUAGE_MAP.get(file_path.suffix.lower())
    
    def _parse_with_regex(self, file_path: Path, language: Optional[str]) -> Optional[ParsedFile]:
        """Fallback parsing using regex for unsupported languages."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return None
        
        language = language or 'unknown'
        lines = content.split('\n')
        
        classes = []
        functions = []
        imports = []
        
        # Simple regex patterns for common constructs
        class_pattern = re.compile(r'(?:class|struct|interface)\s+(\w+)')
        func_pattern = re.compile(r'(?:function|def|func)\s+(\w+)\s*\(')
        import_pattern = re.compile(r'(?:import|from|use|require)\s+[\'"]?([^\'";\n]+)')
        
        for i, line in enumerate(lines):
            # Classes
            for match in class_pattern.finditer(line):
                classes.append(ClassDefinition(
                    name=match.group(1),
                    start_line=i + 1,
                    end_line=i + 1
                ))
            
            # Functions
            for match in func_pattern.finditer(line):
                functions.append(FunctionDefinition(
                    name=match.group(1),
                    parameters=[],
                    start_line=i + 1,
                    end_line=i + 1
                ))
            
            # Imports
            for match in import_pattern.finditer(line):
                imports.append(ImportInfo(module=match.group(1).strip()))
        
        module = ModuleInfo(
            name=file_path.stem,
            classes=classes,
            functions=functions,
            imports=imports
        )
        
        return ParsedFile(
            path=str(file_path),
            language=language,
            module=module,
            classes=classes,
            functions=functions,
            imports=imports
        )
    
    def _parse_python(self, tree: Tree, content: str, file_path: str) -> ParsedFile:
        """Parse Python code using tree-sitter."""
        root = tree.root_node
        lines = content.split('\n')
        
        classes = []
        functions = []
        imports = []
        
        def get_text(node: Node) -> str:
            return content[node.start_byte:node.end_byte]
        
        def traverse(node: Node):
            if node.type == 'class_definition':
                cls = self._extract_python_class(node, get_text, lines)
                classes.append(cls)
            elif node.type == 'function_definition':
                func = self._extract_python_function(node, get_text, lines)
                functions.append(func)
            elif node.type == 'import_statement' or node.type == 'import_from_statement':
                imp = self._extract_python_import(node, get_text)
                imports.append(imp)
            
            for child in node.children:
                traverse(child)
        
        traverse(root)
        
        # Extract module-level functions (not methods)
        module_functions = [f for f in functions if not self._is_method(f, classes)]
        
        module = ModuleInfo(
            name=Path(file_path).stem,
            classes=classes,
            functions=module_functions,
            imports=imports
        )
        
        # Build relationships
        relationships = self._build_relationships(classes, functions, imports)
        
        return ParsedFile(
            path=file_path,
            language='python',
            module=module,
            classes=classes,
            functions=module_functions,
            imports=imports,
            relationships=relationships
        )
    
    def _extract_python_class(self, node: Node, get_text: Callable, lines: List[str]) -> ClassDefinition:
        """Extract Python class information."""
        name = ""
        parent_classes = []
        methods = []
        attributes = []
        decorators = []
        is_dataclass = False
        
        for child in node.children:
            if child.type == 'identifier':
                name = get_text(child)
            elif child.type == 'argument_list':
                # Extract parent classes
                for arg in child.children:
                    if arg.type == 'identifier':
                        parent_classes.append(get_text(arg))
            elif child.type == 'block':
                # Extract methods and attributes
                for item in child.children:
                    if item.type == 'function_definition':
                        method = self._extract_python_function(item, get_text, lines)
                        methods.append(method)
                    elif item.type == 'expression_statement':
                        # Could be attribute assignment
                        attr = self._extract_python_attribute(item, get_text)
                        if attr:
                            attributes.append(attr)
            elif child.type == 'decorator':
                dec_text = get_text(child)
                decorators.append(dec_text)
                if 'dataclass' in dec_text:
                    is_dataclass = True
        
        return ClassDefinition(
            name=name,
            methods=methods,
            attributes=attributes,
            parent_classes=parent_classes,
            decorators=decorators,
            is_dataclass=is_dataclass,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1
        )
    
    def _extract_python_function(self, node: Node, get_text: Callable, lines: List[str]) -> FunctionDefinition:
        """Extract Python function information."""
        name = ""
        parameters = []
        return_type = None
        is_async = False
        decorators = []
        
        for child in node.children:
            if child.type == 'identifier':
                name = get_text(child)
            elif child.type == 'parameters':
                parameters = self._extract_python_parameters(child, get_text)
            elif child.type == 'type':
                return_type = get_text(child)
            elif child.type == 'async':
                is_async = True
            elif child.type == 'decorator':
                decorators.append(get_text(child))
        
        # Check for async in function signature
        func_line = lines[node.start_point[0]]
        is_async = 'async ' in func_line
        is_static = 'staticmethod' in str(decorators)
        is_private = name.startswith('_') and not name.startswith('__')
        
        return FunctionDefinition(
            name=name,
            parameters=parameters,
            return_type=return_type,
            is_async=is_async,
            is_static=is_static,
            is_private=is_private,
            decorators=decorators,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1
        )
    
    def _extract_python_parameters(self, node: Node, get_text: Callable) -> List[Parameter]:
        """Extract Python function parameters."""
        params = []
        
        for child in node.children:
            if child.type == 'identifier':
                params.append(Parameter(name=get_text(child)))
            elif child.type == 'typed_parameter':
                name = ""
                type_annotation = None
                for sub in child.children:
                    if sub.type == 'identifier':
                        name = get_text(sub)
                    elif sub.type == 'type':
                        type_annotation = get_text(sub)
                params.append(Parameter(name=name, type_annotation=type_annotation))
            elif child.type == 'default_parameter':
                name = ""
                default_value = None
                for sub in child.children:
                    if sub.type == 'identifier':
                        name = get_text(sub)
                    elif sub.type not in ('=',):
                        default_value = get_text(sub)
                params.append(Parameter(name=name, default_value=default_value))
        
        return params
    
    def _extract_python_attribute(self, node: Node, get_text: Callable) -> Optional[Parameter]:
        """Extract Python class attribute."""
        text = get_text(node)
        if '=' in text and ':' not in text:
            parts = text.split('=')
            if len(parts) == 2:
                return Parameter(name=parts[0].strip(), default_value=parts[1].strip())
        return None
    
    def _extract_python_import(self, node: Node, get_text: Callable) -> ImportInfo:
        """Extract Python import information."""
        module = ""
        names = []
        is_relative = False
        
        for child in node.children:
            if child.type == 'dotted_name':
                module = get_text(child)
            elif child.type == 'relative_import':
                is_relative = True
                module = get_text(child)
            elif child.type == 'import_list' or child.type == 'dotted_as_names':
                for name in child.children:
                    if name.type in ('dotted_name', 'identifier'):
                        names.append(get_text(name))
        
        return ImportInfo(module=module, names=names, is_relative=is_relative)
    
    def _parse_js_ts(self, tree: Tree, content: str, file_path: str, language: str) -> ParsedFile:
        """Parse JavaScript/TypeScript code."""
        root = tree.root_node
        
        classes = []
        functions = []
        imports = []
        exports = []
        
        def get_text(node: Node) -> str:
            return content[node.start_byte:node.end_byte]
        
        def traverse(node: Node):
            if node.type == 'class_declaration' or node.type == 'class':
                cls = self._extract_js_class(node, get_text)
                classes.append(cls)
            elif node.type in ('function_declaration', 'function', 'arrow_function'):
                func = self._extract_js_function(node, get_text)
                functions.append(func)
            elif node.type == 'method_definition':
                func = self._extract_js_method(node, get_text)
                functions.append(func)
            elif node.type == 'import_statement' or node.type == 'import_declaration':
                imp = self._extract_js_import(node, get_text)
                imports.append(imp)
            elif node.type == 'export_statement':
                exports.append(get_text(node))
            
            for child in node.children:
                traverse(child)
        
        traverse(root)
        
        module = ModuleInfo(
            name=Path(file_path).stem,
            classes=classes,
            functions=[f for f in functions if not self._is_method_in_list(f, classes)],
            imports=imports,
            exports=exports
        )
        
        relationships = self._build_relationships(classes, functions, imports)
        
        return ParsedFile(
            path=file_path,
            language=language,
            module=module,
            classes=classes,
            functions=module.functions,
            imports=imports,
            relationships=relationships
        )
    
    def _extract_js_class(self, node: Node, get_text: Callable) -> ClassDefinition:
        """Extract JavaScript/TypeScript class information."""
        name = ""
        parent_classes = []
        methods = []
        
        for child in node.children:
            if child.type == 'identifier' or child.type == 'type_identifier':
                name = get_text(child)
            elif child.type == 'class_heritage':
                for sub in child.children:
                    if sub.type == 'identifier' or sub.type == 'user_type':
                        parent_classes.append(get_text(sub))
            elif child.type == 'class_body':
                for item in child.children:
                    if item.type == 'method_definition':
                        method = self._extract_js_method(item, get_text)
                        methods.append(method)
        
        return ClassDefinition(
            name=name,
            methods=methods,
            parent_classes=parent_classes,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1
        )
    
    def _extract_js_function(self, node: Node, get_text: Callable) -> FunctionDefinition:
        """Extract JavaScript/TypeScript function information."""
        name = ""
        parameters = []
        is_async = False
        
        for child in node.children:
            if child.type == 'identifier':
                name = get_text(child)
            elif child.type == 'formal_parameters' or child.type == 'formal_parameter_list':
                parameters = self._extract_js_parameters(child, get_text)
            elif child.type == 'async':
                is_async = True
        
        return FunctionDefinition(
            name=name or 'anonymous',
            parameters=parameters,
            is_async=is_async,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1
        )
    
    def _extract_js_method(self, node: Node, get_text: Callable) -> FunctionDefinition:
        """Extract JavaScript/TypeScript method information."""
        name = ""
        parameters = []
        is_async = False
        is_static = False
        
        for child in node.children:
            if child.type == 'property_identifier':
                name = get_text(child)
            elif child.type == 'formal_parameters':
                parameters = self._extract_js_parameters(child, get_text)
            elif child.type == 'async':
                is_async = True
            elif child.type == 'static':
                is_static = True
        
        return FunctionDefinition(
            name=name,
            parameters=parameters,
            is_async=is_async,
            is_static=is_static,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1
        )
    
    def _extract_js_parameters(self, node: Node, get_text: Callable) -> List[Parameter]:
        """Extract JavaScript/TypeScript function parameters."""
        params = []
        
        for child in node.children:
            if child.type == 'identifier':
                params.append(Parameter(name=get_text(child)))
            elif child.type == 'formal_parameter':
                name = ""
                type_annotation = None
                for sub in child.children:
                    if sub.type == 'identifier':
                        name = get_text(sub)
                    elif sub.type == 'type_annotation':
                        type_annotation = get_text(sub)
                params.append(Parameter(name=name, type_annotation=type_annotation))
        
        return params
    
    def _extract_js_import(self, node: Node, get_text: Callable) -> ImportInfo:
        """Extract JavaScript/TypeScript import information."""
        module = ""
        names = []
        
        for child in node.children:
            if child.type == 'string':
                module = get_text(child).strip('"\'')
            elif child.type == 'import_clause' or child.type == 'named_imports':
                for sub in child.children:
                    if sub.type == 'identifier':
                        names.append(get_text(sub))
        
        return ImportInfo(module=module, names=names)
    
    def _parse_rust(self, tree: Tree, content: str, file_path: str) -> ParsedFile:
        """Parse Rust code."""
        root = tree.root_node
        
        classes = []  # In Rust: structs, enums, traits
        functions = []
        imports = []
        
        def get_text(node: Node) -> str:
            return content[node.start_byte:node.end_byte]
        
        def traverse(node: Node):
            if node.type in ('struct_item', 'enum_item', 'trait_item'):
                cls = self._extract_rust_struct(node, get_text)
                classes.append(cls)
            elif node.type == 'function_item':
                func = self._extract_rust_function(node, get_text)
                functions.append(func)
            elif node.type == 'use_declaration':
                imp = self._extract_rust_import(node, get_text)
                imports.append(imp)
            
            for child in node.children:
                traverse(child)
        
        traverse(root)
        
        module = ModuleInfo(
            name=Path(file_path).stem,
            classes=classes,
            functions=functions,
            imports=imports
        )
        
        relationships = self._build_relationships(classes, functions, imports)
        
        return ParsedFile(
            path=file_path,
            language='rust',
            module=module,
            classes=classes,
            functions=functions,
            imports=imports,
            relationships=relationships
        )
    
    def _extract_rust_struct(self, node: Node, get_text: Callable) -> ClassDefinition:
        """Extract Rust struct/enum/trait information."""
        name = ""
        kind = node.type.replace('_item', '')
        
        for child in node.children:
            if child.type == 'type_identifier':
                name = get_text(child)
        
        return ClassDefinition(
            name=f"{kind}: {name}",
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1
        )
    
    def _extract_rust_function(self, node: Node, get_text: Callable) -> FunctionDefinition:
        """Extract Rust function information."""
        name = ""
        parameters = []
        
        for child in node.children:
            if child.type == 'identifier':
                name = get_text(child)
            elif child.type == 'parameters':
                parameters = self._extract_rust_parameters(child, get_text)
        
        return FunctionDefinition(
            name=name,
            parameters=parameters,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1
        )
    
    def _extract_rust_parameters(self, node: Node, get_text: Callable) -> List[Parameter]:
        """Extract Rust function parameters."""
        params = []
        
        for child in node.children:
            if child.type == 'parameter':
                text = get_text(child)
                parts = text.split(':')
                if len(parts) >= 2:
                    params.append(Parameter(
                        name=parts[0].strip(),
                        type_annotation=parts[1].strip()
                    ))
        
        return params
    
    def _extract_rust_import(self, node: Node, get_text: Callable) -> ImportInfo:
        """Extract Rust import (use) information."""
        module = ""
        
        for child in node.children:
            if child.type == 'use_list' or child.type == 'scoped_use_list':
                module = get_text(child)
        
        return ImportInfo(module=module or get_text(node))
    
    def _is_method(self, func: FunctionDefinition, classes: List[ClassDefinition]) -> bool:
        """Check if a function is a method of any class."""
        for cls in classes:
            if func.start_line >= cls.start_line and func.end_line <= cls.end_line:
                return True
        return False
    
    def _is_method_in_list(self, func: FunctionDefinition, classes: List[ClassDefinition]) -> bool:
        """Check if function is in any class's methods."""
        for cls in classes:
            if any(m.name == func.name and m.start_line == func.start_line for m in cls.methods):
                return True
        return False
    
    def _build_relationships(self, classes: List[ClassDefinition], 
                            functions: List[FunctionDefinition],
                            imports: List[ImportInfo]) -> List[tuple]:
        """Build relationships between code elements."""
        relationships = []
        
        # Inheritance relationships
        for cls in classes:
            for parent in cls.parent_classes:
                relationships.append((cls.name, parent, RelationshipType.INHERITS))
        
        # Import relationships
        for imp in imports:
            for name in imp.names:
                relationships.append((imp.module, name, RelationshipType.IMPORTS))
        
        return relationships
    
    def parse_directory(self, directory: str | Path, 
                       pattern: str = "**/*.py") -> List[ParsedFile]:
        """Parse all files in a directory matching a pattern."""
        directory = Path(directory)
        parsed_files = []
        
        for file_path in directory.glob(pattern):
            if 'node_modules' in str(file_path) or '.git' in str(file_path):
                continue
            
            parsed = self.parse_file(file_path)
            if parsed:
                parsed_files.append(parsed)
        
        return parsed_files