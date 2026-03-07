"""
Template Engine: Manages code templates and patterns.
"""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from string import Template


@dataclass
class CodeTemplate:
    """A code template with placeholders."""
    name: str
    language: str
    template: str
    placeholders: List[str]
    description: str


class TemplateEngine:
    """
    Manages code templates for common patterns.
    """
    
    def __init__(self):
        self.templates: Dict[str, CodeTemplate] = {}
        self._load_builtin_templates()
    
    def _load_builtin_templates(self):
        """Load built-in templates for common patterns."""
        
        # FastAPI CRUD template
        self.templates["fastapi_crud"] = CodeTemplate(
            name="fastapi_crud",
            language="python",
            template='''from fastapi import APIRouter, HTTPException, Depends
from typing import List
from pydantic import BaseModel

router = APIRouter(prefix="/$entity_lower", tags=["$entity"])

class $entity(BaseModel):
    id: str
    $fields

class ${entity}Create(BaseModel):
    $create_fields

class ${entity}Update(BaseModel):
    $update_fields

@router.post("/", response_model=$entity)
async def create_${entity_lower}(data: ${entity}Create):
    """Create a new $entity_lower."""
    pass

@router.get("/{id}", response_model=$entity)
async def get_${entity_lower}(id: str):
    """Get $entity_lower by ID."""
    pass

@router.put("/{id}", response_model=$entity)
async def update_${entity_lower}(id: str, data: ${entity}Update):
    """Update $entity_lower."""
    pass

@router.delete("/{id}")
async def delete_${entity_lower}(id: str):
    """Delete $entity_lower."""
    pass
''',
            placeholders=["entity", "entity_lower", "fields", "create_fields", "update_fields"],
            description="FastAPI CRUD endpoints for an entity"
        )
        
        # React Component template
        self.templates["react_component"] = CodeTemplate(
            name="react_component",
            language="javascript",
            template='''import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import './$component_name.css';

const $component_name = ({ $props }) => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Fetch data on mount
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      // TODO: Implement data fetching
      setData({});
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="loading">Loading...</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <div className="$component_class">
      $content
    </div>
  );
};

$component_name.propTypes = {
  $prop_types
};

export default $component_name;
''',
            placeholders=["component_name", "component_class", "props", "content", "prop_types"],
            description="React functional component with hooks"
        )
        
        # Authentication template
        self.templates["auth_middleware"] = CodeTemplate(
            name="auth_middleware",
            language="python",
            template='''from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
import os

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    """Create JWT access token."""
    from datetime import datetime, timedelta
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current user from JWT token."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def require_auth(request: Request):
    """Middleware to require authentication."""
    auth_header = request.headers.get("authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization header required")
    # Token validation logic here
''',
            placeholders=[],
            description="FastAPI JWT authentication middleware"
        )
        
        # Database model template
        self.templates["sqlalchemy_model"] = CodeTemplate(
            name="sqlalchemy_model",
            language="python",
            template='''from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class $entity(Base):
    __tablename__ = "$table_name"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    $columns
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    $relationships
    
    def to_dict(self):
        return {
            "id": self.id,
            $dict_fields
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
''',
            placeholders=["entity", "table_name", "columns", "relationships", "dict_fields"],
            description="SQLAlchemy ORM model"
        )
        
        # API client template
        self.templates["api_client"] = CodeTemplate(
            name="api_client",
            language="python",
            template='''import requests
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class $client_name:
    """API client for $service_name."""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        
        if api_key:
            self.session.headers["Authorization"] = f"Bearer {api_key}"
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
    
    $methods
''',
            placeholders=["client_name", "service_name", "methods"],
            description="Generic API client template"
        )
        
        # Validation schema template
        self.templates["pydantic_validation"] = CodeTemplate(
            name="pydantic_validation",
            language="python",
            template='''from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional
import re

class $model_name(BaseModel):
    """$description"""
    
    $fields
    
    $validators
    
    class Config:
        json_schema_extra = {
            "example": $example
        }
''',
            placeholders=["model_name", "description", "fields", "validators", "example"],
            description="Pydantic validation model"
        )
        
        # Node.js Express route template
        self.templates["express_route"] = CodeTemplate(
            name="express_route",
            language="javascript",
            template='''const express = require('express');
const router = express.Router();
const $controller = require('../controllers/$controller_file');
const { authenticate } = require('../middleware/auth');

/**
 * @route   $method $path
 * @desc    $description
 * @access  $access
 */
router.$method('$path', $middlewares async (req, res) => {
  try {
    const result = await $controller.$handler(req, res);
    res.json(result);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;
''',
            placeholders=["method", "path", "description", "access", "controller", "controller_file", "handler", "middlewares"],
            description="Express.js route definition"
        )
    
    def get_template(self, name: str) -> Optional[CodeTemplate]:
        """Get a template by name."""
        return self.templates.get(name)
    
    def render_template(self, name: str, **kwargs) -> str:
        """
        Render a template with provided values.
        
        Args:
            name: Template name
            **kwargs: Values for placeholders
            
        Returns:
            Rendered template string
        """
        template = self.get_template(name)
        if not template:
            raise ValueError(f"Template '{name}' not found")
        
        # Use Python's Template for substitution
        t = Template(template.template)
        try:
            return t.substitute(**kwargs)
        except KeyError as e:
            missing = str(e).strip("'")
            raise ValueError(f"Missing placeholder '{missing}' for template '{name}'")
    
    def render_template_safe(self, name: str, **kwargs) -> str:
        """
        Render a template safely, ignoring missing placeholders.
        
        Args:
            name: Template name
            **kwargs: Values for placeholders
            
        Returns:
            Rendered template string
        """
        template = self.get_template(name)
        if not template:
            raise ValueError(f"Template '{name}' not found")
        
        t = Template(template.template)
        return t.safe_substitute(**kwargs)
    
    def add_template(self, template: CodeTemplate):
        """Add a custom template."""
        self.templates[template.name] = template
    
    def list_templates(self, language: Optional[str] = None) -> List[str]:
        """List available templates, optionally filtered by language."""
        if language:
            return [name for name, t in self.templates.items() if t.language == language]
        return list(self.templates.keys())
    
    def suggest_template(self, description: str) -> Optional[str]:
        """Suggest a template based on description."""
        desc_lower = description.lower()
        
        # Map keywords to templates
        keyword_map = {
            "fastapi_crud": ["api", "crud", "endpoint", "fastapi"],
            "react_component": ["react", "component", "frontend", "ui"],
            "auth_middleware": ["auth", "login", "jwt", "token", "middleware"],
            "sqlalchemy_model": ["database", "model", "orm", "sqlalchemy", "table"],
            "api_client": ["client", "http", "request", "api"],
            "pydantic_validation": ["validation", "schema", "pydantic", "validate"],
            "express_route": ["express", "route", "nodejs", "endpoint"],
        }
        
        for template_name, keywords in keyword_map.items():
            if any(kw in desc_lower for kw in keywords):
                return template_name
        
        return None
    
    def create_custom_template(
        self, 
        name: str, 
        language: str, 
        code: str,
        description: str = ""
    ) -> CodeTemplate:
        """
        Create a custom template from code.
        
        Args:
            name: Template name
            language: Programming language
            code: Template code with $placeholders
            description: Template description
            
        Returns:
            Created CodeTemplate
        """
        # Extract placeholders
        placeholders = re.findall(r'\$(\w+)', code)
        placeholders = list(set(placeholders))  # Remove duplicates
        
        template = CodeTemplate(
            name=name,
            language=language,
            template=code,
            placeholders=placeholders,
            description=description
        )
        
        self.add_template(template)
        return template
    
    def compose_templates(self, template_names: List[str], separator: str = "\n\n") -> str:
        """
        Compose multiple templates into one.
        
        Args:
            template_names: List of template names to compose
            separator: String to separate templates
            
        Returns:
            Composed template
        """
        parts = []
        for name in template_names:
            template = self.get_template(name)
            if template:
                parts.append(template.template)
        
        return separator.join(parts)


