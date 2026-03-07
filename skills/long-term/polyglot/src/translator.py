"""
Polyglot Translator: Translates code between programming languages.
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Language(Enum):
    """Supported programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    RUST = "rust"
    GO = "go"
    JAVA = "java"
    CPP = "cpp"
    C = "c"


@dataclass
class TranslationRequest:
    """Request for code translation."""
    source_code: str
    source_language: Language
    target_language: Language
    preserve_comments: bool = True
    preserve_docstrings: bool = True
    target_style: Optional[str] = None  # e.g., "idiomatic", "literal"
    context: Optional[Dict[str, Any]] = None


@dataclass
class TranslationResult:
    """Result of code translation."""
    target_code: str
    source_language: Language
    target_language: Language
    warnings: List[str] = field(default_factory=list)
    info: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    confidence: float = 1.0
    partial_translation: bool = False


class PolyglotTranslator:
    """
    Translates code between programming languages while preserving semantics.
    """
    
    # Type mappings between languages
    TYPE_MAPPINGS = {
        (Language.PYTHON, Language.JAVASCRIPT): {
            "int": "number",
            "float": "number",
            "str": "string",
            "bool": "boolean",
            "list": "Array",
            "dict": "Object",
            "set": "Set",
            "tuple": "Array",
            "None": "null",
            "Any": "any",
        },
        (Language.JAVASCRIPT, Language.PYTHON): {
            "number": "float",
            "string": "str",
            "boolean": "bool",
            "Array": "list",
            "Object": "dict",
            "null": "None",
            "undefined": "None",
            "any": "Any",
        },
        (Language.PYTHON, Language.RUST): {
            "int": "i64",
            "float": "f64",
            "str": "String",
            "bool": "bool",
            "list": "Vec",
            "dict": "HashMap",
            "None": "Option",
        },
        (Language.PYTHON, Language.GO): {
            "int": "int",
            "float": "float64",
            "str": "string",
            "bool": "bool",
            "list": "[]interface{}",
            "dict": "map[string]interface{}",
            "None": "nil",
        },
    }
    
    # Function mappings for common operations
    FUNCTION_MAPPINGS = {
        (Language.PYTHON, Language.JAVASCRIPT): {
            "print": "console.log",
            "len": "length",
            "range": "Array.from({length: n}, (_, i) => i)",
            "enumerate": "entries",
            "zip": "zip",
            "map": "map",
            "filter": "filter",
            "reduce": "reduce",
        },
        (Language.JAVASCRIPT, Language.PYTHON): {
            "console.log": "print",
            "console.error": "print",
            "JSON.parse": "json.loads",
            "JSON.stringify": "json.dumps",
            "Array.isArray": "isinstance(..., list)",
            "Object.keys": "list(...keys())",
            "Object.values": "list(...values())",
        },
        (Language.PYTHON, Language.RUST): {
            "print": "println!",
            "len": "len",
            "range": "(0..n)",
            "list.append": "vec.push",
            "dict.get": "HashMap.get",
        },
        (Language.PYTHON, Language.GO): {
            "print": "fmt.Println",
            "len": "len",
            "range": "for i := 0; i < n; i++",
            "list.append": "append",
        },
    }
    
    # Control flow mappings
    CONTROL_FLOW_MAPPINGS = {
        (Language.PYTHON, Language.JAVASCRIPT): {
            "and": "&&",
            "or": "||",
            "not": "!",
            "True": "true",
            "False": "false",
            "is None": "=== null",
            "is not None": "!== null",
            "in": ".includes",
        },
        (Language.JAVASCRIPT, Language.PYTHON): {
            "===": "==",
            "!==": "!=",
            "&&": "and",
            "||": "or",
            "!": "not",
            "true": "True",
            "false": "False",
        },
    }
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self._load_translation_patterns()
    
    def _load_translation_patterns(self):
        """Load language-specific translation patterns."""
        self.patterns = {
            "python_to_javascript": PythonToJavaScriptPatterns(),
            "javascript_to_python": JavaScriptToPythonPatterns(),
            "python_to_rust": PythonToRustPatterns(),
            "python_to_go": PythonToGoPatterns(),
        }
    
    def translate(self, request: TranslationRequest) -> TranslationResult:
        """
        Translate code from source to target language.
        
        Args:
            request: TranslationRequest with source code and languages
            
        Returns:
            TranslationResult with translated code
        """
        warnings = []
        info = []
        
        # Get appropriate pattern handler
        pattern_key = f"{request.source_language.value}_to_{request.target_language.value}"
        patterns = self.patterns.get(pattern_key)
        
        if patterns:
            result = patterns.translate(request)
        else:
            # Generic translation using rule-based approach
            result = self._generic_translate(request)
            warnings.append(f"Using generic translation - {request.source_language.value} to {request.target_language.value} may need manual review")
        
        # Get dependencies for target language
        dependencies = self._get_dependencies(request.target_language, result.target_code)
        
        return TranslationResult(
            target_code=result.target_code,
            source_language=request.source_language,
            target_language=request.target_language,
            warnings=result.warnings + warnings,
            info=result.info + info,
            dependencies=dependencies,
            confidence=result.confidence,
            partial_translation=result.partial_translation,
        )
    
    def translate_file(
        self, 
        source_path: Path, 
        target_path: Path,
        target_language: Language
    ) -> TranslationResult:
        """Translate a file and save to target path."""
        source_code = source_path.read_text()
        source_language = self._detect_language(source_path.suffix)
        
        request = TranslationRequest(
            source_code=source_code,
            source_language=source_language,
            target_language=target_language,
        )
        
        result = self.translate(request)
        target_path.write_text(result.target_code)
        
        return result
    
    def batch_translate(
        self,
        files: List[Tuple[Path, Path]],
        target_language: Language
    ) -> Dict[str, TranslationResult]:
        """Translate multiple files."""
        results = {}
        for source_path, target_path in files:
            result = self.translate_file(source_path, target_path, target_language)
            results[str(source_path)] = result
        return results
    
    def _generic_translate(self, request: TranslationRequest) -> TranslationResult:
        """Generic rule-based translation."""
        code = request.source_code
        warnings = []
        
        # Apply type mappings
        type_map = self.TYPE_MAPPINGS.get(
            (request.source_language, request.target_language), 
            {}
        )
        
        for source_type, target_type in type_map.items():
            # Simple word replacement (very naive)
            code = re.sub(r'\b' + re.escape(source_type) + r'\b', target_type, code)
        
        # Apply function mappings
        func_map = self.FUNCTION_MAPPINGS.get(
            (request.source_language, request.target_language),
            {}
        )
        
        for source_func, target_func in func_map.items():
            code = re.sub(r'\b' + re.escape(source_func) + r'\b', target_func, code)
        
        # Apply control flow mappings
        flow_map = self.CONTROL_FLOW_MAPPINGS.get(
            (request.source_language, request.target_language),
            {}
        )
        
        for source_flow, target_flow in flow_map.items():
            code = code.replace(source_flow, target_flow)
        
        warnings.append("Generic translation used - manual review required")
        
        return TranslationResult(
            target_code=code,
            source_language=request.source_language,
            target_language=request.target_language,
            warnings=warnings,
            info=["Used generic rule-based translation"],
            confidence=0.5,
            partial_translation=True,
        )
    
    def _get_dependencies(self, language: Language, code: str) -> List[str]:
        """Extract dependencies for the target language."""
        deps = {
            Language.PYTHON: [],
            Language.JAVASCRIPT: [],
            Language.TYPESCRIPT: ["typescript"],
            Language.RUST: [],
            Language.GO: [],
        }
        
        # Check for specific imports
        if language == Language.PYTHON:
            if "import json" in code or "json." in code:
                deps[Language.PYTHON].append("json")
            if "requests" in code:
                deps[Language.PYTHON].append("requests")
            if "datetime" in code:
                deps[Language.PYTHON].append("datetime")
        
        elif language == Language.JAVASCRIPT:
            if "fetch(" in code:
                deps[Language.JAVASCRIPT].append("node-fetch")
        
        elif language == Language.RUST:
            if "HashMap" in code:
                deps[Language.RUST].extend(["use std::collections::HashMap"])
            if "println!" in code:
                deps[Language.RUST].append("standard library")
        
        return deps.get(language, [])
    
    def _detect_language(self, extension: str) -> Language:
        """Detect language from file extension."""
        mapping = {
            ".py": Language.PYTHON,
            ".js": Language.JAVASCRIPT,
            ".jsx": Language.JAVASCRIPT,
            ".ts": Language.TYPESCRIPT,
            ".tsx": Language.TYPESCRIPT,
            ".rs": Language.RUST,
            ".go": Language.GO,
            ".java": Language.JAVA,
            ".cpp": Language.CPP,
            ".c": Language.C,
        }
        return mapping.get(extension, Language.PYTHON)


