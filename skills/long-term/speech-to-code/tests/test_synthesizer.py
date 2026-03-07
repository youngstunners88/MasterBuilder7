"""
Tests for CodeSynthesizer.
"""

import pytest
from src.synthesizer import CodeSynthesizer, SynthesisRequest


class TestCodeSynthesizer:
    """Test cases for CodeSynthesizer."""
    
    def setup_method(self):
        self.synthesizer = CodeSynthesizer()
    
    def test_detect_framework_fastapi(self):
        """Test FastAPI framework detection."""
        description = "Create a REST API with endpoints for user management"
        framework = self.synthesizer._detect_framework(description)
        assert framework == "fastapi"
    
    def test_detect_framework_react(self):
        """Test React framework detection."""
        description = "Build a React component for user profiles"
        framework = self.synthesizer._detect_framework(description)
        assert framework == "react"
    
    def test_detect_framework_node(self):
        """Test Node.js framework detection."""
        description = "Create an Express API for orders"
        framework = self.synthesizer._detect_framework(description)
        assert framework == "node"
    
    def test_parse_requirements_auth(self):
        """Test auth requirement detection."""
        description = "Create a login system with JWT authentication"
        requirements = self.synthesizer._parse_requirements(description)
        assert requirements["auth_required"] is True
    
    def test_parse_requirements_crud(self):
        """Test CRUD operation detection."""
        description = "Create, read, update and delete products"
        requirements = self.synthesizer._parse_requirements(description)
        assert "create" in requirements["operations"]
        assert "read" in requirements["operations"]
        assert "update" in requirements["operations"]
        assert "delete" in requirements["operations"]
    
    def test_parse_requirements_entities(self):
        """Test entity extraction."""
        description = "Manage products, orders, and customers"
        requirements = self.synthesizer._parse_requirements(description)
        assert "product" in requirements["entities"] or "products" in requirements["entities"]
    
    def test_synthesize_fastapi_basic(self):
        """Test basic FastAPI synthesis."""
        request = SynthesisRequest(
            description="Create API endpoints for managing products",
            framework="fastapi",
            include_tests=True,
        )
        
        result = self.synthesizer.synthesize(request)
        
        assert "main.py" in result.files
        assert "models.py" in result.files
        assert "routes.py" in result.files
        assert result.estimated_complexity in ["Simple", "Medium", "Complex"]
    
    def test_synthesize_fastapi_with_auth(self):
        """Test FastAPI synthesis with authentication."""
        request = SynthesisRequest(
            description="Build a login system with JWT",
            framework="fastapi",
            include_auth=True,
        )
        
        result = self.synthesizer.synthesize(request)
        
        assert "auth.py" in result.files
        assert "python-jose" in str(result.dependencies) or result.dependencies == []
    
    def test_synthesize_react(self):
        """Test React synthesis."""
        request = SynthesisRequest(
            description="Build a user profile component",
            framework="react",
        )
        
        result = self.synthesizer.synthesize(request)
        
        assert "App.jsx" in result.files
        assert "package.json" in result.files
    
    def test_infer_fields_user(self):
        """Test field inference for User entity."""
        fields = self.synthesizer._infer_fields("user")
        field_names = [f["name"] for f in fields]
        assert "id" in field_names
        assert "email" in field_names
    
    def test_infer_fields_product(self):
        """Test field inference for Product entity."""
        fields = self.synthesizer._infer_fields("product")
        field_names = [f["name"] for f in fields]
        assert "id" in field_names
        assert "price" in field_names
    
    def test_estimate_complexity(self):
        """Test complexity estimation."""
        simple_files = {"main.py": "print('hello')"}
        complex_files = {f"file_{i}.py": "x = 1\n" * 50 for i in range(10)}
        
        assert self.synthesizer._estimate_complexity(simple_files) == "Simple"
        assert self.synthesizer._estimate_complexity(complex_files) == "Complex"


class TestSynthesisRequest:
    """Test cases for SynthesisRequest."""
    
    def test_default_values(self):
        """Test default request values."""
        request = SynthesisRequest(description="test")
        assert request.language == "python"
        assert request.include_tests is True
        assert request.include_auth is False
    
    def test_custom_values(self):
        """Test custom request values."""
        request = SynthesisRequest(
            description="test",
            language="javascript",
            include_auth=True,
            include_tests=False,
        )
        assert request.language == "javascript"
        assert request.include_auth is True
        assert request.include_tests is False
