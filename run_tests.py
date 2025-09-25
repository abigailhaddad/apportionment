#!/usr/bin/env python3
"""
Run all data validation tests for CI/CD pipeline.
Exit with non-zero status if any critical tests fail.
"""

import sys
import subprocess

def run_test(script_name, description):
    """Run a test script and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print('='*60)
    
    try:
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=True, 
                              text=True)
        
        print(result.stdout)
        
        if result.returncode != 0:
            print(f"\n❌ FAILED: {description}")
            print("STDERR:", result.stderr)
            return False
        else:
            print(f"\n✅ PASSED: {description}")
            return True
            
    except Exception as e:
        print(f"\n❌ ERROR running {script_name}: {e}")
        return False

def main():
    """Run all tests and exit with appropriate code."""
    
    tests = [
        ("test_sf133_data.py", "SF133 Data Validation Tests"),
        ("verify_month_progression.py", "Month Progression Verification"),
    ]
    
    all_passed = True
    passed_count = 0
    
    print("RUNNING TEST SUITE")
    print("="*60)
    
    for script, description in tests:
        if run_test(script, description):
            passed_count += 1
        else:
            all_passed = False
    
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {passed_count}")
    print(f"Failed: {len(tests) - passed_count}")
    
    if all_passed:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()