"""Diagram renderer - converts diagrams to various output formats."""

import os
import subprocess
from typing import Optional, List, Dict
from pathlib import Path
from dataclasses import dataclass
import tempfile

from rich.console import Console

console = Console()


@dataclass
class RenderConfig:
    """Configuration for diagram rendering."""
    format: str = "svg"  # svg, png, pdf, html
    width: int = 1200
    height: int = 800
    theme: str = "default"
    background: str = "white"
    scale: float = 1.0


class DiagramRenderer:
    """Renders diagrams to various output formats."""
    
    SUPPORTED_FORMATS = ['svg', 'png', 'pdf', 'html', 'md', 'mmd']
    
    def __init__(self, config: Optional[RenderConfig] = None):
        self.config = config or RenderConfig()
    
    def render(self, diagram_content: str, output_path: str,
               diagram_type: str = "mermaid") -> str:
        """Render a diagram to the specified output format."""
        output_path = Path(output_path)
        output_format = output_path.suffix.lstrip('.')
        
        if output_format not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {output_format}")
        
        if diagram_type == "mermaid":
            return self._render_mermaid(diagram_content, output_path)
        elif diagram_type == "plantuml":
            return self._render_plantuml(diagram_content, output_path)
        elif diagram_type == "dot":
            return self._render_graphviz(diagram_content, output_path)
        else:
            raise ValueError(f"Unsupported diagram type: {diagram_type}")
    
    def _render_mermaid(self, content: str, output_path: Path) -> str:
        """Render Mermaid diagram to various formats."""
        output_format = output_path.suffix.lstrip('.')
        
        if output_format == 'mmd':
            # Just save the mermaid source
            output_path.write_text(content)
            return str(output_path)
        
        if output_format == 'md':
            # Wrap in markdown code block
            markdown = f"```mermaid\n{content}\n```"
            output_path.write_text(markdown)
            return str(output_path)
        
        # Use mermaid-cli (mmdc) for other formats
        return self._render_with_mmdc(content, output_path)
    
    def _render_with_mmdc(self, content: str, output_path: Path) -> str:
        """Render using mermaid-cli (mmdc)."""
        # Check if mmdc is available
        if not self._command_exists('mmdc'):
            console.print("[yellow]Warning:[/yellow] mmdc not found. Installing...")
            self._install_mmdc()
        
        # Create temp file for input
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False) as f:
            f.write(content)
            input_path = f.name
        
        try:
            cmd = [
                'mmdc',
                '-i', input_path,
                '-o', str(output_path),
                '-w', str(self.config.width),
                '-H', str(self.config.height),
                '-b', self.config.background,
                '-s', str(self.config.scale)
            ]
            
            if self.config.theme != 'default':
                cmd.extend(['-t', self.config.theme])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print(f"[red]mmdc error:[/red] {result.stderr}")
                # Fallback: save as markdown
                output_path = output_path.with_suffix('.md')
                output_path.write_text(f"```mermaid\n{content}\n```")
            else:
                console.print(f"[green]✓[/green] Rendered to {output_path}")
            
            return str(output_path)
            
        finally:
            os.unlink(input_path)
    
    def _render_plantuml(self, content: str, output_path: Path) -> str:
        """Render PlantUML diagram."""
        output_format = output_path.suffix.lstrip('.')
        
        # Check for plantuml
        if not self._command_exists('plantuml'):
            console.print("[yellow]Warning:[/yellow] plantuml not found. Saving as text.")
            output_path = output_path.with_suffix('.puml')
            output_path.write_text(content)
            return str(output_path)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.puml', delete=False) as f:
            f.write(content)
            input_path = f.name
        
        try:
            cmd = ['plantuml', '-t' + output_format, input_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print(f"[red]PlantUML error:[/red] {result.stderr}")
                return str(output_path)
            
            # PlantUML creates output in same dir as input
            generated = Path(input_path).with_suffix('.' + output_format)
            if generated.exists():
                generated.rename(output_path)
            
            console.print(f"[green]✓[/green] Rendered to {output_path}")
            return str(output_path)
            
        finally:
            os.unlink(input_path)
    
    def _render_graphviz(self, content: str, output_path: Path) -> str:
        """Render Graphviz DOT diagram."""
        output_format = output_path.suffix.lstrip('.')
        
        try:
            import graphviz
            
            # Create graph from DOT content
            source = graphviz.Source(content)
            source.render(output_path.with_suffix(''), format=output_format, cleanup=True)
            
            console.print(f"[green]✓[/green] Rendered to {output_path}")
            return str(output_path)
            
        except ImportError:
            console.print("[yellow]Warning:[/yellow] graphviz Python package not found.")
            
            # Try command line
            if self._command_exists('dot'):
                with tempfile.NamedTemporaryFile(mode='w', suffix='.dot', delete=False) as f:
                    f.write(content)
                    input_path = f.name
                
                try:
                    cmd = ['dot', '-T' + output_format, input_path, '-o', str(output_path)]
                    subprocess.run(cmd, check=True)
                    console.print(f"[green]✓[/green] Rendered to {output_path}")
                    return str(output_path)
                finally:
                    os.unlink(input_path)
            else:
                # Save as DOT file
                output_path = output_path.with_suffix('.dot')
                output_path.write_text(content)
                return str(output_path)
    
    def render_to_html(self, diagrams: Dict[str, str], 
                       output_path: str,
                       title: str = "Architecture Diagrams") -> str:
        """Render multiple diagrams to an interactive HTML page."""
        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"<title>{title}</title>",
            '<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>',
            '<script>mermaid.initialize({startOnLoad:true, theme:"dark"});</script>',
            """<style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: #1a1a2e;
                    color: #fff;
                    padding: 20px;
                    max-width: 1400px;
                    margin: 0 auto;
                }
                h1, h2 {
                    color: #4ecdc4;
                }
                .diagram {
                    background: #16213e;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 20px 0;
                    overflow-x: auto;
                }
                .mermaid {
                    text-align: center;
                }
                .tabs {
                    display: flex;
                    gap: 10px;
                    margin-bottom: 20px;
                }
                .tab {
                    padding: 10px 20px;
                    background: #0f3460;
                    border: none;
                    color: #fff;
                    cursor: pointer;
                    border-radius: 4px;
                }
                .tab.active {
                    background: #4ecdc4;
                    color: #1a1a2e;
                }
                .tab-content {
                    display: none;
                }
                .tab-content.active {
                    display: block;
                }
            </style>""",
            "</head>",
            "<body>",
            f"<h1>{title}</h1>",
        ]
        
        # Add tabs
        html_parts.append('<div class="tabs">')
        for i, name in enumerate(diagrams.keys()):
            active = 'active' if i == 0 else ''
            html_parts.append(f'<button class="tab {active}" onclick="showTab(\'{name}\')">{name}</button>')
        html_parts.append('</div>')
        
        # Add diagram content
        for i, (name, content) in enumerate(diagrams.items()):
            active = 'active' if i == 0 else ''
            html_parts.append(f'<div id="{name}" class="tab-content {active}">')
            html_parts.append(f'<h2>{name}</h2>')
            html_parts.append('<div class="diagram">')
            html_parts.append('<div class="mermaid">')
            html_parts.append(content)
            html_parts.append('</div>')
            html_parts.append('</div>')
            html_parts.append('</div>')
        
        # Add JavaScript for tabs
        html_parts.append("""
        <script>
        function showTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }
        </script>
        """)
        
        html_parts.extend(["</body>", "</html>"])
        
        html_content = '\n'.join(html_parts)
        Path(output_path).write_text(html_content)
        
        console.print(f"[green]✓[/green] HTML report saved to {output_path}")
        return output_path
    
    def render_to_pdf(self, diagrams: Dict[str, str], output_path: str) -> str:
        """Render diagrams to PDF using ReportLab."""
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib.units import inch
            from reportlab.pdfgen import canvas
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
            from reportlab.lib.enums import TA_CENTER
            
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            
            # Title
            title = Paragraph("<h1>Architecture Diagrams</h1>", styles['Heading1'])
            story.append(title)
            story.append(Spacer(1, 0.2*inch))
            
            # Render each diagram to PNG first, then add to PDF
            for name, content in diagrams.items():
                story.append(Paragraph(f"<h2>{name}</h2>", styles['Heading2']))
                story.append(Spacer(1, 0.1*inch))
                
                # Render diagram to temporary PNG
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                    png_path = f.name
                
                try:
                    self.render(content, png_path, 'mermaid')
                    
                    # Add to PDF
                    img = Image(png_path, width=6*inch, height=4*inch)
                    story.append(img)
                    story.append(Spacer(1, 0.2*inch))
                finally:
                    if os.path.exists(png_path):
                        os.unlink(png_path)
            
            doc.build(story)
            console.print(f"[green]✓[/green] PDF saved to {output_path}")
            return output_path
            
        except ImportError:
            console.print("[yellow]Warning:[/yellow] ReportLab not found. Saving as HTML instead.")
            return self.render_to_html(diagrams, output_path.replace('.pdf', '.html'))
    
    def batch_render(self, diagrams: Dict[str, str], 
                     output_dir: str,
                     formats: List[str] = None) -> Dict[str, List[str]]:
        """Render multiple diagrams in multiple formats."""
        formats = formats or ['svg', 'png']
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results: Dict[str, List[str]] = {}
        
        for name, content in diagrams.items():
            results[name] = []
            for fmt in formats:
                output_path = output_dir / f"{name}.{fmt}"
                try:
                    path = self.render(content, str(output_path), 'mermaid')
                    results[name].append(path)
                except Exception as e:
                    console.print(f"[red]Error rendering {name} to {fmt}:[/red] {e}")
        
        return results
    
    def watch_and_render(self, source_dir: str, output_dir: str,
                        pattern: str = "*.mmd"):
        """Watch source directory and re-render on changes."""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            
            class MermaidHandler(FileSystemEventHandler):
                def __init__(self, renderer, output_dir):
                    self.renderer = renderer
                    self.output_dir = Path(output_dir)
                
                def on_modified(self, event):
                    if event.src_path.endswith('.mmd'):
                        self._render_file(event.src_path)
                
                def on_created(self, event):
                    if event.src_path.endswith('.mmd'):
                        self._render_file(event.src_path)
                
                def _render_file(self, src_path):
                    content = Path(src_path).read_text()
                    name = Path(src_path).stem
                    
                    for fmt in ['svg', 'png']:
                        output_path = self.output_dir / f"{name}.{fmt}"
                        try:
                            self.renderer.render(content, str(output_path), 'mermaid')
                            console.print(f"[green]✓[/green] Rendered {name} to {fmt}")
                        except Exception as e:
                            console.print(f"[red]Error:[/red] {e}")
            
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            event_handler = MermaidHandler(self, output_dir)
            observer = Observer()
            observer.schedule(event_handler, source_dir, recursive=True)
            observer.start()
            
            console.print(f"[blue]Watching {source_dir} for changes...[/blue]")
            console.print("Press Ctrl+C to stop")
            
            try:
                while True:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                observer.stop()
            
            observer.join()
            
        except ImportError:
            console.print("[yellow]Warning:[/yellow] watchdog not installed. Cannot watch files.")
    
    def _command_exists(self, command: str) -> bool:
        """Check if a command exists in PATH."""
        try:
            subprocess.run(['which', command], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _install_mmdc(self):
        """Install mermaid-cli."""
        try:
            subprocess.run(['npm', 'install', '-g', '@mermaid-js/mermaid-cli'], 
                          check=True, capture_output=True)
            console.print("[green]✓[/green] mmdc installed successfully")
        except Exception as e:
            console.print(f"[red]Failed to install mmdc:[/red] {e}")
            console.print("Please install manually: npm install -g @mermaid-js/mermaid-cli")