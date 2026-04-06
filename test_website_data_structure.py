"""
Test suite for website data structure validation.
Ensures CSV files used by the website have correct structure and valid data.
"""

import pandas as pd
import os
import sys
import glob
import json
from pathlib import Path

def test_csv_structure():
    """Test that all CSV files have the correct structure and columns.
    Returns dict with passing years and monthly data."""
    
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
    
    # Expected columns for monthly files (includes Month and Fiscal_Year)
    expected_monthly_columns = [
        'Month',
        'Fiscal_Year',
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
    monthly_files = []
    
    # Main summary file
    main_file = f'{site_data_dir}all_agencies_obligation_summary.csv'
    if os.path.exists(main_file):
        csv_files.append(main_file)
    
    # Year-specific files
    year_files = glob.glob(f'{site_data_dir}all_agencies_obligation_summary_*.csv')
    csv_files.extend(year_files)
    
    # Monthly files - check for both individual month files and combined files
    monthly_files = glob.glob(f'{site_data_dir}all_agencies_monthly_summary_*.csv')
    
    if not csv_files and not monthly_files:
        print("❌ ERROR: No CSV summary files found in site/data/")
        return {"passing_years": [], "monthly_data": {}}
    
    print(f"✅ Found {len(csv_files)} year-specific CSV files and {len(monthly_files)} monthly files to validate")
    
    errors = []
    passing_years = []
    monthly_data = {}  # year -> list of available months
    
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
    
    # Validate monthly files
    for monthly_file in monthly_files:
        file_passed = True
        
        # Extract year from filename (e.g., all_agencies_monthly_summary_2024_all.csv or all_agencies_monthly_summary_2024_Jan.csv)
        year = None
        filename = os.path.basename(monthly_file)
        if filename.startswith('all_agencies_monthly_summary_') and filename.endswith('.csv'):
            # Remove prefix and suffix
            remaining = filename.replace('all_agencies_monthly_summary_', '').replace('.csv', '')
            # Split by underscore and take first part as year
            parts = remaining.split('_')
            year_str = parts[0]
            if year_str.isdigit():
                year = int(year_str)
        
        try:
            # Read monthly CSV
            df = pd.read_csv(monthly_file)
            
            # Check if file is empty
            if len(df) == 0:
                errors.append(f"{monthly_file}: File is empty")
                continue
                
            # Check required columns exist
            missing_cols = set(expected_monthly_columns) - set(df.columns)
            if missing_cols:
                errors.append(f"{monthly_file}: Missing columns: {missing_cols}")
                continue
                
            # Check for minimum number of records
            if len(df) < 100:
                errors.append(f"{monthly_file}: Only {len(df)} records, expected at least 100")
                file_passed = False
                
            # Check for minimum number of agencies
            if 'Agency' in df.columns:
                unique_agencies = df['Agency'].nunique()
                if unique_agencies < 15:
                    errors.append(f"{monthly_file}: Only {unique_agencies} agencies, expected at least 15")
                    file_passed = False
            
            # Get available months for this year
            if file_passed and year is not None:
                if year not in monthly_data:
                    monthly_data[year] = set()
                
                if 'Month' in df.columns:
                    # Combined file with multiple months
                    available_months = df['Month'].unique().tolist()
                    monthly_data[year].update(available_months)
                else:
                    # Individual month file - extract month from filename
                    remaining = filename.replace('all_agencies_monthly_summary_', '').replace('.csv', '')
                    parts = remaining.split('_')
                    if len(parts) >= 2:
                        month = parts[1]  # e.g., "Jan" from "2024_Jan"
                        monthly_data[year].add(month)
                    
            month_count = len(df['Month'].unique()) if 'Month' in df.columns else 1
            print(f"✅ {monthly_file}: Structure OK ({len(df)} records, {df['Agency'].nunique()} agencies, {month_count} months)")
            
        except Exception as e:
            errors.append(f"{monthly_file}: Failed to read - {str(e)}")
            file_passed = False
    
    if errors:
        print("\n❌ STRUCTURE VALIDATION ERRORS:")
        for error in errors:
            print(f"  - {error}")
    
    print(f"\n✅ Years passing structure tests: {sorted(passing_years)}")
    print(f"✅ Years with monthly data: {sorted(monthly_data.keys())}")
    
    # Convert sets to sorted lists
    monthly_data_sorted = {year: sorted(list(months)) for year, months in monthly_data.items()}
    
    return {
        "passing_years": sorted(passing_years),
        "monthly_data": monthly_data_sorted
    }

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

def test_required_files_exist():
    """Test that all required files for website functionality exist."""
    
    site_data_dir = 'site/data/'
    errors = []
    
    # Load approved years to know what we should have
    try:
        with open(f'{site_data_dir}approved_years.json', 'r') as f:
            approval_data = json.load(f)
        approved_years = approval_data['approved_years']
    except (FileNotFoundError, KeyError):
        print("❌ ERROR: Could not load approved_years.json")
        return False
    
    print(f"Checking required files for approved years: {approved_years}")
    
    # Check main files exist
    required_main_files = [
        'all_agencies_obligation_summary.csv',
        'all_agencies_summary.json', 
        'fiscal_year_metadata.json',
        'approved_years.json'
    ]
    
    for filename in required_main_files:
        filepath = f'{site_data_dir}{filename}'
        if not os.path.exists(filepath):
            errors.append(f"Missing required main file: {filename}")
    
    # Check year-specific files exist for approved years
    for year in approved_years:
        # Year-specific CSV (for single year comparison)
        csv_file = f'{site_data_dir}all_agencies_obligation_summary_{year}.csv'
        if not os.path.exists(csv_file):
            errors.append(f"Missing year-specific CSV for FY{year}: all_agencies_obligation_summary_{year}.csv")
        
        # Year-specific JSON (for multi-year comparison "Most Recent")
        json_file = f'{site_data_dir}all_agencies_summary_{year}.json'
        if not os.path.exists(json_file):
            errors.append(f"Missing year-specific JSON for FY{year}: all_agencies_summary_{year}.json")
    
    # Check monthly files exist for years that should have them
    monthly_files_found = {}
    monthly_files = glob.glob(f'{site_data_dir}all_agencies_monthly_summary_*.csv')
    
    for monthly_file in monthly_files:
        filename = os.path.basename(monthly_file)
        if filename.startswith('all_agencies_monthly_summary_') and filename.endswith('.csv'):
            # Extract year from filename
            remaining = filename.replace('all_agencies_monthly_summary_', '').replace('.csv', '')
            parts = remaining.split('_')
            if parts and parts[0].isdigit():
                year = int(parts[0])
                if year not in monthly_files_found:
                    monthly_files_found[year] = []
                
                if len(parts) >= 2:
                    month = parts[1]  # e.g., "Jan", "Feb", "all"
                    monthly_files_found[year].append(month)
    
    # Validate monthly file coverage
    for year in approved_years:
        if year in monthly_files_found:
            months = monthly_files_found[year]
            month_count = len([m for m in months if m != 'all'])  # Don't count 'all' files
            
            # Accept any amount of monthly data - no minimum requirements
            if month_count == 0:
                print(f"⚠️ Note: FY{year} has no monthly files, but this is acceptable")
            else:
                print(f"✅ FY{year} has {month_count} monthly files")
        else:
            # Accept any year without monthly data
            print(f"⚠️ Note: FY{year} has no monthly files, but this is acceptable")
    
    if errors:
        print("❌ REQUIRED FILES VALIDATION ERRORS:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print(f"✅ All required files exist for {len(approved_years)} approved years")
    print(f"✅ Monthly data available for years: {sorted(monthly_files_found.keys())}")
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
    
    validation_results = None
    
    for test_name, test_func in tests:
        print(f"Running {test_name} test...")
        try:
            result = test_func()
            
            # Special handling for CSV Structure test which returns validation data
            if test_name == "CSV Structure":
                validation_results = result
                # Consider it passed if we have any passing years or monthly data
                passed = len(result["passing_years"]) > 0 or len(result["monthly_data"]) > 0
                results.append(passed)
            else:
                results.append(result)
                
            is_passed = result if isinstance(result, bool) else (len(result["passing_years"]) > 0 or len(result["monthly_data"]) > 0)
            print(f"{'✅' if is_passed else '❌'} {test_name}: {'PASSED' if is_passed else 'FAILED'}")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {str(e)}")
            results.append(False)
        print()
    
    # Final summary
    passed = sum(results)
    total = len(results)
    
    print(f"📊 FINAL RESULTS: {passed}/{total} tests passed")
    
    # Show available data summary
    if validation_results:
        print(f"\n📅 DATA AVAILABILITY SUMMARY:")
        print(f"   Years available: {validation_results['passing_years']}")
        if validation_results['monthly_data']:
            print(f"   Monthly data:")
            for year, months in validation_results['monthly_data'].items():
                print(f"     FY{year}: {', '.join(months)} ({len(months)} months)")
        else:
            print(f"   No monthly data available")
    
    if passed == total:
        print("\n🎉 All website data validation tests PASSED!")
        return 0
    else:
        print("\n💥 Some website data validation tests FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())