class PatternLibrary:
    """
    Library of common code patterns.
    """
    
    PATTERNS = {
        "singleton": {
            "python": '''
class Singleton:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
''',
            "javascript": '''
class Singleton {
  static instance = null;
  
  static getInstance() {
    if (!Singleton.instance) {
      Singleton.instance = new Singleton();
    }
    return Singleton.instance;
  }
}
'''
        },
        "factory": {
            "python": '''
class Factory:
    @staticmethod
    def create(type_name, **kwargs):
        if type_name == "type_a":
            return TypeA(**kwargs)
        elif type_name == "type_b":
            return TypeB(**kwargs)
        raise ValueError(f"Unknown type: {type_name}")
''',
        },
        "repository": {
            "python": '''
class Repository:
    def __init__(self, db_session):
        self.db = db_session
    
    def get(self, id):
        return self.db.query(self.model).get(id)
    
    def list(self):
        return self.db.query(self.model).all()
    
    def create(self, data):
        instance = self.model(**data)
        self.db.add(instance)
        self.db.commit()
        return instance
    
    def update(self, id, data):
        instance = self.get(id)
        for key, value in data.items():
            setattr(instance, key, value)
        self.db.commit()
        return instance
    
    def delete(self, id):
        instance = self.get(id)
        self.db.delete(instance)
        self.db.commit()
''',
        },
    }
    
    @classmethod
    def get_pattern(cls, name: str, language: str = "python") -> Optional[str]:
        """Get a pattern implementation."""
        pattern = cls.PATTERNS.get(name, {})
        return pattern.get(language)
    
    @classmethod
    def list_patterns(cls) -> List[str]:
        """List available patterns."""
        return list(cls.PATTERNS.keys())
