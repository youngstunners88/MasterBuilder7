"""
Search module for semantic code search.
Provides search functionality using embeddings and vector similarity.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from loguru import logger

from .embeddings import EmbeddingManager, CodeEmbedding, QueryExpander
from .indexer import TreeSitterIndexer, CodeElement


@dataclass
class SearchResult:
    """Result of a semantic search."""
    element_type: str
    name: str
    file_path: str
    language: str
    start_line: int
    end_line: int
    relevance_score: float
    content_preview: str
    signature: Optional[str]
    docstring: Optional[str]
    parent: Optional[str]
    
    def format(self) -> str:
        """Format result for display."""
        lines = [
            f"📄 {self.file_path}:{self.start_line}-{self.end_line}",
            f"🔍 {self.element_type}: {self.name}",
            f"⭐ Relevance: {self.relevance_score:.3f}",
        ]
        
        if self.signature:
            lines.append(f"   {self.signature}")
        
        if self.docstring:
            doc_preview = self.docstring[:100] + "..." if len(self.docstring) > 100 else self.docstring
            lines.append(f"   📖 {doc_preview}")
        
        return "\n".join(lines)


class SemanticSearchEngine:
    """Main search engine for semantic code search."""
    
    def __init__(
        self,
        project_root: Path,
        embedding_manager: Optional[EmbeddingManager] = None,
        indexer: Optional[TreeSitterIndexer] = None
    ):
        self.project_root = Path(project_root)
        self.embedding_manager = embedding_manager or EmbeddingManager()
        self.indexer = indexer or TreeSitterIndexer(project_root)
        self.query_expander = QueryExpander()
        self.code_embeddings: List[CodeEmbedding] = []
        self.is_indexed = False
    
    def index(self, languages: Optional[List[str]] = None) -> 'SemanticSearchEngine':
        """
        Index the project and create embeddings.
        
        Args:
            languages: List of languages to index
            
        Returns:
            Self for chaining
        """
        logger.info(f"Indexing project: {self.project_root}")
        
        # Index code elements
        self.indexer.index_project(languages=languages)
        elements = self.indexer.get_elements()
        
        logger.info(f"Creating embeddings for {len(elements)} elements...")
        
        # Convert to embedding format
        embedding_inputs = [
            {
                'file_path': e.file_path,
                'element_type': e.element_type,
                'name': e.name,
                'content': e.content,
                'start_line': e.start_line,
                'end_line': e.end_line,
                'language': e.language,
                'metadata': {
                    'signature': e.signature,
                    'docstring': e.docstring,
                    'modifiers': e.modifiers,
                    'parameters': e.parameters,
                    'return_type': e.return_type,
                    'parent': e.parent,
                }
            }
            for e in elements
        ]
        
        # Create embeddings in batches
        if embedding_inputs:
            self.code_embeddings = self.embedding_manager.batch_create_embeddings(
                embedding_inputs
            )
        
        self.is_indexed = True
        logger.info(f"Indexing complete. {len(self.code_embeddings)} embeddings created.")
        
        return self
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        language_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        file_filter: Optional[str] = None,
        min_score: float = 0.0,
        expand_query: bool = True
    ) -> List[SearchResult]:
        """
        Search for code elements matching the query.
        
        Args:
            query: Natural language query
            top_k: Number of results to return
            language_filter: Filter by language (e.g., 'python', 'javascript')
            type_filter: Filter by element type (e.g., 'function', 'class')
            file_filter: Filter by file path pattern
            min_score: Minimum relevance score threshold
            expand_query: Whether to expand query with synonyms
            
        Returns:
            List of search results
        """
        if not self.is_indexed:
            raise RuntimeError("Search engine not indexed. Call index() first.")
        
        if not self.code_embeddings:
            logger.warning("No code embeddings available")
            return []
        
        # Filter embeddings
        filtered_embeddings = self._filter_embeddings(
            language_filter, type_filter, file_filter
        )
        
        if not filtered_embeddings:
            logger.warning("No embeddings match the filters")
            return []
        
        # Create query embedding
        if expand_query:
            enhanced_query = self.query_expander.create_code_specific_query(query)
        else:
            enhanced_query = query
        
        query_embedding = self.embedding_manager.create_embedding(enhanced_query)
        
        # Compute similarities
        similarities = self.embedding_manager.compute_similarity(
            query_embedding, filtered_embeddings
        )
        
        # Filter by minimum score and convert to results
        results = []
        for embedding, score in similarities:
            if score >= min_score:
                result = SearchResult(
                    element_type=embedding.element_type,
                    name=embedding.name,
                    file_path=embedding.file_path,
                    language=embedding.language,
                    start_line=embedding.start_line,
                    end_line=embedding.end_line,
                    relevance_score=round(score, 4),
                    content_preview=embedding.content[:500],
                    signature=embedding.metadata.get('signature'),
                    docstring=embedding.metadata.get('docstring'),
                    parent=embedding.metadata.get('parent')
                )
                results.append(result)
                
                if len(results) >= top_k:
                    break
        
        return results
    
    def search_with_expansion(
        self,
        query: str,
        top_k: int = 10,
        **filters
    ) -> List[SearchResult]:
        """
        Search with query expansion using synonyms.
        
        Args:
            query: Original query
            top_k: Number of results per expanded query
            **filters: Additional filters
            
        Returns:
            Combined and deduplicated results
        """
        expanded_queries = self.query_expander.expand(query)
        
        all_results: Dict[str, SearchResult] = {}
        
        for expanded_query in expanded_queries:
            results = self.search(
                expanded_query,
                top_k=top_k,
                expand_query=False,
                **filters
            )
            
            for result in results:
                key = f"{result.file_path}:{result.name}:{result.start_line}"
                if key not in all_results:
                    all_results[key] = result
                else:
                    # Keep higher score
                    if result.relevance_score > all_results[key].relevance_score:
                        all_results[key] = result
        
        # Sort by relevance
        results = sorted(all_results.values(), key=lambda r: r.relevance_score, reverse=True)
        
        return results[:top_k]
    
    def _filter_embeddings(
        self,
        language: Optional[str],
        element_type: Optional[str],
        file_pattern: Optional[str]
    ) -> List[CodeEmbedding]:
        """Filter embeddings based on criteria."""
        filtered = self.code_embeddings
        
        if language:
            filtered = [e for e in filtered if e.language == language]
        
        if element_type:
            filtered = [e for e in filtered if e.element_type == element_type]
        
        if file_pattern:
            filtered = [
                e for e in filtered 
                if file_pattern.lower() in e.file_path.lower()
            ]
        
        return filtered
    
    def find_similar(
        self,
        file_path: str,
        name: str,
        start_line: int,
        top_k: int = 5
    ) -> List[SearchResult]:
        """
        Find similar code elements to a given element.
        
        Args:
            file_path: Path to the reference file
            name: Name of the reference element
            start_line: Starting line of the reference element
            top_k: Number of similar elements to return
            
        Returns:
            List of similar elements
        """
        # Find the reference embedding
        reference = None
        for emb in self.code_embeddings:
            if (emb.file_path == file_path and 
                emb.name == name and 
                emb.start_line == start_line):
                reference = emb
                break
        
        if reference is None:
            raise ValueError(f"Element not found: {file_path}:{name}:{start_line}")
        
        # Compute similarities (excluding self)
        other_embeddings = [e for e in self.code_embeddings if e.id != reference.id]
        similarities = self.embedding_manager.compute_similarity(
            reference.embedding, other_embeddings
        )
        
        # Convert to results
        results = []
        for embedding, score in similarities[:top_k]:
            result = SearchResult(
                element_type=embedding.element_type,
                name=embedding.name,
                file_path=embedding.file_path,
                language=embedding.language,
                start_line=embedding.start_line,
                end_line=embedding.end_line,
                relevance_score=round(score, 4),
                content_preview=embedding.content[:500],
                signature=embedding.metadata.get('signature'),
                docstring=embedding.metadata.get('docstring'),
                parent=embedding.metadata.get('parent')
            )
            results.append(result)
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get search engine statistics."""
        if not self.is_indexed:
            return {"status": "not_indexed"}
        
        languages = set(e.language for e in self.code_embeddings)
        types = {}
        for e in self.code_embeddings:
            types[e.element_type] = types.get(e.element_type, 0) + 1
        
        return {
            "status": "indexed",
            "total_elements": len(self.code_embeddings),
            "languages": sorted(languages),
            "element_types": types,
            "project_root": str(self.project_root),
        }
    
    def save(self, output_dir: Path):
        """Save search index and embeddings."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save code index
        self.indexer.save_index(output_dir / "code_index.json")
        
        # Save embeddings
        self.embedding_manager.save_embeddings(
            self.code_embeddings,
            output_dir / "embeddings.json"
        )
        
        logger.info(f"Search engine saved to {output_dir}")
    
    def load(self, input_dir: Path):
        """Load search index and embeddings."""
        input_dir = Path(input_dir)
        
        # Load index metadata
        self.indexer.load_index(input_dir / "code_index.json")
        
        # Load embeddings
        self.code_embeddings = self.embedding_manager.load_embeddings(
            input_dir / "embeddings.json"
        )
        
        self.is_indexed = True
        logger.info(f"Search engine loaded from {input_dir}")


class CodeNavigator:
    """Navigate code using semantic search."""
    
    def __init__(self, search_engine: SemanticSearchEngine):
        self.search_engine = search_engine
    
    def find_definition(self, symbol: str) -> Optional[SearchResult]:
        """Find the definition of a symbol."""
        results = self.search_engine.search(
            f"definition of {symbol}",
            top_k=5
        )
        
        # Prioritize exact name matches
        for result in results:
            if result.name == symbol:
                return result
        
        return results[0] if results else None
    
    def find_usages(self, symbol: str) -> List[SearchResult]:
        """Find usages of a symbol."""
        return self.search_engine.search(
            f"uses of {symbol} calls {symbol}",
            top_k=10
        )
    
    def find_related(self, file_path: str, name: str, start_line: int) -> List[SearchResult]:
        """Find related code elements."""
        return self.search_engine.find_similar(file_path, name, start_line, top_k=10)
    
    def explore_file(self, file_path: str) -> List[SearchResult]:
        """Explore all elements in a file."""
        elements = self.search_engine.indexer.get_elements_in_file(file_path)
        
        results = []
        for e in elements:
            # Find similarity to file's overall purpose
            results.append(SearchResult(
                element_type=e.element_type,
                name=e.name,
                file_path=e.file_path,
                language=e.language,
                start_line=e.start_line,
                end_line=e.end_line,
                relevance_score=1.0,
                content_preview=e.content[:500],
                signature=e.signature,
                docstring=e.docstring,
                parent=e.parent
            ))
        
        return results
