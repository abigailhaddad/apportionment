#!/usr/bin/env python3
"""
Check year data completeness without deleting anything on failure.
This script only reports on the status of yearly data files.
"""

import pandas as pd
import os
from pathlib import Path
from datetime import datetime

# Expected agencies list
EXPECTED_AGENCIES = [
    "Legislative Branch",
    "Judicial Branch", 
    "Department of Agriculture",
    "Department of Commerce",
    "Department of Defense-Military",
    "Department of Education",
    "Department of Energy",
    "Department of Health and Human Services",
    "Department of Homeland Security",
    "Department of Housing and Urban Development",
    "Department of the Interior",
    "Department of Justice",
    "Department of Labor",
    "Department of State",
    "Department of Transportation",
    "Department of the Treasury",
    "Department of Veterans Affairs",
    "Corps of Engineers-Civil Works",
    "Other Defense Civil Programs",
    "Environmental Protection Agency",
    "Executive Office of the President",
    "General Services Administration",
    "International Assistance Programs",
    "National Aeronautics and Space Administration",
    "National Science Foundation",
    "Office of Personnel Management",
    "Small Business Administration",
    "Social Security Administration",
    "Other Independent Agencies"
]

# Known data gaps - agencies that are expected to be missing for specific years
KNOWN_EXCEPTIONS = {
    2012: [
        "Judicial Branch"  # 2012 Judicial Branch files exist but are empty
    ]
}

def check_year_data_completeness():
    """Check that we have required data for each fiscal year (read-only)"""
    print("Checking fiscal year data completeness...")
    
    # Get current fiscal year (FY starts in October)
    current_date = datetime.now()
    current_fy = current_date.year + 1 if current_date.month >= 10 else current_date.year
    
    # Find all available year CSV files
    csv_files = list(Path('site/data').glob('all_agencies_obligation_summary_*.csv'))
    available_years = []
    
    for csv_file in csv_files:
        # Extract year from filename like 'all_agencies_obligation_summary_2025.csv'
        filename = csv_file.name
        if filename.startswith('all_agencies_obligation_summary_') and filename.endswith('.csv'):
            year_str = filename.replace('all_agencies_obligation_summary_', '').replace('.csv', '')
            if year_str.isdigit():
                available_years.append(int(year_str))
    
    available_years.sort()
    print(f"✅ Found data for fiscal years: {available_years}")
    
    if not available_years:
        print("❌ ERROR: No year-specific data files found")
        return []
    
    # Check requirements for each year
    passing_years = []
    
    for year in available_years:
        print(f"\n  Checking FY{year}:")
        csv_path = Path(f'site/data/all_agencies_obligation_summary_{year}.csv')
        year_passed = True
        
        try:
            df = pd.read_csv(csv_path)
            
            # Check agency coverage
            agencies_found = set(df['Agency'].unique())
            missing_agencies = set(EXPECTED_AGENCIES) - agencies_found
            
            # Apply known exceptions for this year
            if year in KNOWN_EXCEPTIONS:
                expected_missing = set(KNOWN_EXCEPTIONS[year])
                actual_missing = missing_agencies & expected_missing
                if actual_missing:
                    print(f"    ℹ️  Known missing agencies for FY{year}: {list(actual_missing)}")
                    missing_agencies -= expected_missing
            
            # Special handling for "Other Independent Agencies" - may be broken out individually in some years
            if "Other Independent Agencies" in missing_agencies:
                # Check if we have individual independent agencies instead
                independent_agencies = [a for a in agencies_found if a not in EXPECTED_AGENCIES]
                if len(independent_agencies) > 0:
                    print(f"    ✅ {len(agencies_found)} agencies present (Other Independent Agencies broken out as: {independent_agencies[:3]}{'...' if len(independent_agencies) > 3 else ''})")
                    missing_agencies.discard("Other Independent Agencies")
                else:
                    print(f"    ❌ Missing Other Independent Agencies and no individual independent agencies found")
            
            # Check for other missing agencies (strict requirement)
            if len(missing_agencies) > 0:
                print(f"    ❌ Missing {len(missing_agencies)} required agencies: {list(missing_agencies)}")
                year_passed = False
            elif "Other Independent Agencies" not in missing_agencies:
                print(f"    ✅ {len(agencies_found)} agencies present")
            
            # Check data volume
            if len(df) < 1000:
                print(f"    ❌ Only {len(df)} records, expected >1000")
                year_passed = False
            else:
                print(f"    ✅ {len(df):,} records")
            
            # For completed years, verify we have comprehensive data
            if year < current_fy:
                # Previous years should have comprehensive account coverage
                if len(df) < 8000:  # Previous years should have more comprehensive data
                    print(f"    ⚠️  FY{year} has limited data ({len(df):,} records) - may be partial year")
                else:
                    print(f"    ✅ Comprehensive end-of-year data")
            else:
                # Current year - partial data is expected
                print(f"    ✅ Current year - partial data acceptable")
                
        except Exception as e:
            print(f"    ❌ Error reading FY{year} data: {e}")
            year_passed = False
        
        # Add year to passing list if it passed all checks
        if year_passed:
            passing_years.append(year)
    
    print(f"\n✅ Years passing completeness tests: {passing_years}")
    print(f"📊 Summary: {len(passing_years)}/{len(available_years)} years passed all checks")
    
    return passing_years

def main():
    """Run year data check only"""
    print("📋 Year Data Completeness Check (Read-Only)")
    print("=" * 60)
    print("This script only checks data - no files will be deleted")
    print("=" * 60)
    
    # Change to the repository root
    os.chdir(Path(__file__).parent)
    
    try:
        passing_years = check_year_data_completeness()
        
        print("\n" + "=" * 60)
        if len(passing_years) > 0:
            print(f"✅ Found {len(passing_years)} years with valid data")
            print("No issues detected that would cause file deletion")
        else:
            print("⚠️  No years passed all validation checks")
            print("Files would be deleted if running full test suite")
            
    except Exception as e:
        print(f"❌ ERROR: Check failed with exception: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())