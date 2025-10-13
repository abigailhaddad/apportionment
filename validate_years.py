#!/usr/bin/env python3
"""
Year-based validation coordinator.
Runs both test suites and deploys only years that pass both sets of tests.
"""

import sys
from pathlib import Path

# Import the test functions
from run_tests import test_year_data_completeness
from test_website_data_structure import test_csv_structure

def main():
    """Run both test suites and find years that pass both."""
    
    print("🔍 YEAR-BASED VALIDATION COORDINATOR")
    print("=" * 60)
    print("Running both test suites to find years that pass all validations...")
    print()
    
    # Run the first test suite (data completeness)
    print("📊 RUNNING DATA COMPLETENESS TESTS")
    print("-" * 40)
    try:
        completeness_passing_years = test_year_data_completeness()
        if not isinstance(completeness_passing_years, list):
            print("❌ ERROR: Completeness test didn't return year list")
            return 1
    except Exception as e:
        print(f"❌ ERROR: Completeness tests failed: {e}")
        return 1
    
    print()
    
    # Run the second test suite (structure validation)  
    print("🏗️  RUNNING STRUCTURE VALIDATION TESTS")
    print("-" * 40)
    try:
        structure_passing_years = test_csv_structure()
        if not isinstance(structure_passing_years, list):
            print("❌ ERROR: Structure test didn't return year list")
            return 1
    except Exception as e:
        print(f"❌ ERROR: Structure tests failed: {e}")
        return 1
    
    print()
    
    # Find intersection (years that pass both tests)
    passing_both = set(completeness_passing_years) & set(structure_passing_years)
    passing_both_sorted = sorted(list(passing_both))
    
    print("=" * 60)
    print("📋 VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Years passing completeness tests: {completeness_passing_years}")
    print(f"Years passing structure tests:    {structure_passing_years}")
    print(f"Years passing BOTH tests:        {passing_both_sorted}")
    print()
    
    if len(passing_both_sorted) == 0:
        print("❌ DEPLOYMENT BLOCKED: No years pass both test suites!")
        print("Fix data issues before deploying.")
        return 1
    else:
        print(f"✅ DEPLOYMENT APPROVED: {len(passing_both_sorted)} years ready for production")
        print(f"Deploying years: {passing_both_sorted}")
        
        # Optional: Create a file listing the approved years for deployment scripts
        approved_years_file = Path('site/data/approved_years.json')
        import json
        with open(approved_years_file, 'w') as f:
            json.dump({
                'approved_years': passing_both_sorted,
                'completeness_passing': completeness_passing_years,
                'structure_passing': structure_passing_years
            }, f, indent=2)
        print(f"📄 Approved years list saved to: {approved_years_file}")
        
        return 0

if __name__ == "__main__":
    sys.exit(main())