class TranslationPatterns:
    """Base class for language-specific translation patterns."""
    
    def translate(self, request: TranslationRequest) -> TranslationResult:
        raise NotImplementedError


class PythonToJavaScriptPatterns(TranslationPatterns):
    """Python to JavaScript translation patterns."""
    
    def translate(self, request: TranslationRequest) -> TranslationResult:
        code = request.source_code
        warnings = []
        info = []
        
        # Handle function definitions
        code = self._translate_functions(code)
        
        # Handle list/dict comprehensions
        code = self._translate_comprehensions(code)
        
        # Handle classes
        code = self._translate_classes(code)
        
        # Handle imports
        code = self._translate_imports(code)
        
        # Handle exception handling
        code = self._translate_exceptions(code)
        
        # Handle f-strings
        code = self._translate_fstrings(code)
        
        # Handle list operations
        code = self._translate_list_operations(code)
        
        # Handle dict operations
        code = self._translate_dict_operations(code)
        
        # Handle decorators
        code = self._translate_decorators(code)
        
        # Handle type hints
        code = self._translate_type_hints(code)
        
        return TranslationResult(
            target_code=code,
            source_language=Language.PYTHON,
            target_language=Language.JAVASCRIPT,
            warnings=warnings,
            info=info,
            confidence=0.85,
        )
    
    def _translate_functions(self, code: str) -> str:
        """Translate Python function definitions."""
        # def name(args): -> function name(args) {
        pattern = r'def\s+(\w+)\s*\((.*?)\)(?:\s*->\s*(\w+))?:'
        
        def replacer(match):
            name = match.group(1)
            args = match.group(2)
            return_type = match.group(3)
            
            # Clean up args (remove type hints for now)
            clean_args = re.sub(r':\s*\w+', '', args)
            
            result = f"function {name}({clean_args}) {"
            if return_type:
                result = f"// Returns: {return_type}\n" + result
            return result
        
        return re.sub(pattern, replacer, code)
    
    def _translate_comprehensions(self, code: str) -> str:
        """Translate list/dict comprehensions."""
        # [x for x in y] -> y.map(x => x)
        # {k: v for k, v in d.items()} -> Object.fromEntries(Object.entries(d).map(...))
        
        # Simple list comprehension
        pattern = r'\[(.+?)\s+for\s+(\w+)\s+in\s+(.+?)\]'
        code = re.sub(pattern, r'\3.map(\2 => \1)', code)
        
        return code
    
    def _translate_classes(self, code: str) -> str:
        """Translate Python classes to JavaScript."""
        # class Name: -> class Name {
        pattern = r'class\s+(\w+)(?:\((.*?)\))?:'
        
        def replacer(match):
            name = match.group(1)
            parent = match.group(2)
            if parent:
                return f"class {name} extends {parent} {"
            return f"class {name} {"
        
        return re.sub(pattern, replacer, code)
    
    def _translate_imports(self, code: str) -> str:
        """Translate Python imports to JavaScript."""
        # import x -> const x = require('x');
        # from x import y -> const { y } = require('x');
        
        # Handle 'import x'
        code = re.sub(r'^import\s+(\w+)', r"const \1 = require('\1');", code, flags=re.MULTILINE)
        
        # Handle 'from x import y'
        code = re.sub(
            r'from\s+(\w+)\s+import\s+(.+)', 
            r"const { \2 } = require('\1');", 
            code
        )
        
        return code
    
    def _translate_exceptions(self, code: str) -> str:
        """Translate Python exception handling."""
        # try: -> try {
        # except Exception as e: -> catch (e) {
        # finally: -> finally {
        
        code = code.replace('try:', 'try {')
        code = re.sub(r'except\s+(\w+)?(?:\s+as\s+(\w+))?:', r'catch (\2) {', code)
        code = code.replace('finally:', 'finally {')
        
        return code
    
    def _translate_fstrings(self, code: str) -> str:
        """Translate f-strings to template literals."""
        # f"hello {name}" -> `hello ${name}`
        pattern = r'f["\'](.+?)["\']'
        
        def replacer(match):
            content = match.group(1)
            # Replace {var} with ${var}
            content = re.sub(r'\{(\w+)\}', r'${\1}', content)
            return f'`{content}`'
        
        return re.sub(pattern, replacer, code)
    
    def _translate_list_operations(self, code: str) -> str:
        """Translate Python list operations."""
        # .append(x) -> .push(x)
        code = code.replace('.append(', '.push(')
        
        # len(x) -> x.length
        code = re.sub(r'len\((\w+)\)', r'\1.length', code)
        
        # x[0] -> x[0] (same)
        # x[-1] -> x[x.length - 1]
        code = re.sub(r'(\w+)\[-1\]', r'\1[\1.length - 1]', code)
        
        return code
    
    def _translate_dict_operations(self, code: str) -> str:
        """Translate Python dict operations."""
        # d[key] -> d[key] or d.get(key)
        # d.get(key, default) -> d[key] ?? default
        code = re.sub(r'(\w+)\.get\(([^,]+),\s*([^)]+)\)', r'\1[\2] ?? \3', code)
        
        # key in d -> d.hasOwnProperty(key)
        code = re.sub(r'(\w+)\s+in\s+(\w+)', r'\2.hasOwnProperty(\1)', code)
        
        # d.keys() -> Object.keys(d)
        code = re.sub(r'(\w+)\.keys\(\)', r'Object.keys(\1)', code)
        
        # d.values() -> Object.values(d)
        code = re.sub(r'(\w+)\.values\(\)', r'Object.values(\1)', code)
        
        # d.items() -> Object.entries(d)
        code = re.sub(r'(\w+)\.items\(\)', r'Object.entries(\1)', code)
        
        return code
    
    def _translate_decorators(self, code: str) -> str:
        """Translate Python decorators."""
        warnings = ["Decorators may need manual adjustment in JavaScript"]
        
        # @decorator -> // @decorator (commented out)
        code = re.sub(r'^@(\w+)', r'// @\1', code, flags=re.MULTILINE)
        
        return code
    
    def _translate_type_hints(self, code: str) -> str:
        """Handle Python type hints (remove or convert)."""
        # Remove type hints for now
        code = re.sub(r':\s*\w+(\s*=)', r'\1', code)  # Variable annotations
        
        return code


