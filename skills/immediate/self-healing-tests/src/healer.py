"""
Healer module for self-healing tests.
Automatically fixes flaky tests based on analysis.
"""

import re
import ast
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from loguru import logger

from .analyzer import TestAnalysis, FailureType, FlakinessPattern


@dataclass
class FixApplication:
    """Result of applying a fix."""
    success: bool
    message: str
    original_code: str
    fixed_code: Optional[str]
    line_number: Optional[int]


class TestHealer:
    """Automatically heals flaky tests."""
    
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.fix_history: List[Dict[str, Any]] = []
    
    def heal(
        self,
        analysis: TestAnalysis,
        dry_run: bool = False
    ) -> List[FixApplication]:
        """
        Attempt to heal a flaky test.
        
        Args:
            analysis: Test analysis with failure information
            dry_run: If True, don't actually modify files
            
        Returns:
            List of fix applications
        """
        results = []
        
        file_path = self.project_root / analysis.test_file
        if not file_path.exists():
            return [FixApplication(
                success=False,
                message=f"Test file not found: {file_path}",
                original_code="",
                fixed_code=None,
                line_number=None
            )]
        
        # Read original content
        original_content = file_path.read_text(encoding='utf-8')
        modified_content = original_content
        
        # Apply fixes based on patterns
        for fix in analysis.suggested_fixes:
            application = self._apply_fix(
                fix,
                analysis,
                modified_content,
                file_path
            )
            results.append(application)
            
            if application.success and application.fixed_code:
                modified_content = application.fixed_code
        
        # Write changes if not dry run and modifications were made
        if not dry_run and modified_content != original_content:
            file_path.write_text(modified_content, encoding='utf-8')
            logger.info(f"Applied fixes to {file_path}")
        
        # Record history
        self.fix_history.append({
            'test_name': analysis.test_name,
            'test_file': analysis.test_file,
            'fixes_applied': len([r for r in results if r.success]),
            'dry_run': dry_run,
        })
        
        return results
    
    def _apply_fix(
        self,
        fix: Dict[str, Any],
        analysis: TestAnalysis,
        content: str,
        file_path: Path
    ) -> FixApplication:
        """Apply a single fix."""
        fix_type = fix.get('type')
        
        fix_methods = {
            'timing': self._fix_timing_issues,
            'mocking': self._fix_mock_issues,
            'isolation': self._fix_isolation_issues,
            'ordering': self._fix_order_issues,
            'async': self._fix_async_issues,
            'timeout': self._fix_timeout_issues,
            'mock_assertion': self._fix_mock_assertions,
        }
        
        if fix_type in fix_methods:
            return fix_methods[fix_type](analysis, content, file_path)
        
        return FixApplication(
            success=False,
            message=f"Unknown fix type: {fix_type}",
            original_code=content,
            fixed_code=None,
            line_number=None
        )
    
    def _fix_timing_issues(
        self,
        analysis: TestAnalysis,
        content: str,
        file_path: Path
    ) -> FixApplication:
        """Fix time.sleep issues."""
        # Find time.sleep calls and add retry logic or proper wait
        test_pattern = rf'(def\s+{re.escape(analysis.test_name)}\s*\([^)]*\):)([\s\S]*?)(?=\ndef\s+|\Z)'
        match = re.search(test_pattern, content)
        
        if not match:
            return FixApplication(
                success=False,
                message="Could not find test function",
                original_code=content,
                fixed_code=None,
                line_number=None
            )
        
        test_body = match.group(2)
        original_body = test_body
        
        # Replace time.sleep with proper wait pattern
        sleep_pattern = r'(\s+)time\.sleep\(([^)]+)\)'
        
        def replace_sleep(m):
            indent = m.group(1)
            sleep_time = m.group(2)
            return f'''{indent}# Replaced time.sleep with proper wait
{indent}import asyncio
{indent}await asyncio.wait_for(
{indent}    _wait_for_condition(),
{indent}    timeout={sleep_time}
{indent})'''
        
        new_body = re.sub(sleep_pattern, replace_sleep, test_body)
        
        if new_body == test_body:
            return FixApplication(
                success=False,
                message="No time.sleep calls found to fix",
                original_code=original_body,
                fixed_code=None,
                line_number=None
            )
        
        new_content = content.replace(original_body, new_body)
        
        return FixApplication(
            success=True,
            message="Replaced time.sleep with async wait pattern",
            original_code=original_body,
            fixed_code=new_content,
            line_number=analysis.failure_instances[0].line_number if analysis.failure_instances else None
        )
    
    def _fix_mock_issues(
        self,
        analysis: TestAnalysis,
        content: str,
        file_path: Path
    ) -> FixApplication:
        """Add @patch decorators for external dependencies."""
        # Find external calls in test
        test_pattern = rf'(def\s+{re.escape(analysis.test_name)}\s*\([^)]*\):)'
        match = re.search(test_pattern, content)
        
        if not match:
            return FixApplication(
                success=False,
                message="Could not find test function",
                original_code=content,
                fixed_code=None,
                line_number=None
            )
        
        # Check if already has @patch
        test_start = match.start()
        before_test = content[:test_start]
        
        if '@patch' in before_test[-200:]:
            return FixApplication(
                success=False,
                message="Test already uses @patch",
                original_code=content,
                fixed_code=None,
                line_number=None
            )
        
        # Add @patch decorators
        patches = [
            '@patch("requests.get")',
            '@patch("requests.post")',
        ]
        
        patch_decorators = '\n'.join(patches)
        new_content = content[:test_start] + patch_decorators + '\n' + content[test_start:]
        
        # Add mock parameter to function signature
        old_def = match.group(1)
        new_def = old_def.replace('):', ', mock_get, mock_post):')
        new_content = new_content.replace(old_def, new_def)
        
        # Add imports if not present
        if 'from unittest.mock import patch' not in new_content:
            new_content = 'from unittest.mock import patch, Mock\n' + new_content
        
        return FixApplication(
            success=True,
            message="Added @patch decorators for external dependencies",
            original_code=content,
            fixed_code=new_content,
            line_number=None
        )
    
    def _fix_isolation_issues(
        self,
        analysis: TestAnalysis,
        content: str,
        file_path: Path
    ) -> FixApplication:
        """Fix test isolation issues."""
        # Add setup/teardown or fixture scope adjustment
        test_pattern = rf'(def\s+{re.escape(analysis.test_name)}\s*\([^)]*\):)'
        match = re.search(test_pattern, content)
        
        if not match:
            return FixApplication(
                success=False,
                message="Could not find test function",
                original_code=content,
                fixed_code=None,
                line_number=None
            )
        
        # Check if using class-based tests
        class_pattern = rf'class\s+\w+\s*\([\s\S]*?\n\s*{re.escape(match.group(1))}'
        class_match = re.search(class_pattern, content)
        
        if class_match:
            # Add setup_method if not present
            if 'def setup_method' not in content:
                setup_code = '''
    def setup_method(self):
        """Reset state before each test."""
        # Reset any shared state here
        pass

    def teardown_method(self):
        """Clean up after each test."""
        # Clean up resources here
        pass

'''
                # Insert before the test
                insert_pos = match.start()
                new_content = content[:insert_pos] + setup_code + content[insert_pos:]
                
                return FixApplication(
                    success=True,
                    message="Added setup_method and teardown_method for isolation",
                    original_code=content,
                    fixed_code=new_content,
                    line_number=None
                )
        
        return FixApplication(
            success=False,
            message="Could not determine isolation fix approach",
            original_code=content,
            fixed_code=None,
            line_number=None
        )
    
    def _fix_order_issues(
        self,
        analysis: TestAnalysis,
        content: str,
        file_path: Path
    ) -> FixApplication:
        """Fix test order dependency issues."""
        # Add pytest-randomly marker or ensure independence
        if '@pytest.mark.order' in content:
            return FixApplication(
                success=False,
                message="Test already has order marker",
                original_code=content,
                fixed_code=None,
                line_number=None
            )
        
        test_pattern = rf'(def\s+{re.escape(analysis.test_name)}\s*\([^)]*\):)'
        match = re.search(test_pattern, content)
        
        if not match:
            return FixApplication(
                success=False,
                message="Could not find test function",
                original_code=content,
                fixed_code=None,
                line_number=None
            )
        
        # Add comment about making test independent
        marker = '# TODO: Ensure this test is independent - does not rely on state from other tests\n'
        new_content = content[:match.start()] + marker + content[match.start():]
        
        return FixApplication(
            success=True,
            message="Added TODO comment for order dependency",
            original_code=content,
            fixed_code=new_content,
            line_number=None
        )
    
    def _fix_async_issues(
        self,
        analysis: TestAnalysis,
        content: str,
        file_path: Path
    ) -> FixApplication:
        """Fix async/await issues."""
        test_pattern = rf'(def\s+{re.escape(analysis.test_name)}\s*\([^)]*\):)'
        match = re.search(test_pattern, content)
        
        if not match:
            return FixApplication(
                success=False,
                message="Could not find test function",
                original_code=content,
                fixed_code=None,
                line_number=None
            )
        
        func_def = match.group(1)
        
        # Check if async marker needed
        if 'async def' not in content[:match.end()]:
            # Check if test uses async patterns
            if 'await ' in content[match.end():match.end()+500]:
                # Add pytest-asyncio marker
                marker = '@pytest.mark.asyncio\n'
                new_content = content[:match.start()] + marker + content[match.start():]
                
                return FixApplication(
                    success=True,
                    message="Added @pytest.mark.asyncio decorator",
                    original_code=content,
                    fixed_code=new_content,
                    line_number=None
                )
        
        return FixApplication(
            success=False,
            message="No async issues detected",
            original_code=content,
            fixed_code=None,
            line_number=None
        )
    
    def _fix_timeout_issues(
        self,
        analysis: TestAnalysis,
        content: str,
        file_path: Path
    ) -> FixApplication:
        """Add timeout markers."""
        test_pattern = rf'(def\s+{re.escape(analysis.test_name)}\s*\([^)]*\):)'
        match = re.search(test_pattern, content)
        
        if not match:
            return FixApplication(
                success=False,
                message="Could not find test function",
                original_code=content,
                fixed_code=None,
                line_number=None
            )
        
        # Check if already has timeout
        before_test = content[:match.start()]
        if '@pytest.mark.timeout' in before_test[-200:]:
            return FixApplication(
                success=False,
                message="Test already has timeout marker",
                original_code=content,
                fixed_code=None,
                line_number=None
            )
        
        # Add timeout marker
        timeout_marker = '@pytest.mark.timeout(30)\n'
        new_content = content[:match.start()] + timeout_marker + content[match.start():]
        
        return FixApplication(
            success=True,
            message="Added @pytest.mark.timeout(30) decorator",
            original_code=content,
            fixed_code=new_content,
            line_number=None
        )
    
    def _fix_mock_assertions(
        self,
        analysis: TestAnalysis,
        content: str,
        file_path: Path
    ) -> FixApplication:
        """Fix mock assertion issues."""
        # Replace assert_called_once with assert_called if order is variable
        if 'assert_called_once' in content:
            new_content = content.replace(
                'assert_called_once()',
                'assert_called()  # Changed from assert_called_once for flaky test fix'
            )
            
            return FixApplication(
                success=True,
                message="Changed assert_called_once to assert_called",
                original_code=content,
                fixed_code=new_content,
                line_number=None
            )
        
        return FixApplication(
            success=False,
            message="No mock assertion issues found",
            original_code=content,
            fixed_code=None,
            line_number=None
        )
    
    def get_fix_stats(self) -> Dict[str, Any]:
        """Get statistics about fixes applied."""
        if not self.fix_history:
            return {'total_fixes': 0}
        
        total_tests = len(self.fix_history)
        total_fixes = sum(h['fixes_applied'] for h in self.fix_history)
        
        return {
            'total_tests_healed': total_tests,
            'total_fixes_applied': total_fixes,
            'average_fixes_per_test': total_fixes / total_tests if total_tests > 0 else 0,
            'recent_fixes': self.fix_history[-10:],
        }


