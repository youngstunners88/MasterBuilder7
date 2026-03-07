"""Security report generator."""

import json
import html
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
from dataclasses import asdict

from jinja2 import Template
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree

from .scanner import ScanResult, Vulnerability, Severity

console = Console()


class SecurityReporter:
    """Generates security reports in various formats."""
    
    HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            line-height: 1.6;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 2rem; }
        header {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            padding: 2rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            border: 1px solid #334155;
        }
        h1 { color: #38bdf8; font-size: 2.5rem; margin-bottom: 0.5rem; }
        .meta { color: #94a3b8; font-size: 0.9rem; }
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .stat-card {
            background: #1e293b;
            padding: 1.5rem;
            border-radius: 8px;
            text-align: center;
            border: 1px solid #334155;
        }
        .stat-number {
            font-size: 3rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }
        .stat-label { color: #94a3b8; font-size: 0.9rem; text-transform: uppercase; }
        .critical { color: #ef4444; }
        .high { color: #f97316; }
        .medium { color: #eab308; }
        .low { color: #22c55e; }
        .info { color: #3b82f6; }
        .vuln-list { margin-top: 2rem; }
        .vuln-item {
            background: #1e293b;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            border-left: 4px solid;
            border-color: #475569;
        }
        .vuln-item.critical { border-color: #ef4444; }
        .vuln-item.high { border-color: #f97316; }
        .vuln-item.medium { border-color: #eab308; }
        .vuln-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        .vuln-title { font-size: 1.2rem; font-weight: 600; color: #f8fafc; }
        .vuln-severity {
            padding: 0.25rem 0.75rem;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        .vuln-details { margin-top: 1rem; }
        .vuln-details p { margin-bottom: 0.5rem; }
        .vuln-details strong { color: #94a3b8; }
        .code-snippet {
            background: #0f172a;
            padding: 1rem;
            border-radius: 6px;
            overflow-x: auto;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.9rem;
            margin: 1rem 0;
            border: 1px solid #334155;
        }
        .remediation {
            background: #064e3b;
            border: 1px solid #059669;
            padding: 1rem;
            border-radius: 6px;
            margin-top: 1rem;
        }
        .remediation-title { color: #34d399; font-weight: 600; margin-bottom: 0.5rem; }
        .references { margin-top: 1rem; }
        .references a { color: #38bdf8; text-decoration: none; }
        .references a:hover { text-decoration: underline; }
        .filter-bar {
            display: flex;
            gap: 1rem;
            margin-bottom: 2rem;
            flex-wrap: wrap;
        }
        .filter-btn {
            background: #334155;
            border: none;
            color: #e2e8f0;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            cursor: pointer;
            transition: background 0.2s;
        }
        .filter-btn:hover, .filter-btn.active { background: #475569; }
        .footer {
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: 1px solid #334155;
            color: #64748b;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔒 {{ title }}</h1>
            <p class="meta">
                Target: {{ target_path }} | 
                Scanned: {{ scan_time }} | 
                Duration: {{ duration }}s | 
                Scanners: {{ scanners }}
            </p>
        </header>
        
        <div class="summary">
            <div class="stat-card">
                <div class="stat-number critical">{{ summary.critical }}</div>
                <div class="stat-label">Critical</div>
            </div>
            <div class="stat-card">
                <div class="stat-number high">{{ summary.high }}</div>
                <div class="stat-label">High</div>
            </div>
            <div class="stat-card">
                <div class="stat-number medium">{{ summary.medium }}</div>
                <div class="stat-label">Medium</div>
            </div>
            <div class="stat-card">
                <div class="stat-number low">{{ summary.low }}</div>
                <div class="stat-label">Low</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ summary.total }}</div>
                <div class="stat-label">Total</div>
            </div>
        </div>
        
        <div class="filter-bar">
            <button class="filter-btn active" onclick="filterVulns('all')">All</button>
            <button class="filter-btn" onclick="filterVulns('critical')">Critical</button>
            <button class="filter-btn" onclick="filterVulns('high')">High</button>
            <button class="filter-btn" onclick="filterVulns('medium')">Medium</button>
            <button class="filter-btn" onclick="filterVulns('low')">Low</button>
        </div>
        
        <div class="vuln-list">
            {% for vuln in vulnerabilities %}
            <div class="vuln-item {{ vuln.severity }}" data-severity="{{ vuln.severity }}">
                <div class="vuln-header">
                    <span class="vuln-title">{{ vuln.id }}: {{ vuln.title }}</span>
                    <span class="vuln-severity {{ vuln.severity }}">{{ vuln.severity.upper() }}</span>
                </div>
                <div class="vuln-details">
                    <p><strong>Category:</strong> {{ vuln.category }}</p>
                    <p><strong>File:</strong> {{ vuln.file_path }}:{{ vuln.line_number }}</p>
                    <p><strong>Scanner:</strong> {{ vuln.scanner }} | <strong>Confidence:</strong> {{ vuln.confidence }}</p>
                    {% if vuln.cwe_id %}
                    <p><strong>CWE:</strong> {{ vuln.cwe_id }}</p>
                    {% endif %}
                    {% if vuln.cvss_score %}
                    <p><strong>CVSS Score:</strong> {{ vuln.cvss_score }}</p>
                    {% endif %}
                </div>
                <div class="code-snippet">{{ vuln.code_snippet }}</div>
                <div class="remediation">
                    <div class="remediation-title">🔧 Remediation</div>
                    <p>{{ vuln.remediation }}</p>
                </div>
                {% if vuln.references %}
                <div class="references">
                    <strong>References:</strong>
                    {% for ref in vuln.references %}
                    <br><a href="{{ ref }}" target="_blank">{{ ref }}</a>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        
        <div class="footer">
            <p>Generated by Security Oracle | RobeetsDay Project</p>
        </div>
    </div>
    
    <script>
        function filterVulns(severity) {
            const items = document.querySelectorAll('.vuln-item');
            const buttons = document.querySelectorAll('.filter-btn');
            
            buttons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            
            items.forEach(item => {
                if (severity === 'all' || item.dataset.severity === severity) {
                    item.style.display = 'block';
                } else {
                    item.style.display = 'none';
                }
            });
        }
    </script>
</body>
</html>
"""
    
    def __init__(self, result: ScanResult):
        self.result = result
    
    def to_html(self, title: str = "Security Scan Report") -> str:
        """Generate HTML report."""
        template = Template(self.HTML_TEMPLATE)
        
        data = {
            'title': title,
            'target_path': html.escape(self.result.target_path),
            'scan_time': self.result.scan_time.strftime('%Y-%m-%d %H:%M:%S'),
            'duration': f"{self.result.duration_seconds:.2f}",
            'scanners': ', '.join(self.result.scanners_used),
            'summary': {
                'critical': self.result.critical_count,
                'high': self.result.high_count,
                'medium': len(self.result.get_by_severity(Severity.MEDIUM)),
                'low': len(self.result.get_by_severity(Severity.LOW)),
                'info': len(self.result.get_by_severity(Severity.INFO)),
                'total': len(self.result.vulnerabilities)
            },
            'vulnerabilities': [
                {
                    'id': html.escape(v.id),
                    'title': html.escape(v.title),
                    'severity': v.severity.value,
                    'category': v.category.value.replace('_', ' ').title(),
                    'file_path': html.escape(v.file_path),
                    'line_number': v.line_number,
                    'scanner': v.scanner,
                    'confidence': v.confidence,
                    'cwe_id': v.cwe_id or '',
                    'cvss_score': v.cvss_score or '',
                    'code_snippet': html.escape(v.code_snippet),
                    'remediation': html.escape(v.remediation),
                    'references': v.references
                }
                for v in sorted(self.result.vulnerabilities, 
                               key=lambda x: {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4}.get(x.severity.value, 5))
            ]
        }
        
        return template.render(**data)
    
    def to_json(self) -> str:
        """Generate JSON report."""
        return json.dumps(self.result.to_dict(), indent=2)
    
    def to_sarif(self) -> Dict[str, Any]:
        """Generate SARIF (Static Analysis Results Interchange Format) report."""
        sarif = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "Security Oracle",
                        "version": "1.0.0",
                        "informationUri": "https://github.com/robeetsday/security-oracle"
                    }
                },
                "results": []
            }]
        }
        
        for vuln in self.result.vulnerabilities:
            result = {
                "ruleId": vuln.id,
                "message": {"text": vuln.description},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": vuln.file_path},
                        "region": {
                            "startLine": vuln.line_number,
                            "startColumn": vuln.column
                        }
                    }
                }],
                "level": self._sarif_level(vuln.severity),
                "properties": {
                    "category": vuln.category.value,
                    "confidence": vuln.confidence,
                    "cwe": vuln.cwe_id
                }
            }
            sarif["runs"][0]["results"].append(result)
        
        return sarif
    
    def to_markdown(self) -> str:
        """Generate Markdown report."""
        lines = [
            "# 🔒 Security Scan Report",
            "",
            f"**Target:** `{self.result.target_path}`",
            f"**Scan Time:** {self.result.scan_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Duration:** {self.result.duration_seconds:.2f}s",
            f"**Scanners:** {', '.join(self.result.scanners_used)}",
            "",
            "## Summary",
            "",
            "| Severity | Count |",
            "|----------|-------|",
            f"| 🔴 Critical | {self.result.critical_count} |",
            f"| 🟠 High | {self.result.high_count} |",
            f"| 🟡 Medium | {len(self.result.get_by_severity(Severity.MEDIUM))} |",
            f"| 🟢 Low | {len(self.result.get_by_severity(Severity.LOW))} |",
            f"| 🔵 Info | {len(self.result.get_by_severity(Severity.INFO))} |",
            f"| **Total** | **{len(self.result.vulnerabilities)}** |",
            "",
            "## Vulnerabilities",
            ""
        ]
        
        # Sort by severity
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4}
        sorted_vulns = sorted(self.result.vulnerabilities, 
                             key=lambda x: severity_order.get(x.severity.value, 5))
        
        for vuln in sorted_vulns:
            emoji = {
                'critical': '🔴',
                'high': '🟠',
                'medium': '🟡',
                'low': '🟢',
                'info': '🔵'
            }.get(vuln.severity.value, '⚪')
            
            lines.extend([
                f"### {emoji} {vuln.id}: {vuln.title}",
                "",
                f"- **Severity:** {vuln.severity.value.upper()}",
                f"- **Category:** {vuln.category.value.replace('_', ' ').title()}",
                f"- **Location:** `{vuln.file_path}:{vuln.line_number}`",
                f"- **Scanner:** {vuln.scanner}",
                f"- **Confidence:** {vuln.confidence}",
                "",
                "**Code:**",
                f"```python\n{vuln.code_snippet}\n```",
                "",
                "**Remediation:**",
                f"{vuln.remediation}",
                ""
            ])
            
            if vuln.references:
                lines.extend([
                    "**References:**",
                    *[f"- {ref}" for ref in vuln.references],
                    ""
                ])
            
            lines.append("---")
        
        return '\n'.join(lines)
    
    def display_console(self):
        """Display report in console."""
        # Summary panel
        summary_text = (
            f"Target: {self.result.target_path}\n"
            f"Scan Time: {self.result.scan_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Duration: {self.result.duration_seconds:.2f}s\n"
            f"Scanners: {', '.join(self.result.scanners_used)}"
        )
        
        console.print(Panel(summary_text, title="🔒 Security Scan Summary", border_style="cyan"))
        
        # Statistics table
        table = Table(title="Vulnerability Summary")
        table.add_column("Severity", style="cyan")
        table.add_column("Count", justify="right")
        
        severities = [
            ("Critical", self.result.critical_count, "red"),
            ("High", self.result.high_count, "orange3"),
            ("Medium", len(self.result.get_by_severity(Severity.MEDIUM)), "yellow"),
            ("Low", len(self.result.get_by_severity(Severity.LOW)), "green"),
            ("Info", len(self.result.get_by_severity(Severity.INFO)), "blue"),
        ]
        
        for sev, count, color in severities:
            table.add_row(f"[{color}]{sev}[/{color}]", str(count))
        
        table.add_row("[bold]Total[/bold]", f"[bold]{len(self.result.vulnerabilities)}[/bold]")
        console.print(table)
        
        # Critical and High vulnerabilities
        critical_high = [v for v in self.result.vulnerabilities 
                        if v.severity in (Severity.CRITICAL, Severity.HIGH)]
        
        if critical_high:
            console.print("\n[bold red]Critical & High Priority Issues:[/bold red]")
            
            for vuln in critical_high[:10]:  # Show top 10
                console.print(f"\n  [red]•[/red] [bold]{vuln.title}[/bold]")
                console.print(f"    Location: {vuln.file_path}:{vuln.line_number}")
                console.print(f"    Scanner: {vuln.scanner}")
            
            if len(critical_high) > 10:
                console.print(f"\n  ... and {len(critical_high) - 10} more")
    
    def save(self, output_path: str, format: str = "html"):
        """Save report to file."""
        output_path = Path(output_path)
        
        if format == "html":
            content = self.to_html()
        elif format == "json":
            content = self.to_json()
        elif format == "sarif":
            content = json.dumps(self.to_sarif(), indent=2)
        elif format == "md" or format == "markdown":
            content = self.to_markdown()
        else:
            raise ValueError(f"Unknown format: {format}")
        
        output_path.write_text(content)
        console.print(f"[green]✓[/green] Report saved to {output_path}")
        return str(output_path)
    
    def create_github_issue(self, repo_full_name: str, github_token: str,
                           vuln: Optional[Vulnerability] = None):
        """Create GitHub issue for vulnerability."""
        from github import Github
        
        g = Github(github_token)
        repo = g.get_repo(repo_full_name)
        
        if vuln:
            vulns = [vuln]
        else:
            # Create issues for all critical/high vulnerabilities
            vulns = [v for v in self.result.vulnerabilities 
                    if v.severity in (Severity.CRITICAL, Severity.HIGH)]
        
        for v in vulns:
            title = f"[Security] {v.id}: {v.title[:60]}"
            body = f"""## Security Vulnerability Detected

**ID:** {v.id}
**Severity:** {v.severity.value.upper()}
**Category:** {v.category.value.replace('_', ' ').title()}
**Confidence:** {v.confidence}

### Location
`{v.file_path}:{v.line_number}`

### Description
{v.description}

### Code
```{v.category.value.split('_')[0] if '_' in v.category.value else 'python'}
{v.code_snippet}
```

### Remediation
{v.remediation}

### References
{chr(10).join(f"- {ref}" for ref in v.references) if v.references else "- None provided"}

---
*This issue was automatically generated by Security Oracle*
"""
            
            try:
                labels = ['security', v.severity.value]
                if v.cwe_id:
                    labels.append(v.cwe_id.lower())
                
                issue = repo.create_issue(title=title, body=body, labels=labels)
                console.print(f"[green]✓[/green] Created issue #{issue.number}: {title[:50]}...")
            except Exception as e:
                console.print(f"[red]Failed to create issue:[/red] {e}")
    
    def _sarif_level(self, severity: Severity) -> str:
        """Convert severity to SARIF level."""
        mapping = {
            Severity.CRITICAL: "error",
            Severity.HIGH: "error",
            Severity.MEDIUM: "warning",
            Severity.LOW: "note",
            Severity.INFO: "none"
        }
        return mapping.get(severity, "warning")