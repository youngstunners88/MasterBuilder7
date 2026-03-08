#!/usr/bin/env python3
"""CRITICAL FIX: Builder that actually builds AAB from source"""
import subprocess
import os
from pathlib import Path

def build_aab(repo_url: str, output_dir: str = "/tmp/builds") -> str:
    """Clone, install, sync, build AAB"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Clone
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    build_path = f"{output_dir}/{repo_name}"
    
    subprocess.run(["git", "clone", "--depth", "1", repo_url, build_path], check=True)
    
    # Install dependencies
    frontend = f"{build_path}/frontend"
    subprocess.run(["npm", "install"], cwd=frontend, check=True)
    
    # Build web assets
    subprocess.run(["npm", "run", "build"], cwd=frontend, check=True)
    
    # Sync Capacitor
    subprocess.run(["npx", "cap", "sync", "android"], cwd=frontend, check=True)
    
    # Build AAB
    android_path = f"{frontend}/android"
    subprocess.run(["./gradlew", "bundleRelease"], cwd=android_path, check=True)
    
    return f"{android_path}/app/build/outputs/bundle/release/app-release.aab"

if __name__ == "__main__":
    import sys
    aab = build_aab(sys.argv[1] if len(sys.argv) > 1 else "https://github.com/youngstunners88/iHhashi")
    print(f"Built: {aab}")
