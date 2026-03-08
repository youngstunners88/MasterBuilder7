#!/usr/bin/env python3
"""
Simple deployment dashboard
Shows deployment status and history
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print dashboard header"""
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "Google Play Deployment Dashboard" + " " * 23 + "║")
    print("╚" + "═" * 68 + "╝")
    print()

def load_deployments() -> List[Dict[str, Any]]:
    """Load deployment history"""
    history_file = Path('/tmp/google_play_deployments.json')
    if not history_file.exists():
        return []
    
    try:
        with open(history_file) as f:
            return json.load(f)
    except:
        return []

def get_status_icon(status: str) -> str:
    """Get status icon"""
    icons = {
        'completed': '✅',
        'failed': '❌',
        'pending': '⏳',
        'processing': '🔄',
        'validating': '🔍',
        'uploading': '📤',
    }
    return icons.get(status.lower(), '❓')

def format_time(iso_time: str) -> str:
    """Format ISO time to readable format"""
    try:
        dt = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M')
    except:
        return iso_time[:16] if iso_time else 'Unknown'

def print_recent_deployments(deployments: List[Dict], limit: int = 10):
    """Print recent deployments"""
    print("📦 RECENT DEPLOYMENTS")
    print("─" * 70)
    
    if not deployments:
        print("  No deployments found.")
        print("  Run: python google_play_deployment.py deploy <aab> <track>")
        return
    
    # Sort by started_at descending
    sorted_deployments = sorted(
        deployments,
        key=lambda x: x.get('started_at', ''),
        reverse=True
    )[:limit]
    
    print(f"{'ID':<12} {'Track':<12} {'Status':<14} {'Time':<16}")
    print("─" * 70)
    
    for dep in sorted_deployments:
        dep_id = dep.get('deployment_id', 'N/A')[:10]
        track = dep.get('track', 'N/A')[:11]
        status = dep.get('status', 'unknown')
        time_str = format_time(dep.get('started_at', ''))
        icon = get_status_icon(status)
        
        print(f"{dep_id:<12} {track:<12} {icon} {status:<12} {time_str:<16}")
    
    if len(deployments) > limit:
        print(f"\n  ... and {len(deployments) - limit} more")

def print_statistics(deployments: List[Dict]):
    """Print deployment statistics"""
    print("\n📊 STATISTICS")
    print("─" * 70)
    
    if not deployments:
        print("  No data available")
        return
    
    total = len(deployments)
    successful = sum(1 for d in deployments if d.get('status') == 'completed')
    failed = sum(1 for d in deployments if d.get('status') == 'failed')
    
    # Track breakdown
    tracks = {}
    for d in deployments:
        track = d.get('track', 'unknown')
        tracks[track] = tracks.get(track, 0) + 1
    
    print(f"  Total Deployments: {total}")
    print(f"  Successful:        {successful} ({successful/total*100:.1f}%)")
    print(f"  Failed:            {failed} ({failed/total*100:.1f}%)")
    print()
    print("  By Track:")
    for track, count in sorted(tracks.items()):
        print(f"    {track:12} {count:3} deployments")

def print_current_status():
    """Print current system status"""
    print("\n🔧 SYSTEM STATUS")
    print("─" * 70)
    
    # Check environment
    from google_play_deployment import SecurityConfig
    valid, errors = SecurityConfig.validate_environment()
    
    if valid:
        print("  ✅ Environment configured")
        print(f"  📦 Package: {os.getenv('GOOGLE_PLAY_PACKAGE_NAME', 'N/A')}")
    else:
        print("  ❌ Environment not configured")
        for error in errors:
            print(f"     - {error}")
        print("\n  Run: python gp_wizard.py")
    
    # Check audit log
    audit_log = Path('/tmp/google_play_security.log')
    if audit_log.exists():
        size_kb = audit_log.stat().st_size / 1024
        print(f"  📝 Audit log: {size_kb:.1f} KB")

def print_quick_actions():
    """Print quick actions"""
    print("\n⚡ QUICK ACTIONS")
    print("─" * 70)
    print("  1. Deploy to internal:  python gp_wizard.py --deploy")
    print("  2. Deploy to production: python google_play_deployment.py deploy <aab> production")
    print("  3. View deployment:      python google_play_deployment.py status <id>")
    print("  4. List all:             python google_play_deployment.py list")
    print("  5. Setup wizard:         python gp_wizard.py")

def main():
    """Main dashboard function"""
    clear_screen()
    print_header()
    
    # Load deployments
    deployments = load_deployments()
    
    # Print sections
    print_current_status()
    print_recent_deployments(deployments)
    print_statistics(deployments)
    print_quick_actions()
    
    print("\n" + "═" * 70)
    print("Dashboard refreshes every 5 seconds. Press Ctrl+C to exit.")
    print("═" * 70)

if __name__ == "__main__":
    try:
        if len(sys.argv) > 1 and sys.argv[1] == '--watch':
            import time
            while True:
                main()
                time.sleep(5)
        else:
            main()
    except KeyboardInterrupt:
        print("\n\nDashboard closed.")
        sys.exit(0)
