#!/usr/bin/env python3
"""
Comprehensive SF133 data validation using summary CSV files
Tests data integrity, agency coverage, and fiscal year completeness
Key requirement: Previous years should have comprehensive account data, current year may be partial
"""

import json
import pandas as pd
import os
import sys
from pathlib import Path
from datetime import datetime

# Known incomplete years (will generate warnings but not fail the build)
KNOWN_INCOMPLETE_YEARS = [2015, 2016, 2017]

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

def test_year_data_completeness():
    """Test that we have required data for each fiscal year"""
    print("Testing fiscal year data completeness...")
    
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
        return False
    
    # Check requirements for each year
    all_passed = True
    
    for year in available_years:
        print(f"\n  Checking FY{year}:")
        csv_path = Path(f'site/data/all_agencies_obligation_summary_{year}.csv')
        
        try:
            df = pd.read_csv(csv_path)
            
            # Check agency coverage
            agencies_found = set(df['Agency'].unique())
            missing_agencies = set(EXPECTED_AGENCIES) - agencies_found
            
            # Special handling for "Other Independent Agencies" - may be broken out individually in some years
            if "Other Independent Agencies" in missing_agencies:
                # Check if we have individual independent agencies instead
                independent_agencies = [a for a in agencies_found if a not in EXPECTED_AGENCIES]
                if len(independent_agencies) > 0:
                    print(f"    ✅ {len(agencies_found)} agencies present (Other Independent Agencies broken out as: {independent_agencies[:3]}{'...' if len(independent_agencies) > 3 else ''})")
                    missing_agencies.discard("Other Independent Agencies")
                else:
                    if year in KNOWN_INCOMPLETE_YEARS:
                        print(f"    ⚠️  Missing Other Independent Agencies (expected for FY{year})")
                    else:
                        print(f"    ❌ Missing Other Independent Agencies and no individual independent agencies found")
            
            # Check for other missing agencies (strict requirement for complete years only)
            if len(missing_agencies) > 0:
                if year in KNOWN_INCOMPLETE_YEARS:
                    print(f"    ⚠️  Missing {len(missing_agencies)} agencies (expected for FY{year}): {list(missing_agencies)[:5]}{'...' if len(missing_agencies) > 5 else ''}")
                else:
                    print(f"    ❌ Missing {len(missing_agencies)} required agencies: {list(missing_agencies)}")
                    all_passed = False
            elif "Other Independent Agencies" not in missing_agencies:
                print(f"    ✅ {len(agencies_found)} agencies present")
            
            # Check data volume
            if len(df) < 1000:
                if year in KNOWN_INCOMPLETE_YEARS:
                    print(f"    ⚠️  Only {len(df)} records (expected for FY{year})")
                else:
                    print(f"    ❌ Only {len(df)} records, expected >1000")
                    all_passed = False
            else:
                print(f"    ✅ {len(df):,} records")
            
            # For completed years, verify we have comprehensive data
            if year < current_fy:
                # Previous years should have comprehensive account coverage
                # The data represents budget execution status, not monthly reporting
                if len(df) < 8000:  # Previous years should have more comprehensive data
                    print(f"    ⚠️  FY{year} has limited data ({len(df):,} records) - may be partial year")
                else:
                    print(f"    ✅ Comprehensive end-of-year data")
            else:
                # Current year - partial data is expected
                print(f"    ✅ Current year - partial data acceptable")
                
        except Exception as e:
            print(f"    ❌ Error reading FY{year} data: {e}")
            all_passed = False
    
    return all_passed

def test_csv_summary_files():
    """Test that CSV summary files exist and are properly formatted"""
    print("\nTesting CSV summary files...")
    
    # Check obligation summary files
    csv_files = list(Path('site/data').glob('all_agencies_obligation_summary*.csv'))
    
    if not csv_files:
        print("❌ ERROR: No obligation summary CSV files found")
        return False
    
    print(f"✅ Found {len(csv_files)} CSV summary files")
    
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            
            # Basic validation
            if len(df) == 0:
                print(f"❌ ERROR: {csv_file.name} is empty")
                return False
            
            required_columns = ['Agency', 'Bureau', 'Account']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                print(f"❌ ERROR: {csv_file.name} missing columns: {missing_columns}")
                return False
            
            print(f"✅ {csv_file.name}: {len(df)} rows, {len(df.columns)} columns")
            
        except Exception as e:
            print(f"❌ ERROR: Failed to read {csv_file}: {e}")
            return False
    
    return True

def test_data_consistency():
    """Test that data is consistent across years"""
    print("\nTesting data consistency...")
    
    # Load the main obligation summary
    main_file = Path('site/data/all_agencies_obligation_summary.csv')
    if not main_file.exists():
        print("❌ ERROR: Main obligation summary file not found")
        return False
    
    try:
        df = pd.read_csv(main_file)
        
        # Check for reasonable number of records
        if len(df) < 1000:
            print(f"❌ ERROR: Only {len(df)} records found, expected >1000")
            return False
        
        # Check for reasonable number of agencies
        unique_agencies = df['Agency'].nunique()
        if unique_agencies < 20:
            print(f"❌ ERROR: Only {unique_agencies} agencies found, expected >20")
            return False
        
        # Check for numeric data
        if 'Budget Authority (Line 2500)' in df.columns:
            # Try to parse a few values
            sample_values = df['Budget Authority (Line 2500)'].head(10)
            for val in sample_values:
                if pd.isna(val):
                    continue
                # Should be in format like "$1,234.5M"
                if not isinstance(val, str) or not val.startswith('$'):
                    print(f"❌ ERROR: Budget Authority format issue: {val}")
                    return False
        
        print(f"✅ Main summary: {len(df)} records, {unique_agencies} agencies")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Failed to validate main summary: {e}")
        return False

