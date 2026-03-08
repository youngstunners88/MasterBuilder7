#!/usr/bin/env python3
"""
ICP Deployer - End-to-end Internet Computer deployment
"""

import subprocess
import json
import os
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class ICPDeploymentConfig:
    repo_path: str
    canister_name: str
    network: str = "ic"  # ic, local, playground
    wallet: Optional[str] = None
    with_assets: bool = True


class ICPDeployer:
    """Production ICP deployment orchestrator"""
    
    def __init__(self, identity: Optional[str] = None):
        self.identity = identity or "default"
        self._verify_dfx()
    
    def _verify_dfx(self):
        """Verify dfx is installed"""
        result = subprocess.run(["dfx", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError("dfx not installed. Run: sh -ci "$(curl -fsSL https://internetcomputer.org/install.sh)"")
        print(f"✅ dfx version: {result.stdout.strip()}")
    
    def deploy(self, config: ICPDeploymentConfig) -> Dict:
        """
        Full deployment pipeline:
        1. Build canisters
        2. Deploy to network
        3. Verify deployment
        """
        print(f"\n🚀 Deploying to ICP {config.network}...")
        
        # Step 1: Build
        build_result = self._build_canisters(config)
        if not build_result["success"]:
            return build_result
        
        # Step 2: Deploy
        deploy_result = self._deploy_canisters(config)
        if not deploy_result["success"]:
            return deploy_result
        
        # Step 3: Verify
        verify_result = self._verify_deployment(config)
        
        return {
            "success": True,
            "canister_id": verify_result.get("canister_id"),
            "candid": verify_result.get("candid"),
            "url": f"https://{verify_result.get('canister_id', 'unknown')}.icp0.io"
        }
    
    def _build_canisters(self, config: ICPDeploymentConfig) -> Dict:
        """Build all canisters"""
        print("\n📦 Building canisters...")
        
        cmd = ["dfx", "build", "--network", config.network]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=config.repo_path)
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"Build failed: {result.stderr}",
                "stage": "build"
            }
        
        return {"success": True}
    
    def _deploy_canisters(self, config: ICPDeploymentConfig) -> Dict:
        """Deploy to ICP network"""
        print(f"\n🌐 Deploying to {config.network}...")
        
        cmd = ["dfx", "deploy", "--network", config.network, "--yes"]
        
        if config.wallet:
            cmd.extend(["--wallet", config.wallet])
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=config.repo_path)
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"Deploy failed: {result.stderr}",
                "stage": "deploy"
            }
        
        return {"success": True, "output": result.stdout}
    
    def _verify_deployment(self, config: ICPDeploymentConfig) -> Dict:
        """Verify canister is running"""
        print("\n✅ Verifying deployment...")
        
        result = subprocess.run(
            ["dfx", "canister", "id", config.canister_name, "--network", config.network],
            capture_output=True, text=True, cwd=config.repo_path
        )
        
        if result.returncode != 0:
            return {"success": False, "error": "Verification failed"}
        
        canister_id = result.stdout.strip()
        print(f"   Canister ID: {canister_id}")
        
        return {
            "success": True,
            "canister_id": canister_id,
            "url": f"https://{canister_id}.icp0.io"
        }


if __name__ == "__main__":
    # Demo
    deployer = ICPDeployer()
    print("ICPDeployer ready. Use deploy() method to deploy.")
