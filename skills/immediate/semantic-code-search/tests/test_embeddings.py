"""Tests for embeddings module."""

import pytest
import numpy as np
from pathlib import Path
import tempfile

from src.embeddings import (
    EmbeddingManager,
    CodeEmbedding,
    QueryExpander
)


class TestCodeEmbedding:
    """Test CodeEmbedding dataclass."""
    
    def test_creation(self):
        emb = CodeEmbedding(
            id="test123",
            file_path="src/test.py",
            element_type="function",
            name="test_func",
            content="def test(): pass",
            start_line=1,
            end_line=3,
            embedding=np.array([0.1, 0.2, 0.3]),
            language="python",
            metadata={"signature": "def test()"}
        )
        
        assert emb.id == "test123"
        assert emb.file_path == "src/test.py"
        assert emb.name == "test_func"
    
    def test_to_dict(self):
        emb = CodeEmbedding(
            id="test123",
            file_path="src/test.py",
            element_type="function",
            name="test_func",
            content="def test(): pass" * 100,  # Long content
            start_line=1,
            end_line=3,
            embedding=np.array([0.1, 0.2, 0.3]),
            language="python",
            metadata={}
        )
        
        d = emb.to_dict()
        assert d['id'] == "test123"
        assert d['name'] == "test_func"
        assert 'embedding' not in d  # Should not include embedding
        assert len(d['content']) < len(emb.content)  # Should be truncated


class TestEmbeddingManager:
    """Test EmbeddingManager class."""
    
    @pytest.fixture
    def manager(self):
        return EmbeddingManager(model_name='all-MiniLM-L6-v2')
    
    def test_load_model(self, manager):
        model = manager.load_model()
        assert model is not None
        assert manager.model is model  # Should cache
    
    def test_create_embedding(self, manager):
        text = "This is a test function for authentication"
        embedding = manager.create_embedding(text)
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape[0] > 0  # Should have dimensions
    
    def test_create_code_embedding(self, manager):
        emb = manager.create_code_embedding(
            file_path="src/auth.py",
            element_type="function",
            name="authenticate",
            content="def authenticate(user, pass): return True",
            start_line=10,
            end_line=15,
            language="python",
            metadata={}
        )
        
        assert emb.file_path == "src/auth.py"
        assert emb.name == "authenticate"
        assert emb.element_type == "function"
        assert isinstance(emb.embedding, np.ndarray)
    
    def test_extract_docstring_python(self, manager):
        code = '''
def test():
    """This is a docstring."""
    pass
'''
        doc = manager._extract_docstring(code, "python")
        assert "docstring" in doc
    
    def test_extract_docstring_js(self, manager):
        code = '''
/**
 * This is JSDoc
 * @param {string} name
 */
function test(name) {}
'''
        doc = manager._extract_docstring(code, "javascript")
        assert "JSDoc" in doc
    
    def test_batch_create_embeddings(self, manager):
        elements = [
            {
                'file_path': f"src/file{i}.py",
                'element_type': 'function',
                'name': f'func{i}',
                'content': f'def func{i}(): pass',
                'start_line': i,
                'end_line': i + 5,
                'language': 'python',
                'metadata': {}
            }
            for i in range(3)
        ]
        
        embeddings = manager.batch_create_embeddings(elements)
        
        assert len(embeddings) == 3
        assert all(isinstance(e, CodeEmbedding) for e in embeddings)
    
    def test_compute_similarity(self, manager):
        # Create test embeddings
        emb1 = CodeEmbedding(
            id="1",
            file_path="a.py",
            element_type="function",
            name="auth",
            content="def auth(): pass",
            start_line=1,
            end_line=2,
            embedding=np.array([1.0, 0.0, 0.0]),
            language="python",
            metadata={}
        )
        emb2 = CodeEmbedding(
            id="2",
            file_path="b.py",
            element_type="function",
            name="login",
            content="def login(): pass",
            start_line=1,
            end_line=2,
            embedding=np.array([0.9, 0.1, 0.0]),  # Similar to emb1
            language="python",
            metadata={}
        )
        emb3 = CodeEmbedding(
            id="3",
            file_path="c.py",
            element_type="function",
            name="logout",
            content="def logout(): pass",
            start_line=1,
            end_line=2,
            embedding=np.array([0.0, 1.0, 0.0]),  # Different from emb1
            language="python",
            metadata={}
        )
        
        query = np.array([1.0, 0.0, 0.0])
        similarities = manager.compute_similarity(query, [emb1, emb2, emb3])
        
        assert len(similarities) == 3
        # emb1 should be most similar to itself
        assert similarities[0][0].id == "1"
        assert similarities[0][1] > 0.99  # Very high similarity
    
    def test_save_and_load_embeddings(self, manager):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            
            # Create test embeddings
            embeddings = [
                CodeEmbedding(
                    id=f"{i}",
                    file_path=f"src/file{i}.py",
                    element_type="function",
                    name=f"func{i}",
                    content="def test(): pass",
                    start_line=i,
                    end_line=i+5,
                    embedding=np.array([0.1 * i, 0.2 * i, 0.3 * i]),
                    language="python",
                    metadata={}
                )
                for i in range(3)
            ]
            
            output_file = tmp_path / "embeddings.json"
            manager.save_embeddings(embeddings, output_file)
            
            assert output_file.exists()
            
            loaded = manager.load_embeddings(output_file)
            assert len(loaded) == 3
            assert loaded[0].name == "func0"


class TestQueryExpander:
    """Test QueryExpander class."""
    
    @pytest.fixture
    def expander(self):
        return QueryExpander()
    
    def test_expand_simple(self, expander):
        expanded = expander.expand("test authentication")
        
        assert "test authentication" in expanded  # Original
        assert len(expanded) >= 1
    
    def test_expand_with_synonyms(self, expander):
        expanded = expander.expand("auth system")
        
        assert "auth system" in expanded
        # Should include synonyms
        assert any("authentication" in q for q in expanded)
    
    def test_expand_multiple_terms(self, expander):
        expanded = expander.expand("db config")
        
        assert "db config" in expanded
        # Both terms should be expanded
        assert any("database" in q for q in expanded)
    
    def test_create_code_specific_query_function(self, expander):
        query = expander.create_code_specific_query("find user function")
        
        assert "find user function" in query
        assert "Type: function" in query
    
    def test_create_code_specific_query_class(self, expander):
        query = expander.create_code_specific_query("User class")
        
        assert "Type: class" in query
    
    def test_create_code_specific_query_no_hint(self, expander):
        query = expander.create_code_specific_query("general search")
        
        assert query == "general search"  # No hints added