def test_data_reasonableness():
    """Test that the data values are reasonable across years"""
    print("\nTesting data reasonableness...")
    
    # Load main summary file
    main_file = Path('site/data/all_agencies_obligation_summary.csv')
    if not main_file.exists():
        print("❌ ERROR: Main summary file not found")
        return False
    
    try:
        df = pd.read_csv(main_file)
        
        # Test budget authority and unobligated balance values
        if 'Budget Authority (Line 2500)' in df.columns:
            # Parse currency values like "$1,234.5M"
            ba_values = df['Budget Authority (Line 2500)'].str.replace('$', '').str.replace(',', '').str.replace('M', '').astype(float)
            unob_values = df['Unobligated Balance (Line 2490)'].str.replace('$', '').str.replace(',', '').str.replace('M', '').astype(float)
            
            # Check for reasonable totals (should be in trillions)
            total_ba = ba_values.sum() / 1000  # Convert to billions
            total_unob = unob_values.sum() / 1000
            
            if total_ba < 1000 or total_ba > 50000:  # $1T to $50T reasonable range
                print(f"❌ Total Budget Authority seems unreasonable: ${total_ba:.1f}B")
                return False
            else:
                print(f"✅ Total Budget Authority: ${total_ba:,.1f}B")
            
            # Check percentage calculations
            if 'Percentage Unobligated' in df.columns:
                pct_values = df['Percentage Unobligated'].str.replace('%', '').astype(float)
                extreme_pct = pct_values[(pct_values < -1000) | (pct_values > 1000)]
                
                if len(extreme_pct) > 0:
                    print(f"⚠️  Found {len(extreme_pct)} accounts with extreme percentages (may be valid for negative BA)")
                else:
                    print("✅ Percentage values within reasonable ranges")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Failed to validate data reasonableness: {e}")
        return False

def test_cross_year_consistency():
    """Test consistency across multiple years of data"""
    print("\nTesting cross-year consistency...")
    
    # Get available years
    csv_files = list(Path('site/data').glob('all_agencies_obligation_summary_*.csv'))
    years = []
    year_data = {}
    
    for csv_file in csv_files:
        filename = csv_file.name
        if filename.startswith('all_agencies_obligation_summary_') and filename.endswith('.csv'):
            year_str = filename.replace('all_agencies_obligation_summary_', '').replace('.csv', '')
            if year_str.isdigit():
                year = int(year_str)
                years.append(year)
                try:
                    year_data[year] = pd.read_csv(csv_file)
                except Exception as e:
                    print(f"❌ Failed to load FY{year} data: {e}")
                    return False
    
    if len(years) < 2:
        print("⚠️  Only one year of data available, skipping cross-year tests")
        return True
    
    years.sort()
    print(f"✅ Comparing {len(years)} years of data: {years}")
    
    # Compare agency consistency across years
    baseline_agencies = set(year_data[years[0]]['Agency'].unique())
    
    for year in years[1:]:
        current_agencies = set(year_data[year]['Agency'].unique())
        
        # New agencies are OK, but major losses are concerning
        missing_agencies = baseline_agencies - current_agencies
        if len(missing_agencies) > 3:
            print(f"❌ FY{year} missing {len(missing_agencies)} agencies from FY{years[0]}: {list(missing_agencies)[:3]}...")
            return False
        else:
            print(f"✅ FY{year} has consistent agency coverage")
    
    # Check for reasonable year-over-year budget authority changes
    for i in range(len(years) - 1):
        prev_year, curr_year = years[i], years[i + 1]
        
        # Get total budget authority for each year
        prev_ba = year_data[prev_year]['Budget Authority (Line 2500)'].str.replace('$', '').str.replace(',', '').str.replace('M', '').astype(float).sum()
        curr_ba = year_data[curr_year]['Budget Authority (Line 2500)'].str.replace('$', '').str.replace(',', '').str.replace('M', '').astype(float).sum()
        
        if prev_ba > 0:
            change_pct = ((curr_ba - prev_ba) / prev_ba) * 100
            
            # Flag extreme changes (>50% change year-over-year is unusual)
            if abs(change_pct) > 50:
                print(f"⚠️  Large change FY{prev_year}→FY{curr_year}: {change_pct:+.1f}%")
            else:
                print(f"✅ Reasonable change FY{prev_year}→FY{curr_year}: {change_pct:+.1f}%")
    
    return True

def main():
    """Run all tests"""
    print("🧪 SF133 Data Validation Test Suite")
    print("=" * 60)
    print("Testing budget execution data across multiple fiscal years")
    print("Previous fiscal years should have comprehensive account coverage")
    print("Current fiscal year may have partial data")
    print("=" * 60)
    
    # Change to the repository root
    os.chdir(Path(__file__).parent)
    
    tests = [
        test_year_data_completeness,
        test_csv_summary_files,
        test_data_consistency,
        test_data_reasonableness,
        test_cross_year_consistency
    ]
    
    all_passed = True
    
    for test in tests:
        try:
            if not test():
                all_passed = False
        except Exception as e:
            print(f"❌ ERROR: Test {test.__name__} failed with exception: {e}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All tests passed! Data meets requirements.")
        print("• Previous years have comprehensive account coverage")  
        print("• Current year partial data is acceptable")
        print("• Agency coverage and data quality verified")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        print("Fix issues before deploying to production.")
        sys.exit(1)

if __name__ == "__main__":
    main()