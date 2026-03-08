#!/usr/bin/env python3
"""
Configuration management for Google Play deployment
Supports YAML config files and environment variables
"""

import os
import sys
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class GooglePlayConfig:
    """Google Play specific configuration"""
    credentials_file: Optional[str] = None
    credentials_json: Optional[str] = None
    package_name: str = ""
    
@dataclass
class DeploymentConfig:
    """Deployment settings"""
    default_track: str = "internal"
    auto_promote: bool = False
    promote_from: str = "internal"
    promote_to: str = "alpha"
    
@dataclass
class NotificationConfig:
    """Notification settings"""
    slack_enabled: bool = False
    slack_webhook: str = ""
    email_enabled: bool = False
    email_address: str = ""
    
@dataclass
class GPDeployConfig:
    """Main configuration"""
    google_play: GooglePlayConfig = field(default_factory=GooglePlayConfig)
    deployment: DeploymentConfig = field(default_factory=DeploymentConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> 'GPDeployConfig':
        """
        Load configuration from file or environment variables
        
        Priority:
        1. Explicit config file path
        2. Environment variable GOOGLE_PLAY_SERVICE_ACCOUNT_JSON
        3. ~/.config/gp-deploy/config.yml
        4. Current directory gp-deploy.yml
        """
        config = cls()
        
        # Try to load from file
        config_file = None
        if config_path:
            config_file = Path(config_path)
        else:
            # Search common locations
            search_paths = [
                Path.home() / '.config' / 'gp-deploy' / 'config.yml',
                Path('gp-deploy.yml'),
                Path('config' ) / 'gp-deploy.yml',
            ]
            for path in search_paths:
                if path.exists():
                    config_file = path
                    break
        
        if config_file and config_file.exists():
            config._load_from_file(config_file)
        
        # Environment variables override file config
        config._load_from_env()
        
        return config
    
    def _load_from_file(self, path: Path):
        """Load configuration from YAML file"""
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
            
            if not data:
                return
            
            # Google Play settings
            gp_data = data.get('google_play', {})
            if 'credentials_file' in gp_data:
                creds_path = Path(gp_data['credentials_file']).expanduser()
                if creds_path.exists():
                    with open(creds_path) as f:
                        self.google_play.credentials_json = f.read()
            if 'credentials_json' in gp_data:
                self.google_play.credentials_json = gp_data['credentials_json']
            if 'package_name' in gp_data:
                self.google_play.package_name = gp_data['package_name']
            
            # Deployment settings
            dep_data = data.get('deployment', {})
            if 'default_track' in dep_data:
                self.deployment.default_track = dep_data['default_track']
            if 'auto_promote' in dep_data:
                self.deployment.auto_promote = dep_data['auto_promote']
            if 'promote_from' in dep_data:
                self.deployment.promote_from = dep_data['promote_from']
            if 'promote_to' in dep_data:
                self.deployment.promote_to = dep_data['promote_to']
            
            # Notification settings
            notif_data = data.get('notifications', {})
            slack_data = notif_data.get('slack', {})
            if slack_data.get('enabled'):
                self.notifications.slack_enabled = True
                self.notifications.slack_webhook = slack_data.get('webhook_url', '')
            
            email_data = notif_data.get('email', {})
            if email_data.get('enabled'):
                self.notifications.email_enabled = True
                self.notifications.email_address = email_data.get('address', '')
                
        except Exception as e:
            print(f"Warning: Could not load config file: {e}", file=sys.stderr)
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        # Google Play credentials
        if os.getenv('GOOGLE_PLAY_SERVICE_ACCOUNT_JSON'):
            self.google_play.credentials_json = os.getenv('GOOGLE_PLAY_SERVICE_ACCOUNT_JSON')
        if os.getenv('GOOGLE_PLAY_PACKAGE_NAME'):
            self.google_play.package_name = os.getenv('GOOGLE_PLAY_PACKAGE_NAME')
        
        # Deployment settings
        if os.getenv('GP_DEPLOY_TRACK'):
            self.deployment.default_track = os.getenv('GP_DEPLOY_TRACK')
        
        # Notifications
        if os.getenv('SLACK_WEBHOOK_URL'):
            self.notifications.slack_enabled = True
            self.notifications.slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        if os.getenv('DEPLOY_NOTIFICATION_EMAIL'):
            self.notifications.email_enabled = True
            self.notifications.email_address = os.getenv('DEPLOY_NOTIFICATION_EMAIL')
    
    def validate(self) -> tuple[bool, list[str]]:
        """Validate configuration"""
        errors = []
        
        if not self.google_play.credentials_json and not self.google_play.credentials_file:
            errors.append("Google Play credentials not configured")
        
        if not self.google_play.package_name:
            errors.append("Package name not configured")
        
        return len(errors) == 0, errors
    
    def save(self, path: Optional[str] = None):
        """Save configuration to file"""
        if path is None:
            path = Path.home() / '.config' / 'gp-deploy' / 'config.yml'
        
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Don't save credentials in YAML, use separate file
        creds_file = path.parent / 'credentials.json'
        if self.google_play.credentials_json:
            with open(creds_file, 'w') as f:
                f.write(self.google_play.credentials_json)
            os.chmod(creds_file, 0o600)
        
        data = {
            'google_play': {
                'credentials_file': str(creds_file) if creds_file.exists() else None,
                'package_name': self.google_play.package_name,
            },
            'deployment': {
                'default_track': self.deployment.default_track,
                'auto_promote': self.deployment.auto_promote,
                'promote_from': self.deployment.promote_from,
                'promote_to': self.deployment.promote_to,
            },
            'notifications': {
                'slack': {
                    'enabled': self.notifications.slack_enabled,
                    'webhook_url': self.notifications.slack_webhook,
                },
                'email': {
                    'enabled': self.notifications.email_enabled,
                    'address': self.notifications.email_address,
                }
            }
        }
        
        with open(path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)
        os.chmod(path, 0o600)


def load_config() -> GPDeployConfig:
    """Convenience function to load configuration"""
    return GPDeployConfig.load()