class JavaScriptToPythonPatterns(TranslationPatterns):
    """JavaScript to Python translation patterns."""
    
    def translate(self, request: TranslationRequest) -> TranslationResult:
        code = request.source_code
        warnings = []
        info = []
        
        # Handle function definitions
        code = self._translate_functions(code)
        
        # Handle arrow functions
        code = self._translate_arrow_functions(code)
        
        # Handle const/let/var
        code = self._translate_declarations(code)
        
        # Handle object methods
        code = self._translate_object_methods(code)
        
        # Handle Promise/async
        code = self._translate_async(code)
        
        # Handle template literals
        code = self._translate_templates(code)
        
        # Handle array methods
        code = self._translate_array_methods(code)
        
        # Handle object operations
        code = self._translate_object_operations(code)
        
        # Handle imports
        code = self._translate_imports(code)
        
        return TranslationResult(
            target_code=code,
            source_language=Language.JAVASCRIPT,
            target_language=Language.PYTHON,
            warnings=warnings,
            info=info,
            confidence=0.85,
        )
    
    def _translate_functions(self, code: str) -> str:
        """Translate JavaScript functions."""
        # function name(args) { -> def name(args):
        pattern = r'function\s+(\w+)\s*\((.*?)\)\s*\{'
        
        def replacer(match):
            name = match.group(1)
            args = match.group(2)
            return f"def {name}({args}):"
        
        return re.sub(pattern, replacer, code)
    
    def _translate_arrow_functions(self, code: str) -> str:
        """Translate arrow functions to lambda."""
        # (x) => x * 2 -> lambda x: x * 2
        # (x) => { return x * 2; } -> lambda x: x * 2
        
        pattern = r'\((.*?)\)\s*=>\s*\{?\s*(?:return\s+)?(.+?);?\s*\}?'
        
        def replacer(match):
            args = match.group(1)
            body = match.group(2)
            return f"lambda {args}: {body}"
        
        return re.sub(pattern, replacer, code)
    
    def _translate_declarations(self, code: str) -> str:
        """Translate variable declarations."""
        # const x = -> x =
        # let x = -> x =
        # var x = -> x =
        
        code = re.sub(r'\b(?:const|let|var)\s+', '', code)
        
        return code
    
    def _translate_object_methods(self, code: str) -> str:
        """Translate object method definitions."""
        # method() { -> def method(self):
        warnings = ["Object methods converted to class methods"]
        
        return code
    
    def _translate_async(self, code: str) -> str:
        """Translate async/Promise code."""
        # async function -> async def
        code = re.sub(r'async\s+function', 'async def', code)
        
        # await -> await (same in Python 3.5+)
        # Promise -> asyncio
        
        return code
    
    def _translate_templates(self, code: str) -> str:
        """Translate template literals to f-strings."""
        # `hello ${name}` -> f"hello {name}"
        pattern = r'`(.+?)`'
        
        def replacer(match):
            content = match.group(1)
            # Replace ${var} with {var}
            content = re.sub(r'\$\{(\w+)\}', r'{\1}', content)
            return f'f"{content}"'
        
        return re.sub(pattern, replacer, code)
    
    def _translate_array_methods(self, code: str) -> str:
        """Translate array methods."""
        # .map(x => ...) -> [ ... for x in ... ]
        # .filter(x => ...) -> [ x for x in ... if ... ]
        # .reduce(...) -> functools.reduce(...)
        
        pattern = r'(\w+)\.map\((.+?)\s*=>\s*(.+?)\)'
        code = re.sub(pattern, r'[\3 for \2 in \1]', code)
        
        pattern = r'(\w+)\.filter\((.+?)\s*=>\s*(.+?)\)'
        code = re.sub(pattern, r'[\2 for \2 in \1 if \3]', code)
        
        return code
    
    def _translate_object_operations(self, code: str) -> str:
        """Translate object operations."""
        # Object.keys(obj) -> list(obj.keys())
        code = re.sub(r'Object\.keys\((\w+)\)', r'list(\1.keys())', code)
        
        # Object.values(obj) -> list(obj.values())
        code = re.sub(r'Object\.values\((\w+)\)', r'list(\1.values())', code)
        
        # Object.entries(obj) -> list(obj.items())
        code = re.sub(r'Object\.entries\((\w+)\)', r'list(\1.items())', code)
        
        # obj.hasOwnProperty(key) -> key in obj
        code = re.sub(r'(\w+)\.hasOwnProperty\((\w+)\)', r'\2 in \1', code)
        
        return code
    
    def _translate_imports(self, code: str) -> str:
        """Translate JavaScript imports."""
        # const x = require('x') -> import x
        code = re.sub(r"const\s+(\w+)\s+=\s+require\(['\"](.+?)['\"]\);?", r'import \1', code)
        
        # const { a, b } = require('x') -> from x import a, b
        code = re.sub(r"const\s*\{\s*(.+?)\s*\}\s*=\s+require\(['\"](.+?)['\"]\);?", 
                      r'from \2 import \1', code)
        
        return code


