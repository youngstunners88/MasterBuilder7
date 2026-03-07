"""
Indexer module for semantic code search.
Uses tree-sitter to parse and index code files.
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict
import hashlib
import json
from loguru import logger

# Tree-sitter imports
from tree_sitter import Language, Parser, Tree, Node

# Language parsers
PARSERS = {}


def get_parser(language: str) -> Optional[Parser]:
    """Get or create a parser for a language."""
    if language in PARSERS:
        return PARSERS[language]
    
    try:
        parser = Parser()
        
        if language == 'python':
            import tree_sitter_python as tspython
            parser.set_language(Language(tspython.language()))
        elif language == 'javascript':
            import tree_sitter_javascript as tsjs
            parser.set_language(Language(tsjs.language()))
        elif language == 'typescript':
            import tree_sitter_typescript as tsts
            parser.set_language(Language(tsts.language_typescript()))
        elif language == 'tsx':
            import tree_sitter_typescript as tsts
            parser.set_language(Language(tsts.language_tsx()))
        elif language == 'rust':
            import tree_sitter_rust as tsrust
            parser.set_language(Language(tsrust.language()))
        elif language == 'go':
            import tree_sitter_go as tsgo
            parser.set_language(Language(tsgo.language()))
        elif language == 'java':
            import tree_sitter_java as tsjava
            parser.set_language(Language(tsjava.language()))
        else:
            return None
        
        PARSERS[language] = parser
        return parser
    
    except Exception as e:
        logger.warning(f"Could not load parser for {language}: {e}")
        return None


@dataclass
class CodeElement:
    """Represents a code element (function, class, etc.)."""
    element_type: str  # function, class, method, interface, etc.
    name: str
    content: str
    start_line: int
    end_line: int
    file_path: str
    language: str
    signature: Optional[str] = None
    docstring: Optional[str] = None
    modifiers: List[str] = field(default_factory=list)
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    parent: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'element_type': self.element_type,
            'name': self.name,
            'file_path': self.file_path,
            'language': self.language,
            'start_line': self.start_line,
            'end_line': self.end_line,
            'signature': self.signature,
            'docstring': self.docstring,
            'modifiers': self.modifiers,
            'parameters': self.parameters,
            'return_type': self.return_type,
            'parent': self.parent,
            'content_preview': self.content[:200] if self.content else None,
        }


class LanguageMapper:
    """Maps file extensions to languages."""
    
    EXTENSION_MAP = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'tsx',
        '.rs': 'rust',
        '.go': 'go',
        '.java': 'java',
    }
    
    @classmethod
    def get_language(cls, file_path: Path) -> Optional[str]:
        """Get language from file extension."""
        return cls.EXTENSION_MAP.get(file_path.suffix.lower())
    
    @classmethod
    def get_supported_extensions(cls) -> Set[str]:
        """Get set of supported file extensions."""
        return set(cls.EXTENSION_MAP.keys())
    
    @classmethod
    def is_supported(cls, file_path: Path) -> bool:
        """Check if file extension is supported."""
        return file_path.suffix.lower() in cls.EXTENSION_MAP


class TreeSitterIndexer:
    """Indexes code files using tree-sitter parsers."""
    
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.elements: List[CodeElement] = []
        self.file_hashes: Dict[str, str] = {}  # path -> content hash
    
    def index_project(
        self,
        languages: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> int:
        """
        Index the entire project.
        
        Args:
            languages: List of languages to index (None = all supported)
            exclude_patterns: List of patterns to exclude
            
        Returns:
            Number of elements indexed
        """
        if languages is None:
            languages = list(LanguageMapper.EXTENSION_MAP.values())
        
        exclude_patterns = exclude_patterns or [
            '**/node_modules/**', '**/.git/**', '**/__pycache__/**',
            '**/.venv/**', '**/venv/**', '**/dist/**', '**/build/**',
            '**/coverage/**', '**/*.min.js', '**/*.bundle.js'
        ]
        
        extensions = [
            ext for ext, lang in LanguageMapper.EXTENSION_MAP.items()
            if lang in languages
        ]
        
        logger.info(f"Indexing project for languages: {languages}")
        
        files = self._find_files(extensions, exclude_patterns)
        logger.info(f"Found {len(files)} files to index")
        
        for file_path in files:
            try:
                self._index_file(file_path)
            except Exception as e:
                logger.warning(f"Failed to index {file_path}: {e}")
        
        logger.info(f"Indexed {len(self.elements)} code elements")
        return len(self.elements)
    
    def _find_files(
        self,
        extensions: List[str],
        exclude_patterns: List[str]
    ) -> List[Path]:
        """Find all matching files in project."""
        files = []
        
        for ext in extensions:
            for file_path in self.project_root.rglob(f"*{ext}"):
                # Check exclude patterns
                if not self._should_exclude(file_path, exclude_patterns):
                    files.append(file_path)
        
        return sorted(files)
    
    def _should_exclude(self, file_path: Path, patterns: List[str]) -> bool:
        """Check if file should be excluded."""
        path_str = str(file_path)
        
        # Skip hidden directories and common exclusions
        exclude_dirs = {
            'node_modules', '.git', '__pycache__', '.venv', 'venv',
            'dist', 'build', '.pytest_cache', '.mypy_cache', '.tox',
            'coverage', 'htmlcov', '.kimi', '.cache'
        }
        
        for part in file_path.parts:
            if part in exclude_dirs:
                return True
        
        # Skip large files (>500KB)
        try:
            if file_path.stat().st_size > 500 * 1024:
                return True
        except:
            pass
        
        return False
    
    def _index_file(self, file_path: Path):
        """Index a single file."""
        language = LanguageMapper.get_language(file_path)
        if not language:
            return
        
        parser = get_parser(language)
        if not parser:
            return
        
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        
        # Check if file has changed
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        if self.file_hashes.get(str(file_path)) == content_hash:
            return  # Skip unchanged files
        
        self.file_hashes[str(file_path)] = content_hash
        
        # Parse the file
        tree = parser.parse(bytes(content, 'utf-8'))
        
        # Extract elements based on language
        if language == 'python':
            elements = self._extract_python_elements(tree, content, file_path)
        elif language in ['javascript', 'typescript', 'tsx']:
            elements = self._extract_js_elements(tree, content, file_path, language)
        elif language == 'rust':
            elements = self._extract_rust_elements(tree, content, file_path)
        elif language == 'go':
            elements = self._extract_go_elements(tree, content, file_path)
        elif language == 'java':
            elements = self._extract_java_elements(tree, content, file_path)
        else:
            elements = []
        
        self.elements.extend(elements)
    
    def _extract_python_elements(
        self,
        tree: Tree,
        content: str,
        file_path: Path
    ) -> List[CodeElement]:
        """Extract Python code elements."""
        elements = []
        lines = content.split('\n')
        root_node = tree.root_node
        
        def get_text(node: Node) -> str:
            return content[node.start_byte:node.end_byte]
        
        def get_line_number(node: Node) -> int:
            return node.start_point[0] + 1
        
        def visit_node(node: Node, parent_class: Optional[str] = None):
            if node.type == 'function_definition':
                name_node = node.child_by_field_name('name')
                params_node = node.child_by_field_name('parameters')
                return_node = node.child_by_field_name('return_type')
                
                name = get_text(name_node) if name_node else '<anonymous>'
                params = get_text(params_node) if params_node else '()'
                return_type = get_text(return_node) if return_node else None
                
                # Determine if method or function
                element_type = 'method' if parent_class else 'function'
                
                # Extract docstring
                docstring = None
                body_node = node.child_by_field_name('body')
                if body_node:
                    for child in body_node.children:
                        if child.type == 'expression_statement':
                            expr = child.children[0] if child.children else None
                            if expr and expr.type == 'string':
                                docstring = get_text(expr).strip('"\'')
                                break
                
                # Build signature
                signature = f"def {name}{params}"
                if return_type:
                    signature += f" -> {return_type}"
                
                element = CodeElement(
                    element_type=element_type,
                    name=name,
                    content=get_text(node),
                    start_line=get_line_number(node),
                    end_line=node.end_point[0] + 1,
                    file_path=str(file_path.relative_to(self.project_root)),
                    language='python',
                    signature=signature,
                    docstring=docstring,
                    parameters=[p.strip() for p in params.strip('()').split(',') if p.strip()],
                    return_type=return_type,
                    parent=parent_class
                )
                elements.append(element)
            
            elif node.type == 'class_definition':
                name_node = node.child_by_field_name('name')
                name = get_text(name_node) if name_node else '<anonymous>'
                
                element = CodeElement(
                    element_type='class',
                    name=name,
                    content=get_text(node),
                    start_line=get_line_number(node),
                    end_line=node.end_point[0] + 1,
                    file_path=str(file_path.relative_to(self.project_root)),
                    language='python',
                    signature=f"class {name}",
                )
                elements.append(element)
                
                # Visit children with parent class
                for child in node.children:
                    visit_node(child, parent_class=name)
            
            else:
                for child in node.children:
                    visit_node(child, parent_class)
        
        visit_node(root_node)
        return elements
    
    def _extract_js_elements(
        self,
        tree: Tree,
        content: str,
        file_path: Path,
        language: str
    ) -> List[CodeElement]:
        """Extract JavaScript/TypeScript code elements."""
        elements = []
        root_node = tree.root_node
        
        def get_text(node: Node) -> str:
            return content[node.start_byte:node.end_byte]
        
        def get_line_number(node: Node) -> int:
            return node.start_point[0] + 1
        
        def visit_node(node: Node, parent_class: Optional[str] = None):
            # Function declarations
            if node.type in ['function_declaration', 'function']:
                name_node = node.child_by_field_name('name')
                params_node = node.child_by_field_name('parameters')
                
                name = get_text(name_node) if name_node else '<anonymous>'
                params = get_text(params_node) if params_node else '()'
                
                element_type = 'method' if parent_class else 'function'
                
                element = CodeElement(
                    element_type=element_type,
                    name=name,
                    content=get_text(node),
                    start_line=get_line_number(node),
                    end_line=node.end_point[0] + 1,
                    file_path=str(file_path.relative_to(self.project_root)),
                    language=language,
                    signature=f"function {name}{params}",
                    parameters=[p.strip() for p in params.strip('()').split(',') if p.strip()],
                    parent=parent_class
                )
                elements.append(element)
            
            # Arrow functions (variable declarations)
            elif node.type == 'lexical_declaration':
                for child in node.children:
                    if child.type == 'variable_declarator':
                        name_node = child.child_by_field_name('name')
                        value_node = child.child_by_field_name('value')
                        
                        if value_node and value_node.type == 'arrow_function':
                            name = get_text(name_node) if name_node else '<anonymous>'
                            params_node = value_node.child_by_field_name('parameters')
                            params = get_text(params_node) if params_node else '()'
                            
                            element = CodeElement(
                                element_type='function',
                                name=name,
                                content=get_text(node),
                                start_line=get_line_number(node),
                                end_line=node.end_point[0] + 1,
                                file_path=str(file_path.relative_to(self.project_root)),
                                language=language,
                                signature=f"const {name}{params} =>",
                                parameters=[p.strip() for p in params.strip('()').split(',') if p.strip()],
                            )
                            elements.append(element)
            
            # Class declarations
            elif node.type == 'class_declaration':
                name_node = node.child_by_field_name('name')
                name = get_text(name_node) if name_node else '<anonymous>'
                
                element = CodeElement(
                    element_type='class',
                    name=name,
                    content=get_text(node),
                    start_line=get_line_number(node),
                    end_line=node.end_point[0] + 1,
                    file_path=str(file_path.relative_to(self.project_root)),
                    language=language,
                    signature=f"class {name}",
                )
                elements.append(element)
                
                # Visit children for methods
                body_node = node.child_by_field_name('body')
                if body_node:
                    for child in body_node.children:
                        if child.type == 'method_definition':
                            method_name_node = child.child_by_field_name('name')
                            method_name = get_text(method_name_node) if method_name_node else '<anonymous>'
                            params_node = child.child_by_field_name('parameters')
                            params = get_text(params_node) if params_node else '()'
                            
                            method_element = CodeElement(
                                element_type='method',
                                name=method_name,
                                content=get_text(child),
                                start_line=get_line_number(child),
                                end_line=child.end_point[0] + 1,
                                file_path=str(file_path.relative_to(self.project_root)),
                                language=language,
                                signature=f"{method_name}{params}",
                                parameters=[p.strip() for p in params.strip('()').split(',') if p.strip()],
                                parent=name
                            )
                            elements.append(method_element)
            
            # Continue visiting
            for child in node.children:
                if node.type != 'class_declaration':  # Skip class body (handled above)
                    visit_node(child, parent_class)
        
        visit_node(root_node)
        return elements
    
    def _extract_rust_elements(
        self,
        tree: Tree,
        content: str,
        file_path: Path
    ) -> List[CodeElement]:
        """Extract Rust code elements."""
        elements = []
        root_node = tree.root_node
        
        def get_text(node: Node) -> str:
            return content[node.start_byte:node.end_byte]
        
        def get_line_number(node: Node) -> int:
            return node.start_point[0] + 1
        
        def visit_node(node: Node):
            if node.type == 'function_item':
                name_node = node.child_by_field_name('name')
                params_node = node.child_by_field_name('parameters')
                return_node = node.child_by_field_name('return_type')
                
                name = get_text(name_node) if name_node else '<anonymous>'
                params = get_text(params_node) if params_node else '()'
                return_type = get_text(return_node) if return_node else None
                
                element = CodeElement(
                    element_type='function',
                    name=name,
                    content=get_text(node),
                    start_line=get_line_number(node),
                    end_line=node.end_point[0] + 1,
                    file_path=str(file_path.relative_to(self.project_root)),
                    language='rust',
                    signature=f"fn {name}{params}",
                    parameters=[p.strip() for p in params.strip('()').split(',') if p.strip()],
                    return_type=return_type,
                )
                elements.append(element)
            
            elif node.type == 'struct_item':
                for child in node.children:
                    if child.type == 'type_identifier':
                        name = get_text(child)
                        element = CodeElement(
                            element_type='struct',
                            name=name,
                            content=get_text(node),
                            start_line=get_line_number(node),
                            end_line=node.end_point[0] + 1,
                            file_path=str(file_path.relative_to(self.project_root)),
                            language='rust',
                            signature=f"struct {name}",
                        )
                        elements.append(element)
                        break
            
            elif node.type == 'impl_item':
                for child in node.children:
                    if child.type == 'type_identifier':
                        parent_name = get_text(child)
                        # Visit children to find methods
                        for impl_child in node.children:
                            if impl_child.type == 'function_item':
                                visit_node(impl_child)
                        break
            
            else:
                for child in node.children:
                    visit_node(child)
        
        visit_node(root_node)
        return elements
    
    def _extract_go_elements(
        self,
        tree: Tree,
        content: str,
        file_path: Path
    ) -> List[CodeElement]:
        """Extract Go code elements."""
        elements = []
        root_node = tree.root_node
        
        def get_text(node: Node) -> str:
            return content[node.start_byte:node.end_byte]
        
        def get_line_number(node: Node) -> int:
            return node.start_point[0] + 1
        
        def visit_node(node: Node):
            if node.type == 'function_declaration':
                name_node = node.child_by_field_name('name')
                params_node = node.child_by_field_name('parameters')
                result_node = node.child_by_field_name('result')
                
                name = get_text(name_node) if name_node else '<anonymous>'
                params = get_text(params_node) if params_node else '()'
                return_type = get_text(result_node) if result_node else None
                
                element = CodeElement(
                    element_type='function',
                    name=name,
                    content=get_text(node),
                    start_line=get_line_number(node),
                    end_line=node.end_point[0] + 1,
                    file_path=str(file_path.relative_to(self.project_root)),
                    language='go',
                    signature=f"func {name}{params}",
                    parameters=[p.strip() for p in params.strip('()').split(',') if p.strip()],
                    return_type=return_type,
                )
                elements.append(element)
            
            elif node.type == 'method_declaration':
                name_node = node.child_by_field_name('name')
                receiver_node = node.child_by_field_name('receiver')
                params_node = node.child_by_field_name('parameters')
                
                name = get_text(name_node) if name_node else '<anonymous>'
                receiver = get_text(receiver_node) if receiver_node else ''
                params = get_text(params_node) if params_node else '()'
                
                element = CodeElement(
                    element_type='method',
                    name=name,
                    content=get_text(node),
                    start_line=get_line_number(node),
                    end_line=node.end_point[0] + 1,
                    file_path=str(file_path.relative_to(self.project_root)),
                    language='go',
                    signature=f"func {receiver} {name}{params}",
                    parameters=[p.strip() for p in params.strip('()').split(',') if p.strip()],
                )
                elements.append(element)
            
            elif node.type == 'type_declaration':
                for child in node.children:
                    if child.type == 'type_spec':
                        name_node = child.child_by_field_name('name')
                        if name_node:
                            name = get_text(name_node)
                            element = CodeElement(
                                element_type='type',
                                name=name,
                                content=get_text(node),
                                start_line=get_line_number(node),
                                end_line=node.end_point[0] + 1,
                                file_path=str(file_path.relative_to(self.project_root)),
                                language='go',
                                signature=f"type {name}",
                            )
                            elements.append(element)
            
            else:
                for child in node.children:
                    visit_node(child)
        
        visit_node(root_node)
        return elements
    
    def _extract_java_elements(
        self,
        tree: Tree,
        content: str,
        file_path: Path
    ) -> List[CodeElement]:
        """Extract Java code elements."""
        elements = []
        root_node = tree.root_node
        
        def get_text(node: Node) -> str:
            return content[node.start_byte:node.end_byte]
        
        def get_line_number(node: Node) -> int:
            return node.start_point[0] + 1
        
        def visit_node(node: Node, parent_class: Optional[str] = None):
            if node.type == 'method_declaration':
                name_node = node.child_by_field_name('name')
                params_node = node.child_by_field_name('parameters')
                type_node = node.child_by_field_name('type')
                
                # Get modifiers
                modifiers = []
                for child in node.children:
                    if child.type in ['public', 'private', 'protected', 'static', 'final']:
                        modifiers.append(child.type)
                
                name = get_text(name_node) if name_node else '<anonymous>'
                params = get_text(params_node) if params_node else '()'
                return_type = get_text(type_node) if type_node else None
                
                element_type = 'method' if parent_class else 'function'
                
                element = CodeElement(
                    element_type=element_type,
                    name=name,
                    content=get_text(node),
                    start_line=get_line_number(node),
                    end_line=node.end_point[0] + 1,
                    file_path=str(file_path.relative_to(self.project_root)),
                    language='java',
                    signature=f"{' '.join(modifiers)} {return_type or 'void'} {name}{params}",
                    modifiers=modifiers,
                    parameters=[p.strip() for p in params.strip('()').split(',') if p.strip()],
                    return_type=return_type,
                    parent=parent_class
                )
                elements.append(element)
            
            elif node.type == 'class_declaration':
                name_node = node.child_by_field_name('name')
                if name_node:
                    name = get_text(name_node)
                    
                    # Get modifiers
                    modifiers = []
                    for child in node.children:
                        if child.type in ['public', 'private', 'abstract', 'final']:
                            modifiers.append(child.type)
                    
                    element = CodeElement(
                        element_type='class',
                        name=name,
                        content=get_text(node),
                        start_line=get_line_number(node),
                        end_line=node.end_point[0] + 1,
                        file_path=str(file_path.relative_to(self.project_root)),
                        language='java',
                        signature=f"{' '.join(modifiers)} class {name}",
                        modifiers=modifiers,
                    )
                    elements.append(element)
                    
                    # Visit children
                    body_node = node.child_by_field_name('body')
                    if body_node:
                        for child in body_node.children:
                            visit_node(child, parent_class=name)
            
            else:
                for child in node.children:
                    visit_node(child, parent_class)
        
        visit_node(root_node)
        return elements
    
    def get_elements(self) -> List[CodeElement]:
        """Get all indexed elements."""
        return self.elements
    
    def get_elements_by_language(self, language: str) -> List[CodeElement]:
        """Get elements filtered by language."""
        return [e for e in self.elements if e.language == language]
    
    def get_elements_by_type(self, element_type: str) -> List[CodeElement]:
        """Get elements filtered by type."""
        return [e for e in self.elements if e.element_type == element_type]
    
    def get_elements_in_file(self, file_path: str) -> List[CodeElement]:
        """Get elements in a specific file."""
        return [e for e in self.elements if e.file_path == file_path]
    
    def save_index(self, output_path: Path):
        """Save index to disk."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'project_root': str(self.project_root),
            'element_count': len(self.elements),
            'elements': [e.to_dict() for e in self.elements],
            'file_hashes': self.file_hashes,
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved index to {output_path}")
    
    def load_index(self, input_path: Path):
        """Load index from disk."""
        with open(input_path, 'r') as f:
            data = json.load(f)
        
        # Note: We only load metadata, not full elements
        # Full elements need to be re-indexed
        self.file_hashes = data.get('file_hashes', {})
        
        logger.info(f"Loaded index metadata from {input_path}")
