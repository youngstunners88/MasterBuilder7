#!/usr/bin/env python3
"""
ICP Canister Manager - Production-grade canister lifecycle management
"""

import subprocess
import json
import time
from typing import Dict, Optional, List
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CanisterInfo:
    name: str
    id: str
    cycles: int
    status: str
    module_hash: Optional[str] = None


class CanisterManager:
    """Production-grade ICP canister lifecycle management"""
    
    def __init__(self, network: str = "ic", identity: Optional[str] = None):
        self.network = network
        self.identity = identity or "default"
        self._ensure_identity()
    
    def _ensure_identity(self):
        """Ensure dfx identity is configured"""
        result = subprocess.run(
            ["dfx", "identity", "use", self.identity],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Identity error: {result.stderr}")
    
    def create_canister(self, name: str, cycles: int = 2_000_000_000_000) -> str:
        """Create new canister with cycles"""
        cmd = [
            "dfx", "canister", "create", name,
            "--network", self.network,
            "--with-cycles", str(cycles)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Canister creation failed: {result.stderr}")
        return self.get_canister_id(name)
    
    def get_canister_id(self, name: str) -> str:
        """Get canister ID"""
        result = subprocess.run(
            ["dfx", "canister", "id", name, "--network", self.network],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Canister ID error: {result.stderr}")
        return result.stdout.strip()
    
    def install_code(self, name: str, wasm_path: str, mode: str = "install"):
        """Install/reinstall/upgrade canister code"""
        cmd = [
            "dfx", "canister", "install", name,
            "--network", self.network,
            "--wasm", wasm_path,
            "--mode", mode
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Install failed: {result.stderr}")
    
    def get_status(self, name: str) -> CanisterInfo:
        """Get canister status"""
        result = subprocess.run(
            ["dfx", "canister", "status", name, "--network", self.network],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Status error: {result.stderr}")
        
        # Parse status output
        lines = result.stdout.split("\n")
        return CanisterInfo(
            name=name,
            id=self.get_canister_id(name),
            cycles=0,  # Parse from lines
            status="running" if "Running" in result.stdout else "stopped"
        )
    
    def add_cycles(self, name: str, cycles: int):
        """Top up canister with cycles"""
        cmd = [
            "dfx", "canister", "deposit-cycles", name,
            "--network", self.network,
            str(cycles)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Deposit failed: {result.stderr}")


if __name__ == "__main__":
    # Demo
    manager = CanisterManager(network="local")
    print("CanisterManager ready")
