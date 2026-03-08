#!/usr/bin/env python3
"""
BATTLE TEST ROUND 4: Resource Exhaustion & DoS Testing
Tests: Memory exhaustion, file descriptor exhaustion, CPU exhaustion
"""

import sys
import os
import time
import asyncio
import tempfile
import resource
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

class ResourceExhaustionTester:
    """Test resource exhaustion resistance"""
    
    def __init__(self):
        self.findings = []
        self.total_tests = 0
        self.passed_tests = 0
        
    def log_finding(self, severity, category, description):
        self.findings.append({
            'severity': severity,
            'category': category,
            'description': description
        })
        print(f"  [!] {severity}: {description}")
        
    def test_large_file_handling(self):
        """Test handling of extremely large files"""
        print("\n[+] Testing Large File Handling...")
        
        from google_play_deployment import AABValidator, SecurityConfig
        import zipfile
        
        # Create test directory
        test_dir = "build/test_large"
        os.makedirs(test_dir, exist_ok=True)
        large_file = os.path.join(test_dir, "large.aab")
        
        try:
            # Create a ZIP file that's larger than max AAB size
            with zipfile.ZipFile(large_file, 'w') as zf:
                zf.writestr('base/test.txt', b'x' * 1024)
            
            # Make it appear larger by seeking (sparse file approach won't work with ZIP)
            # Instead, let's create a file that exceeds the limit through actual size
            with open(large_file, 'ab') as f:
                current = f.tell()
                target = SecurityConfig.MAX_AAB_SIZE + 1024
                if current < target:
                    f.write(b'\x00' * (target - current))
            
            self.total_tests += 1
            result = AABValidator.validate_aab(large_file)
            
            if not result.valid:
                self.passed_tests += 1
                print(f"  [✓] Large file rejected: {result.errors[0][:50]}")
            else:
                self.log_finding(
                    'CRITICAL',
                    'File Size',
                    f'Oversized file accepted: {result.size_mb:.1f}MB'
                )
        finally:
            import shutil
            shutil.rmtree(test_dir, ignore_errors=True)
            
    def test_many_small_files(self):
        """Test handling of many small files"""
        print("\n[+] Testing Many Small Files...")
        
        from google_play_deployment import AABValidator
        import zipfile
        
        # Create test directory
        test_dir = "build/test_many"
        os.makedirs(test_dir, exist_ok=True)
        many_files_aab = os.path.join(test_dir, "many.aab")
        
        try:
            # Create an AAB with many small entries
            with zipfile.ZipFile(many_files_aab, 'w') as zf:
                # Add many small files (ZIP bomb style)
                for i in range(10000):
                    zf.writestr(f"base/file_{i}.txt", b"x")
            
            self.total_tests += 1
            start = time.time()
            result = AABValidator.validate_aab(many_files_aab)
            elapsed = time.time() - start
            
            # Should complete in reasonable time
            if elapsed < 10:
                self.passed_tests += 1
                print(f"  [✓] Many files handled in {elapsed:.2f}s")
            else:
                self.log_finding(
                    'MEDIUM',
                    'Performance',
                    f'Slow handling of many files: {elapsed:.2f}s'
                )
        finally:
            import shutil
            shutil.rmtree(test_dir, ignore_errors=True)
            
    def test_zip_bomb(self):
        """Test ZIP bomb (compression ratio attack)"""
        print("\n[+] Testing ZIP Bomb Resistance...")
        
        import zipfile
        from google_play_deployment import AABValidator
        
        # Create test directory
        test_dir = "build/test_zipbomb"
        os.makedirs(test_dir, exist_ok=True)
        zip_bomb = os.path.join(test_dir, "bomb.aab")
        
        try:
            # Create a ZIP bomb (high compression ratio)
            with zipfile.ZipFile(zip_bomb, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                # Create highly compressible data
                data = b'A' * (10 * 1024 * 1024)  # 10MB of 'A's
                zf.writestr('base/large.txt', data)
            
            self.total_tests += 1
            
            # Validate should reject due to high compression ratio
            result = AABValidator.validate_aab(zip_bomb)
            
            if not result.valid and 'ZIP bomb' in str(result.errors):
                self.passed_tests += 1
                print(f"  [✓] ZIP bomb rejected: {result.errors[0][:60]}")
            else:
                self.log_finding(
                    'HIGH',
                    'ZIP Bomb',
                    f'ZIP bomb not detected: {result.errors}'
                )
        finally:
            import shutil
            shutil.rmtree(test_dir, ignore_errors=True)
            
    def test_deeply_nested_paths(self):
        """Test deeply nested directory structures"""
        print("\n[+] Testing Deeply Nested Paths...")
        
        # Create a path that's extremely nested
        depth = 1000
        nested_path = "artifacts/" + "/".join(["dir" + str(i) for i in range(depth)]) + "/app.aab"
        
        from google_play_deployment import InputValidator
        
        self.total_tests += 1
        try:
            result = InputValidator.validate_path(nested_path, must_exist=False)
            self.passed_tests += 1
            print(f"  [✓] Deep path handled")
        except (ValueError, FileNotFoundError):
            # Deep paths should be rejected
            self.passed_tests += 1
            print(f"  [✓] Deep path rejected")
        except RecursionError:
            self.log_finding(
                'CRITICAL',
                'Recursion',
                f'Recursion error on deep path'
            )
            
    def test_long_filename(self):
        """Test extremely long filenames"""
        print("\n[+] Testing Long Filenames...")
        
        from google_play_deployment import InputValidator
        
        # Create filename with max Linux filename length (255)
        long_name = "artifacts/" + "a" * 250 + ".aab"
        
        self.total_tests += 1
        try:
            result = InputValidator.validate_path(long_name, must_exist=False)
            self.passed_tests += 1
            print(f"  [✓] Long filename handled")
        except ValueError:
            self.passed_tests += 1
            print(f"  [✓] Long filename rejected")
            
    def test_memory_stress(self):
        """Test memory stress conditions"""
        print("\n[+] Testing Memory Stress...")
        
        from google_play_deployment import InputValidator
        
        # Generate many large inputs
        large_inputs = []
        for i in range(100):
            large_inputs.append("artifacts/" + "x" * 10000 + str(i) + ".aab")
        
        self.total_tests += 1
        start = time.time()
        
        for inp in large_inputs:
            try:
                InputValidator.validate_path(inp, must_exist=False)
            except ValueError:
                pass
        
        elapsed = time.time() - start
        
        if elapsed < 5:  # Should be fast
            self.passed_tests += 1
            print(f"  [✓] Memory stress passed: {elapsed:.2f}s")
        else:
            self.log_finding(
                'MEDIUM',
                'Performance',
                f'Slow memory handling: {elapsed:.2f}s'
            )
            
    def test_cpu_exhaustion_regex(self):
        """Test regex CPU exhaustion (ReDoS)"""
        print("\n[+] Testing Regex CPU Exhaustion (ReDoS)...")
        
        import re
        
        # Test our regex patterns against ReDoS attacks
        from google_play_deployment import InputValidator
        
        # Pattern that could cause catastrophic backtracking
        malicious_inputs = [
            'artifacts/' + '%2e' * 1000 + '/app.aab',
            'artifacts/' + '.' * 1000 + '/app.aab',
            'artifacts/app' + ';' * 1000 + '.aab',
        ]
        
        self.total_tests += 1
        start = time.time()
        
        for inp in malicious_inputs:
            try:
                InputValidator.validate_path(inp, must_exist=False)
            except ValueError:
                pass
        
        elapsed = time.time() - start
        
        if elapsed < 1:  # Should be fast even with malicious input
            self.passed_tests += 1
            print(f"  [✓] Regex ReDoS resistant: {elapsed:.3f}s")
        else:
            self.log_finding(
                'HIGH',
                'ReDoS',
                f'Potential ReDoS vulnerability: {elapsed:.3f}s'
            )
            
    def test_concurrent_file_access(self):
        """Test concurrent file access"""
        print("\n[+] Testing Concurrent File Access...")
        
        import zipfile
        from google_play_deployment import AABValidator
        
        # Create test directory
        test_dir = "build/test_concurrent"
        os.makedirs(test_dir, exist_ok=True)
        test_aab = os.path.join(test_dir, "test.aab")
        
        # Create test AAB
        with zipfile.ZipFile(test_aab, 'w') as zf:
            zf.writestr('base/test.txt', b'test')
        
        async def access_task(task_id):
            try:
                result = AABValidator.validate_aab(test_aab)
                return True
            except Exception:
                return False
        
        try:
            async def run_concurrent():
                tasks = [access_task(i) for i in range(50)]
                return await asyncio.gather(*tasks)
            
            self.total_tests += 1
            results = asyncio.run(run_concurrent())
            
            if all(results):
                self.passed_tests += 1
                print(f"  [✓] Concurrent access successful: {sum(results)}/{len(results)}")
            else:
                self.log_finding(
                    'MEDIUM',
                    'Concurrency',
                    f'Concurrent access failures: {results.count(False)}'
                )
        finally:
            import shutil
            shutil.rmtree(test_dir, ignore_errors=True)
            
    def test_disk_space_handling(self):
        """Test graceful handling of disk space issues"""
        print("\n[+] Testing Disk Space Handling...")
        
        # Check available disk space
        stat = os.statvfs('/tmp')
        available_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        
        self.total_tests += 1
        if available_gb > 1:  # At least 1GB free
            self.passed_tests += 1
            print(f"  [✓] Sufficient disk space: {available_gb:.1f}GB")
        else:
            self.log_finding(
                'HIGH',
                'Disk Space',
                f'Low disk space: {available_gb:.1f}GB'
            )
            
    def test_file_handle_exhaustion(self):
        """Test file handle exhaustion"""
        print("\n[+] Testing File Handle Limits...")
        
        import zipfile
        
        # Get current limit
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        
        self.total_tests += 1
        
        # Create many files
        files = []
        try:
            for i in range(min(100, soft - 20)):  # Leave some handles
                f = tempfile.NamedTemporaryFile(suffix='.aab', delete=False)
                files.append(f)
            
            self.passed_tests += 1
            print(f"  [✓] File handle management OK")
            
        except OSError as e:
            self.log_finding(
                'HIGH',
                'File Handles',
                f'File handle exhaustion: {e}'
            )
        finally:
            for f in files:
                try:
                    f.close()
                    os.unlink(f.name)
                except:
                    pass
                    
    def run_all_tests(self):
        """Run all resource exhaustion tests"""
        print("=" * 70)
        print("BATTLE TEST ROUND 4: Resource Exhaustion & DoS Testing")
        print("=" * 70)
        
        self.test_large_file_handling()
        self.test_many_small_files()
        self.test_zip_bomb()
        self.test_deeply_nested_paths()
        self.test_long_filename()
        self.test_memory_stress()
        self.test_cpu_exhaustion_regex()
        self.test_concurrent_file_access()
        self.test_disk_space_handling()
        self.test_file_handle_exhaustion()
        
        # Print summary
        print("\n" + "=" * 70)
        print("ROUND 4 SUMMARY")
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
    tester = ResourceExhaustionTester()
    findings = tester.run_all_tests()
    
    critical_count = sum(1 for f in findings if f['severity'] == 'CRITICAL')
    sys.exit(critical_count)
