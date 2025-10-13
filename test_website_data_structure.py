"""
Test suite for website data structure validation.
Ensures CSV files used by the website have correct structure and valid data.
"""

import pandas as pd
import os
import sys
import glob
from pathlib import Path

def test_csv_structure():
    """Test that all CSV files have the correct structure and columns.
    Returns list of years that pass validation."""
    
    # Expected columns based on website HTML table headers
    expected_columns = [
        'Agency',
        'Bureau', 
        'Account',
        'Account_Number',
        'Period_of_Performance',
        'Expiration_Year',
        'TAFS',
        'Unobligated Balance (Line 2490)',
        'Budget Authority (Line 2500)',
        'Percentage Unobligated'
    ]
    
    # Find all CSV files that the website uses
    site_data_dir = 'site/data/'
    csv_files = []
    
    # Main summary file
    main_file = f'{site_data_dir}all_agencies_obligation_summary.csv'
    if os.path.exists(main_file):
        csv_files.append(main_file)
    
    # Year-specific files
    year_files = glob.glob(f'{site_data_dir}all_agencies_obligation_summary_*.csv')
    csv_files.extend(year_files)
    
    if not csv_files:
        print("❌ ERROR: No CSV summary files found in site/data/")
        return False
    
    print(f"✅ Found {len(csv_files)} CSV files to validate")
    
    errors = []
    passing_years = []
    
    for csv_file in csv_files:
        file_passed = True
        
        # Extract year from filename if it's a year-specific file
        year = None
        filename = os.path.basename(csv_file)
        if filename.startswith('all_agencies_obligation_summary_') and filename.endswith('.csv'):
            year_str = filename.replace('all_agencies_obligation_summary_', '').replace('.csv', '')
            if year_str.isdigit():
                year = int(year_str)
        
        try:
            # Read CSV
            df = pd.read_csv(csv_file)
            
            # Check if file is empty
            if len(df) == 0:
                errors.append(f"{csv_file}: File is empty")
                continue
                
            # Check required columns exist
            missing_cols = set(expected_columns) - set(df.columns)
            if missing_cols:
                errors.append(f"{csv_file}: Missing columns: {missing_cols}")
                continue
                
            # Check for minimum number of records
            if len(df) < 100:
                errors.append(f"{csv_file}: Only {len(df)} records, expected at least 100")
                file_passed = False
                
            # Check for minimum number of agencies
            if 'Agency' in df.columns:
                unique_agencies = df['Agency'].nunique()
                if unique_agencies < 15:
                    errors.append(f"{csv_file}: Only {unique_agencies} agencies, expected at least 15")
                    file_passed = False
                    
            print(f"✅ {csv_file}: Structure OK ({len(df)} records, {df['Agency'].nunique()} agencies)")
            
        except Exception as e:
            errors.append(f"{csv_file}: Failed to read - {str(e)}")
            file_passed = False
        
        # Add year to passing list if it passed and is a year-specific file
        if file_passed and year is not None:
            passing_years.append(year)
    
    if errors:
        print("\n❌ STRUCTURE VALIDATION ERRORS:")
        for error in errors:
            print(f"  - {error}")
    
    print(f"\n✅ Years passing structure tests: {sorted(passing_years)}")
    return sorted(passing_years)

