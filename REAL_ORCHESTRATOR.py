#!/usr/bin/env python3
"""
REAL ORCHESTRATOR - No more asyncio.sleep(), just real builds
"""

import json
import sys
import os
from pathlib import Path

# Import real builder
from REAL_BUILDER import build_ihhashi, deploy_to_render, deploy_to_icp


def orchestrate(repo_path, targets, render_key=None, dfx_identity=None):
    """
    Orchestrate real deployment - no simulation
    """
    print("="*60)
    print("⚡ REAL ORCHESTRATOR - iHhashi Production Deploy")
    print("="*60)
    
    results = {
        "repo": repo_path,
        "targets": targets,
        "steps": []
    }
    
    # Step 1: Build Android
    if "android" in targets or "all" in targets:
        print("\n📱 Building Android (Capacitor + Gradle)...")
        build_result = build_ihhashi(repo_path)
        results["steps"].append({
            "step": "android_build",
            "result": build_result
        })
        
        if not build_result["success"]:
            print(f"❌ Android build FAILED: {build_result.get('error')}")
            return results
        print("✅ Android build SUCCESS")
    
    # Step 2: Deploy Backend to Render
    if "render" in targets or "backend" in targets or "all" in targets:
        if not render_key:
            print("⚠️  Skipping Render - no RENDER_API_KEY provided")
        else:
            print("\n🚀 Deploying to Render...")
            deploy_result = deploy_to_render(repo_path, render_key)
            results["steps"].append({
                "step": "render_deploy",
                "result": deploy_result
            })
            
            if deploy_result["success"]:
                print(f"✅ Render SUCCESS: {deploy_result.get('url')}")
            else:
                print(f"❌ Render FAILED: {deploy_result.get('error')}")
    
    # Step 3: Deploy to ICP
    if "icp" in targets or "all" in targets:
        if not dfx_identity:
            print("⚠️  Skipping ICP - no DFX_IDENTITY provided")
        else:
            print("\n🔗 Deploying to ICP...")
            deploy_result = deploy_to_icp(repo_path, dfx_identity)
            results["steps"].append({
                "step": "icp_deploy",
                "result": deploy_result
            })
            
            if deploy_result["success"]:
                print(f"✅ ICP SUCCESS: {deploy_result.get('canister_id')}")
            else:
                print(f"❌ ICP FAILED: {deploy_result.get('error')}")
    
    # Final status
    all_success = all(
        step["result"]["success"] 
        for step in results["steps"]
    )
    
    results["overall_success"] = all_success
    
    print("\n" + "="*60)
    if all_success:
        print("🎉 ALL DEPLOYMENTS SUCCESSFUL")
    else:
        print("⚠️  SOME DEPLOYMENTS FAILED - Check logs above")
    print("="*60)
    
    return results


def main():
    if len(sys.argv) < 3:
        print("Usage: REAL_ORCHESTRATOR.py <repo_path> <targets> [render_key] [dfx_identity]")
        print("  targets: android,backend,icp,render,all")
        print("\nExample:")
        print("  python3 REAL_ORCHESTRATOR.py /home/workspace/iHhashi all $RENDER_KEY $DFX_ID")
        sys.exit(1)
    
    repo = sys.argv[1]
    targets_str = sys.argv[2]
    targets = targets_str.split(",")
    render_key = sys.argv[3] if len(sys.argv) > 3 else os.getenv("RENDER_API_KEY")
    dfx_id = sys.argv[4] if len(sys.argv) > 4 else os.getenv("DFX_IDENTITY")
    
    result = orchestrate(repo, targets, render_key, dfx_id)
    
    # Save result
    output_file = "/tmp/deploy_result.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"\n📄 Full result saved to: {output_file}")
    print(json.dumps(result, indent=2))
    
    sys.exit(0 if result["overall_success"] else 1)


if __name__ == "__main__":
    main()
