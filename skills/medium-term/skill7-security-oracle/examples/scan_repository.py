#!/usr/bin/env python3
"""Example: Scan a repository for security vulnerabilities."""

import sys
import os
sys.path.insert(0, '..')

from src.scanner import SecurityScanner
from src.reporter import SecurityReporter
from src.remediator import Remediator

def main():
    print("=" * 60)
    print("Security Oracle - Repository Scan Example")
    print("=" * 60)
    
    # Initialize scanner
    print("\n1. Initializing scanner...")
    scanner = SecurityScanner()
    
    # Set target (current directory)
    target = "../"
    
    # Run scan
    print(f"\n2. Scanning {target}...")
    print("   This may take a few minutes...")
    
    result = scanner.scan(target, scanners=['secrets', 'custom'])
    
    # Display summary
    print(f"\n3. Scan Summary:")
    print(f"   Files scanned: {result.files_scanned}")
    print(f"   Duration: {result.duration_seconds:.2f}s")
    print(f"   Scanners used: {', '.join(result.scanners_used)}")
    print(f"   Vulnerabilities found: {len(result.vulnerabilities)}")
    print(f"   Critical: {result.critical_count}")
    print(f"   High: {result.high_count}")
    print(f"   Medium: {len(result.get_by_severity(scanner.Severity.MEDIUM))}")
    print(f"   Low: {len(result.get_by_severity(scanner.Severity.LOW))}")
    
    # Generate reports
    print("\n4. Generating reports...")
    reporter = SecurityReporter(result)
    
    # Console display
    print("\n   Console Report:")
    reporter.display_console()
    
    # HTML report
    reporter.save("security_report.html", "html")
    print("   ✓ Saved HTML report to security_report.html")
    
    # Markdown report
    reporter.save("security_report.md", "markdown")
    print("   ✓ Saved Markdown report to security_report.md")
    
    # SARIF for GitHub/CodeQL
    reporter.save("security_report.sarif", "sarif")
    print("   ✓ Saved SARIF report to security_report.sarif")
    
    # Generate remediation suggestions
    print("\n5. Generating remediation suggestions...")
    remediator = Remediator()
    suggestions = remediator.generate_suggestions(result.vulnerabilities)
    
    print(f"   Generated {len(suggestions)} suggestions")
    
    # Display top suggestions
    if suggestions:
        print("\n   Top Suggestions:")
        for i, sugg in enumerate(suggestions[:5], 1):
            print(f"   {i}. {sugg.title} ({sugg.confidence} confidence)")
            if sugg.requires_review:
                print(f"      ⚠ Requires manual review")
    
    # Generate patch file
    patch = remediator.generate_patch(suggestions)
    with open("security_patch.md", "w") as f:
        f.write(patch)
    print("\n   ✓ Saved patch file to security_patch.md")
    
    # Create GitHub issues (if token available)
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token and result.critical_count > 0:
        print("\n6. Creating GitHub issues for critical vulnerabilities...")
        repo = input("   Enter repository (owner/repo) or press Enter to skip: ")
        if repo:
            try:
                reporter.create_github_issue(repo, github_token)
                print("   ✓ Created GitHub issues")
            except Exception as e:
                print(f"   ⚠ Could not create issues: {e}")
    
    print("\n" + "=" * 60)
    print("Scan completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()