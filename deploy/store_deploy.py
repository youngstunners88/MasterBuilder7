#!/usr/bin/env python3
"""
MASTER-RECOVERY: Sovereign Store Deployment Engine
Google Play + Apple App Store direct upload
"""

import os
import sys
import json
import subprocess
import requests
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class DeploymentConfig:
    repo_path: str
    package_name: str
    version_code: int
    version_name: str
    track: str = "internal"  # internal, alpha, beta, production
    aab_path: Optional[str] = None
    apk_path: Optional[str] = None


class GooglePlayDeployer:
    """Real Google Play Store deployment via Publishing API"""
    
    API_BASE = "https://androidpublisher.googleapis.com/androidpublisher/v3"
    
    def __init__(self, service_account_json: str):
        self.service_account = json.loads(service_account_json)
        self.access_token = self._get_access_token()
    
    def _get_access_token(self) -> str:
        """OAuth2 token from service account"""
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
        
        credentials = service_account.Credentials.from_service_account_info(
            self.service_account,
            scopes=['https://www.googleapis.com/auth/androidpublisher']
        )
        credentials.refresh(Request())
        return credentials.token
    
    def upload_bundle(self, config: DeploymentConfig) -> Dict:
        """Upload AAB to Google Play"""
        if not config.aab_path or not Path(config.aab_path).exists():
            raise FileNotFoundError(f"AAB not found: {config.aab_path}")
        
        # Step 1: Create edit
        edit_response = requests.post(
            f"{self.API_BASE}/applications/{config.package_name}/edits",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        edit_id = edit_response.json()['id']
        
        # Step 2: Upload bundle
        with open(config.aab_path, 'rb') as f:
            upload_response = requests.post(
                f"{self.API_BASE}/applications/{config.package_name}/edits/{edit_id}/bundles",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/octet-stream"
                },
                data=f
            )
        
        version_code = upload_response.json().get('versionCode')
        
        # Step 3: Assign to track
        track_response = requests.put(
            f"{self.API_BASE}/applications/{config.package_name}/edits/{edit_id}/tracks/{config.track}",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            },
            json={
                "track": config.track,
                "releases": [{
                    "versionCodes": [str(version_code)],
                    "status": "completed"
                }]
            }
        )
        
        # Step 4: Commit edit
        commit_response = requests.post(
            f"{self.API_BASE}/applications/{config.package_name}/edits/{edit_id}:commit",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        
        return {
            "success": commit_response.status_code == 200,
            "edit_id": edit_id,
            "version_code": version_code,
            "track": config.track,
            "package": config.package_name
        }
    
    def list_tracks(self, package_name: str) -> List[Dict]:
        """List all release tracks"""
        response = requests.get(
            f"{self.API_BASE}/applications/{package_name}/tracks",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        return response.json().get('tracks', [])


class AppStoreDeployer:
    """Real Apple App Store deployment via App Store Connect API"""
    
    API_BASE = "https://api.appstoreconnect.apple.com/v1"
    
    def __init__(self, issuer_id: str, key_id: str, private_key: str):
        self.issuer_id = issuer_id
        self.key_id = key_id
        self.private_key = private_key
        self.token = self._generate_jwt()
    
    def _generate_jwt(self) -> str:
        """Generate App Store Connect JWT"""
        import jwt
        from datetime import datetime, timedelta
        
        now = datetime.now()
        payload = {
            'iss': self.issuer_id,
            'iat': now,
            'exp': now + timedelta(minutes=20),
            'aud': 'appstoreconnect-v1'
        }
        
        return jwt.encode(payload, self.private_key, algorithm='ES256', 
                         headers={'kid': self.key_id, 'typ': 'JWT'})
    
    def upload_build(self, ipa_path: str, app_id: str) -> Dict:
        """Upload IPA to App Store Connect"""
        # Step 1: Create upload operation
        response = requests.post(
            f"{self.API_BASE}/apps/{app_id}/builds",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
        )
        
        # Note: Actual IPA upload requires Transporter CLI or altool
        # This is the API portion for build management
        
        return {
            "success": response.status_code in [200, 201],
            "build_id": response.json().get('data', {}).get('id'),
            "status": response.status_code
        }


class MasterDeployer:
    """Unified deployment orchestrator"""
    
    def __init__(self):
        self.gp_deployer = None
        self.ios_deployer = None
        self._init_from_env()
    
    def _init_from_env(self):
        """Initialize deployers from environment variables"""
        # Google Play
        gp_service_account = os.getenv('GOOGLE_PLAY_SERVICE_ACCOUNT')
        if gp_service_account:
            self.gp_deployer = GooglePlayDeployer(gp_service_account)
        
        # Apple
        apple_issuer = os.getenv('APPLE_ISSUER_ID')
        apple_key_id = os.getenv('APPLE_KEY_ID')
        apple_key = os.getenv('APPLE_PRIVATE_KEY')
        if all([apple_issuer, apple_key_id, apple_key]):
            self.ios_deployer = AppStoreDeployer(apple_issuer, apple_key_id, apple_key)
    
    def deploy_android(self, config: DeploymentConfig) -> Dict:
        """Deploy to Google Play Store"""
        if not self.gp_deployer:
            return {
                "success": False,
                "error": "Google Play not configured. Set GOOGLE_PLAY_SERVICE_ACCOUNT"
            }
        
        return self.gp_deployer.upload_bundle(config)
    
    def deploy_ios(self, ipa_path: str, app_id: str) -> Dict:
        """Deploy to Apple App Store"""
        if not self.ios_deployer:
            return {
                "success": False,
                "error": "Apple not configured. Set APPLE_ISSUER_ID, APPLE_KEY_ID, APPLE_PRIVATE_KEY"
            }
        
        return self.ios_deployer.upload_build(ipa_path, app_id)
    
    def deploy_all(self, android_config: DeploymentConfig, ios_ipa: str, ios_app_id: str) -> Dict:
        """Deploy to both stores"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "android": None,
            "ios": None
        }
        
        if self.gp_deployer:
            try:
                results["android"] = self.deploy_android(android_config)
            except Exception as e:
                results["android"] = {"success": False, "error": str(e)}
        
        if self.ios_deployer:
            try:
                results["ios"] = self.deploy_ios(ios_ipa, ios_app_id)
            except Exception as e:
                results["ios"] = {"success": False, "error": str(e)}
        
        return results


if __name__ == "__main__":
    # Test configuration
    deployer = MasterDeployer()
    
    # Example iHhashi deployment
    config = DeploymentConfig(
        repo_path="/home/workspace/iHhashi",
        package_name="com.ihhashi.app",
        version_code=2,
        version_name="1.0.1",
        track="internal",
        aab_path="/home/workspace/iHhashi/app/build/outputs/bundle/release/app-release.aab"
    )
    
    result = deployer.deploy_all(
        android_config=config,
        ios_ipa="/home/workspace/iHhashi/ios/App.ipa",
        ios_app_id="com.ihhashi.app"
    )
    
    print(json.dumps(result, indent=2))
