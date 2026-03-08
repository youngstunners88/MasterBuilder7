#!/usr/bin/env python3
"""
REAL BUILDER - Actually runs commands, no more sleep() bullshit
"""

import subprocess
import os
import sys
from pathlib import Path


def run_command(cmd, cwd=None, env=None):
    """Run a real shell command and return result"""
    print(f"▶️  Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"❌ FAILED: {result.stderr}")
        return False, result.stderr
    print(f"✅ SUCCESS: {result.stdout[:200]}")
    return True, result.stdout


def build_ihhashi(repo_path):
    """
    REAL build for iHhashi - no more fake sleep()
    """
    frontend_dir = Path(repo_path) / "frontend"
    android_dir = frontend_dir / "android"
    
    # Step 1: npm install
    success, output = run_command(
        ["npm", "install"],
        cwd=frontend_dir
    )
    if not success:
        return {"success": False, "error": "npm install failed", "details": output}
    
    # Step 2: npm run build
    success, output = run_command(
        ["npm", "run", "build"],
        cwd=frontend_dir
    )
    if not success:
        return {"success": False, "error": "npm build failed", "details": output}
    
    # Step 3: npx cap sync
    success, output = run_command(
        ["npx", "cap", "sync"],
        cwd=frontend_dir
    )
    if not success:
        return {"success": False, "error": "cap sync failed", "details": output}
    
    # Step 4: Build AAB (if keystore exists)
    keystore_path = android_dir / "app" / "ihhashi-keystore.jks"
    
    if keystore_path.exists():
        success, output = run_command(
            ["./gradlew", "bundleRelease"],
            cwd=android_dir,
            env={**os.environ, "IHHASHI_BUILD": "production"}
        )
        if not success:
            return {"success": False, "error": "gradle build failed", "details": output}
        
        aab_path = android_dir / "app" / "build" / "outputs" / "bundle" / "release" / "app-release.aab"
        return {
            "success": True,
            "aab_path": str(aab_path) if aab_path.exists() else None,
            "message": "Build completed successfully"
        }
    else:
        # Unsigned build
        success, output = run_command(
            ["./gradlew", "bundleRelease"],
            cwd=android_dir
        )
        if not success:
            return {"success": False, "error": "gradle build failed", "details": output}
        
        return {
            "success": True,
            "message": "Build completed (unsigned - needs keystore for Play Store)"
        }


def deploy_to_render(repo_path, render_api_key):
    """
    REAL Render deployment using their API
    """
    import requests
    
    # Get or create service
    headers = {
        "Authorization": f"Bearer {render_api_key}",
        "Content-Type": "application/json"
    }
    
    # Deploy via Render API
    deploy_url = "https://api.render.com/v1/services"
    
    payload = {
        "type": "web_service",
        "name": "ihhashi-backend",
        "repo": "https://github.com/youngstunners88/ihhashi",
        "branch": "main",
        "build_command": "pip install -r requirements.txt",
        "start_command": "uvicorn main:app --host 0.0.0.0 --port $PORT"
    }
    
    response = requests.post(deploy_url, headers=headers, json=payload)
    
    if response.status_code in [200, 201]:
        data = response.json()
        return {
            "success": True,
            "url": data.get("url"),
            "service_id": data.get("id"),
            "message": "Deployed to Render"
        }
    else:
        return {
            "success": False,
            "error": f"Render API error: {response.status_code}",
            "details": response.text
        }


def deploy_to_icp(repo_path, dfx_identity):
    """
    REAL ICP deployment using dfx
    """
    icp_dir = Path(repo_path) / "icp"
    
    if not icp_dir.exists():
        return {"success": False, "error": "No ICP directory found"}
    
    # Step 1: dfx deploy
    success, output = run_command(
        ["dfx", "deploy", "--network", "ic"],
        cwd=icp_dir,
        env={**os.environ, "DFX_IDENTITY": dfx_identity}
    )
    
    if not success:
        return {"success": False, "error": "dfx deploy failed", "details": output}
    
    # Extract canister ID from output
    canister_id = None
    for line in output.split("\n"):
        if "canister id:" in line.lower():
            canister_id = line.split(":")[-1].strip()
            break
    
    return {
        "success": True,
        "canister_id": canister_id,
        "message": "Deployed to ICP"
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: REAL_BUILDER.py <repo_path> [render_key] [dfx_identity]")
        sys.exit(1)
    
    repo = sys.argv[1]
    render_key = sys.argv[2] if len(sys.argv) > 2 else None
    dfx_id = sys.argv[3] if len(sys.argv) > 3 else None
    
    print("="*60)
    print("🔥 REAL BUILD - NO MORE FAKE SLEEP()")
    print("="*60)
    
    # Build
    result = build_ihhashi(repo)
    print(f"\n📦 Build result: {result}")
    
    if result["success"] and render_key:
        print("\n🚀 Deploying to Render...")
        deploy = deploy_to_render(repo, render_key)
        print(f"Render: {deploy}")
    
    if result["success"] and dfx_id:
        print("\n🔗 Deploying to ICP...")
        deploy = deploy_to_icp(repo, dfx_id)
        print(f"ICP: {deploy}")
