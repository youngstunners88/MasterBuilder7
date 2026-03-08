#!/usr/bin/env python3
"""
ship - One command to deploy iHhashi to Google Play

Usage:
    python ship.py --repo /path/to/ihhashi --track internal
    python ship.py --repo /path/to/ihhashi --track production --percentage 10
"""

import argparse
import os
import sys

# Add current dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator import MasterOrchestrator


def main():
    parser = argparse.ArgumentParser(
        description="Ship iHhashi to Google Play Store",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Deploy to internal testing
    python ship.py --repo /home/workspace/iHhashi --track internal
    
    # Production rollout at 10%
    python ship.py --repo /home/workspace/iHhashi --track production --percentage 10
        """
    )
    
    parser.add_argument(
        "--repo", 
        required=True,
        help="Path to iHhashi repository"
    )
    parser.add_argument(
        "--track",
        choices=["internal", "alpha", "beta", "production"],
        default="internal",
        help="Play Store track (default: internal)"
    )
    parser.add_argument(
        "--percentage",
        type=int,
        default=100,
        help="Rollout percentage for production (default: 100)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build only, don't deploy"
    )
    
    args = parser.parse_args()
    
    # Validate repo exists
    if not os.path.exists(args.repo):
        print(f"❌ Repository not found: {args.repo}")
        sys.exit(1)
    
    # Check for required env vars
    if not os.getenv("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON"):
        print("❌ GOOGLE_PLAY_SERVICE_ACCOUNT_JSON not set")
        print("   Export your service account JSON or base64-encoded version")
        sys.exit(1)
    
    print(f"""
╔════════════════════════════════════════╗
║  🦀 MasterBuilder7 - iHhashi Shipper   ║
╠════════════════════════════════════════╣
║  Repo:   {args.repo:<35} ║
║  Track:  {args.track:<35} ║
║  Rollout: {args.percentage}%{' '*33} ║
╚════════════════════════════════════════╝
    """)
    
    # Execute deployment
    orchestrator = MasterOrchestrator()
    
    if args.dry_run:
        print("🔍 DRY RUN: Building only...")
        from capacitor_android_builder import build_capacitor_android
        aab_path = build_capacitor_android(args.repo)
        print(f"✅ AAB built: {aab_path}")
        print("   (Not deploying - dry run mode)")
        return
    
    print("🚀 Executing full deployment pipeline...")
    result = orchestrator.deploy(
        repo=args.repo,
        targets=["android"]
    )
    
    # Print results
    if result["status"] == "success":
        android_result = result["results"]["android"]["deploy"]
        print(f"""
🎉 iHhashi deployed successfully!

📦 Build:
   AAB: {result["results"]["android"]["build"]["aab_path"]}

🚀 Deployment:
   Track: {android_result.get("track", "unknown")}
   Version Code: {android_result.get("version_code", "unknown")}
   Edit ID: {android_result.get("edit_id", "unknown")}

🔗 Next Steps:
   1. Check Play Console: https://play.google.com/console
   2. Internal testers can download in ~10 minutes
   3. Promote to production when ready
        """)
    else:
        print(f"❌ Deployment failed: {result}")
        sys.exit(1)


if __name__ == "__main__":
    main()
