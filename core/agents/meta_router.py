#!/usr/bin/env python3
"""
Agent 1: Meta-Router
Intelligent stack detection and routing
"""

import os
import json
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class StackDetection:
    primary_stack: str
    frontend_framework: str
    backend_type: str
    database: str
    mobile_framework: str
    build_tool: str
    automation_potential: float
    estimated_build_time_minutes: int


class MetaRouterAgent:
    """
    First agent in the pipeline.
    Analyzes repository and routes to appropriate specialist agents.
    """
    
    def __init__(self):
        self.name = "Meta-Router"
        self.capabilities = [
            "repo_analysis",
            "stack_detection", 
            "routing_logic",
            "hygiene_check",
            "complexity_assessment"
        ]
    
    async def analyze_repository(self, repo_path: str) -> Dict:
        """Analyze repository structure and detect stack"""
        
        if not os.path.exists(repo_path):
            return {"error": "Repository path does not exist"}
        
        # Detect files
        files = self._scan_files(repo_path)
        
        # Detect stack
        stack = self._detect_stack(files, repo_path)
        
        # Check hygiene
        hygiene = self._check_hygiene(files, repo_path)
        
        # Assess complexity
        complexity = self._assess_complexity(files, repo_path)
        
        return {
            "stack_detection": stack,
            "hygiene_score": hygiene,
            "complexity": complexity,
            "routing_decision": self._make_routing_decision(stack, complexity),
            "files_found": files
        }
    
    def _scan_files(self, repo_path: str) -> Dict[str, List[str]]:
        """Scan repository for key files"""
        files = {
            "config": [],
            "source": [],
            "test": [],
            "docs": [],
            "dependencies": []
        }
        
        for root, dirs, filenames in os.walk(repo_path):
            # Skip node_modules and other common ignore dirs
            dirs[:] = [d for d in dirs if d not in ['node_modules', '.git', '__pycache__', '.venv']]
            
            for filename in filenames:
                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(filepath, repo_path)
                
                # Categorize files
                if filename.endswith(('.json', '.yaml', '.yml', '.toml', '.config.js', '.config.ts')):
                    files["config"].append(rel_path)
                elif filename.endswith(('.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs')):
                    files["source"].append(rel_path)
                elif filename.endswith(('.test.js', '.test.ts', '.spec.js', '.spec.ts', '_test.py')):
                    files["test"].append(rel_path)
                elif filename.endswith(('.md', '.rst', '.txt')):
                    files["docs"].append(rel_path)
                elif filename in ['package.json', 'requirements.txt', 'Cargo.toml', 'go.mod']:
                    files["dependencies"].append(rel_path)
        
        return files
    
    def _detect_stack(self, files: Dict, repo_path: str) -> StackDetection:
        """Detect technology stack from files"""
        
        config_files = [f.lower() for f in files["config"]]
        dep_files = [f.lower() for f in files["dependencies"]]
        source_files = [f.lower() for f in files["source"]]
        
        # Detect mobile framework
        mobile_framework = "none"
        if any('capacitor' in f for f in config_files):
            mobile_framework = "capacitor"
        elif any('expo' in f for f in dep_files + config_files):
            mobile_framework = "expo"
        elif any('flutter' in f for f in config_files):
            mobile_framework = "flutter"
        
        # Detect frontend framework
        frontend_framework = "unknown"
        if any('react' in f or 'react' in self._read_deps(repo_path) for f in dep_files):
            frontend_framework = "react"
        elif any('vue' in f for f in dep_files):
            frontend_framework = "vue"
        elif any('svelte' in f for f in dep_files):
            frontend_framework = "svelte"
        elif any('angular' in f for f in dep_files):
            frontend_framework = "angular"
        
        # Detect backend
        backend_type = "none"
        if any('fastapi' in f or 'fastapi' in self._read_deps(repo_path) for f in dep_files):
            backend_type = "fastapi"
        elif any('django' in f for f in dep_files):
            backend_type = "django"
        elif any('express' in f for f in dep_files):
            backend_type = "express"
        elif any('flask' in f for f in dep_files):
            backend_type = "flask"
        
        # Detect database
        database = "none"
        if any('supabase' in f for f in dep_files):
            database = "supabase"
        elif any('mongodb' in f for f in dep_files):
            database = "mongodb"
        elif any('postgresql' in f or 'postgres' in f for f in dep_files):
            database = "postgresql"
        elif any('firebase' in f for f in dep_files):
            database = "firebase"
        
        # Detect build tool
        build_tool = "unknown"
        if any('vite' in f for f in config_files):
            build_tool = "vite"
        elif any('webpack' in f for f in config_files):
            build_tool = "webpack"
        elif any('parcel' in f for f in config_files):
            build_tool = "parcel"
        
        # Determine primary stack
        if mobile_framework == "capacitor":
            primary_stack = "capacitor"
            automation_potential = 0.70
        elif mobile_framework == "expo":
            primary_stack = "expo"
            automation_potential = 0.95
        elif mobile_framework == "flutter":
            primary_stack = "flutter"
            automation_potential = 0.85
        elif frontend_framework != "unknown":
            primary_stack = "web"
            automation_potential = 0.98
        else:
            primary_stack = "unknown"
            automation_potential = 0.50
        
        return StackDetection(
            primary_stack=primary_stack,
            frontend_framework=frontend_framework,
            backend_type=backend_type,
            database=database,
            mobile_framework=mobile_framework,
            build_tool=build_tool,
            automation_potential=automation_potential,
            estimated_build_time_minutes=self._estimate_build_time(files, automation_potential)
        )
    
    def _read_deps(self, repo_path: str) -> str:
        """Read dependency files to detect packages"""
        content = ""
        package_json = os.path.join(repo_path, "package.json")
        requirements_txt = os.path.join(repo_path, "requirements.txt")
        
        if os.path.exists(package_json):
            try:
                with open(package_json, 'r') as f:
                    content += f.read().lower()
            except:
                pass
        
        if os.path.exists(requirements_txt):
            try:
                with open(requirements_txt, 'r') as f:
                    content += f.read().lower()
            except:
                pass
        
        return content
    
    def _estimate_build_time(self, files: Dict, automation: float) -> int:
        """Estimate build time based on complexity"""
        source_count = len(files["source"])
        test_count = len(files["test"])
        
        # Base time
        base_time = 30  # minutes
        
        # Add time per source file
        file_time = source_count * 2
        
        # Add time for tests
        test_time = test_count * 1
        
        # Adjust for automation potential
        total = (base_time + file_time + test_time) * (1 - automation * 0.5)
        
        return max(15, int(total))  # Minimum 15 minutes
    
    def _check_hygiene(self, files: Dict, repo_path: str) -> Dict:
        """Check repository hygiene"""
        checks = {
            "has_readme": any('readme' in f.lower() for f in files["docs"]),
            "has_gitignore": os.path.exists(os.path.join(repo_path, ".gitignore")),
            "has_license": any('license' in f.lower() for f in files["docs"]),
            "has_tests": len(files["test"]) > 0,
            "has_ci_config": any('.github' in f or '.gitlab' in f for f in files["config"]),
            "has_env_example": any('.env' in f and 'example' in f.lower() for f in files["config"])
        }
        
        score = sum(checks.values()) / len(checks)
        
        return {
            "score": score,
            "checks": checks,
            "recommendations": [
                k.replace("has_", "Add ") for k, v in checks.items() if not v
            ]
        }
    
    def _assess_complexity(self, files: Dict, repo_path: str) -> Dict:
        """Assess project complexity"""
        source_count = len(files["source"])
        
        if source_count < 20:
            level = "simple"
            description = "Small project, straightforward implementation"
        elif source_count < 100:
            level = "moderate"
            description = "Medium project, some complexity to manage"
        elif source_count < 500:
            level = "complex"
            description = "Large project, requires careful architecture"
        else:
            level = "enterprise"
            description = "Very large project, extensive planning required"
        
        return {
            "level": level,
            "source_files": source_count,
            "test_files": len(files["test"]),
            "description": description
        }
    
    def _make_routing_decision(self, stack: StackDetection, complexity: Dict) -> Dict:
        """Decide which agents to route to"""
        
        agents_needed = []
        
        # Always need planning
        agents_needed.append({
            "agent": "planning",
            "reason": "Architecture and spec generation required"
        })
        
        # Frontend if web/mobile
        if stack.frontend_framework != "unknown":
            agents_needed.append({
                "agent": "frontend",
                "reason": f"{stack.frontend_framework} frontend detected"
            })
        
        # Backend if API/server detected
        if stack.backend_type != "none":
            agents_needed.append({
                "agent": "backend",
                "reason": f"{stack.backend_type} backend detected"
            })
        
        # Testing always
        agents_needed.append({
            "agent": "testing",
            "reason": "Quality assurance required"
        })
        
        # DevOps if complex or has deployment needs
        if complexity["level"] in ["complex", "enterprise"]:
            agents_needed.append({
                "agent": "devops",
                "reason": f"{complexity['level']} project needs CI/CD"
            })
        
        return {
            "agents_needed": agents_needed,
            "parallel_execution": len(agents_needed) > 2,
            "estimated_total_time": stack.estimated_build_time_minutes * len(agents_needed) // 2
        }


if __name__ == "__main__":
    import asyncio
    
    async def test():
        agent = MetaRouterAgent()
        
        # Test with current directory
        result = await agent.analyze_repository("/home/teacherchris37/MasterBuilder7")
        
        print("Meta-Router Analysis:")
        print(json.dumps(result, indent=2, default=str))
    
    asyncio.run(test())
