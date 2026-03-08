#!/usr/bin/env python3
"""
Google Play Deployment Setup Wizard
Interactive configuration for first-time users
"""

import os
import sys
import json
import base64
from pathlib import Path
from typing import Optional, Tuple

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

class SetupWizard:
    """Interactive setup wizard for Google Play deployment"""
    
    def __init__(self):
        self.config = {}
        
    def print_header(self, text: str):
        """Print a formatted header"""
        print(f"\n{Colors.HEADER}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}{text}{Colors.END}")
        print(f"{Colors.HEADER}{'='*60}{Colors.END}\n")
        
    def print_success(self, text: str):
        print(f"{Colors.GREEN}✓ {text}{Colors.END}")
        
    def print_error(self, text: str):
        print(f"{Colors.RED}✗ {text}{Colors.END}")
        
    def print_info(self, text: str):
        print(f"{Colors.BLUE}ℹ {text}{Colors.END}")
        
    def print_warning(self, text: str):
        print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")
        
    def ask(self, question: str, default: Optional[str] = None, required: bool = True) -> str:
        """Ask user for input"""
        prompt = f"{Colors.BOLD}{question}{Colors.END}"
        if default:
            prompt += f" [{default}]: "
        else:
            prompt += ": "
            
        while True:
            response = input(prompt).strip()
            if response:
                return response
            if default is not None:
                return default
            if not required:
                return ""
            self.print_error("This field is required")
            
    def ask_yes_no(self, question: str, default: bool = False) -> bool:
        """Ask yes/no question"""
        suffix = " [Y/n]: " if default else " [y/N]: "
        response = input(f"{Colors.BOLD}{question}{Colors.END}{suffix}").strip().lower()
        if not response:
            return default
        return response in ['y', 'yes']
    
    def ask_choice(self, question: str, choices: list, default: int = 0) -> int:
        """Ask user to choose from options"""
        print(f"\n{Colors.BOLD}{question}{Colors.END}")
        for i, choice in enumerate(choices):
            marker = "→" if i == default else " "
            print(f"  {marker} {i+1}. {choice}")
        
        while True:
            response = input(f"\nSelect option [1-{len(choices)}]: ").strip()
            if not response:
                return default
            try:
                idx = int(response) - 1
                if 0 <= idx < len(choices):
                    return idx
            except ValueError:
                pass
            self.print_error("Invalid choice")
    
    def step_welcome(self):
        """Welcome step"""
        self.print_header("Google Play Deployment Setup Wizard")
        print("""
This wizard will help you configure Google Play Store deployment.

You'll need:
  1. A Google Play service account JSON key
  2. Your app's package name (e.g., com.example.app)
  3. [Optional] Slack webhook for notifications

The setup takes about 3 minutes.
""")
        input("Press Enter to continue...")
        
    def step_credentials(self) -> bool:
        """Configure Google Play credentials"""
        self.print_header("Step 1: Google Play Credentials")
        
        print("""
You need a Google Play service account key. Here's how to get one:

1. Go to: https://play.google.com/console
2. Setup → API Access → Create Service Account
3. Download the JSON key file
4. Copy the contents here (or provide the file path)
""")
        
        # Ask for credentials
        cred_method = self.ask_choice(
            "How would you like to provide credentials?",
            [
                "Paste JSON content directly",
                "Provide file path to JSON",
                "Base64-encoded JSON"
            ]
        )
        
        credentials = None
        
        if cred_method == 0:  # Paste JSON
            print("\nPaste your service account JSON (press Ctrl+D when done):")
            lines = []
            try:
                while True:
                    line = input()
                    lines.append(line)
            except EOFError:
                pass
            credentials = '\n'.join(lines)
            
        elif cred_method == 1:  # File path
            file_path = self.ask("Path to service account JSON file")
            try:
                with open(os.path.expanduser(file_path)) as f:
                    credentials = f.read()
                self.print_success(f"Read credentials from {file_path}")
            except Exception as e:
                self.print_error(f"Could not read file: {e}")
                return False
                
        else:  # Base64
            b64_string = self.ask("Paste base64-encoded credentials")
            try:
                credentials = base64.b64decode(b64_string).decode('utf-8')
                self.print_success("Decoded credentials")
            except Exception as e:
                self.print_error(f"Could not decode: {e}")
                return False
        
        # Validate JSON
        try:
            creds_json = json.loads(credentials)
            required_fields = ['type', 'project_id', 'private_key', 'client_email']
            missing = [f for f in required_fields if f not in creds_json]
            
            if missing:
                self.print_error(f"Missing fields: {missing}")
                return False
                
            if creds_json.get('type') != 'service_account':
                self.print_error("Credential type must be 'service_account'")
                return False
                
            self.config['credentials'] = credentials
            self.config['client_email'] = creds_json.get('client_email')
            self.print_success("Credentials validated successfully")
            return True
            
        except json.JSONDecodeError as e:
            self.print_error(f"Invalid JSON: {e}")
            return False
    
    def step_package_name(self) -> bool:
        """Configure package name"""
        self.print_header("Step 2: Package Name")
        
        print("""
Your app's package name is the unique identifier in Google Play.
Examples:
  - com.yourcompany.yourapp
  - io.github.yourname.app
""")
        
        while True:
            package = self.ask("Enter your app's package name")
            
            # Basic validation
            if not package or '.' not in package:
                self.print_error("Invalid package name (must contain dots)")
                continue
                
            # Check for invalid characters
            valid_chars = set('abcdefghijklmnopqrstuvwxyz0123456789._')
            if not all(c in valid_chars for c in package.lower()):
                self.print_error("Package name contains invalid characters")
                continue
                
            self.config['package_name'] = package
            self.print_success(f"Package name set to: {package}")
            return True
    
    def step_default_track(self):
        """Configure default track"""
        self.print_header("Step 3: Default Track")
        
        print("""
Which track should be used for deployments by default?

  internal  - Internal testing (fastest, recommended for CI/CD)
  alpha     - Closed testing
  beta      - Open testing
  production- Production (use with caution!)
""")
        
        tracks = ['internal', 'alpha', 'beta', 'production']
        choice = self.ask_choice(
            "Select default track:",
            tracks,
            default=0
        )
        
        self.config['default_track'] = tracks[choice]
        self.print_success(f"Default track: {tracks[choice]}")
        
        # Production warning
        if tracks[choice] == 'production':
            self.print_warning("Production track selected! Deployments will be live immediately.")
            if not self.ask_yes_no("Are you sure?", default=False):
                return self.step_default_track()
    
    def step_notifications(self):
        """Configure notifications"""
        self.print_header("Step 4: Notifications (Optional)")
        
        if not self.ask_yes_no("Would you like to configure notifications?", default=False):
            return
            
        # Slack
        if self.ask_yes_no("Configure Slack notifications?"):
            webhook = self.ask("Slack webhook URL")
            self.config['slack_webhook'] = webhook
            self.print_success("Slack configured")
            
        # Email
        if self.ask_yes_no("Configure email notifications?"):
            email = self.ask("Email address")
            self.config['email'] = email
            self.print_success("Email configured")
    
    def step_test_connection(self) -> bool:
        """Test connection to Google Play"""
        self.print_header("Step 5: Testing Connection")
        
        print("Testing connection to Google Play API...")
        
        # Set temporary env vars for testing
        os.environ['GOOGLE_PLAY_SERVICE_ACCOUNT_JSON'] = self.config['credentials']
        os.environ['GOOGLE_PLAY_PACKAGE_NAME'] = self.config['package_name']
        
        try:
            # Try to import and validate
            from google_play_deployment import SecurityConfig
            valid, errors = SecurityConfig.validate_environment()
            
            if valid:
                self.print_success("Environment configuration valid")
                print("\nAttempting to connect to Google Play API...")
                
                # Try actual connection (will fail without google module, that's OK)
                try:
                    from google.oauth2 import service_account
                    from googleapiclient.discovery import build
                    
                    creds = service_account.Credentials.from_service_account_info(
                        json.loads(self.config['credentials']),
                        scopes=['https://www.googleapis.com/auth/androidpublisher']
                    )
                    service = build('androidpublisher', 'v3', credentials=creds)
                    
                    # Try to access the app
                    app_info = service.edits().insert(
                        packageName=self.config['package_name']
                    ).execute()
                    
                    self.print_success("Successfully connected to Google Play API!")
                    return True
                    
                except ImportError:
                    self.print_warning("Google API module not installed (pip install google-api-python-client)")
                    self.print_info("Configuration is valid, but connection test skipped")
                    return True
                except Exception as e:
                    self.print_error(f"Could not connect: {e}")
                    if "permission" in str(e).lower():
                        print("\nMake sure your service account has access to this app in Play Console.")
                    return False
            else:
                for error in errors:
                    self.print_error(error)
                return False
                
        except Exception as e:
            self.print_error(f"Validation failed: {e}")
            return False
    
    def step_save_configuration(self) -> str:
        """Save configuration to file"""
        self.print_header("Step 6: Save Configuration")
        
        # Determine config file location
        config_dir = Path.home() / '.config' / 'gp-deploy'
        config_dir.mkdir(parents=True, exist_ok=True)
        
        config_file = config_dir / 'config.yml'
        
        # Also save credentials separately for security
        creds_file = config_dir / 'credentials.json'
        with open(creds_file, 'w') as f:
            f.write(self.config['credentials'])
        os.chmod(creds_file, 0o600)  # Owner read/write only
        
        # Create YAML config (without credentials)
        config_yaml = f"""# Google Play Deployment Configuration
# Generated by setup wizard on {__import__('datetime').datetime.now().isoformat()}

google_play:
  credentials_file: {creds_file}
  package_name: {self.config['package_name']}

deployment:
  default_track: {self.config.get('default_track', 'internal')}
  
notifications:
  slack:
    enabled: {'webhook' in self.config}
    webhook_url: {self.config.get('slack_webhook', '')}
  email:
    enabled: {'email' in self.config}
    address: {self.config.get('email', '')}
"""
        
        with open(config_file, 'w') as f:
            f.write(config_yaml)
        os.chmod(config_file, 0o600)
        
        self.print_success(f"Configuration saved to: {config_file}")
        self.print_info(f"Credentials saved to: {creds_file}")
        
        # Show how to use
        print(f"""
{Colors.BOLD}You're all set!{Colors.END}

Next steps:
  1. Build your AAB: ./gradlew bundleRelease
  2. Deploy: python google_play_deployment.py deploy build/app.aab

Or use auto-detect:
  python gp_wizard.py --deploy

Configuration location: {config_file}
""")
        
        return str(config_file)
    
    def run(self):
        """Run the full wizard"""
        try:
            self.step_welcome()
            
            if not self.step_credentials():
                self.print_error("Setup failed at credentials step")
                return 1
                
            if not self.step_package_name():
                self.print_error("Setup failed at package name step")
                return 1
                
            self.step_default_track()
            self.step_notifications()
            
            if not self.step_test_connection():
                if not self.ask_yes_no("Continue anyway?"):
                    return 1
            
            self.step_save_configuration()
            
            self.print_header("Setup Complete! 🎉")
            return 0
            
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}Setup cancelled.{Colors.END}")
            return 130
        except Exception as e:
            self.print_error(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return 1


def quick_deploy():
    """Quick deploy with auto-detection"""
    print(f"{Colors.BOLD}Auto-detecting AAB file...{Colors.END}")
    
    # Search for AAB files in common locations
    search_paths = [
        'build/app/outputs/bundle/release',
        'build/app/outputs/bundle/Release',
        'android/app/build/outputs/bundle/release',
        'app/build/outputs/bundle/release',
        'build',
        '.',
    ]
    
    found_aabs = []
    for path in search_paths:
        if os.path.exists(path):
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith('.aab'):
                        full_path = os.path.join(root, file)
                        found_aabs.append(full_path)
    
    if not found_aabs:
        print(f"{Colors.RED}No AAB files found.{Colors.END}")
        print("Build your app first: ./gradlew bundleRelease")
        return 1
    
    # Show options
    if len(found_aabs) == 1:
        aab_path = found_aabs[0]
        print(f"{Colors.GREEN}Found: {aab_path}{Colors.END}")
    else:
        print(f"\n{Colors.BOLD}Multiple AAB files found:{Colors.END}")
        for i, aab in enumerate(found_aabs[:10], 1):
            size_mb = os.path.getsize(aab) / (1024 * 1024)
            print(f"  {i}. {aab} ({size_mb:.1f}MB)")
        
        choice = int(input("\nSelect file (number): ")) - 1
        aab_path = found_aabs[choice]
    
    # Load config
    config_file = Path.home() / '.config' / 'gp-deploy' / 'config.yml'
    if config_file.exists():
        print(f"\n{Colors.BLUE}Using configuration: {config_file}{Colors.END}")
    
    # Ask for track
    track = input(f"\nDeploy to track [internal/alpha/beta/production] [internal]: ").strip() or "internal"
    
    print(f"\n{Colors.BOLD}Deploying {aab_path} to {track}...{Colors.END}\n")
    
    # Run deployment
    import asyncio
    from google_play_deployment import DeploymentManager, Track, AABValidator
    
    async def deploy():
        # Validate first
        print("[1/4] Validating AAB...")
        validation = AABValidator.validate_aab(aab_path)
        if not validation.valid:
            print(f"{Colors.RED}Validation failed:{Colors.END}")
            for error in validation.errors:
                print(f"  - {error}")
            return 1
        print(f"{Colors.GREEN}✓ Valid ({validation.size_mb:.1f}MB){Colors.END}")
        
        # Deploy
        print(f"[2/4] Initializing deployment...")
        manager = DeploymentManager()
        
        print(f"[3/4] Uploading to Google Play...")
        result = await manager.deploy(aab_path, track)
        
        if result.success:
            print(f"{Colors.GREEN}✓ Deployment successful!{Colors.END}")
            print(f"\n  Deployment ID: {result.deployment_id}")
            print(f"  Track: {result.track}")
            if result.google_play_response:
                print(f"  Version Code: {result.google_play_response.get('version_code')}")
            return 0
        else:
            print(f"{Colors.RED}✗ Deployment failed:{Colors.END}")
            print(f"  {result.error_details}")
            return 1
    
    return asyncio.run(deploy())


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--deploy':
        sys.exit(quick_deploy())
    else:
        wizard = SetupWizard()
        sys.exit(wizard.run())
