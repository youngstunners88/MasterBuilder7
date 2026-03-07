"""
Code Synthesizer: Converts natural language to complete code implementations.
"""

import os
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

from .template_engine import TemplateEngine
from .validator import CodeValidator


@dataclass
class SynthesisRequest:
    """Request for code synthesis."""
    description: str
    language: str = "python"
    framework: Optional[str] = None
    include_tests: bool = True
    include_auth: bool = False
    include_validation: bool = True
    target_directory: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


@dataclass
class SynthesisResult:
    """Result of code synthesis."""
    files: Dict[str, str]
    tests: Dict[str, str]
    dependencies: List[str]
    setup_instructions: List[str]
    validation_results: Dict[str, Any]
    estimated_complexity: str


class CodeSynthesizer:
    """
    Main synthesizer that converts natural language to code.
    """
    
    FRAMEWORK_PATTERNS = {
        "fastapi": {
            "patterns": ["api", "endpoint", "fastapi", "rest", "backend"],
            "dependencies": ["fastapi", "uvicorn", "pydantic"],
        },
        "react": {
            "patterns": ["react", "frontend", "component", "ui", "jsx"],
            "dependencies": ["react", "react-dom", "@types/react"],
        },
        "node": {
            "patterns": ["node", "express", "backend", "javascript"],
            "dependencies": ["express", "cors", "dotenv"],
        },
        "django": {
            "patterns": ["django", "python web"],
            "dependencies": ["django", "djangorestframework"],
        },
        "flask": {
            "patterns": ["flask", "python api"],
            "dependencies": ["flask", "flask-restful"],
        },
    }
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.template_engine = TemplateEngine()
        self.validator = CodeValidator()
        
    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        """
        Main entry point for code synthesis.
        
        Args:
            request: SynthesisRequest with description and options
            
        Returns:
            SynthesisResult with all generated files
        """
        # Detect framework if not specified
        if not request.framework:
            request.framework = self._detect_framework(request.description)
            
        # Parse requirements from description
        requirements = self._parse_requirements(request.description)
        
        # Generate architecture
        architecture = self._generate_architecture(requirements, request)
        
        # Generate code files
        files = self._generate_files(architecture, request)
        
        # Generate tests
        tests = {}
        if request.include_tests:
            tests = self._generate_tests(files, request)
            
        # Validate generated code
        validation_results = self.validator.validate_files(files, request.language)
        
        # Extract dependencies
        dependencies = self._extract_dependencies(files, request)
        
        # Generate setup instructions
        setup_instructions = self._generate_setup_instructions(request, dependencies)
        
        # Estimate complexity
        complexity = self._estimate_complexity(files)
        
        return SynthesisResult(
            files=files,
            tests=tests,
            dependencies=dependencies,
            setup_instructions=setup_instructions,
            validation_results=validation_results,
            estimated_complexity=complexity
        )
    
    def _detect_framework(self, description: str) -> Optional[str]:
        """Detect framework from description."""
        desc_lower = description.lower()
        
        for framework, config in self.FRAMEWORK_PATTERNS.items():
            for pattern in config["patterns"]:
                if pattern in desc_lower:
                    return framework
        return None
    
    def _parse_requirements(self, description: str) -> Dict[str, Any]:
        """Parse requirements from natural language description."""
        requirements = {
            "entities": [],
            "operations": [],
            "auth_required": False,
            "validation_rules": [],
            "endpoints": [],
            "database_entities": [],
        }
        
        desc_lower = description.lower()
        
        # Detect authentication requirement
        auth_keywords = ["login", "auth", "authenticate", "sign in", "jwt", "token"]
        requirements["auth_required"] = any(kw in desc_lower for kw in auth_keywords)
        
        # Detect CRUD operations
        crud_patterns = {
            "create": ["create", "add", "new", "register"],
            "read": ["get", "fetch", "retrieve", "list", "view"],
            "update": ["update", "edit", "modify", "change"],
            "delete": ["delete", "remove", "destroy"],
        }
        
        for operation, patterns in crud_patterns.items():
            if any(p in desc_lower for p in patterns):
                requirements["operations"].append(operation)
        
        # Extract entities using simple heuristics
        entity_patterns = [
            r'(?:for|of|manage|handle)\s+(\w+)s?\s',
            r'(\w+)\s+(?:model|entity|table|collection)',
            r'create\s+(?:a|an)\s+(\w+)',
        ]
        
        for pattern in entity_patterns:
            matches = re.findall(pattern, desc_lower)
            requirements["entities"].extend(matches)
        
        requirements["entities"] = list(set(requirements["entities"]))
        
        return requirements
    
    def _generate_architecture(
        self, 
        requirements: Dict[str, Any], 
        request: SynthesisRequest
    ) -> Dict[str, Any]:
        """Generate system architecture based on requirements."""
        architecture = {
            "modules": [],
            "routes": [],
            "models": [],
            "services": [],
        }
        
        # Generate models based on entities
        for entity in requirements["entities"]:
            architecture["models"].append({
                "name": entity.capitalize(),
                "fields": self._infer_fields(entity),
            })
        
        # Generate routes based on operations
        if request.framework in ["fastapi", "flask", "django"]:
            for entity in requirements["entities"]:
                for op in requirements["operations"]:
                    route = self._generate_route_spec(entity, op, requirements["auth_required"])
                    architecture["routes"].append(route)
        
        # Generate service layer
        for entity in requirements["entities"]:
            architecture["services"].append({
                "name": f"{entity.capitalize()}Service",
                "entity": entity.capitalize(),
            })
        
        return architecture
    
    def _infer_fields(self, entity: str) -> List[Dict[str, str]]:
        """Infer fields for an entity based on common patterns."""
        common_fields = {
            "user": [
                {"name": "id", "type": "str", "primary": True},
                {"name": "email", "type": "str", "required": True},
                {"name": "password_hash", "type": "str", "required": True},
                {"name": "created_at", "type": "datetime", "auto": True},
                {"name": "is_active", "type": "bool", "default": True},
            ],
            "product": [
                {"name": "id", "type": "str", "primary": True},
                {"name": "name", "type": "str", "required": True},
                {"name": "description", "type": "str"},
                {"name": "price", "type": "float", "required": True},
                {"name": "stock", "type": "int", "default": 0},
            ],
            "order": [
                {"name": "id", "type": "str", "primary": True},
                {"name": "user_id", "type": "str", "required": True},
                {"name": "total", "type": "float", "required": True},
                {"name": "status", "type": "str", "default": "pending"},
                {"name": "created_at", "type": "datetime", "auto": True},
            ],
        }
        
        entity_lower = entity.lower()
        if entity_lower in common_fields:
            return common_fields[entity_lower]
        
        # Default fields for unknown entities
        return [
            {"name": "id", "type": "str", "primary": True},
            {"name": "name", "type": "str", "required": True},
            {"name": "created_at", "type": "datetime", "auto": True},
        ]
    
    def _generate_route_spec(
        self, 
        entity: str, 
        operation: str,
        auth_required: bool
    ) -> Dict[str, Any]:
        """Generate route specification."""
        route_specs = {
            "create": {
                "method": "POST",
                "path": f"/api/v1/{entity.lower()}s",
                "handler": f"create_{entity.lower()}",
            },
            "read": {
                "method": "GET",
                "path": f"/api/v1/{entity.lower()}s/{{id}}",
                "handler": f"get_{entity.lower()}",
            },
            "update": {
                "method": "PUT",
                "path": f"/api/v1/{entity.lower()}s/{{id}}",
                "handler": f"update_{entity.lower()}",
            },
            "delete": {
                "method": "DELETE",
                "path": f"/api/v1/{entity.lower()}s/{{id}}",
                "handler": f"delete_{entity.lower()}",
            },
        }
        
        spec = route_specs.get(operation, route_specs["read"])
        spec["auth"] = auth_required
        spec["entity"] = entity
        return spec
    
    def _generate_files(
        self, 
        architecture: Dict[str, Any], 
        request: SynthesisRequest
    ) -> Dict[str, str]:
        """Generate all code files."""
        files = {}
        
        if request.framework == "fastapi":
            files.update(self._generate_fastapi_files(architecture, request))
        elif request.framework == "react":
            files.update(self._generate_react_files(architecture, request))
        elif request.framework == "node":
            files.update(self._generate_node_files(architecture, request))
        elif request.framework == "flask":
            files.update(self._generate_flask_files(architecture, request))
        else:
            files.update(self._generate_generic_python_files(architecture, request))
        
        return files
    
    def _generate_fastapi_files(
        self, 
        architecture: Dict[str, Any], 
        request: SynthesisRequest
    ) -> Dict[str, str]:
        """Generate FastAPI project files."""
        files = {}
        
        # Generate models
        models_code = ["from pydantic import BaseModel, Field", "from datetime import datetime", "from typing import Optional", ""]
        for model in architecture["models"]:
            models_code.append(f"class {model['name']}(BaseModel):")
            models_code.append(f'    """{model["name"]} model."""')
            for field in model["fields"]:
                field_type = field["type"]
                if field_type == "datetime":
                    field_type = "datetime"
                default = ""
                if "default" in field:
                    default = f" = {field['default']}"
                elif not field.get("required", False):
                    default = " = None"
                    field_type = f"Optional[{field_type}]"
                models_code.append(f"    {field['name']}: {field_type}{default}")
            models_code.append("")
        
        files["models.py"] = "\n".join(models_code)
        
        # Generate routes
        routes_code = [
            "from fastapi import APIRouter, HTTPException, Depends",
            "from typing import List",
            "from .models import *",
            "",
            "router = APIRouter()",
            "",
        ]
        
        for route in architecture["routes"]:
            method = route["method"]
            path = route["path"]
            handler = route["handler"]
            entity = route["entity"]
            
            if method == "POST":
                routes_code.append(f"@router.post('{path}')")
                routes_code.append(f"async def {handler}(data: {entity}Create):")
                routes_code.append(f'    """Create a new {entity.lower()}."""')
                routes_code.append(f"    # TODO: Implement creation logic")
                routes_code.append(f"    return {{'message': '{entity} created'}}")
                routes_code.append("")
            elif method == "GET":
                routes_code.append(f"@router.get('{path}')")
                routes_code.append(f"async def {handler}(id: str):")
                routes_code.append(f'    """Get {entity.lower()} by ID."""')
                routes_code.append(f"    # TODO: Implement retrieval logic")
                routes_code.append(f"    return {{'id': id}}")
                routes_code.append("")
            elif method == "PUT":
                routes_code.append(f"@router.put('{path}')")
                routes_code.append(f"async def {handler}(id: str, data: {entity}Update):")
                routes_code.append(f'    """Update {entity.lower()}."""')
                routes_code.append(f"    # TODO: Implement update logic")
                routes_code.append(f"    return {{'message': '{entity} updated'}}")
                routes_code.append("")
            elif method == "DELETE":
                routes_code.append(f"@router.delete('{path}')")
                routes_code.append(f"async def {handler}(id: str):")
                routes_code.append(f'    """Delete {entity.lower()}."""')
                routes_code.append(f"    # TODO: Implement deletion logic")
                routes_code.append(f"    return {{'message': '{entity} deleted'}}")
                routes_code.append("")
        
        files["routes.py"] = "\n".join(routes_code)
        
        # Generate main app
        main_code = [
            "from fastapi import FastAPI",
            "from fastapi.middleware.cors import CORSMiddleware",
            "from .routes import router",
            "",
            "app = FastAPI(title='API', version='1.0.0')",
            "",
            "app.add_middleware(",
            "    CORSMiddleware,",
            "    allow_origins=['*'],",
            "    allow_credentials=True,",
            "    allow_methods=['*'],",
            "    allow_headers=['*'],",
            ")",
            "",
            "app.include_router(router, prefix='/api/v1')",
            "",
            "@app.get('/health')",
            "async def health_check():",
            "    return {'status': 'healthy'}",
        ]
        files["main.py"] = "\n".join(main_code)
        
        # Generate auth if required
        if request.include_auth:
            auth_code = [
                "from fastapi import Depends, HTTPException, status",
                "from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials",
                "from jose import JWTError, jwt",
                "from passlib.context import CryptContext",
                "",
                "SECRET_KEY = 'your-secret-key'  # Change in production",
                "ALGORITHM = 'HS256'",
                "",
                "pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')",
                "security = HTTPBearer()",
                "",
                "def verify_password(plain_password, hashed_password):",
                "    return pwd_context.verify(plain_password, hashed_password)",
                "",
                "def get_password_hash(password):",
                "    return pwd_context.hash(password)",
                "",
                "async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):",
                "    token = credentials.credentials",
                "    try:",
                "        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])",
                "        user_id: str = payload.get('sub')",
                "        if user_id is None:",
                "            raise HTTPException(status_code=401, detail='Invalid token')",
                "        return user_id",
                "    except JWTError:",
                "        raise HTTPException(status_code=401, detail='Invalid token')",
            ]
            files["auth.py"] = "\n".join(auth_code)
        
        # Generate requirements
        req_lines = ["fastapi>=0.100.0", "uvicorn[standard]>=0.23.0", "pydantic>=2.0.0"]
        if request.include_auth:
            req_lines.extend(["python-jose[cryptography]>=3.3.0", "passlib[bcrypt]>=1.7.4"])
        files["requirements.txt"] = "\n".join(req_lines)
        
        return files
    
    def _generate_react_files(
        self, 
        architecture: Dict[str, Any], 
        request: SynthesisRequest
    ) -> Dict[str, str]:
        """Generate React project files."""
        files = {}
        
        # Generate components
        for model in architecture["models"]:
            component_name = model["name"]
            fields = model["fields"]
            
            component_code = [
                "import React, { useState, useEffect } from 'react';",
                "import './styles.css';",
                "",
                f"const {component_name}Component = () => {{",
                f"  const [{component_name.lower()}, set{component_name}] = useState(null);",
                f"  const [loading, setLoading] = useState(false);",
                f"  const [error, setError] = useState(null);",
                "",
                "  // TODO: Implement data fetching",
                "  useEffect(() => {",
                "    // fetchData();",
                "  }, []);",
                "",
                f"  return (",
                f"    <div className=\"{component_name.lower()}-container\">",
                f"      <h2>{component_name}</h2>",
                f"      {{loading && <p>Loading...</p>}}",
                f"      {{error && <p className=\"error\">{{error}}</p>}}",
                f"      <div className=\"{component_name.lower()}-content\">",
                f"        {{/* Render {component_name} data here */}}",
                f"      </div>",
                f"    </div>",
                f"  );",
                f"}};",
                "",
                f"export default {component_name}Component;",
            ]
            files[f"components/{component_name}.jsx"] = "\n".join(component_code)
        
        # Generate App.jsx
        imports = [f"import {m['name']} from './components/{m['name']}';" for m in architecture["models"]]
        app_code = [
            "import React from 'react';",
        ] + imports + [
            "",
            "function App() {",
            "  return (",
            "    <div className=\"App\">",
            "      <header className=\"App-header\">",
            "        <h1>Application</h1>",
            "      </header>",
            "      <main>",
        ]
        
        for model in architecture["models"]:
            app_code.append(f"        <{model['name']} />")
        
        app_code.extend([
            "      </main>",
            "    </div>",
            "  );",
            "}",
            "",
            "export default App;",
        ])
        
        files["App.jsx"] = "\n".join(app_code)
        
        # Generate package.json
        package_json = """{
  "name": "app",
  "version": "1.0.0",
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test"
  },
  "browserslist": {
    "production": [">0.2%", "not dead", "not op_mini all"],
    "development": ["last 1 chrome version", "last 1 firefox version", "last 1 safari version"]
  }
}"""
        files["package.json"] = package_json
        
        return files
    
    def _generate_node_files(
        self, 
        architecture: Dict[str, Any], 
        request: SynthesisRequest
    ) -> Dict[str, str]:
        """Generate Node.js/Express project files."""
        files = {}
        
        # Generate models
        for model in architecture["models"]:
            model_code = [
                "const mongoose = require('mongoose');",
                "",
                f"const {model['name']}Schema = new mongoose.Schema({{",
            ]
            for field in model["fields"]:
                field_type = "String"
                if field["type"] == "int":
                    field_type = "Number"
                elif field["type"] == "bool":
                    field_type = "Boolean"
                elif field["type"] == "datetime":
                    field_type = "Date"
                
                default_val = ""
                if "default" in field:
                    default_val = f", default: {field['default']}"
                
                model_code.append(f"  {field['name']}: {{ type: {field_type}{default_val} }}")
            
            model_code.extend([
                "}, { timestamps: true });",
                "",
                f"module.exports = mongoose.model('{model['name']}', {model['name']}Schema);",
            ])
            files[f"models/{model['name']}.js"] = "\n".join(model_code)
        
        # Generate routes
        routes_code = [
            "const express = require('express');",
            "const router = express.Router();",
            "",
        ]
        
        for route in architecture["routes"]:
            method = route["method"].lower()
            path = route["path"].replace("{", ":").replace("}", "")
            handler = route["handler"]
            entity = route["entity"]
            
            routes_code.append(f"// {route['method']} {path}")
            routes_code.append(f"router.{method}('{path}', async (req, res) => {{")
            routes_code.append(f"  try {{")
            routes_code.append(f"    // TODO: Implement {handler}")
            routes_code.append(f"    res.json({{ message: '{entity} operation successful' }});")
            routes_code.append(f"  }} catch (error) {{")
            routes_code.append(f"    res.status(500).json({{ error: error.message }});")
            routes_code.append(f"  }}")
            routes_code.append(f"}});")
            routes_code.append("")
        
        routes_code.append("module.exports = router;")
        files["routes.js"] = "\n".join(routes_code)
        
        # Generate app.js
        app_code = [
            "const express = require('express');",
            "const cors = require('cors');",
            "const mongoose = require('mongoose');",
            "const routes = require('./routes');",
            "",
            "const app = express();",
            "const PORT = process.env.PORT || 3000;",
            "",
            "app.use(cors());",
            "app.use(express.json());",
            "",
            "// Routes",
            "app.use('/api/v1', routes);",
            "",
            "// Health check",
            "app.get('/health', (req, res) => {",
            "  res.json({ status: 'healthy' });",
            "});",
            "",
            "// Error handling",
            "app.use((err, req, res, next) => {",
            "  console.error(err.stack);",
            "  res.status(500).json({ error: 'Something went wrong!' });",
            "});",
            "",
            "// Database connection",
            "mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/app', {",
            "  useNewUrlParser: true,",
            "  useUnifiedTopology: true,",
            "});",
            "",
            "app.listen(PORT, () => {",
            "  console.log(`Server running on port ${PORT}`);",
            "});",
            "",
            "module.exports = app;",
        ]
        files["app.js"] = "\n".join(app_code)
        
        # Generate package.json
        package_json = """{
  "name": "app",
  "version": "1.0.0",
  "main": "app.js",
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5",
    "mongoose": "^7.5.0",
    "dotenv": "^16.3.1"
  },
  "scripts": {
    "start": "node app.js",
    "dev": "nodemon app.js"
  }
}"""
        files["package.json"] = package_json
        
        return files
    
    def _generate_flask_files(
        self, 
        architecture: Dict[str, Any], 
        request: SynthesisRequest
    ) -> Dict[str, str]:
        """Generate Flask project files."""
        files = {}
        
        # Similar to FastAPI but Flask-specific
        # Implementation would go here
        files["app.py"] = "# Flask implementation\nfrom flask import Flask\n\napp = Flask(__name__)\n"
        
        return files
    
    def _generate_generic_python_files(
        self, 
        architecture: Dict[str, Any], 
        request: SynthesisRequest
    ) -> Dict[str, str]:
        """Generate generic Python files."""
        files = {}
        
        # Generate classes
        for model in architecture["models"]:
            class_code = [
                "from dataclasses import dataclass",
                "from datetime import datetime",
                "from typing import Optional",
                "",
                f"@dataclass",
                f"class {model['name']}:",
                f'    """{model["name"]} entity."""',
            ]
            for field in model["fields"]:
                type_hint = field["type"]
                if type_hint == "datetime":
                    type_hint = "datetime"
                if not field.get("required", False):
                    type_hint = f"Optional[{type_hint}]"
                class_code.append(f"    {field['name']}: {type_hint}")
            
            files[f"{model['name'].lower()}.py"] = "\n".join(class_code)
        
        return files
    
    def _generate_tests(
        self, 
        files: Dict[str, str], 
        request: SynthesisRequest
    ) -> Dict[str, str]:
        """Generate test files."""
        tests = {}
        
        if request.framework == "fastapi":
            test_code = [
                "import pytest",
                "from fastapi.testclient import TestClient",
                "from main import app",
                "",
                "client = TestClient(app)",
                "",
                "def test_health_check():",
                "    response = client.get('/health')",
                "    assert response.status_code == 200",
                "    assert response.json() == {'status': 'healthy'}",
                "",
            ]
            tests["test_main.py"] = "\n".join(test_code)
            
        elif request.framework == "react":
            test_code = [
                "import { render, screen } from '@testing-library/react';",
                "import App from './App';",
                "",
                "test('renders app', () => {",
                "  render(<App />);",
                "  const headerElement = screen.getByText(/Application/i);",
                "  expect(headerElement).toBeInTheDocument();",
                "});",
            ]
            tests["App.test.js"] = "\n".join(test_code)
        
        return tests
    
    def _extract_dependencies(
        self, 
        files: Dict[str, str], 
        request: SynthesisRequest
    ) -> List[str]:
        """Extract dependencies from generated files."""
        if request.framework and request.framework in self.FRAMEWORK_PATTERNS:
            return self.FRAMEWORK_PATTERNS[request.framework]["dependencies"]
        return []
    
    def _generate_setup_instructions(
        self, 
        request: SynthesisRequest, 
        dependencies: List[str]
    ) -> List[str]:
        """Generate setup instructions."""
        instructions = []
        
        if request.framework == "fastapi":
            instructions = [
                "1. Install dependencies: pip install -r requirements.txt",
                "2. Run the server: uvicorn main:app --reload",
                "3. API docs available at: http://localhost:8000/docs",
            ]
        elif request.framework == "react":
            instructions = [
                "1. Install dependencies: npm install",
                "2. Start development: npm start",
                "3. Open http://localhost:3000",
            ]
        elif request.framework == "node":
            instructions = [
                "1. Install dependencies: npm install",
                "2. Start server: npm start",
                "3. Server runs on http://localhost:3000",
            ]
        
        return instructions
    
    def _estimate_complexity(self, files: Dict[str, str]) -> str:
        """Estimate complexity of generated code."""
        total_lines = sum(len(content.split("\n")) for content in files.values())
        
        if total_lines < 100:
            return "Simple"
        elif total_lines < 300:
            return "Medium"
        else:
            return "Complex"
