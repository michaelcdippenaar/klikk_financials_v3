#!/usr/bin/env python3
"""
Simple test runner that executes tests and saves output to file.
"""
import subprocess
import sys
from pathlib import Path

def run_test(project_path, test_path, output_file):
    """Run a test and save output."""
    print(f"Running: {test_path}")
    print(f"Project: {project_path}")
    
    cmd = ['python3', 'manage.py', 'test', test_path, '--verbosity=2']
    
    try:
        result = subprocess.run(
            cmd,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        output = f"""
{'='*80}
Test: {test_path}
Project: {project_path}
Exit Code: {result.returncode}
{'='*80}

STDOUT:
{result.stdout}

STDERR:
{result.stderr}
"""
        
        with open(output_file, 'w') as f:
            f.write(output)
        
        print(f"Output saved to: {output_file}")
        print(f"Exit code: {result.returncode}")
        print(f"Output length: {len(result.stdout)} chars")
        
        return result.returncode == 0
        
    except Exception as e:
        error_msg = f"Error running test: {e}"
        print(error_msg)
        with open(output_file, 'w') as f:
            f.write(error_msg)
        return False

if __name__ == '__main__':
    output_dir = Path('/tmp/test_results')
    output_dir.mkdir(exist_ok=True)
    
    # Test v2
    v2_path = '/Users/mcdippenaar/PycharmProjects/klikk_financials_v2/klikk_business_intelligence'
    run_test(v2_path, 'apps.xero.test_views.XeroAuthInitiateViewTest', 
             output_dir / 'v2_views.txt')
    
    # Test v3
    v3_path = '/Users/mcdippenaar/PycharmProjects/klikk_financials_v3'
    run_test(v3_path, 'apps.xero.xero_auth.tests.XeroAuthInitiateViewTest',
             output_dir / 'v3_auth.txt')
    
    print(f"\nResults saved in: {output_dir}")

