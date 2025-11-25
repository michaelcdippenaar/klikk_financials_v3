#!/usr/bin/env python
"""
Inline test runner for v2 and v3.
Runs tests and displays results.
"""
import os
import sys
import subprocess
from pathlib import Path

def run_django_tests(project_path, test_path, description):
    """Run Django tests and return results."""
    print(f"\n{'='*80}")
    print(f"Running {description}")
    print(f"Path: {project_path}")
    print(f"Test: {test_path}")
    print(f"{'='*80}\n")
    
    os.chdir(project_path)
    
    cmd = ['python3', 'manage.py', 'test', test_path, '--verbosity=2']
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        print(f"\n{'='*80}")
        if result.returncode == 0:
            print(f"✓ {description} - PASSED")
        else:
            print(f"✗ {description} - FAILED (exit code: {result.returncode})")
        print(f"{'='*80}\n")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"✗ {description} - TIMEOUT")
        return False
    except Exception as e:
        print(f"✗ {description} - ERROR: {e}")
        return False

def main():
    """Main test runner."""
    print("="*80)
    print("INLINE TEST RUNNER - v2 vs v3")
    print("="*80)
    
    v2_path = Path('/Users/mcdippenaar/PycharmProjects/klikk_financials_v2/klikk_business_intelligence')
    v3_path = Path('/Users/mcdippenaar/PycharmProjects/klikk_financials_v3')
    
    results = {}
    
    # Test v2 views
    results['v2_views'] = run_django_tests(
        v2_path,
        'apps.xero.test_views',
        'v2 - View Tests'
    )
    
    # Test v2 services
    results['v2_services'] = run_django_tests(
        v2_path,
        'apps.xero.test_services',
        'v2 - Service Tests'
    )
    
    # Test v3 auth
    results['v3_auth'] = run_django_tests(
        v3_path,
        'apps.xero.xero_auth',
        'v3 - Auth Tests'
    )
    
    # Test v3 core
    results['v3_core'] = run_django_tests(
        v3_path,
        'apps.xero.xero_core',
        'v3 - Core Tests'
    )
    
    # Test v3 sync
    results['v3_sync'] = run_django_tests(
        v3_path,
        'apps.xero.xero_sync',
        'v3 - Sync Tests'
    )
    
    # Test v3 cube
    results['v3_cube'] = run_django_tests(
        v3_path,
        'apps.xero.xero_cube',
        'v3 - Cube Tests'
    )
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name:20} {status}")
    
    all_passed = all(results.values())
    print("="*80)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("="*80)
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())

