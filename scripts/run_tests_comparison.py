#!/usr/bin/env python
"""
Test comparison script to ensure v2 and v3 behave the same.
Runs equivalent tests in both versions and compares results.
"""
import os
import sys
import subprocess
import json
from pathlib import Path

# Color output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def run_tests(project_path, test_pattern=None):
    """Run Django tests and return results."""
    os.chdir(project_path)
    
    cmd = ['python3', 'manage.py', 'test', '--verbosity=2']
    if test_pattern:
        cmd.append(test_pattern)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'stdout': '',
            'stderr': 'Test timeout',
            'returncode': -1
        }

def compare_test_results(v2_result, v3_result):
    """Compare test results from v2 and v3."""
    print(f"\n{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BLUE}Test Comparison Results{Colors.END}")
    print(f"{Colors.BLUE}{'='*80}{Colors.END}\n")
    
    # Overall status
    if v2_result['success'] and v3_result['success']:
        print(f"{Colors.GREEN}✓ Both v2 and v3 tests passed{Colors.END}\n")
        return True
    elif not v2_result['success'] and not v3_result['success']:
        print(f"{Colors.YELLOW}⚠ Both v2 and v3 tests failed{Colors.END}\n")
        return False
    else:
        print(f"{Colors.RED}✗ Test results differ:{Colors.END}")
        if v2_result['success']:
            print(f"  - v2: {Colors.GREEN}PASSED{Colors.END}")
            print(f"  - v3: {Colors.RED}FAILED{Colors.END}")
        else:
            print(f"  - v2: {Colors.RED}FAILED{Colors.END}")
            print(f"  - v3: {Colors.GREEN}PASSED{Colors.END}")
        print()
        return False

def main():
    """Main comparison function."""
    v2_path = Path('/Users/mcdippenaar/PycharmProjects/klikk_financials_v2/klikk_business_intelligence')
    v3_path = Path('/Users/mcdippenaar/PycharmProjects/klikk_financials_v3')
    
    print(f"{Colors.BLUE}Running v2 tests...{Colors.END}")
    v2_result = run_tests(v2_path, 'apps.xero')
    
    print(f"{Colors.BLUE}Running v3 tests...{Colors.END}")
    v3_result = run_tests(v3_path, 'apps.xero')
    
    # Compare results
    success = compare_test_results(v2_result, v3_result)
    
    # Show detailed output if needed
    if not success:
        print(f"\n{Colors.YELLOW}Detailed Output:{Colors.END}\n")
        if not v2_result['success']:
            print(f"{Colors.RED}v2 Test Output:{Colors.END}")
            print(v2_result['stdout'])
            print(v2_result['stderr'])
        if not v3_result['success']:
            print(f"{Colors.RED}v3 Test Output:{Colors.END}")
            print(v3_result['stdout'])
            print(v3_result['stderr'])
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())

