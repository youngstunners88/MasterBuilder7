"""
Tests for TemplateEngine.
"""

import pytest
from src.template_engine import TemplateEngine, CodeTemplate


class TestTemplateEngine:
    """Test cases for TemplateEngine."""
    
    def setup_method(self):
        self.engine = TemplateEngine()
    
    def test_get_template_exists(self):
        """Test getting an existing template."""
        template = self.engine.get_template("fastapi_crud")
        assert template is not None
        assert template.name == "fastapi_crud"
    
    def test_get_template_not_exists(self):
        """Test getting a non-existent template."""
        template = self.engine.get_template("nonexistent")
        assert template is None
    
    def test_render_template(self):
        """Test template rendering."""
        code = self.engine.render_template(
            "fastapi_crud",
            entity="Product",
            entity_lower="product",
            fields="name: str\n    price: float",
            create_fields="name: str\n    price: float",
            update_fields="name: Optional[str]\n    price: Optional[float]"
        )
        
        assert "class Product(BaseModel)" in code
        assert "router = APIRouter" in code
    
    def test_render_template_missing_placeholder(self):
        """Test rendering with missing placeholder."""
        with pytest.raises(ValueError):
            self.engine.render_template("fastapi_crud", entity="Product")
    
    def test_render_template_safe(self):
        """Test safe template rendering."""
        code = self.engine.render_template_safe(
            "fastapi_crud",
            entity="Product"
        )
        # Should not raise, just leave placeholders
        assert "$entity" in code or "Product" in code
    
    def test_add_template(self):
        """Test adding custom template."""
        template = CodeTemplate(
            name="custom",
            language="python",
            template="def $name(): pass",
            placeholders=["name"],
            description="Custom template"
        )
        
        self.engine.add_template(template)
        retrieved = self.engine.get_template("custom")
        assert retrieved == template
    
    def test_list_templates(self):
        """Test listing templates."""
        templates = self.engine.list_templates()
        assert "fastapi_crud" in templates
        assert "react_component" in templates
    
    def test_list_templates_by_language(self):
        """Test listing templates by language."""
        python_templates = self.engine.list_templates("python")
        assert "fastapi_crud" in python_templates
    
    def test_suggest_template(self):
        """Test template suggestion."""
        suggested = self.engine.suggest_template("Create a FastAPI CRUD endpoint")
        assert suggested == "fastapi_crud"
        
        suggested = self.engine.suggest_template("Build a React component")
        assert suggested == "react_component"
    
    def test_create_custom_template(self):
        """Test creating custom template from code."""
        template = self.engine.create_custom_template(
            name="my_template",
            language="python",
            code="def $func_name($arg): return $value",
            description="My custom template"
        )
        
        assert template.name == "my_template"
        assert "func_name" in template.placeholders
        assert "arg" in template.placeholders
        assert "value" in template.placeholders
    
    def test_compose_templates(self):
        """Test composing multiple templates."""
        composed = self.engine.compose_templates(["fastapi_crud", "auth_middleware"])
        assert "APIRouter" in composed
        assert "security" in composed
