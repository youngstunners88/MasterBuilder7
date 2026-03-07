#!/usr/bin/env python3
"""
APEX Self-Evaluation System v2.0
Production-ready agent performance evaluation with actionable recommendations

Evaluates agent output across five criteria:
- CODE_QUALITY: Syntax, complexity, style
- TEST_COVERAGE: Coverage percentage, test quality  
- PERFORMANCE: Efficiency, resource usage
- SECURITY: Vulnerabilities, best practices
- MAINTAINABILITY: Documentation, modularity

Author: APEX Agent Intelligence Team
Version: 2.0.0
"""

import ast
import hashlib
import json
import logging
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set, Callable

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import consensus engine for integration
try:
    from ..reliability.consensus_engine import (
        ConsensusEngine, ConsensusReport, ConsensusDecision, 
        VerificationResult, Finding, AgentType
    )
    CONSENSUS_AVAILABLE = True
except ImportError:
    CONSENSUS_AVAILABLE = False
    logger.warning("ConsensusEngine not available. Integration features disabled.")


class EvaluationCriteria(Enum):
    """
    Criteria types for agent performance evaluation
    
    Each criterion represents a critical dimension of code quality
    and agent effectiveness.
    """
    CODE_QUALITY = "code_quality"
    TEST_COVERAGE = "test_coverage"
    PERFORMANCE = "performance"
    SECURITY = "security"
    MAINTAINABILITY = "maintainability"
    
    @classmethod
    def all(cls) -> List['EvaluationCriteria']:
        """Return all evaluation criteria"""
        return [cls.CODE_QUALITY, cls.TEST_COVERAGE, cls.PERFORMANCE, 
                cls.SECURITY, cls.MAINTAINABILITY]


class Severity(Enum):
    """
    Severity levels for evaluation findings
    
    - CRITICAL: Must fix immediately
    - HIGH: Should fix before deployment
    - MEDIUM: Address in next iteration
    - LOW: Nice to have improvements
    - INFO: Informational only
    """
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    
    def weight(self) -> float:
        """Numerical weight for scoring calculations"""
        weights = {
            Severity.CRITICAL: 1.0,
            Severity.HIGH: 0.75,
            Severity.MEDIUM: 0.5,
            Severity.LOW: 0.25,
            Severity.INFO: 0.1
        }
        return weights[self]


class ScoreThreshold(Enum):
    """
    Score thresholds with action recommendations
    
    EXCELLENT (90-100): Proceed, extract patterns for future use
    GOOD (80-89): Proceed with minor recommendations
    ACCEPTABLE (70-79): Proceed with warnings
    NEEDS_IMPROVEMENT (60-69): Review required before proceeding
    FAILED (<60): Reject, trigger rollback
    """
    EXCELLENT = (90, "Proceed, extract patterns")
    GOOD = (80, "Proceed with minor recommendations")
    ACCEPTABLE = (70, "Proceed with warnings")
    NEEDS_IMPROVEMENT = (60, "Review required")
    FAILED = (0, "Reject, trigger rollback")
    
    def __init__(self, min_score: int, action: str):
        self.min_score = min_score
        self.action = action
    
    @classmethod
    def from_score(cls, score: float) -> 'ScoreThreshold':
        """Determine threshold level from score"""
        if score >= 90:
            return cls.EXCELLENT
        elif score >= 80:
            return cls.GOOD
        elif score >= 70:
            return cls.ACCEPTABLE
        elif score >= 60:
            return cls.NEEDS_IMPROVEMENT
        else:
            return cls.FAILED
    
    def should_proceed(self) -> bool:
        """Determine if evaluation result should proceed"""
        return self in [cls.EXCELLENT, cls.GOOD, cls.ACCEPTABLE]
    
    def should_rollback(self) -> bool:
        """Determine if rollback should be triggered"""
        return self == cls.FAILED


@dataclass
class FindingDetail:
    """Detailed finding from evaluation"""
    criteria: EvaluationCriteria
    severity: Severity
    category: str
    message: str
    location: Optional[str] = None
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    suggestion: Optional[str] = None
    fix_example: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert finding to dictionary"""
        return {
            'criteria': self.criteria.value,
            'severity': self.severity.value,
            'category': self.category,
            'message': self.message,
            'location': self.location,
            'line_number': self.line_number,
            'code_snippet': self.code_snippet,
            'suggestion': self.suggestion,
            'fix_example': self.fix_example
        }


@dataclass
class Recommendation:
    """Actionable recommendation for improvement"""
    priority: int  # 1-5, 1 being highest
    criteria: EvaluationCriteria
    title: str
    description: str
    action_items: List[str] = field(default_factory=list)
    estimated_effort: str = "medium"  # small, medium, large
    impact: str = "medium"  # low, medium, high
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert recommendation to dictionary"""
        return {
            'priority': self.priority,
            'criteria': self.criteria.value,
            'title': self.title,
            'description': self.description,
            'action_items': self.action_items,
            'estimated_effort': self.estimated_effort,
            'impact': self.impact
        }