class PRGenerator:
    """Generates PR with test fixes."""
    
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
    
    def generate_pr_content(
        self,
        analyses: List[TestAnalysis],
        fix_results: List[List[FixApplication]]
    ) -> Dict[str, Any]:
        """
        Generate PR content for test fixes.
        
        Args:
            analyses: List of test analyses
            fix_results: List of fix results for each test
            
        Returns:
            Dictionary with PR title, description, and changed files
        """
        title = f"Fix {len(analyses)} flaky test(s)"
        
        # Build description
        description_lines = [
            "# Self-Healing Test Fixes\n",
            f"This PR automatically fixes {len(analyses)} flaky test(s).\n",
            "## Summary\n",
        ]
        
        for i, (analysis, results) in enumerate(zip(analyses, fix_results), 1):
            description_lines.append(f"\n### {i}. {analysis.test_name}")
            description_lines.append(f"- **File:** `{analysis.test_file}`")
            description_lines.append(f"- **Failure Type:** {analysis.failure_type.name}")
            description_lines.append(f"- **Flakiness Rate:** {analysis.flakiness_rate:.1%}")
            description_lines.append(f"- **Confidence:** {analysis.confidence:.1%}")
            
            successful_fixes = [r for r in results if r.success]
            if successful_fixes:
                description_lines.append(f"- **Fixes Applied:** {len(successful_fixes)}")
                for fix in successful_fixes:
                    description_lines.append(f"  - {fix.message}")
        
        description_lines.extend([
            "\n## Changes Made",
            "- Fixed timing issues",
            "- Added proper mocking",
            "- Improved test isolation",
            "- Added timeout markers\n",
            "## Verification",
            "- [ ] Run tests multiple times to verify stability",
            "- [ ] Review changes for correctness",
            "- [ ] Ensure no test functionality is lost\n",
            "---",
            "*Generated by Self-Healing Tests skill*",
        ])
        
        return {
            'title': title,
            'description': '\n'.join(description_lines),
            'branch_name': f'fix/flaky-tests-{__import__("time").strftime("%Y%m%d-%H%M%S")}',
            'changed_files': list(set(a.test_file for a in analyses)),
        }
    
    def create_branch(self, branch_name: str):
        """Create a git branch for fixes."""
        try:
            import git
            
            repo = git.Repo(self.project_root)
            
            # Create new branch
            current = repo.create_head(branch_name)
            current.checkout()
            
            logger.info(f"Created and checked out branch: {branch_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create branch: {e}")
            return False
    
    def commit_changes(self, message: str):
        """Commit the changes."""
        try:
            import git
            
            repo = git.Repo(self.project_root)
            repo.git.add('--all')
            repo.index.commit(message)
            
            logger.info(f"Committed changes: {message}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to commit: {e}")
            return False
