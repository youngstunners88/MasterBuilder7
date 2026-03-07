"""Graph visualization for repository relationships."""

import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import asdict

import networkx as nx
from pyvis.network import Network
from rich.console import Console

from .indexer import RepoIndexer
from .dependency_mapper import DependencyMapper, DependencyLink

console = Console()


class RepoGraph:
    """Creates interactive visualizations of repository relationships."""
    
    def __init__(self, indexer: RepoIndexer, mapper: Optional[DependencyMapper] = None):
        self.indexer = indexer
        self.mapper = mapper or DependencyMapper(indexer)
        self.graph = nx.DiGraph()
        
    def build_graph(self) -> nx.DiGraph:
        """Build a NetworkX graph from indexed repositories."""
        self.graph = nx.DiGraph()
        
        # Map dependencies if not already done
        if not self.mapper.dependencies:
            self.mapper.map_dependencies()
        
        # Add nodes for each repository
        for repo_name, metadata in self.indexer.metadata.items():
            self.graph.add_node(
                repo_name,
                title=repo_name,
                size=metadata.size_kb / 100,  # Scale size
                language=self._get_primary_language(metadata.languages),
                issues=metadata.open_issues,
                url=metadata.url
            )
        
        # Add edges for dependencies
        for dep in self.mapper.dependencies:
            self.graph.add_edge(
                dep.source_repo,
                dep.target_repo,
                weight=dep.strength,
                type=dep.dependency_type,
                details=dep.details
            )
        
        console.print(f"[green]✓[/green] Graph built with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges")
        return self.graph
    
    def _get_primary_language(self, languages: Dict[str, int]) -> str:
        """Get the primary language from a language distribution."""
        if not languages:
            return "unknown"
        return max(languages.items(), key=lambda x: x[1])[0]
    
    def to_interactive_html(self, output_path: str = "repo_graph.html",
                           height: str = "800px",
                           bgcolor: str = "#1a1a2e",
                           font_color: str = "#ffffff") -> str:
        """Generate an interactive HTML visualization using PyVis."""
        if self.graph.number_of_nodes() == 0:
            self.build_graph()
        
        # Create PyVis network
        net = Network(height=height, bgcolor=bgcolor, font_color=font_color, directed=True)
        net.barnes_hut(gravity=-8000, central_gravity=0.3, spring_length=250)
        
        # Color scheme by language
        language_colors = {
            'python': '#3776ab',
            'javascript': '#f7df1e',
            'typescript': '#3178c6',
            'rust': '#dea584',
            'go': '#00add8',
            'java': '#b07219',
            'ruby': '#701516',
            'unknown': '#808080'
        }
        
        # Edge colors by type
        edge_colors = {
            'import': '#4ecdc4',
            'shared_lib': '#ff6b6b',
            'api': '#ffe66d',
            'config': '#a8e6cf'
        }
        
        # Add nodes
        for node, attrs in self.graph.nodes(data=True):
            lang = attrs.get('language', 'unknown')
            color = language_colors.get(lang, '#808080')
            
            title = f"{node}\n"
            title += f"Language: {lang}\n"
            title += f"Size: {attrs.get('size', 0)} KB\n"
            title += f"Open Issues: {attrs.get('issues', 0)}"
            
            net.add_node(
                node,
                label=node,
                title=title,
                color=color,
                size=max(20, min(100, attrs.get('size', 20)))
            )
        
        # Add edges
        for source, target, attrs in self.graph.edges(data=True):
            dep_type = attrs.get('type', 'import')
            color = edge_colors.get(dep_type, '#cccccc')
            weight = attrs.get('weight', 1)
            
            title = f"Type: {dep_type}\n"
            title += f"Strength: {weight}\n"
            title += "Details:\n" + "\n".join(attrs.get('details', [])[:5])
            
            net.add_edge(
                source,
                target,
                title=title,
                color=color,
                width=max(1, weight / 2),
                arrows={'to': {'enabled': True, 'scaleFactor': 1}}
            )
        
        # Add legend
        legend_html = self._generate_legend(language_colors, edge_colors)
        net.html = net.html.replace('</body>', f'{legend_html}</body>')
        
        # Save
        net.save_graph(output_path)
        console.print(f"[green]✓[/green] Interactive graph saved to {output_path}")
        return output_path
    
    def _generate_legend(self, node_colors: Dict, edge_colors: Dict) -> str:
        """Generate HTML legend for the graph."""
        legend = """
        <div style="position: absolute; top: 10px; right: 10px; 
                    background: rgba(0,0,0,0.8); padding: 15px; border-radius: 8px;
                    font-family: Arial, sans-serif; font-size: 12px;
                    border: 1px solid #444;">
            <h3 style="margin: 0 0 10px 0; color: #fff; font-size: 14px;">Legend</h3>
            <div style="margin-bottom: 10px;">
                <strong style="color: #ccc;">Languages:</strong><br>
        """
        
        for lang, color in node_colors.items():
            legend += f'<span style="display: inline-block; width: 12px; height: 12px; '
            legend += f'background: {color}; margin-right: 5px; border-radius: 50%;"></span>'
            legend += f'<span style="color: #ddd;">{lang.title()}</span><br>'
        
        legend += """
            </div>
            <div>
                <strong style="color: #ccc;">Dependencies:</strong><br>
        """
        
        for dep_type, color in edge_colors.items():
            legend += f'<span style="display: inline-block; width: 20px; height: 3px; '
            legend += f'background: {color}; margin-right: 5px; vertical-align: middle;"></span>'
            legend += f'<span style="color: #ddd;">{dep_type.replace("_", " ").title()}</span><br>'
        
        legend += """
            </div>
        </div>
        """
        
        return legend
    
    def to_mermaid(self) -> str:
        """Generate Mermaid diagram syntax."""
        if self.graph.number_of_nodes() == 0:
            self.build_graph()
        
        lines = ["graph TD"]
        
        # Add nodes with styling
        for node, attrs in self.graph.nodes(data=True):
            lang = attrs.get('language', 'unknown')
            lines.append(f"    {self._sanitize_id(node)}[{node}]")
        
        # Add edges
        for source, target, attrs in self.graph.edges(data=True):
            dep_type = attrs.get('type', 'import')
            weight = attrs.get('weight', 1)
            
            edge_style = "--" if dep_type == 'shared_lib' else "-->"
            if weight > 5:
                edge_style = "==>"  # Strong dependency
            
            lines.append(f"    {self._sanitize_id(source)}{edge_style}|{dep_type}|{self._sanitize_id(target)}")
        
        # Add styling classes
        lines.append("")
        lines.append("    classDef python fill:#3776ab,color:#fff")
        lines.append("    classDef javascript fill:#f7df1e,color:#000")
        lines.append("    classDef typescript fill:#3178c6,color:#fff")
        lines.append("    classDef rust fill:#dea584,color:#000")
        lines.append("    classDef go fill:#00add8,color:#fff")
        
        return '\n'.join(lines)
    
    def _sanitize_id(self, name: str) -> str:
        """Sanitize a name for use as Mermaid ID."""
        return name.replace('-', '_').replace('.', '_').replace(' ', '_')
    
    def to_d3_json(self) -> Dict[str, Any]:
        """Generate D3.js compatible JSON."""
        if self.graph.number_of_nodes() == 0:
            self.build_graph()
        
        nodes = []
        for node, attrs in self.graph.nodes(data=True):
            nodes.append({
                'id': node,
                'name': node,
                'language': attrs.get('language', 'unknown'),
                'size': attrs.get('size', 20),
                'issues': attrs.get('issues', 0),
                'url': attrs.get('url', '')
            })
        
        links = []
        for source, target, attrs in self.graph.edges(data=True):
            links.append({
                'source': source,
                'target': target,
                'type': attrs.get('type', 'import'),
                'weight': attrs.get('weight', 1),
                'details': attrs.get('details', [])
            })
        
        return {'nodes': nodes, 'links': links}
    
    def save_d3_json(self, output_path: str = "repo_graph.json"):
        """Save graph as D3.js compatible JSON."""
        data = self.to_d3_json()
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        console.print(f"[green]✓[/green] D3 JSON saved to {output_path}")
        return output_path
    
    def analyze_graph(self) -> Dict[str, Any]:
        """Analyze the graph structure."""
        if self.graph.number_of_nodes() == 0:
            self.build_graph()
        
        analysis = {
            'basic_stats': {
                'nodes': self.graph.number_of_nodes(),
                'edges': self.graph.number_of_edges(),
                'density': nx.density(self.graph),
                'is_directed': nx.is_directed(self.graph)
            },
            'centrality': {},
            'communities': [],
            'cycles': list(nx.simple_cycles(self.graph)) if self.graph.number_of_edges() > 0 else [],
            'isolated': list(nx.isolates(self.graph))
        }
        
        # Calculate centrality measures
        if self.graph.number_of_nodes() > 0:
            try:
                analysis['centrality']['degree'] = dict(nx.degree_centrality(self.graph))
                analysis['centrality']['betweenness'] = dict(nx.betweenness_centrality(self.graph))
                analysis['centrality']['closeness'] = dict(nx.closeness_centrality(self.graph))
                analysis['centrality']['eigenvector'] = dict(nx.eigenvector_centrality(self.graph, max_iter=1000))
            except Exception as e:
                analysis['centrality_error'] = str(e)
        
        # Detect communities (weakly connected components for directed graph)
        try:
            components = list(nx.weakly_connected_components(self.graph))
            analysis['communities'] = [list(comp) for comp in components]
        except Exception:
            pass
        
        # Find most connected repos
        if analysis['centrality'].get('degree'):
            sorted_by_degree = sorted(
                analysis['centrality']['degree'].items(),
                key=lambda x: x[1],
                reverse=True
            )
            analysis['most_connected'] = sorted_by_degree[:5]
        
        return analysis
    
    def generate_subgraph(self, repo_names: List[str], 
                         depth: int = 1) -> nx.DiGraph:
        """Generate a subgraph focused on specific repositories."""
        if self.graph.number_of_nodes() == 0:
            self.build_graph()
        
        nodes_to_include = set(repo_names)
        
        # Add nodes within specified depth
        for _ in range(depth):
            new_nodes = set()
            for node in nodes_to_include:
                if node in self.graph:
                    new_nodes.update(self.graph.predecessors(node))
                    new_nodes.update(self.graph.successors(node))
            nodes_to_include.update(new_nodes)
        
        return self.graph.subgraph(nodes_to_include).copy()