@dataclass
class EvaluationResult:
    """
    Complete evaluation result for a single criterion
    
    Attributes:
        criteria: The evaluation criterion
        score: Score from 0-100
        passed: Whether the criterion passed evaluation
        findings: List of detailed findings
        recommendations: List of actionable recommendations
        severity: Overall severity of the evaluation
        metadata: Additional context and metrics
        timestamp: When evaluation occurred
    """
    criteria: EvaluationCriteria
    score: float  # 0-100
    passed: bool
    findings: List[FindingDetail] = field(default_factory=list)
    recommendations: List[Recommendation] = field(default_factory=list)
    severity: Severity = Severity.INFO
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def critical_findings(self) -> List[FindingDetail]:
        """Get critical severity findings"""
        return [f for f in self.findings if f.severity == Severity.CRITICAL]
    
    @property
    def high_findings(self) -> List[FindingDetail]:
        """Get high severity findings"""
        return [f for f in self.findings if f.severity == Severity.HIGH]
    
    @property
    def total_findings(self) -> int:
        """Total number of findings"""
        return len(self.findings)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            'criteria': self.criteria.value,
            'score': round(self.score, 2),
            'passed': self.passed,
            'severity': self.severity.value,
            'findings_count': len(self.findings),
            'findings': [f.to_dict() for f in self.findings],
            'recommendations': [r.to_dict() for r in self.recommendations],
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class EvaluationReport:
    """
    Comprehensive evaluation report across all criteria
    
    Includes individual criterion results, overall score,
    and integration with consensus engine results.
    """
    task_id: str
    agent_id: str
    overall_score: float
    threshold: ScoreThreshold
    results: Dict[EvaluationCriteria, EvaluationResult]
    consensus_report: Optional[Dict[str, Any]] = None
    should_rollback: bool = False
    patterns_extracted: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    execution_time_ms: float = 0.0
    
    @property
    def passed(self) -> bool:
        """Check if overall evaluation passed"""
        return self.threshold.should_proceed()
    
    @property
    def all_findings(self) -> List[FindingDetail]:
        """Get all findings across all criteria"""
        findings = []
        for result in self.results.values():
            findings.extend(result.findings)
        return sorted(findings, key=lambda f: f.severity.weight(), reverse=True)
    
    @property
    def all_recommendations(self) -> List[Recommendation]:
        """Get all recommendations sorted by priority"""
        recommendations = []
        for result in self.results.values():
            recommendations.extend(result.recommendations)
        return sorted(recommendations, key=lambda r: r.priority)
    
    def get_result(self, criteria: EvaluationCriteria) -> Optional[EvaluationResult]:
        """Get result for specific criterion"""
        return self.results.get(criteria)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary"""
        return {
            'task_id': self.task_id,
            'agent_id': self.agent_id,
            'overall_score': round(self.overall_score, 2),
            'threshold': {
                'level': self.threshold.name,
                'action': self.threshold.action,
                'should_proceed': self.threshold.should_proceed(),
                'should_rollback': self.threshold.should_rollback()
            },
            'passed': self.passed,
            'should_rollback': self.should_rollback,
            'results': {k.value: v.to_dict() for k, v in self.results.items()},
            'consensus_integration': self.consensus_report,
            'patterns_extracted': self.patterns_extracted,
            'timestamp': self.timestamp.isoformat(),
            'execution_time_ms': round(self.execution_time_ms, 2)
        }
    
    def to_markdown(self) -> str:
        """Generate markdown report for human readability"""
        lines = [
            f"# Self-Evaluation Report: {self.task_id}",
            "",
            f"**Agent ID:** {self.agent_id}",
            f"**Overall Score:** {self.overall_score:.1f}/100",
            f"**Threshold:** {self.threshold.name} - {self.threshold.action}",
            f"**Status:** {'✅ PASSED' if self.passed else '❌ FAILED'}",
            f"**Timestamp:** {self.timestamp.isoformat()}",
            "",
            "## Summary",
            "",
        ]
        
        # Add criterion summaries
        for criteria, result in self.results.items():
            status = "✅" if result.passed else "❌"
            lines.append(f"- {status} **{criteria.value}**: {result.score:.1f}/100 ({len(result.findings)} findings)")
        
        lines.extend(["", "## Detailed Results", ""])
        
        # Add detailed results
        for criteria, result in self.results.items():
            lines.extend([
                f"### {criteria.value.replace('_', ' ').title()}",
                f"**Score:** {result.score:.1f}/100 | **Passed:** {'Yes' if result.passed else 'No'}",
                "",
            ])
            
            if result.findings:
                lines.append("**Findings:**")
                for finding in result.findings:
                    emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "info": "🔵"}[finding.severity.value]
                    lines.append(f"- {emoji} [{finding.severity.value.upper()}] {finding.message}")
                    if finding.suggestion:
                        lines.append(f"  - 💡 {finding.suggestion}")
                lines.append("")
            
            if result.recommendations:
                lines.append("**Recommendations:**")
                for rec in sorted(result.recommendations, key=lambda r: r.priority):
                    lines.append(f"- P{rec.priority}: {rec.title} - {rec.description}")
                lines.append("")
        
        # Add recommendations summary
        if self.all_recommendations:
            lines.extend(["## Top Recommendations", ""])
            for i, rec in enumerate(self.all_recommendations[:5], 1):
                lines.append(f"{i}. **{rec.title}** (P{rec.priority}, {rec.impact} impact)")
                lines.append(f"   - {rec.description}")
                for action in rec.action_items[:3]:
                    lines.append(f"   - [ ] {action}")
                lines.append("")
        
        return "\n".join(lines)


class FeedbackLoop:
    """
    Feedback loop to send evaluation results to Evolution agent
    for pattern extraction and continuous improvement
    """
    
    def __init__(self, evolution_endpoint: Optional[str] = None):
        self.evolution_endpoint = evolution_endpoint
        self.pattern_history: List[Dict[str, Any]] = []
        
    def send_to_evolution(self, report: EvaluationReport) -> Dict[str, Any]:
        """
        Send evaluation results to Evolution agent
        
        Returns patterns extracted from successful evaluations
        """
        # Extract patterns from excellent/good results
        patterns = self._extract_patterns(report)
        
        feedback_data = {
            'task_id': report.task_id,
            'agent_id': report.agent_id,
            'overall_score': report.overall_score,
            'threshold': report.threshold.name,
            'patterns': patterns,
            'timestamp': datetime.now().isoformat()
        }
        
        # Store locally
        self.pattern_history.append(feedback_data)
        
        # Log for now - in production, this would POST to evolution endpoint
        logger.info(f"Feedback sent to Evolution agent: {len(patterns)} patterns extracted")
        
        return {
            'success': True,
            'patterns_extracted': len(patterns),
            'patterns': patterns
        }
    
    def _extract_patterns(self, report: EvaluationReport) -> List[Dict[str, Any]]:
        """Extract successful patterns from evaluation"""
        patterns = []
        
        # Only extract patterns from good/excellent results
        if report.threshold not in [ScoreThreshold.EXCELLENT, ScoreThreshold.GOOD]:
            return patterns
        
        for criteria, result in report.results.items():
            if result.score >= 85:
                pattern = {
                    'criteria': criteria.value,
                    'score': result.score,
                    'techniques': self._identify_techniques(criteria, result),
                    'metrics': result.metadata
                }
                patterns.append(pattern)
        
        return patterns
    
    def _identify_techniques(self, criteria: EvaluationCriteria, 
                            result: EvaluationResult) -> List[str]:
        """Identify successful techniques from result metadata"""
        techniques = []
        
        if criteria == EvaluationCriteria.CODE_QUALITY:
            if result.metadata.get('complexity_score', 0) > 80:
                techniques.append('low_complexity_functions')
            if result.metadata.get('style_score', 0) > 90:
                techniques.append('consistent_code_style')
                
        elif criteria == EvaluationCriteria.TEST_COVERAGE:
            if result.metadata.get('coverage_percentage', 0) > 80:
                techniques.append('high_test_coverage')
            if result.metadata.get('has_unit_tests'):
                techniques.append('unit_test_patterns')
                
        elif criteria == EvaluationCriteria.PERFORMANCE:
            if result.metadata.get('efficiency_score', 0) > 85:
                techniques.append('algorithmic_efficiency')
                
        elif criteria == EvaluationCriteria.SECURITY:
            if result.score >= 95:
                techniques.append('security_best_practices')
                
        elif criteria == EvaluationCriteria.MAINTAINABILITY:
            if result.metadata.get('documentation_score', 0) > 80:
                techniques.append('comprehensive_documentation')
            if result.metadata.get('modularity_score', 0) > 80:
                techniques.append('high_modularity')
        
        return techniques


class SelfEvaluationEngine:
    """
    Main evaluation engine for agent performance assessment
    
    Evaluates code changes and agent-generated output across
    multiple criteria, provides recommendations, and determines
    if rollback is needed.
    """
    
    # Score thresholds for passing each criterion
    PASSING_SCORES = {
        EvaluationCriteria.CODE_QUALITY: 70,
        EvaluationCriteria.TEST_COVERAGE: 60,
        EvaluationCriteria.PERFORMANCE: 70,
        EvaluationCriteria.SECURITY: 80,
        EvaluationCriteria.MAINTAINABILITY: 65
    }
    
    # Weight for each criterion in overall score
    CRITERIA_WEIGHTS = {
        EvaluationCriteria.CODE_QUALITY: 0.25,
        EvaluationCriteria.TEST_COVERAGE: 0.15,
        EvaluationCriteria.PERFORMANCE: 0.20,
        EvaluationCriteria.SECURITY: 0.25,
        EvaluationCriteria.MAINTAINABILITY: 0.15
    }
    
    def __init__(self, 
                 consensus_engine: Optional[Any] = None,
                 enable_feedback_loop: bool = True,
                 evolution_endpoint: Optional[str] = None):
        """
        Initialize self-evaluation engine
        
        Args:
            consensus_engine: Optional ConsensusEngine for integration
            enable_feedback_loop: Whether to send results to Evolution agent
            evolution_endpoint: Endpoint for Evolution agent feedback
        """
        self.consensus_engine = consensus_engine
        self.enable_feedback_loop = enable_feedback_loop
        self.feedback_loop = FeedbackLoop(evolution_endpoint) if enable_feedback_loop else None
        self.evaluation_history: List[EvaluationReport] = []
        
        logger.info("Self-Evaluation Engine initialized")
    
    # ==================== PUBLIC API ====================
    
    def evaluate_change(self, 
                       task_id: str,
                       agent_id: str,
                       code: str,
                       file_path: str,
                       context: Optional[Dict[str, Any]] = None) -> EvaluationReport:
        """
        Evaluate a code change comprehensively
        
        Args:
            task_id: Unique task identifier
            agent_id: Agent that made the change
            code: Source code to evaluate
            file_path: Path to the file being evaluated
            context: Additional context (tests, dependencies, etc.)
        
        Returns:
            Complete evaluation report
        """
        context = context or {}
        start_time = datetime.now()
        
        logger.info(f"Starting self-evaluation for task {task_id}")
        
        # Run all criterion evaluations
        results = {}
        
        results[EvaluationCriteria.CODE_QUALITY] = self._evaluate_code_quality(
            code, file_path, context
        )
        results[EvaluationCriteria.TEST_COVERAGE] = self._evaluate_test_coverage(
            code, file_path, context
        )
        results[EvaluationCriteria.PERFORMANCE] = self._evaluate_performance(
            code, file_path, context
        )
        results[EvaluationCriteria.SECURITY] = self._evaluate_security(
            code, file_path, context
        )
        results[EvaluationCriteria.MAINTAINABILITY] = self._evaluate_maintainability(
            code, file_path, context
        )
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(results)
        threshold = ScoreThreshold.from_score(overall_score)
        
        # Check if rollback is needed
        rollback_needed = self.should_rollback(results, overall_score)
        
        # Integrate with consensus engine if available
        consensus_report = None
        if self.consensus_engine and CONSENSUS_AVAILABLE:
            consensus_report = self._integrate_consensus(
                task_id, code, file_path, context
            )
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        report = EvaluationReport(
            task_id=task_id,
            agent_id=agent_id,
            overall_score=overall_score,
            threshold=threshold,
            results=results,
            consensus_report=consensus_report,
            should_rollback=rollback_needed,
            execution_time_ms=execution_time
        )
        
        # Store in history
        self.evaluation_history.append(report)
        
        # Send feedback to Evolution agent
        if self.feedback_loop and self.enable_feedback_loop:
            patterns = self.feedback_loop.send_to_evolution(report)
            report.patterns_extracted = patterns.get('patterns', [])
        
        logger.info(
            f"Self-evaluation complete for {task_id}: "
            f"{threshold.name} (score: {overall_score:.1f}, time: {execution_time:.1f}ms)"
        )
        
        return report
    
    def evaluate_agent_output(self,
                             task_id: str,
                             agent_id: str,
                             output: str,
                             output_type: str = "code",
                             context: Optional[Dict[str, Any]] = None) -> EvaluationReport:
        """
        Evaluate general agent-generated output (not just code)
        
        Args:
            task_id: Unique task identifier
            agent_id: Agent that generated output
            output: The generated output
            output_type: Type of output (code, text, config, etc.)
            context: Additional context
        
        Returns:
            Evaluation report
        """
        context = context or {}
        context['output_type'] = output_type
        
        # For non-code output, adapt evaluation
        if output_type in ['text', 'documentation', 'markdown']:
            return self._evaluate_text_output(task_id, agent_id, output, context)
        
        # Default to code evaluation
        return self.evaluate_change(task_id, agent_id, output, 
                                    context.get('file_path', 'unknown'), context)
    
    def generate_report(self, 
                       task_id: str,
                       format: str = "dict") -> Optional[Any]:
        """
        Generate comprehensive evaluation report
        
        Args:
            task_id: Task to generate report for
            format: Output format (dict, markdown, json)
        
        Returns:
            Report in requested format
        """
        # Find report in history
        report = None
        for r in self.evaluation_history:
            if r.task_id == task_id:
                report = r
                break
        
        if not report:
            logger.warning(f"No evaluation found for task {task_id}")
            return None
        
        if format == "markdown":
            return report.to_markdown()
        elif format == "json":
            return json.dumps(report.to_dict(), indent=2)
        else:
            return report.to_dict()
    
    def should_rollback(self, 
                       results: Dict[EvaluationCriteria, EvaluationResult],
                       overall_score: Optional[float] = None) -> bool:
        """
        Determine if rollback is needed based on evaluation results
        
        Rollback triggers:
        - Overall score < 60 (FAILED threshold)
        - Any CRITICAL security finding
        - Two or more criteria failed
        - Code quality score < 50
        
        Args:
            results: Evaluation results by criterion
            overall_score: Optional pre-calculated overall score
        
        Returns:
            True if rollback should be triggered
        """
        # Check overall score
        if overall_score is None:
            overall_score = self._calculate_overall_score(results)
        
        if overall_score < 60:
            logger.warning(f"Rollback triggered: Overall score {overall_score:.1f} < 60")
            return True
        
        # Check for critical security findings
        security_result = results.get(EvaluationCriteria.SECURITY)
        if security_result:
            critical_count = len(security_result.critical_findings)
            if critical_count > 0:
                logger.warning(f"Rollback triggered: {critical_count} critical security findings")
                return True
        
        # Check failed criteria count
        failed_criteria = [c for c, r in results.items() if not r.passed]
        if len(failed_criteria) >= 2:
            logger.warning(f"Rollback triggered: {len(failed_criteria)} criteria failed")
            return True
        
        # Check code quality minimum
        code_quality = results.get(EvaluationCriteria.CODE_QUALITY)
        if code_quality and code_quality.score < 50:
            logger.warning(f"Rollback triggered: Code quality {code_quality.score:.1f} < 50")
            return True
        
        return False
    
    # ==================== CRITERION EVALUATION METHODS ====================
    
    def _evaluate_code_quality(self, 
                              code: str, 
                              file_path: str,
                              context: Dict[str, Any]) -> EvaluationResult:
        """
        Evaluate code quality: syntax, complexity, and style
        
        Checks:
        - Syntax validity
        - Cyclomatic complexity
        - Function length
        - Code style consistency
        - Naming conventions
        """
        findings = []
        metadata = {}
        
        file_ext = Path(file_path).suffix.lower()
        
        # Check 1: Syntax validity
        syntax_score = 100
        if file_ext == '.py':
            try:
                ast.parse(code)
                metadata['syntax_valid'] = True
            except SyntaxError as e:
                syntax_score = 0
                metadata['syntax_valid'] = False
                findings.append(FindingDetail(
                    criteria=EvaluationCriteria.CODE_QUALITY,
                    severity=Severity.CRITICAL,
                    category='syntax',
                    message=f'Syntax error: {str(e)}',
                    line_number=getattr(e, 'lineno', None),
                    suggestion='Fix the syntax error before proceeding'
                ))
        
        # Check 2: Cyclomatic complexity
        complexity_score = 100
        if file_ext == '.py' and metadata.get('syntax_valid', True):
            try:
                tree = ast.parse(code)
                complexities = self._calculate_complexity(tree)
                max_complexity = max(complexities.values()) if complexities else 0
                avg_complexity = sum(complexities.values()) / len(complexities) if complexities else 0
                
                metadata['max_complexity'] = max_complexity
                metadata['avg_complexity'] = avg_complexity
                metadata['function_count'] = len(complexities)
                
                if max_complexity > 15:
                    complexity_score = 50
                    findings.append(FindingDetail(
                        criteria=EvaluationCriteria.CODE_QUALITY,
                        severity=Severity.HIGH,
                        category='complexity',
                        message=f'High cyclomatic complexity ({max_complexity}) in one or more functions',
                        suggestion='Refactor complex functions into smaller, more manageable pieces'
                    ))
                elif max_complexity > 10:
                    complexity_score = 75
                    findings.append(FindingDetail(
                        criteria=EvaluationCriteria.CODE_QUALITY,
                        severity=Severity.MEDIUM,
                        category='complexity',
                        message=f'Moderate cyclomatic complexity ({max_complexity}) detected',
                        suggestion='Consider simplifying complex conditional logic'
                    ))
            except Exception as e:
                logger.warning(f"Complexity calculation failed: {e}")
        
        # Check 3: Function length
        length_score = 100
        if file_ext == '.py' and metadata.get('syntax_valid', True):
            long_functions = self._find_long_functions(code)
            if len(long_functions) > 0:
                length_score = max(0, 100 - len(long_functions) * 10)
                for func_name, lines in long_functions[:3]:
                    findings.append(FindingDetail(
                        criteria=EvaluationCriteria.CODE_QUALITY,
                        severity=Severity.MEDIUM if lines < 80 else Severity.HIGH,
                        category='function_length',
                        message=f'Function "{func_name}" is {lines} lines long',
                        suggestion='Consider breaking long functions into smaller units'
                    ))
        
        # Check 4: Code style (basic checks)
        style_score = 100
        style_issues = []
        
        # Check for mixed indentation
        if '\t' in code and '    ' in code:
            style_score -= 20
            style_issues.append('Mixed tabs and spaces for indentation')
        
        # Check line length
        long_lines = [i for i, line in enumerate(code.split('\n'), 1) if len(line) > 120]
        if len(long_lines) > 5:
            style_score -= min(30, len(long_lines))
            style_issues.append(f'{len(long_lines)} lines exceed 120 characters')
        
        if style_issues:
            findings.append(FindingDetail(
                criteria=EvaluationCriteria.CODE_QUALITY,
                severity=Severity.LOW,
                category='style',
                message='; '.join(style_issues),
                suggestion='Follow PEP 8 style guidelines'
            ))
        
        # Calculate final score
        score = (syntax_score * 0.4 + complexity_score * 0.3 + 
                length_score * 0.2 + style_score * 0.1)
        
        metadata.update({
            'syntax_score': syntax_score,
            'complexity_score': complexity_score,
            'length_score': length_score,
            'style_score': style_score
        })
        
        # Generate recommendations
        recommendations = []
        if complexity_score < 80:
            recommendations.append(Recommendation(
                priority=2,
                criteria=EvaluationCriteria.CODE_QUALITY,
                title='Reduce Cyclomatic Complexity',
                description='Refactor functions with high complexity scores',
                action_items=[
                    'Extract complex conditionals into helper functions',
                    'Use early returns to reduce nesting',
                    'Consider using design patterns for complex logic'
                ],
                estimated_effort='medium',
                impact='high'
            ))
        
        if style_score < 90:
            recommendations.append(Recommendation(
                priority=4,
                criteria=EvaluationCriteria.CODE_QUALITY,
                title='Improve Code Style Consistency',
                description='Address style issues for better readability',
                action_items=[
                    'Run code formatter (black, autopep8)',
                    'Configure editor to use consistent indentation',
                    'Add linting to pre-commit hooks'
                ],
                estimated_effort='small',
                impact='low'
            ))
        
        passed = score >= self.PASSING_SCORES[EvaluationCriteria.CODE_QUALITY]
        severity = self._calculate_severity(findings)
        
        return EvaluationResult(
            criteria=EvaluationCriteria.CODE_QUALITY,
            score=score,
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            severity=severity,
            metadata=metadata
        )
    
    def _evaluate_test_coverage(self,
                               code: str,
                               file_path: str,
                               context: Dict[str, Any]) -> EvaluationResult:
        """
        Evaluate test coverage and quality
        
        Checks:
        - Coverage percentage
        - Test file existence
        - Test quality indicators
        - Edge case coverage
        """
        findings = []
        metadata = {}
        
        # Get coverage from context if available
        coverage_percentage = context.get('test_coverage', 0)
        metadata['coverage_percentage'] = coverage_percentage
        
        # Check for test files
        has_tests = context.get('has_tests', False)
        test_files = context.get('test_files', [])
        metadata['has_tests'] = has_tests
        metadata['test_files_count'] = len(test_files)
        
        # Calculate coverage score
        coverage_score = min(100, coverage_percentage)
        
        if coverage_percentage < 50:
            findings.append(FindingDetail(
                criteria=EvaluationCriteria.TEST_COVERAGE,
                severity=Severity.HIGH,
                category='coverage',
                message=f'Low test coverage: {coverage_percentage:.1f}%',
                suggestion='Add unit tests to cover critical code paths'
            ))
        elif coverage_percentage < 70:
            findings.append(FindingDetail(
                criteria=EvaluationCriteria.TEST_COVERAGE,
                severity=Severity.MEDIUM,
                category='coverage',
                message=f'Moderate test coverage: {coverage_percentage:.1f}%',
                suggestion='Increase test coverage for better reliability'
            ))
        
        # Check test quality indicators in code
        test_quality_score = 100
        if has_tests:
            # Check for test assertions
            assertion_count = len(re.findall(r'\b(assert|expect|should)\b', code, re.IGNORECASE))
            metadata['assertion_count'] = assertion_count
            
            if assertion_count < 3:
                test_quality_score -= 30
                findings.append(FindingDetail(
                    criteria=EvaluationCriteria.TEST_COVERAGE,
                    severity=Severity.MEDIUM,
                    category='test_quality',
                    message='Few assertions found in tests',
                    suggestion='Add more assertions to validate expected behavior'
                ))
            
            # Check for edge case tests
            edge_case_indicators = ['empty', 'null', 'none', 'error', 'exception', 
                                   'boundary', 'invalid', 'edge']
            has_edge_cases = any(ind in code.lower() for ind in edge_case_indicators)
            metadata['has_edge_case_tests'] = has_edge_cases
            
            if not has_edge_cases:
                test_quality_score -= 20
                findings.append(FindingDetail(
                    criteria=EvaluationCriteria.TEST_COVERAGE,
                    severity=Severity.LOW,
                    category='edge_cases',
                    message='No edge case tests detected',
                    suggestion='Add tests for boundary conditions and error cases'
                ))
        else:
            test_quality_score = 0
            findings.append(FindingDetail(
                criteria=EvaluationCriteria.TEST_COVERAGE,
                severity=Severity.HIGH,
                category='missing_tests',
                message='No test files found for this code',
                suggestion='Create comprehensive test suite'
            ))
        
        # Calculate final score
        if has_tests:
            score = coverage_score * 0.6 + test_quality_score * 0.4
        else:
            score = 0
        
        metadata.update({
            'coverage_score': coverage_score,
            'test_quality_score': test_quality_score
        })
        
        # Generate recommendations
        recommendations = []
        if coverage_percentage < 70:
            recommendations.append(Recommendation(
                priority=1,
                criteria=EvaluationCriteria.TEST_COVERAGE,
                title='Increase Test Coverage',
                description=f'Current coverage {coverage_percentage:.1f}% is below target of 70%',
                action_items=[
                    'Write unit tests for all public functions',
                    'Add integration tests for critical paths',
                    'Use coverage tools to identify gaps'
                ],
                estimated_effort='large',
                impact='high'
            ))
        
        if not has_edge_cases:
            recommendations.append(Recommendation(
                priority=3,
                criteria=EvaluationCriteria.TEST_COVERAGE,
                title='Add Edge Case Tests',
                description='Test boundary conditions and error scenarios',
                action_items=[
                    'Test with empty/null inputs',
                    'Test boundary values',
                    'Test error handling paths'
                ],
                estimated_effort='medium',
                impact='medium'
            ))
        
        passed = score >= self.PASSING_SCORES[EvaluationCriteria.TEST_COVERAGE]
        severity = self._calculate_severity(findings)
        
        return EvaluationResult(
            criteria=EvaluationCriteria.TEST_COVERAGE,
            score=score,
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            severity=severity,
            metadata=metadata
        )
    
    def _evaluate_performance(self,
                             code: str,
                             file_path: str,
                             context: Dict[str, Any]) -> EvaluationResult:
        """
        Evaluate performance characteristics
        
        Checks:
        - Algorithmic efficiency
        - Resource usage patterns
        - Potential bottlenecks
        - Caching opportunities
        """
        findings = []
        metadata = {}
        
        efficiency_score = 100
        
        # Check 1: Nested loops (O(n²) or worse)
        nested_loops = self._detect_nested_loops(code)
        if nested_loops > 0:
            efficiency_score -= min(40, nested_loops * 10)
            findings.append(FindingDetail(
                criteria=EvaluationCriteria.PERFORMANCE,
                severity=Severity.MEDIUM if nested_loops < 3 else Severity.HIGH,
                category='complexity',
                message=f'{nested_loops} nested loop patterns detected',
                suggestion='Consider using hash maps or more efficient algorithms to reduce complexity'
            ))
        
        metadata['nested_loops'] = nested_loops
        
        # Check 2: Inefficient string concatenation in loops
        string_concat = self._detect_inefficient_string_ops(code)
        if string_concat > 0:
            efficiency_score -= min(20, string_concat * 5)
            findings.append(FindingDetail(
                criteria=EvaluationCriteria.PERFORMANCE,
                severity=Severity.LOW,
                category='string_ops',
                message=f'{string_concat} instances of inefficient string concatenation',
                suggestion='Use join() or StringBuilder instead of += in loops'
            ))
        
        metadata['inefficient_string_ops'] = string_concat
        
        # Check 3: Repeated property access
        repeated_access = self._detect_repeated_property_access(code)
        if repeated_access > 0:
            efficiency_score -= min(15, repeated_access * 3)
            findings.append(FindingDetail(
                criteria=EvaluationCriteria.PERFORMANCE,
                severity=Severity.LOW,
                category='optimization',
                message='Repeated property access detected',
                suggestion='Cache frequently accessed properties in local variables'
            ))
        
        # Check 4: Missing caching for expensive operations
        expensive_ops = ['database', 'api', 'fetch', 'request', 'query']
        has_caching = 'cache' in code.lower() or 'memoiz' in code.lower()
        has_expensive = any(op in code.lower() for op in expensive_ops)
        
        metadata['has_expensive_ops'] = has_expensive
        metadata['has_caching'] = has_caching
        
        if has_expensive and not has_caching:
            efficiency_score -= 15
            findings.append(FindingDetail(
                criteria=EvaluationCriteria.PERFORMANCE,
                severity=Severity.MEDIUM,
                category='caching',
                message='Expensive operations without caching detected',
                suggestion='Consider adding caching for database/API calls'
            ))
        
        # Check 5: Memory usage - large data structures
        large_structures = self._detect_large_data_structures(code)
        if large_structures > 0:
            efficiency_score -= min(20, large_structures * 5)
            findings.append(FindingDetail(
                criteria=EvaluationCriteria.PERFORMANCE,
                severity=Severity.MEDIUM,
                category='memory',
                message=f'{large_structures} potentially large in-memory data structures',
                suggestion='Consider streaming or pagination for large datasets'
            ))
        
        metadata['large_structures'] = large_structures
        
        # Calculate final score
        score = max(0, efficiency_score)
        metadata['efficiency_score'] = efficiency_score
        
        # Generate recommendations
        recommendations = []
        if nested_loops > 0:
            recommendations.append(Recommendation(
                priority=1,
                criteria=EvaluationCriteria.PERFORMANCE,
                title='Optimize Algorithmic Complexity',
                description='Replace nested loops with more efficient data structures',
                action_items=[
                    'Use dictionaries/hash maps for O(1) lookups',
                    'Consider sorting + two-pointer technique',
                    'Profile to identify actual bottlenecks'
                ],
                estimated_effort='medium',
                impact='high'
            ))
        
        if has_expensive and not has_caching:
            recommendations.append(Recommendation(
                priority=2,
                criteria=EvaluationCriteria.PERFORMANCE,
                title='Add Caching Layer',
                description='Cache expensive database or API operations',
                action_items=[
                    'Implement Redis or in-memory caching',
                    'Add cache invalidation strategy',
                    'Set appropriate TTL values'
                ],
                estimated_effort='medium',
                impact='high'
            ))
        
        if large_structures > 0:
            recommendations.append(Recommendation(
                priority=3,
                criteria=EvaluationCriteria.PERFORMANCE,
                title='Optimize Memory Usage',
                description='Handle large datasets more efficiently',
                action_items=[
                    'Use generators for large collections',
                    'Implement pagination for API responses',
                    'Consider database-level aggregation'
                ],
                estimated_effort='medium',
                impact='medium'
            ))
        
        passed = score >= self.PASSING_SCORES[EvaluationCriteria.PERFORMANCE]
        severity = self._calculate_severity(findings)
        
        return EvaluationResult(
            criteria=EvaluationCriteria.PERFORMANCE,
            score=score,
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            severity=severity,
            metadata=metadata
        )
    
    def _evaluate_security(self,
                          code: str,
                          file_path: str,
                          context: Dict[str, Any]) -> EvaluationResult:
        """
        Evaluate security posture
        
        Checks:
        - Secret detection
        - Injection vulnerabilities
        - Input validation
        - Authentication/authorization patterns
        - Insecure dependencies
        """
        findings = []
        metadata = {}
        
        security_score = 100
        
        # Check 1: Secret detection
        secrets_found = self._detect_secrets(code)
        if secrets_found:
            security_score -= len(secrets_found) * 25
            for secret in secrets_found:
                findings.append(FindingDetail(
                    criteria=EvaluationCriteria.SECURITY,
                    severity=Severity.CRITICAL,
                    category='secrets',
                    message=f'Potential secret detected: {secret["type"]}',
                    line_number=secret.get('line'),
                    suggestion='Move secrets to environment variables or secrets manager',
                    fix_example=f'os.environ.get("{secret["type"].upper()}_KEY")'
                ))
        
        metadata['secrets_detected'] = len(secrets_found)
        
        # Check 2: SQL injection
        sql_injection = self._detect_sql_injection(code)
        if sql_injection:
            security_score -= len(sql_injection) * 30
            for issue in sql_injection:
                findings.append(FindingDetail(
                    criteria=EvaluationCriteria.SECURITY,
                    severity=Severity.CRITICAL,
                    category='injection',
                    message=f'SQL injection vulnerability: {issue}',
                    suggestion='Use parameterized queries or ORM methods',
                    fix_example='cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))'
                ))
        
        metadata['sql_injection_risks'] = len(sql_injection)
        
        # Check 3: XSS vulnerabilities
        xss_issues = self._detect_xss_vulnerabilities(code)
        if xss_issues:
            security_score -= len(xss_issues) * 20
            for issue in xss_issues:
                findings.append(FindingDetail(
                    criteria=EvaluationCriteria.SECURITY,
                    severity=Severity.HIGH,
                    category='xss',
                    message=f'XSS vulnerability: {issue}',
                    suggestion='Use output encoding and Content Security Policy'
                ))
        
        # Check 4: Input validation
        input_issues = self._check_input_validation(code)
        if input_issues:
            security_score -= len(input_issues) * 10
            for issue in input_issues:
                findings.append(FindingDetail(
                    criteria=EvaluationCriteria.SECURITY,
                    severity=Severity.MEDIUM,
                    category='input_validation',
                    message=issue,
                    suggestion='Validate and sanitize all user inputs'
                ))
        
        metadata['input_validation_issues'] = len(input_issues)
        
        # Check 5: Insecure functions
        insecure_patterns = self._detect_insecure_patterns(code)
        if insecure_patterns:
            security_score -= len(insecure_patterns) * 15
            for pattern in insecure_patterns:
                findings.append(FindingDetail(
                    criteria=EvaluationCriteria.SECURITY,
                    severity=Severity.HIGH,
                    category='insecure_patterns',
                    message=pattern['message'],
                    suggestion=pattern.get('suggestion', 'Use secure alternatives')
                ))
        
        metadata['insecure_patterns'] = len(insecure_patterns)
        
        # Calculate final score
        score = max(0, security_score)
        metadata['security_score'] = security_score
        
        # Generate recommendations
        recommendations = []
        if secrets_found:
            recommendations.append(Recommendation(
                priority=1,
                criteria=EvaluationCriteria.SECURITY,
                title='Remove Hardcoded Secrets',
                description=f'{len(secrets_found)} potential secrets detected in code',
                action_items=[
                    'Move secrets to environment variables',
                    'Use a secrets manager (AWS Secrets Manager, Vault)',
                    'Rotate exposed credentials immediately',
                    'Add secret scanning to CI/CD pipeline'
                ],
                estimated_effort='small',
                impact='critical'
            ))
        
        if sql_injection:
            recommendations.append(Recommendation(
                priority=1,
                criteria=EvaluationCriteria.SECURITY,
                title='Fix SQL Injection Vulnerabilities',
                description='Unparameterized SQL queries detected',
                action_items=[
                    'Use parameterized queries exclusively',
                    'Adopt ORM for database operations',
                    'Run security scanners (Bandit, Semgrep)'
                ],
                estimated_effort='medium',
                impact='critical'
            ))
        
        if xss_issues:
            recommendations.append(Recommendation(
                priority=2,
                criteria=EvaluationCriteria.SECURITY,
                title='Prevent XSS Vulnerabilities',
                description='Unescaped output in HTML context detected',
                action_items=[
                    'Use template auto-escaping',
                    'Implement Content Security Policy',
                    'Validate and sanitize user input'
                ],
                estimated_effort='medium',
                impact='high'
            ))
        
        if not recommendations and score < 100:
            recommendations.append(Recommendation(
                priority=3,
                criteria=EvaluationCriteria.SECURITY,
                title='General Security Hardening',
                description='Additional security improvements recommended',
                action_items=[
                    'Enable security headers',
                    'Implement rate limiting',
                    'Add security monitoring'
                ],
                estimated_effort='medium',
                impact='medium'
            ))
        
        passed = score >= self.PASSING_SCORES[EvaluationCriteria.SECURITY]
        severity = self._calculate_severity(findings)
        
        return EvaluationResult(
            criteria=EvaluationCriteria.SECURITY,
            score=score,
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            severity=severity,
            metadata=metadata
        )
    
    def _evaluate_maintainability(self,
                                 code: str,
                                 file_path: str,
                                 context: Dict[str, Any]) -> EvaluationResult:
        """
        Evaluate code maintainability
        
        Checks:
        - Documentation quality
        - Code modularity
        - Naming conventions
        - Code duplication
        - Dependency management
        """
        findings = []
        metadata = {}
        
        # Check 1: Documentation
        doc_score = 100
        lines = code.split('\n')
        total_lines = len(lines)
        comment_lines = len([l for l in lines if l.strip().startswith('#')])
        docstring_lines = len(re.findall(r'["\']{3}.*?["\']{3}', code, re.DOTALL))
        
        comment_ratio = (comment_lines + docstring_lines) / total_lines if total_lines > 0 else 0
        metadata['comment_ratio'] = comment_ratio
        metadata['total_lines'] = total_lines
        
        if comment_ratio < 0.05:
            doc_score -= 40
            findings.append(FindingDetail(
                criteria=EvaluationCriteria.MAINTAINABILITY,
                severity=Severity.MEDIUM,
                category='documentation',
                message=f'Low documentation ratio ({comment_ratio:.1%})',
                suggestion='Add docstrings and inline comments for complex logic'
            ))
        elif comment_ratio < 0.1:
            doc_score -= 20
            findings.append(FindingDetail(
                criteria=EvaluationCriteria.MAINTAINABILITY,
                severity=Severity.LOW,
                category='documentation',
                message=f'Could benefit from more documentation ({comment_ratio:.1%})',
                suggestion='Add docstrings to public functions and classes'
            ))
        
        # Check function docstrings
        functions = self._extract_functions(code)
        functions_with_docs = sum(1 for f in functions if f.get('has_docstring'))
        doc_ratio = functions_with_docs / len(functions) if functions else 1.0
        metadata['function_doc_ratio'] = doc_ratio
        
        if doc_ratio < 0.5 and len(functions) > 3:
            doc_score -= 20
            findings.append(FindingDetail(
                criteria=EvaluationCriteria.MAINTAINABILITY,
                severity=Severity.MEDIUM,
                category='documentation',
                message=f'Only {functions_with_docs}/{len(functions)} functions have docstrings',
                suggestion='Add docstrings to all public functions'
            ))
        
        # Check 2: Modularity
        modularity_score = 100
        
        # Check file length
        if total_lines > 500:
            modularity_score -= 30
            findings.append(FindingDetail(
                criteria=EvaluationCriteria.MAINTAINABILITY,
                severity=Severity.MEDIUM,
                category='modularity',
                message=f'Large file ({total_lines} lines)',
                suggestion='Consider splitting into multiple modules'
            ))
        
        # Check for god classes/functions
        large_functions = [f for f in functions if f.get('lines', 0) > 50]
        if len(large_functions) > 2:
            modularity_score -= 20
            findings.append(FindingDetail(
                criteria=EvaluationCriteria.MAINTAINABILITY,
                severity=Severity.MEDIUM,
                category='modularity',
                message=f'{len(large_functions)} functions exceed 50 lines',
                suggestion='Break large functions into smaller, focused units'
            ))
        
        # Check imports
        imports = self._extract_imports(code)
        metadata['import_count'] = len(imports)
        
        if len(imports) > 30:
            modularity_score -= 15
            findings.append(FindingDetail(
                criteria=EvaluationCriteria.MAINTAINABILITY,
                severity=Severity.LOW,
                category='dependencies',
                message=f'High number of imports ({len(imports)})',
                suggestion='Review if all imports are necessary'
            ))
        
        # Check 3: Naming conventions
        naming_score = 100
        naming_issues = []
        
        # Check for single-letter variables (except common ones)
        single_letter = re.findall(r'\b([a-zA-Z])\b', code)
        common_single = {'i', 'j', 'k', 'x', 'y', 'z', 'n', 'm', 'e'}
        bad_single = [v for v in single_letter if v not in common_single]
        if len(bad_single) > 5:
            naming_score -= 15
            naming_issues.append(f'{len(bad_single)} single-letter variable names')
        
        # Check for inconsistent naming
        snake_case = len(re.findall(r'\b[a-z]+_[a-z_]+\b', code))
        camelCase = len(re.findall(r'\b[a-z]+[A-Z][a-zA-Z]*\b', code))
        if snake_case > 5 and camelCase > 5:
            naming_score -= 10
            naming_issues.append('Mixed snake_case and camelCase naming')
        
        if naming_issues:
            findings.append(FindingDetail(
                criteria=EvaluationCriteria.MAINTAINABILITY,
                severity=Severity.LOW,
                category='naming',
                message='; '.join(naming_issues),
                suggestion='Follow consistent naming conventions (PEP 8 for Python)'
            ))
        
        # Check 4: Code duplication
        duplication_score = 100
        duplicates = self._detect_code_duplication(code)
        if duplicates > 0:
            duplication_score -= min(30, duplicates * 5)
            findings.append(FindingDetail(
                criteria=EvaluationCriteria.MAINTAINABILITY,
                severity=Severity.MEDIUM,
                category='duplication',
                message=f'{duplicates} potential code duplications detected',
                suggestion='Extract common code into reusable functions'
            ))
        
        metadata['duplication_blocks'] = duplicates
        
        # Calculate final score
        score = (doc_score * 0.3 + modularity_score * 0.3 + 
                naming_score * 0.2 + duplication_score * 0.2)
        
        metadata.update({
            'doc_score': doc_score,
            'modularity_score': modularity_score,
            'naming_score': naming_score,
            'duplication_score': duplication_score,
            'function_count': len(functions)
        })
        
        # Generate recommendations
        recommendations = []
        if doc_ratio < 0.5:
            recommendations.append(Recommendation(
                priority=2,
                criteria=EvaluationCriteria.MAINTAINABILITY,
                title='Improve Documentation',
                description=f'Only {doc_ratio:.0%} of functions have docstrings',
                action_items=[
                    'Add docstrings to all public functions',
                    'Document complex algorithms',
                    'Add type hints where appropriate'
                ],
                estimated_effort='medium',
                impact='medium'
            ))
        
        if total_lines > 500:
            recommendations.append(Recommendation(
                priority=3,
                criteria=EvaluationCriteria.MAINTAINABILITY,
                title='Split Large Module',
                description=f'File has {total_lines} lines, consider splitting',
                action_items=[
                    'Group related functions into separate modules',
                    'Extract utility functions to common module',
                    'Create class-based structure'
                ],
                estimated_effort='large',
                impact='medium'
            ))
        
        if duplicates > 0:
            recommendations.append(Recommendation(
                priority=3,
                criteria=EvaluationCriteria.MAINTAINABILITY,
                title='Reduce Code Duplication',
                description=f'{duplicates} duplicate code blocks found',
                action_items=[
                    'Extract common patterns into functions',
                    'Use inheritance for shared behavior',
                    'Create utility modules'
                ],
                estimated_effort='medium',
                impact='medium'
            ))
        
        passed = score >= self.PASSING_SCORES[EvaluationCriteria.MAINTAINABILITY]
        severity = self._calculate_severity(findings)
        
        return EvaluationResult(
            criteria=EvaluationCriteria.MAINTAINABILITY,
            score=score,
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            severity=severity,
            metadata=metadata
        )
    
    def _evaluate_text_output(self,
                             task_id: str,
                             agent_id: str,
                             output: str,
                             context: Dict[str, Any]) -> EvaluationReport:
        """Evaluate non-code text output"""
        # Simplified evaluation for text output
        results = {}
        
        # Code quality - check for obvious issues
        cq_findings = []
        if len(output) < 50:
            cq_findings.append(FindingDetail(
                criteria=EvaluationCriteria.CODE_QUALITY,
                severity=Severity.MEDIUM,
                category='length',
                message='Output is very short',
                suggestion='Provide more comprehensive response'
            ))
        
        results[EvaluationCriteria.CODE_QUALITY] = EvaluationResult(
            criteria=EvaluationCriteria.CODE_QUALITY,
            score=80 if len(output) > 100 else 60,
            passed=len(output) > 50,
            findings=cq_findings,
            recommendations=[]
        )
        
        # Maintainability - structure and clarity
        maint_findings = []
        paragraphs = len([p for p in output.split('\n\n') if p.strip()])
        if paragraphs < 2 and len(output) > 200:
            maint_findings.append(FindingDetail(
                criteria=EvaluationCriteria.MAINTAINABILITY,
                severity=Severity.LOW,
                category='structure',
                message='Long output without clear paragraph breaks',
                suggestion='Break into sections with headers'
            ))
        
        results[EvaluationCriteria.MAINTAINABILITY] = EvaluationResult(
            criteria=EvaluationCriteria.MAINTAINABILITY,
            score=85 if paragraphs >= 2 else 70,
            passed=True,
            findings=maint_findings,
            recommendations=[]
        )
        
        # Other criteria - placeholder for text
        for criteria in [EvaluationCriteria.TEST_COVERAGE, 
                        EvaluationCriteria.PERFORMANCE,
                        EvaluationCriteria.SECURITY]:
            results[criteria] = EvaluationResult(
                criteria=criteria,
                score=100,  # N/A for text
                passed=True,
                findings=[],
                recommendations=[],
                metadata={'not_applicable': True, 'output_type': 'text'}
            )
        
        overall_score = sum(r.score for r in results.values()) / len(results)
        threshold = ScoreThreshold.from_score(overall_score)
        
        return EvaluationReport(
            task_id=task_id,
            agent_id=agent_id,
            overall_score=overall_score,
            threshold=threshold,
            results=results,
            should_rollback=False
        )
    
    # ==================== HELPER METHODS ====================
    
    def _calculate_overall_score(self, 
                                results: Dict[EvaluationCriteria, EvaluationResult]) -> float:
        """Calculate weighted overall score"""
        total_weight = 0
        weighted_sum = 0
        
        for criteria, result in results.items():
            weight = self.CRITERIA_WEIGHTS.get(criteria, 0.2)
            weighted_sum += result.score * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0
    
    def _calculate_severity(self, findings: List[FindingDetail]) -> Severity:
        """Determine overall severity from findings"""
        if any(f.severity == Severity.CRITICAL for f in findings):
            return Severity.CRITICAL
        elif any(f.severity == Severity.HIGH for f in findings):
            return Severity.HIGH
        elif any(f.severity == Severity.MEDIUM for f in findings):
            return Severity.MEDIUM
        elif any(f.severity == Severity.LOW for f in findings):
            return Severity.LOW
        return Severity.INFO
    
    def _integrate_consensus(self, task_id: str, code: str, 
                            file_path: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Integrate with consensus engine"""
        if not self.consensus_engine or not CONSENSUS_AVAILABLE:
            return None
        
        try:
            agent_type = AgentType(context.get('agent_type', 'fullstack'))
            consensus_report = self.consensus_engine.evaluate_consensus(
                task_id=task_id,
                code=code,
                file_path=file_path,
                agent_type=agent_type,
                context=context
            )
            
            return {
                'consensus_decision': consensus_report.decision.name,
                'consensus_score': consensus_report.overall_score,
                'syntax_score': consensus_report.syntax_result.score,
                'logic_score': consensus_report.logic_result.score,
                'security_score': consensus_report.security_result.score,
                'findings_count': (
                    len(consensus_report.syntax_result.findings) +
                    len(consensus_report.logic_result.findings) +
                    len(consensus_report.security_result.findings)
                )
            }
        except Exception as e:
            logger.error(f"Consensus integration failed: {e}")
            return None
    
    # ==================== CODE ANALYSIS HELPERS ====================
    
    def _calculate_complexity(self, tree: ast.AST) -> Dict[str, int]:
        """Calculate cyclomatic complexity for functions"""
        complexities = {}
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_name = node.name
                complexity = 1  # Base complexity
                
                # Count decision points
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.While, ast.For, 
                                         ast.ExceptHandler, ast.With)):
                        complexity += 1
                    elif isinstance(child, ast.BoolOp):
                        complexity += len(child.values) - 1
                    elif isinstance(child, ast.Compare):
                        complexity += len(child.ops) - 1
                
                complexities[func_name] = complexity
        
        return complexities
    
    def _find_long_functions(self, code: str) -> List[Tuple[str, int]]:
        """Find functions that are too long"""
        long_functions = []
        
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Calculate function length
                    start_line = node.lineno
                    end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line
                    length = end_line - start_line + 1
                    
                    if length > 30:
                        long_functions.append((node.name, length))
        except:
            pass
        
        return long_functions
    
    def _detect_nested_loops(self, code: str) -> int:
        """Detect potentially inefficient nested loops"""
        nested_count = 0
        lines = code.split('\n')
        
        for i, line in enumerate(lines):
            indent_level = len(line) - len(line.lstrip())
            
            # Check for loop keywords
            if re.search(r'\b(for|while)\s+', line):
                # Check if there's another loop inside
                for j in range(i + 1, min(i + 50, len(lines))):
                    inner_line = lines[j]
                    inner_indent = len(inner_line) - len(inner_line.lstrip())
                    
                    # If we hit a line with same or less indent, we're out of the loop
                    if inner_line.strip() and inner_indent <= indent_level:
                        break
                    
                    # Check for nested loop
                    if inner_indent > indent_level and re.search(r'\b(for|while)\s+', inner_line):
                        nested_count += 1
        
        return nested_count
    
    def _detect_inefficient_string_ops(self, code: str) -> int:
        """Detect inefficient string concatenation in loops"""
        count = 0
        # Pattern: variable += string inside a loop
        pattern = r'\b(\w+)\s*\+?=.*["\'].*["\'].*:\s*\n.*\1\s*\+='
        count += len(re.findall(pattern, code))
        return count
    
    def _detect_repeated_property_access(self, code: str) -> int:
        """Detect repeated property access that could be cached"""
        # Simple pattern matching for repeated attribute access
        matches = re.findall(r'(\w+\.\w+)', code)
        from collections import Counter
        counts = Counter(matches)
        return sum(1 for _, c in counts.items() if c > 3)
    
    def _detect_large_data_structures(self, code: str) -> int:
        """Detect potentially large in-memory data structures"""
        count = 0
        # Pattern: loading entire files or large datasets
        patterns = [
            r'read\(\)',  # file.read() without size limit
            r'fetchall\(\)',  # database fetchall
            r'list\(.*\)',  # converting large iterables to list
            r'dict\(.*\)',  # converting large iterables to dict
        ]
        for pattern in patterns:
            count += len(re.findall(pattern, code))
        return count
    
    def _detect_secrets(self, code: str) -> List[Dict[str, Any]]:
        """Detect potential secrets in code"""
        secrets = []
        
        # Secret patterns
        patterns = [
            (r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']([a-zA-Z0-9_-]{16,})["\']', 'API_KEY'),
            (r'(?i)(secret[_-]?key|secretkey)\s*[:=]\s*["\']([a-zA-Z0-9_-]{16,})["\']', 'SECRET_KEY'),
            (r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']([^"\']{8,})["\']', 'PASSWORD'),
            (r'(?i)(token|auth[_-]?token)\s*[:=]\s*["\']([a-zA-Z0-9_-]{20,})["\']', 'TOKEN'),
            (r'(?i)(aws[_-]?access[_-]?key|aws_secret)\s*[:=]\s*["\']([A-Z0-9]{20})["\']', 'AWS_KEY'),
            (r'private[_-]?key.*?BEGIN', 'PRIVATE_KEY'),
        ]
        
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern, secret_type in patterns:
                if re.search(pattern, line):
                    secrets.append({
                        'type': secret_type,
                        'line': i,
                        'snippet': line.strip()[:100]
                    })
        
        return secrets
    
    def _detect_sql_injection(self, code: str) -> List[str]:
        """Detect SQL injection vulnerabilities"""
        issues = []
        
        # Pattern: string concatenation in SQL
        patterns = [
            r'execute\s*\(\s*["\'].*?%s.*?["\']',
            r'execute\s*\(\s*["\'].*?\+.*?\+.*?["\']',
            r'execute\s*\(\s*f["\'].*?\{.*?\}.*?["\']',
            r'\.format\s*\(.*\)\s*.*execute',
            r'execute\s*\(\s*["\'].*?\$\{.*?\}.*?["\']',
        ]
        
        for pattern in patterns:
            if re.search(pattern, code, re.IGNORECASE):
                issues.append(f"Potential SQL injection: {pattern}")
        
        return issues
    
    def _detect_xss_vulnerabilities(self, code: str) -> List[str]:
        """Detect XSS vulnerabilities"""
        issues = []
        
        # Pattern: unescaped output in HTML
        patterns = [
            r'innerHTML\s*=',
            r'document\.write\s*\(',
            r'\.html\s*\(',
            r'{{.*?\|.*?safe.*?}}',
            r'@Html\.Raw',
        ]
        
        for pattern in patterns:
            if re.search(pattern, code, re.IGNORECASE):
                issues.append(f"Potential XSS: {pattern}")
        
        return issues
    
    def _check_input_validation(self, code: str) -> List[str]:
        """Check for input validation"""
        issues = []
        
        # Check for request parameters without validation
        if 'request.' in code or 'req.' in code or 'params' in code:
            # Check if there's validation
            validation_patterns = ['validate', 'sanitize', 'schema', 'validator']
            has_validation = any(p in code.lower() for p in validation_patterns)
            
            if not has_validation:
                issues.append('User input detected without validation')
        
        return issues
    
    def _detect_insecure_patterns(self, code: str) -> List[Dict[str, str]]:
        """Detect insecure coding patterns"""
        patterns = []
        
        # Insecure random
        if re.search(r'random\.random\(\)|Math\.random\(\)', code):
            patterns.append({
                'message': 'Using insecure random number generator for security purposes',
                'suggestion': 'Use secrets.token_hex() or crypto.randomBytes()'
            })
        
        # Hardcoded temp paths
        if '/tmp/' in code or 'C:\\temp' in code:
            patterns.append({
                'message': 'Hardcoded temporary file path',
                'suggestion': 'Use tempfile.mkstemp() or equivalent'
            })
        
        # Weak hashing
        if re.search(r'hashlib\.md5|hashlib\.sha1|md5\(|sha1\(', code):
            patterns.append({
                'message': 'Using weak hashing algorithm',
                'suggestion': 'Use hashlib.sha256 or bcrypt/scrypt for passwords'
            })
        
        # Pickle usage
        if 'pickle.loads' in code or 'pickle.load' in code:
            patterns.append({
                'message': 'Unsafe deserialization with pickle',
                'suggestion': 'Use JSON or implement safe deserialization'
            })
        
        return patterns
    
    def _extract_functions(self, code: str) -> List[Dict[str, Any]]:
        """Extract function information from code"""
        functions = []
        
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_info = {
                        'name': node.name,
                        'lines': (node.end_lineno - node.lineno + 1) if hasattr(node, 'end_lineno') else 0,
                        'has_docstring': (
                            node.body and 
                            isinstance(node.body[0], ast.Expr) and
                            isinstance(node.body[0].value, (ast.Str, ast.Constant))
                        )
                    }
                    functions.append(func_info)
        except:
            pass
        
        return functions
    
    def _extract_imports(self, code: str) -> List[str]:
        """Extract import statements from code"""
        imports = []
        
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or '')
        except:
            pass
        
        return imports
    
    def _detect_code_duplication(self, code: str, min_lines: int = 5) -> int:
        """Detect potential code duplication"""
        lines = [l.strip() for l in code.split('\n') if l.strip() and not l.strip().startswith('#')]
        
        # Simple check for repeated line sequences
        duplicates = 0
        seen_blocks = set()
        
        for i in range(len(lines) - min_lines + 1):
            block = tuple(lines[i:i + min_lines])
            if block in seen_blocks:
                duplicates += 1
            else:
                seen_blocks.add(block)
        
        return duplicates
    
    # ==================== STATISTICS & HISTORY ====================
    
    def get_evaluation_statistics(self) -> Dict[str, Any]:
        """Get statistics from evaluation history"""
        if not self.evaluation_history:
            return {'message': 'No evaluation history available'}
        
        total_evaluations = len(self.evaluation_history)
        passed = sum(1 for r in self.evaluation_history if r.passed)
        failed = total_evaluations - passed
        
        avg_score = sum(r.overall_score for r in self.evaluation_history) / total_evaluations
        
        # Score distribution
        thresholds = {}
        for report in self.evaluation_history:
            threshold_name = report.threshold.name
            thresholds[threshold_name] = thresholds.get(threshold_name, 0) + 1
        
        # Criteria averages
        criteria_scores = {criteria.value: [] for criteria in EvaluationCriteria.all()}
        for report in self.evaluation_history:
            for criteria, result in report.results.items():
                criteria_scores[criteria.value].append(result.score)
        
        criteria_averages = {
            k: sum(v) / len(v) if v else 0 
            for k, v in criteria_scores.items()
        }
        
        return {
            'total_evaluations': total_evaluations,
            'passed': passed,
            'failed': failed,
            'pass_rate': passed / total_evaluations if total_evaluations > 0 else 0,
            'average_score': round(avg_score, 2),
            'threshold_distribution': thresholds,
            'criteria_averages': criteria_averages,
            'recent_evaluations': [
                {
                    'task_id': r.task_id,
                    'score': r.overall_score,
                    'threshold': r.threshold.name,
                    'passed': r.passed
                }
                for r in self.evaluation_history[-10:]
            ]
        }