def test_numerical_data():
    """Test that numerical data can be parsed by the website (like JavaScript parseFloat)."""
    
    site_data_dir = 'site/data/'
    
    # Get all CSV files 
    csv_files = []
    main_file = f'{site_data_dir}all_agencies_obligation_summary.csv'
    if os.path.exists(main_file):
        csv_files.append(main_file)
    year_files = glob.glob(f'{site_data_dir}all_agencies_obligation_summary_*.csv')
    csv_files.extend(year_files)
    
    if not csv_files:
        print("❌ ERROR: No CSV files to validate")
        return False
    
    errors = []
    
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            
            if len(df) == 0:
                continue
                
            # Test that Budget Authority values can be parsed (like JavaScript parseFloat)
            if 'Budget Authority (Line 2500)' in df.columns:
                ba_col = df['Budget Authority (Line 2500)'].str.replace(r'[\$,M]', '', regex=True)
                ba_numeric = pd.to_numeric(ba_col, errors='coerce')
                
                # Check for unparseable values (would become NaN in JavaScript)
                unparseable_ba = ba_numeric.isna()
                if unparseable_ba.any():
                    errors.append(f"{csv_file}: Found {unparseable_ba.sum()} unparseable Budget Authority values")
            
            # Test that Unobligated Balance values can be parsed
            if 'Unobligated Balance (Line 2490)' in df.columns:
                unob_col = df['Unobligated Balance (Line 2490)'].str.replace(r'[\$,M]', '', regex=True)
                unob_numeric = pd.to_numeric(unob_col, errors='coerce')
                
                # Check for unparseable values
                unparseable_unob = unob_numeric.isna()
                if unparseable_unob.any():
                    errors.append(f"{csv_file}: Found {unparseable_unob.sum()} unparseable Unobligated Balance values")
            
            # Test that percentage values can be parsed
            if 'Percentage Unobligated' in df.columns:
                pct_col = df['Percentage Unobligated'].str.replace('%', '')
                pct_numeric = pd.to_numeric(pct_col, errors='coerce')
                
                # Check for unparseable percentages
                unparseable_pct = pct_numeric.isna()
                if unparseable_pct.any():
                    errors.append(f"{csv_file}: Found {unparseable_pct.sum()} unparseable percentage values")
            
            print(f"✅ {csv_file}: All numerical fields are parseable by website")
            
        except Exception as e:
            errors.append(f"{csv_file}: Failed to validate parseability - {str(e)}")
    
    if errors:
        print("\n❌ PARSEABILITY VALIDATION ERRORS:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print("✅ All numerical data is parseable by website")
    return True

def test_required_fields():
    """Test that required fields have no missing values."""
    
    site_data_dir = 'site/data/'
    csv_files = []
    main_file = f'{site_data_dir}all_agencies_obligation_summary.csv'
    if os.path.exists(main_file):
        csv_files.append(main_file)
    year_files = glob.glob(f'{site_data_dir}all_agencies_obligation_summary_*.csv')
    csv_files.extend(year_files)
    
    # Fields that should never be empty
    required_fields = ['Agency', 'Bureau', 'Account', 'Account_Number']
    
    errors = []
    
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            
            if len(df) == 0:
                continue
                
            for field in required_fields:
                if field in df.columns:
                    missing_count = df[field].isna().sum() + (df[field] == '').sum()
                    if missing_count > 0:
                        errors.append(f"{csv_file}: {missing_count} missing values in required field '{field}'")
            
            print(f"✅ {csv_file}: Required fields validation passed")
            
        except Exception as e:
            errors.append(f"{csv_file}: Failed to validate required fields - {str(e)}")
    
    if errors:
        print("\n❌ REQUIRED FIELDS VALIDATION ERRORS:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print("✅ All required fields have valid data")
    return True

def test_data_consistency():
    """Test data consistency across years and files."""
    
    site_data_dir = 'site/data/'
    
    # Check that main summary file exists
    main_file = f'{site_data_dir}all_agencies_obligation_summary.csv'
    if not os.path.exists(main_file):
        print("❌ ERROR: Main summary file not found: all_agencies_obligation_summary.csv")
        return False
    
    # Check that we have data for recent years
    current_year = 2025  # Update this as needed
    expected_years = [current_year - 1, current_year]  # At minimum last year and current year
    
    missing_years = []
    for year in expected_years:
        year_file = f'{site_data_dir}all_agencies_obligation_summary_{year}.csv'
        if not os.path.exists(year_file):
            missing_years.append(year)
    
    if missing_years:
        print(f"⚠️  WARNING: Missing data for years: {missing_years}")
        # Don't fail, just warn
    
    try:
        main_df = pd.read_csv(main_file)
        
        # Basic sanity checks
        if len(main_df) < 1000:
            print(f"❌ ERROR: Main file has only {len(main_df)} records, expected at least 1000")
            return False
            
        unique_agencies = main_df['Agency'].nunique()
        if unique_agencies < 20:
            print(f"❌ ERROR: Main file has only {unique_agencies} agencies, expected at least 20")
            return False
            
        print(f"✅ Data consistency check passed ({len(main_df)} records, {unique_agencies} agencies)")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Failed to validate main data file - {str(e)}")
        return False

def main():
    """Run all website data validation tests."""
    
    print("🔍 Validating website data structure and integrity...")
    print()
    
    tests = [
        ("CSV Structure", test_csv_structure),
        ("Data Parseability", test_numerical_data), 
        ("Required Fields", test_required_fields),
        ("Data Consistency", test_data_consistency)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"Running {test_name} test...")
        try:
            result = test_func()
            results.append(result)
            print(f"{'✅' if result else '❌'} {test_name}: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {str(e)}")
            results.append(False)
        print()
    
    # Final summary
    passed = sum(results)
    total = len(results)
    
    print(f"📊 FINAL RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All website data validation tests PASSED!")
        return 0
    else:
        print("💥 Some website data validation tests FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())