class PythonToRustPatterns(TranslationPatterns):
    """Python to Rust translation patterns."""
    
    def translate(self, request: TranslationRequest) -> TranslationResult:
        code = request.source_code
        warnings = ["Rust translation requires manual review for ownership"]
        info = []
        
        # Handle function definitions
        code = self._translate_functions(code)
        
        # Handle variable declarations
        code = self._translate_variables(code)
        
        # Handle ownership patterns
        code = self._translate_ownership(code)
        
        # Handle error handling
        code = self._translate_errors(code)
        
        return TranslationResult(
            target_code=code,
            source_language=Language.PYTHON,
            target_language=Language.RUST,
            warnings=warnings,
            info=info,
            confidence=0.7,
        )
    
    def _translate_functions(self, code: str) -> str:
        """Translate Python functions to Rust."""
        # def name(args) -> ret: -> fn name(args) -> ret {
        pattern = r'def\s+(\w+)\s*\((.*?)\)(?:\s*->\s*(\w+))?:'
        
        def replacer(match):
            name = match.group(1)
            args = match.group(2)
            ret_type = match.group(3)
            
            # Convert args (simplified)
            rust_args = self._convert_args_to_rust(args)
            
            result = f"fn {name}({rust_args})"
            if ret_type:
                rust_ret = self._convert_type_to_rust(ret_type)
                result += f" -> {rust_ret}"
            result += " {"
            
            return result
        
        return re.sub(pattern, replacer, code)
    
    def _convert_args_to_rust(self, args: str) -> str:
        """Convert Python args to Rust args."""
        if not args:
            return ""
        
        rust_args = []
        for arg in args.split(','):
            arg = arg.strip()
            if ':' in arg:
                name, type_ = arg.split(':', 1)
                rust_type = self._convert_type_to_rust(type_.strip())
                rust_args.append(f"{name.strip()}: {rust_type}")
            else:
                rust_args.append(f"{arg}: i32")  # Default type
        
        return ", ".join(rust_args)
    
    def _convert_type_to_rust(self, py_type: str) -> str:
        """Convert Python type to Rust type."""
        type_map = {
            "int": "i64",
            "float": "f64",
            "str": "String",
            "bool": "bool",
            "list": "Vec",
            "dict": "HashMap<String, ",
        }
        return type_map.get(py_type.strip(), py_type)
    
    def _translate_variables(self, code: str) -> str:
        """Translate variable declarations."""
        # x = value -> let x = value;
        pattern = r'^(\w+)\s*=\s*(.+)$'
        
        def replacer(match):
            name = match.group(1)
            value = match.group(2)
            return f"let {name} = {value};"
        
        return re.sub(pattern, replacer, code, flags=re.MULTILINE)
    
    def _translate_ownership(self, code: str) -> str:
        """Add ownership annotations."""
        # This is complex - simplified version
        return code
    
    def _translate_errors(self, code: str) -> str:
        """Translate Python exceptions to Rust Results."""
        # try: -> match operation {
        # except -> Err(e) =>
        
        return code


