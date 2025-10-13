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
    """Test that all CSV files have the correct structure and columns."""
    
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
    
    for csv_file in csv_files:
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
                
            # Check for minimum number of agencies
            if 'Agency' in df.columns:
                unique_agencies = df['Agency'].nunique()
                if unique_agencies < 15:
                    errors.append(f"{csv_file}: Only {unique_agencies} agencies, expected at least 15")
                    
            print(f"✅ {csv_file}: Structure OK ({len(df)} records, {df['Agency'].nunique()} agencies)")
            
        except Exception as e:
            errors.append(f"{csv_file}: Failed to read - {str(e)}")
    
    if errors:
        print("\n❌ STRUCTURE VALIDATION ERRORS:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print("✅ All CSV files have correct structure")
    return True

def test_numerical_data():
    """Test that numerical data is valid and makes sense."""
    
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
                
            # Parse Budget Authority values
            if 'Budget Authority (Line 2500)' in df.columns:
                # Remove $ and M, convert to float
                ba_col = df['Budget Authority (Line 2500)'].str.replace('$', '').str.replace(',', '').str.replace('M', '')
                ba_numeric = pd.to_numeric(ba_col, errors='coerce')
                
                # Check for negative budget authority (shouldn't happen)
                negative_ba = ba_numeric < 0
                if negative_ba.any():
                    errors.append(f"{csv_file}: Found {negative_ba.sum()} negative Budget Authority values")
                
                # Check for unreasonably large values (>1 trillion)
                huge_ba = ba_numeric > 1000000  # More than 1 trillion dollars in millions
                if huge_ba.any():
                    errors.append(f"{csv_file}: Found {huge_ba.sum()} unreasonably large Budget Authority values (>$1T)")
            
            # Parse Unobligated Balance values  
            if 'Unobligated Balance (Line 2490)' in df.columns:
                unob_col = df['Unobligated Balance (Line 2490)'].str.replace('$', '').str.replace(',', '').str.replace('M', '')
                unob_numeric = pd.to_numeric(unob_col, errors='coerce')
                
                # Check for negative unobligated balance (shouldn't happen normally)
                negative_unob = unob_numeric < 0
                if negative_unob.any():
                    errors.append(f"{csv_file}: Found {negative_unob.sum()} negative Unobligated Balance values")
            
            # Check percentage values
            if 'Percentage Unobligated' in df.columns:
                pct_col = df['Percentage Unobligated'].str.replace('%', '')
                pct_numeric = pd.to_numeric(pct_col, errors='coerce')
                
                # Check for valid percentage range (0-100)
                invalid_pct = (pct_numeric < 0) | (pct_numeric > 100)
                if invalid_pct.any():
                    errors.append(f"{csv_file}: Found {invalid_pct.sum()} invalid percentage values (not 0-100%)")
            
            # Check that unobligated <= budget authority (when both > 0)
            if all(col in df.columns for col in ['Budget Authority (Line 2500)', 'Unobligated Balance (Line 2490)']):
                ba_clean = df['Budget Authority (Line 2500)'].str.replace('$', '').str.replace(',', '').str.replace('M', '').astype(float)
                unob_clean = df['Unobligated Balance (Line 2490)'].str.replace('$', '').str.replace(',', '').str.replace('M', '').astype(float)
                
                # Check logical constraint: unobligated should not exceed budget authority
                invalid_ratio = (unob_clean > ba_clean) & (ba_clean > 0)
                if invalid_ratio.any():
                    errors.append(f"{csv_file}: Found {invalid_ratio.sum()} cases where Unobligated > Budget Authority")
            
            print(f"✅ {csv_file}: Numerical data validation passed")
            
        except Exception as e:
            errors.append(f"{csv_file}: Failed to validate numbers - {str(e)}")
    
    if errors:
        print("\n❌ NUMERICAL VALIDATION ERRORS:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print("✅ All numerical data is valid")
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
        ("Numerical Data", test_numerical_data), 
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