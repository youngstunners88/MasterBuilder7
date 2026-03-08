#!/usr/bin/env python3
"""
Google Play Deployer v2 - IMPROVED VERSION
Based on: f692cc1cd28c10f3f99e81e85bdd5573090c65ba (Codex PR)
"""

import os
import json
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('google-play-deployer')

SCOPES = ['https://www.googleapis.com/auth/androidpublisher']

class GooglePlayDeployerV2:
    """Production-grade Google Play API client with full track management"""
    
    def __init__(self, service_account_json: str, package_name: str = "com.ihhashi.app"):
        self.package_name = package_name
        self.service_account_json = service_account_json
        self.credentials = None
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Play API"""
        try:
            credentials_info = json.loads(self.service_account_json)
            self.credentials = service_account.Credentials.from_service_account_info(
                credentials_info, scopes=SCOPES
            )
            self.service = build('androidpublisher', 'v3', credentials=self.credentials)
            logger.info("✅ Authenticated with Google Play API")
        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            raise
    
    def upload_bundle(self, aab_path: str, version_code: int) -> dict:
        """Upload Android App Bundle to Google Play"""
        try:
            edit = self.service.edits().insert(packageName=self.package_name).execute()
            edit_id = edit['id']
            logger.info(f"Created edit: {edit_id}")
            
            media = MediaFileUpload(aab_path, mimetype='application/octet-stream')
            bundle = self.service.edits().bundles().upload(
                packageName=self.package_name,
                editId=edit_id,
                media_body=media
            ).execute()
            
            logger.info(f"✅ Uploaded bundle: versionCode={bundle['versionCode']}")
            return {"edit_id": edit_id, "version_code": bundle['versionCode'], "sha1": bundle.get('sha1', 'N/A')}
        except Exception as e:
            logger.error(f"❌ Upload failed: {e}")
            raise
    
    def update_track(self, edit_id: str, track: str, version_code: int, release_notes: list = None) -> dict:
        """Update track (internal, alpha, beta, production)"""
        try:
            track_body = {
                "releases": [{
                    "versionCodes": [str(version_code)],
                    "status": "completed"
                }]
            }
            
            if release_notes:
                track_body["releases"][0]["releaseNotes"] = [
                    {"language": note["language"], "text": note["text"]} 
                    for note in release_notes
                ]
            
            result = self.service.edits().tracks().update(
                packageName=self.package_name,
                editId=edit_id,
                track=track,
                body=track_body
            ).execute()
            
            logger.info(f"✅ Updated {track} track with version {version_code}")
            return result
        except Exception as e:
            logger.error(f"❌ Track update failed: {e}")
            raise
    
    def commit_edit(self, edit_id: str) -> dict:
        """Commit the edit to finalize deployment"""
        try:
            result = self.service.edits().commit(
                packageName=self.package_name,
                editId=edit_id
            ).execute()
            logger.info(f"✅ Commited edit: {result}")
            return result
        except Exception as e:
            logger.error(f"❌ Commit failed: {e}")
            raise
    
    def get_track_status(self, track: str = "internal") -> dict:
        """Get current track status"""
        try:
            edit = self.service.edits().insert(packageName=self.package_name).execute()
            edit_id = edit['id']
            
            track_info = self.service.edits().tracks().get(
                packageName=self.package_name,
                editId=edit_id,
                track=track
            ).execute()
            
            return track_info
        except Exception as e:
            logger.error(f"❌ Failed to get track status: {e}")
            raise
    
    def full_deploy(self, aab_path: str, track: str = "internal", release_notes: list = None) -> dict:
        """Complete deployment workflow: upload + update track + commit"""
        logger.info(f"🚀 Starting deployment to {track} track...")
        
        # Extract version code from AAB filename or gradle
        version_code = self._extract_version_code(aab_path)
        
        # 1. Upload bundle
        upload_result = self.upload_bundle(aab_path, version_code)
        edit_id = upload_result['edit_id']
        
        # 2. Update track
        self.update_track(edit_id, track, version_code, release_notes)
        
        # 3. Commit
        commit_result = self.commit_edit(edit_id)
        
        return {
            "status": "success",
            "track": track,
            "version_code": version_code,
            "edit_id": edit_id,
            "commit_result": commit_result
        }
    
    def _extract_version_code(self, aab_path: str) -> int:
        """Extract version code from AAB or use timestamp"""
        import re
        match = re.search(r'versionCode\.(\d+)', aab_path)
        if match:
            return int(match.group(1))
        # Use timestamp as fallback
        from datetime import datetime
        return int(datetime.now().strftime("%y%m%d%H%M"))


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy to Google Play')
    parser.add_argument('--aab', required=True, help='Path to .aab file')
    parser.add_argument('--track', default='internal', choices=['internal', 'alpha', 'beta', 'production'])
    parser.add_argument('--package', default='com.ihhashi.app', help='Package name')
    parser.add_argument('--version-code', type=int, help='Version code (auto-detected if not provided)')
    
    args = parser.parse_args()
    
    # Load service account from environment
    service_account_json = os.getenv('GOOGLE_PLAY_SERVICE_ACCOUNT_JSON')
    if not service_account_json:
        print("❌ Set GOOGLE_PLAY_SERVICE_ACCOUNT_JSON environment variable")
        return 1
    
    try:
        deployer = GooglePlayDeployerV2(service_account_json, args.package)
        result = deployer.full_deploy(args.aab, args.track)
        print(f"\n🎉 Deployment successful!")
        print(f"   Track: {result['track']}")
        print(f"   Version Code: {result['version_code']}")
        return 0
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