# ==================== EXPORT FUNCTIONS ====================

def create_evaluation_engine(consensus_engine: Optional[Any] = None,
                             enable_feedback: bool = True) -> SelfEvaluationEngine:
    """Factory function to create evaluation engine"""
    return SelfEvaluationEngine(
        consensus_engine=consensus_engine,
        enable_feedback_loop=enable_feedback
    )


def quick_evaluate(code: str, 
                  file_path: str,
                  task_id: Optional[str] = None) -> EvaluationReport:
    """Quick evaluation without full engine setup"""
    engine = SelfEvaluationEngine(enable_feedback_loop=False)
    return engine.evaluate_change(
        task_id=task_id or f"quick-eval-{datetime.now().timestamp()}",
        agent_id="quick-evaluator",
        code=code,
        file_path=file_path
    )


# ==================== MAIN EXECUTION ====================

if __name__ == "__main__":
    # Example usage and self-test
    print("APEX Self-Evaluation System v2.0")
    print("=" * 50)
    
    # Test with sample code
    sample_code = '''
def calculate_total(items):
    """Calculate total price of items."""
    total = 0
    for item in items:
        total += item['price'] * item['quantity']
    return total

def process_order(user_id, items):
    # TODO: Add validation
    total = calculate_total(items)
    # Save to database
    query = f"INSERT INTO orders (user_id, total) VALUES ({user_id}, {total})"
    return query
'''
    
    engine = SelfEvaluationEngine(enable_feedback_loop=False)
    report = engine.evaluate_change(
        task_id="test-evaluation",
        agent_id="test-agent",
        code=sample_code,
        file_path="test_module.py"
    )
    
    print(f"\nOverall Score: {report.overall_score:.1f}/100")
    print(f"Threshold: {report.threshold.name}")
    print(f"Should Rollback: {report.should_rollback}")
    print(f"\nCriteria Breakdown:")
    for criteria, result in report.results.items():
        status = "✓" if result.passed else "✗"
        print(f"  {status} {criteria.value}: {result.score:.1f}/100")
    
    print("\n" + report.to_markdown()[:2000] + "...")