class PythonToGoPatterns(TranslationPatterns):
    """Python to Go translation patterns."""
    
    def translate(self, request: TranslationRequest) -> TranslationResult:
        code = request.source_code
        warnings = ["Go translation requires manual review"]
        info = []
        
        # Handle function definitions
        code = self._translate_functions(code)
        
        # Handle variable declarations
        code = self._translate_variables(code)
        
        # Handle error handling
        code = self._translate_errors(code)
        
        # Add package declaration
        code = "package main\n\n" + code
        
        return TranslationResult(
            target_code=code,
            source_language=Language.PYTHON,
            target_language=Language.GO,
            warnings=warnings,
            info=info,
            confidence=0.7,
        )
    
    def _translate_functions(self, code: str) -> str:
        """Translate Python functions to Go."""
        # def name(args): -> func name(args) ret {
        pattern = r'def\s+(\w+)\s*\((.*?)\)(?:\s*->\s*(\w+))?:'
        
        def replacer(match):
            name = match.group(1)
            args = match.group(2)
            ret_type = match.group(3)
            
            go_args = self._convert_args_to_go(args)
            
            result = f"func {name}({go_args})"
            if ret_type:
                go_ret = self._convert_type_to_go(ret_type)
                result += f" {go_ret}"
            result += " {"
            
            return result
        
        return re.sub(pattern, replacer, code)
    
    def _convert_args_to_go(self, args: str) -> str:
        """Convert Python args to Go args."""
        if not args:
            return ""
        
        go_args = []
        for arg in args.split(','):
            arg = arg.strip()
            if ':' in arg:
                name, type_ = arg.split(':', 1)
                go_type = self._convert_type_to_go(type_.strip())
                go_args.append(f"{name.strip()} {go_type}")
            else:
                go_args.append(f"{arg} interface{{}}")
        
        return ", ".join(go_args)
    
    def _convert_type_to_go(self, py_type: str) -> str:
        """Convert Python type to Go type."""
        type_map = {
            "int": "int",
            "float": "float64",
            "str": "string",
            "bool": "bool",
            "list": "[]interface{}",
            "dict": "map[string]interface{}",
        }
        return type_map.get(py_type.strip(), "interface{}")
    
    def _translate_variables(self, code: str) -> str:
        """Translate variable declarations."""
        # x = value -> x := value
        pattern = r'^(\w+)\s*=\s*(.+)$'
        
        def replacer(match):
            name = match.group(1)
            value = match.group(2)
            return f"{name} := {value}"
        
        return re.sub(pattern, replacer, code, flags=re.MULTILINE)
    
    def _translate_errors(self, code: str) -> str:
        """Translate Python exceptions to Go error handling."""
        # try: -> result, err := operation()
        #        if err != nil { ... }
        
        return code
