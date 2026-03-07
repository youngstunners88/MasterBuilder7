"""
Pytest plugin for self-healing tests.
Integrates with pytest to detect and fix flaky tests.
"""

import time
from typing import List, Dict, Any, Optional
from pathlib import Path

import pytest
from _pytest.config import Config
from _pytest.reports import TestReport
from _pytest.nodes import Item
from loguru import logger

from .analyzer import FailureAnalyzer, TestAnalysis
from .healer import TestHealer, PRGenerator


class SelfHealingPlugin:
    """Pytest plugin for self-healing tests."""
    
    def __init__(
        self,
        project_root: Path,
        auto_heal: bool = False,
        dry_run: bool = True,
        generate_pr: bool = False,
        min_runs: int = 3,
        flakiness_threshold: float = 0.1
    ):
        self.project_root = Path(project_root)
        self.auto_heal = auto_heal
        self.dry_run = dry_run
        self.generate_pr = generate_pr
        self.min_runs = min_runs
        self.flakiness_threshold = flakiness_threshold
        
        self.analyzer = FailureAnalyzer()
        self.healer = TestHealer(self.project_root)
        self.pr_generator = PRGenerator(self.project_root)
        
        self.test_runs: Dict[str, int] = {}
        self.test_passes: Dict[str, int] = {}
        self.test_failures: Dict[str, int] = {}
        self.flaky_tests: List[TestAnalysis] = []
        self.fix_results: List[List] = []
    
    @pytest.hookimpl(tryfirst=True, hookwrapper=True)
    def pytest_runtest_makereport(self, item: Item, call):
        """Capture test results."""
        outcome = yield
        report = outcome.get_result()
        
        test_id = f"{item.fspath}::{item.name}"
        
        if report.when == "call":
            self.test_runs[test_id] = self.test_runs.get(test_id, 0) + 1
            
            if report.failed:
                self.test_failures[test_id] = self.test_failures.get(test_id, 0) + 1
                
                # Record failure details
                self.analyzer.record_failure(
                    test_name=item.name,
                    test_file=str(item.fspath),
                    error_type=report.longrepr.reprcrash.type_name if report.longrepr and report.longrepr.reprcrash else "Unknown",
                    error_message=str(report.longrepr.reprcrash.message) if report.longrepr and report.longrepr.reprcrash else "",
                    traceback=str(report.longrepr) if report.longrepr else "",
                    duration=report.duration,
                    timestamp=time.time()
                )
            else:
                self.test_passes[test_id] = self.test_passes.get(test_id, 0) + 1
                self.analyzer.record_success(
                    test_name=item.name,
                    test_file=str(item.fspath),
                    duration=report.duration
                )
    
    def pytest_sessionfinish(self, session, exitstatus):
        """Analyze results after test session."""
        logger.info("Self-healing analysis starting...")
        
        # Analyze each test that had multiple runs
        for test_id, run_count in self.test_runs.items():
            if run_count < self.min_runs:
                continue
            
            passes = self.test_passes.get(test_id, 0)
            failures = self.test_failures.get(test_id, 0)
            
            flakiness_rate = failures / run_count if run_count > 0 else 0
            
            if flakiness_rate >= self.flakiness_threshold:
                # Extract test file and name
                parts = test_id.split("::")
                test_file = parts[0]
                test_name = parts[1] if len(parts) > 1 else parts[0]
                
                analysis = self.analyzer.analyze_test(test_name, test_file)
                
                if analysis and analysis.confidence > 0.5:
                    self.flaky_tests.append(analysis)
        
        if self.flaky_tests:
            logger.info(f"Detected {len(self.flaky_tests)} flaky test(s)")
            self._handle_flaky_tests()
        else:
            logger.info("No flaky tests detected")
    
    def _handle_flaky_tests(self):
        """Handle detected flaky tests."""
        if self.auto_heal:
            logger.info("Auto-healing enabled, attempting fixes...")
            
            for analysis in self.flaky_tests:
                logger.info(f"Healing: {analysis.test_name}")
                results = self.healer.heal(analysis, dry_run=self.dry_run)
                self.fix_results.append(results)
                
                for result in results:
                    if result.success:
                        logger.info(f"  ✓ {result.message}")
                    else:
                        logger.warning(f"  ✗ {result.message}")
            
            # Generate PR if requested
            if self.generate_pr and not self.dry_run:
                self._create_pr()
        else:
            logger.info("Auto-healing disabled. Run with --auto-heal to fix tests.")
            self._report_flaky_tests()
    
    def _report_flaky_tests(self):
        """Report flaky tests without fixing."""
        print("\n" + "=" * 70)
        print("FLAKY TESTS DETECTED")
        print("=" * 70)
        
        for i, analysis in enumerate(self.flaky_tests, 1):
            print(f"\n{i}. {analysis.test_name}")
            print(f"   File: {analysis.test_file}")
            print(f"   Flakiness: {analysis.flakiness_rate:.1%}")
            print(f"   Failure Type: {analysis.failure_type.name}")
            print(f"   Confidence: {analysis.confidence:.1%}")
            print("   Suggested Fixes:")
            for fix in analysis.suggested_fixes[:3]:
                print(f"     - [{fix['type']}] {fix['description']}")
        
        print("\n" + "=" * 70)
        print("Run with --auto-heal to apply fixes")
        print("=" * 70 + "\n")
    
    def _create_pr(self):
        """Create PR with fixes."""
        pr_content = self.pr_generator.generate_pr_content(
            self.flaky_tests,
            self.fix_results
        )
        
        # Create branch
        if not self.pr_generator.create_branch(pr_content['branch_name']):
            logger.error("Failed to create branch for PR")
            return
        
        # Commit changes
        commit_message = f"Fix {len(self.flaky_tests)} flaky test(s)\n\n"
        commit_message += "Changes:\n"
        for analysis in self.flaky_tests:
            commit_message += f"- {analysis.test_name}: {analysis.failure_type.name}\n"
        
        if not self.pr_generator.commit_changes(commit_message):
            logger.error("Failed to commit changes")
            return
        
        logger.info(f"Created branch: {pr_content['branch_name']}")
        logger.info(f"PR Title: {pr_content['title']}")
        print("\n" + "=" * 70)
        print("PULL REQUEST READY")
        print("=" * 70)
        print(f"Branch: {pr_content['branch_name']}")
        print(f"Title: {pr_content['title']}")
        print("\nPush this branch and create a PR:")
        print(f"  git push origin {pr_content['branch_name']}")
        print("=" * 70 + "\n")


