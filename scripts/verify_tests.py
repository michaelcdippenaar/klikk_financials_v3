#!/usr/bin/env python
"""
Quick verification script to check test files are syntactically correct.
"""
import ast
import sys
from pathlib import Path

def check_file_syntax(file_path):
    """Check if a Python file has valid syntax."""
    try:
        with open(file_path, 'r') as f:
            code = f.read()
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)

def main():
    """Check all test files."""
    test_files = [
        # v2 tests
        '/Users/mcdippenaar/PycharmProjects/klikk_financials_v2/klikk_business_intelligence/apps/xero/test_views.py',
        '/Users/mcdippenaar/PycharmProjects/klikk_financials_v2/klikk_business_intelligence/apps/xero/test_services.py',
        
        # v3 tests
        '/Users/mcdippenaar/PycharmProjects/klikk_financials_v3/apps/xero/xero_auth/tests.py',
        '/Users/mcdippenaar/PycharmProjects/klikk_financials_v3/apps/xero/xero_core/tests.py',
        '/Users/mcdippenaar/PycharmProjects/klikk_financials_v3/apps/xero/xero_sync/tests.py',
        '/Users/mcdippenaar/PycharmProjects/klikk_financials_v3/apps/xero/xero_sync/test_services.py',
        '/Users/mcdippenaar/PycharmProjects/klikk_financials_v3/apps/xero/xero_cube/tests.py',
        '/Users/mcdippenaar/PycharmProjects/klikk_financials_v3/apps/xero/xero_cube/test_services.py',
    ]
    
    print("="*80)
    print("VERIFYING TEST FILES SYNTAX")
    print("="*80)
    
    all_ok = True
    for file_path in test_files:
        path = Path(file_path)
        if not path.exists():
            print(f"✗ {path.name:50} FILE NOT FOUND")
            all_ok = False
            continue
        
        ok, error = check_file_syntax(file_path)
        if ok:
            print(f"✓ {path.name:50} OK")
        else:
            print(f"✗ {path.name:50} SYNTAX ERROR: {error}")
            all_ok = False
    
    print("="*80)
    if all_ok:
        print("✓ ALL TEST FILES HAVE VALID SYNTAX")
    else:
        print("✗ SOME TEST FILES HAVE ERRORS")
    print("="*80)
    
    return 0 if all_ok else 1

if __name__ == '__main__':
    sys.exit(main())

