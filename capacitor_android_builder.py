#!/usr/bin/env python3
"""
Capacitor Android Builder - ACTUALLY builds the AAB
"""

import subprocess
import os
from pathlib import Path


def build_capacitor_android(repo_path: str, output_dir: str = "/tmp/builds") -> str:
    """
    Real build process for Capacitor Android app
    Returns path to generated .aab file
    """
    repo = Path(repo_path)
    android_dir = repo / "android"
    
    # 1. Install dependencies
    print("📦 Running npm ci...")
    subprocess.run(
        ["npm", "ci"],
        cwd=repo,
        check=True,
        capture_output=True
    )
    
    # 2. Build web assets
    print("🔨 Building web assets...")
    subprocess.run(
        ["npm", "run", "build"],
        cwd=repo,
        check=True,
        capture_output=True
    )
    
    # 3. Sync to Android
    print("📱 Syncing to Android...")
    subprocess.run(
        ["npx", "cap", "sync", "android"],
        cwd=repo,
        check=True,
        capture_output=True
    )
    
    # 4. Build AAB
    print("🏗️  Building Android App Bundle...")
    gradlew = android_dir / "gradlew"
    subprocess.run(
        ["./gradlew", "bundleRelease"],
        cwd=android_dir,
        check=True,
        capture_output=True
    )
    
    # 5. Find output
    outputs_dir = android_dir / "app" / "build" / "outputs" / "bundle" / "release"
    aab_files = list(outputs_dir.glob("*.aab"))
    
    if not aab_files:
        raise FileNotFoundError("No AAB file found after build")
    
    return str(aab_files[0])


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python capacitor_android_builder.py <repo_path>")
        sys.exit(1)
    
    aab_path = build_capacitor_android(sys.argv[1])
    print(f"✅ AAB built: {aab_path}")