def pytest_addoption(parser):
    """Add pytest options for self-healing."""
    group = parser.getgroup("self-healing", "Self-healing tests")
    
    group.addoption(
        "--self-heal",
        action="store_true",
        default=False,
        help="Enable self-healing test detection"
    )
    
    group.addoption(
        "--auto-heal",
        action="store_true",
        default=False,
        help="Automatically fix flaky tests (requires --self-heal)"
    )
    
    group.addoption(
        "--heal-dry-run",
        action="store_true",
        default=True,
        help="Show fixes without applying them (default: True)"
    )
    
    group.addoption(
        "--heal-no-dry-run",
        action="store_false",
        dest="heal_dry_run",
        help="Apply fixes for real"
    )
    
    group.addoption(
        "--heal-generate-pr",
        action="store_true",
        default=False,
        help="Generate PR with fixes (requires --auto-heal and --heal-no-dry-run)"
    )
    
    group.addoption(
        "--heal-min-runs",
        type=int,
        default=3,
        help="Minimum test runs before considering flaky (default: 3)"
    )
    
    group.addoption(
        "--heal-threshold",
        type=float,
        default=0.1,
        help="Flakiness threshold (default: 0.1 = 10%)"
    )


def pytest_configure(config: Config):
    """Configure self-healing plugin."""
    if config.getoption("--self-heal"):
        plugin = SelfHealingPlugin(
            project_root=Path.cwd(),
            auto_heal=config.getoption("--auto-heal"),
            dry_run=config.getoption("--heal_dry_run"),
            generate_pr=config.getoption("--heal-generate_pr"),
            min_runs=config.getoption("--heal_min_runs"),
            flakiness_threshold=config.getoption("--heal_threshold")
        )
        config.pluginmanager.register(plugin, "self_healing_plugin")


# Export for use as pytest plugin
pytest_plugins = []
