"""Tests for diff module."""

import pytest
from pathlib import Path
import tempfile

from src.diff import (
    DiffAnalyzer,
    CodeChange,
    ChangeType
)


class TestCodeChange:
    """Test CodeChange dataclass."""
    
    def test_creation(self):
        change = CodeChange(
            file_path="src/auth.py",
            change_type=ChangeType.NEW_FEATURE,
            element_type="function",
            name="authenticate",
            description="New authentication function",
            line_numbers=[10, 15],
            impact_level="high"
        )
        
        assert change.file_path == "src/auth.py"
        assert change.change_type == ChangeType.NEW_FEATURE
        assert change.impact_level == "high"
    
    def test_to_dict(self):
        change = CodeChange(
            file_path="src/test.py",
            change_type=ChangeType.BUGFIX,
            element_type="function",
            name="fix_bug",
            description="Fixed null pointer",
            old_signature="def old()",
            new_signature="def fix_bug()",
            line_numbers=[5],
            impact_level="medium"
        )
        
        d = change.to_dict()
        assert d['file_path'] == "src/test.py"
        assert d['change_type'] == 'bugfix'
        assert d['old_signature'] == "def old()"


class TestDiffAnalyzer:
    """Test DiffAnalyzer class."""
    
    @pytest.fixture
    def analyzer(self):
        return DiffAnalyzer()
    
    def test_detect_file_type_python(self, analyzer):
        assert analyzer._detect_file_type(Path("test.py")) == "python"
    
    def test_detect_file_type_route(self, analyzer):
        assert analyzer._detect_file_type(Path("routes.py")) == "route"
        assert analyzer._detect_file_type(Path("api/endpoints.py")) == "route"
    
    def test_detect_file_type_model(self, analyzer):
        assert analyzer._detect_file_type(Path("models.py")) == "model"
        assert analyzer._detect_file_type(Path("database/models.py")) == "model"
    
    def test_detect_file_type_config(self, analyzer):
        assert analyzer._detect_file_type(Path("config.yaml")) == "config"
        assert analyzer._detect_file_type(Path("settings.json")) == "config"
    
    def test_detect_change_type_new_feature(self, analyzer):
        content = "def new_function(): pass"
        change_type = analyzer._detect_change_type(content)
        assert change_type == ChangeType.NEW_FEATURE
    
    def test_detect_change_type_bugfix(self, analyzer):
        content = "fix: handle null pointer exception"
        change_type = analyzer._detect_change_type(content)
        assert change_type == ChangeType.BUGFIX
    
    def test_detect_change_type_refactor(self, analyzer):
        content = "refactor: rename variable"
        change_type = analyzer._detect_change_type(content)
        assert change_type == ChangeType.REFACTOR
    
    def test_determine_impact_critical(self, analyzer):
        assert analyzer._determine_impact("auth", "def auth(): pass") == "critical"
        assert analyzer._determine_impact("user", "security check") == "critical"
    
    def test_determine_impact_high(self, analyzer):
        assert analyzer._determine_impact("config", "settings") == "high"
        assert analyzer._determine_impact("UserModel", "public") == "high"
    
    def test_determine_impact_low(self, analyzer):
        assert analyzer._determine_impact("helper", "internal") == "low"
    
    def test_analyze_new_file_python(self, analyzer):
        with tempfile.TemporaryDirectory() as tmp:
            file_path = Path(tmp) / "test.py"
            content = """
class UserManager:
    def get_user(self, id):
        return None

def authenticate(username, password):
    return True
"""
            changes = analyzer._analyze_new_file(file_path, content)
            
            assert len(changes) >= 2  # Class + function
            assert any(c.name == "UserManager" for c in changes)
            assert any(c.name == "authenticate" for c in changes)
    
    def test_analyze_new_file_routes(self, analyzer):
        with tempfile.TemporaryDirectory() as tmp:
            file_path = Path(tmp) / "routes.py"
            content = """
@app.get("/users")
def get_users():
    return []

@app.post("/auth/login")
def login():
    pass
"""
            changes = analyzer._analyze_new_file(file_path, content)
            
            route_changes = [c for c in changes if c.element_type == "route"]
            assert len(route_changes) >= 2
    
    def test_categorize_changes(self, analyzer):
        changes = [
            CodeChange("a.py", ChangeType.NEW_FEATURE, "function", "new_func", "New"),
            CodeChange("b.py", ChangeType.BUGFIX, "function", "fix_bug", "Fix"),
            CodeChange("c.py", ChangeType.REFACTOR, "function", "refactor", "Refactor"),
        ]
        
        categorized = analyzer.categorize_changes(changes)
        
        assert len(categorized['new_features']) == 1
        assert len(categorized['bugfixes']) == 1
        assert len(categorized['refactors']) == 1
    
    def test_get_summary(self, analyzer):
        changes = [
            CodeChange("a.py", ChangeType.NEW_FEATURE, "route", "GET /users", "New API", impact_level="high"),
            CodeChange("b.py", ChangeType.NEW_FEATURE, "model", "User", "New model", impact_level="critical"),
        ]
        
        summary = analyzer.get_summary(changes)
        
        assert summary['total_changes'] == 2
        assert summary['by_impact']['critical'] == 1
        assert summary['by_impact']['high'] == 1
        assert len(summary['critical_changes']) == 1
