#!/usr/bin/env python3
"""
Parse SF133 files from 2012 using Raw Data sheet.
2012 has a unique format where each file contains only ONE month of data 
(AMT_NOV, AMT_JUL, or AMT_AUG) rather than multiple month columns per file.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# List of expected agencies (same as original)
TARGET_AGENCIES = [
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

def find_agency_from_raw_data(df):
    """Find agency name from Raw Data sheet."""
    if len(df) > 0 and 'AGENCY' in df.columns:
        # Get the most common agency name (should be consistent across all rows)
        agency_names = df['AGENCY'].dropna().unique()
        if len(agency_names) > 0:
            agency_name = agency_names[0]
            
            # Clean up and match against target agencies
            agency_normalized = str(agency_name).replace('--', '-').lower()
            for target_agency in TARGET_AGENCIES:
                target_normalized = target_agency.lower()
                if target_normalized in agency_normalized:
                    return target_agency
                # Handle special cases
                if target_agency == "Department of Defense-Military" and "defense" in agency_normalized and ("military" in agency_normalized or "dod" in agency_normalized):
                    return target_agency
                if target_agency == "Corps of Engineers-Civil Works" and "corps of engineers" in agency_normalized and "civil" in agency_normalized:
                    return target_agency
                if target_agency == "Other Defense Civil Programs" and "other defense" in agency_normalized and "civil" in agency_normalized:
                    return target_agency
                    
            # If no exact match, return the original name
            return str(agency_name).strip()
    
    return "Unknown Agency"

def parse_sf133_2012_file(file_path):
    """Parse a single 2012 SF 133 file (single month format)."""
    print(f"Processing 2012 file: {file_path.name}")
    
    try:
        # Check if Raw Data sheet exists
        xl_file = pd.ExcelFile(file_path, engine='openpyxl')
        sheet_names = xl_file.sheet_names
        
        if 'Raw Data' not in sheet_names:
            print(f"  No Raw Data sheet found")
            xl_file.close()
            return None
        
        # Read Raw Data sheet
        df = pd.read_excel(file_path, sheet_name='Raw Data')
        
        if len(df) == 0:
            print(f"  Raw Data sheet is empty")
            xl_file.close()
            return None
        
        print(f"  Raw data dimensions: {df.shape}")
        
        # Find agency name
        agency_name = find_agency_from_raw_data(df)
        print(f"  Agency: {agency_name}")
        
        # Identify which month this file contains
        month_name = None
        month_column = None
        
        # Check for specific month columns (2012 format)
        if 'AMT_NOV' in df.columns:
            month_name = 'Nov'
            month_column = 'AMT_NOV'
        elif 'AMT_JUL' in df.columns:
            month_name = 'Jul'
            month_column = 'AMT_JUL'
        elif 'AMT_AUG' in df.columns:
            month_name = 'Aug'
            month_column = 'AMT_AUG'
        else:
            print(f"  No recognized month column found in: {df.columns.tolist()}")
            xl_file.close()
            return None
        
        print(f"  Month: {month_name} (from {month_column})")
        
        # Rename the month column to standard format
        df = df.rename(columns={month_column: month_name})
        
        # Add metadata columns
        df['Agency'] = agency_name
        df['Source_File'] = Path(file_path).name
        df['Month'] = month_name
        
        # Apply TAFS detail equivalent filtering
        # 1. Keep only rows with valid line numbers (LINENO column)  
        if 'LINENO' in df.columns:
            df = df[df['LINENO'].notna()]
            print(f"  Rows with line numbers: {len(df)}")
            
            # 2. Filter to standard line number ranges that appear in TAFS detail
            numeric_line_nos = pd.to_numeric(df['LINENO'], errors='coerce')
            standard_lines = df[(numeric_line_nos >= 1000) & (numeric_line_nos <= 9999)]
            print(f"  Rows with standard line numbers (1000-9999): {len(standard_lines)}")
            df = standard_lines
            
            # 3. Aggregate to match TAFS detail level: use only fields needed for final output
            grouping_cols = ['BUREAU', 'OMB_ACCT', 'LINENO']
            
            if len(grouping_cols) >= 3:  # We need at least Bureau, Account, Line Number
                print(f"  Aggregating by: {grouping_cols}")
                
                # Create aggregation dictionary
                agg_dict = {}
                for col in df.columns:
                    if col == month_name:
                        agg_dict[col] = 'sum'  # Sum monthly amounts
                    elif col in grouping_cols:
                        continue  # These are grouping columns
                    elif col in ['Agency', 'Source_File', 'Month']:
                        agg_dict[col] = 'first'  # Keep metadata
                    else:
                        agg_dict[col] = 'first'  # Take first value for other descriptive fields
                
                # Group and aggregate
                df = df.groupby(grouping_cols, as_index=False).agg(agg_dict)
                print(f"  After aggregation to TAFS detail level: {len(df)} rows")
            
        else:
            print(f"  Warning: No LINENO column found")
        
        xl_file.close()
        return df
        
    except Exception as e:
        print(f"  Error processing {file_path}: {str(e)}")
        return None

def parse_all_sf133_2012_data(source_dir='raw_data/2012'):
    """Process all 2012 SF 133 files and combine by agency across months."""
    sf133_dir = Path(source_dir)
    
    # Ensure data directory exists
    output_data_dir = Path('data')
    output_data_dir.mkdir(exist_ok=True)
    
    # Get all Excel files
    excel_files = list(sf133_dir.glob('*.xlsx')) + list(sf133_dir.glob('*.xls'))
    print(f"Found {len(excel_files)} Excel files to process\n")
    
    # Process each file
    all_data = []
    successful_files = 0
    agencies_processed = set()
    month_data = {}  # Track data by agency and month
    
    for file_path in excel_files:
        try:
            df = parse_sf133_2012_file(file_path)
            if df is not None and len(df) > 0:
                all_data.append(df)
                successful_files += 1
                agency = df['Agency'].iloc[0]
                month = df['Month'].iloc[0]
                agencies_processed.add(agency)
                
                # Track which months each agency has
                if agency not in month_data:
                    month_data[agency] = set()
                month_data[agency].add(month)
                
                print(f"  Success: {len(df)} rows for {agency} - {month}")
            else:
                print(f"  Skipping - no data extracted")
        except Exception as e:
            print(f"  Error processing {file_path.name}: {str(e)}")
        print()
    
    # Analyze month coverage per agency
    print(f"\n=== MONTH COVERAGE ANALYSIS ===")
    expected_months = {'Nov', 'Jul', 'Aug'}
    agencies_with_missing_months = []
    
    for agency in sorted(agencies_processed):
        months = month_data[agency]
        missing_months = expected_months - months
        if missing_months:
            agencies_with_missing_months.append((agency, missing_months))
            print(f"⚠️  {agency}: Missing {sorted(missing_months)} (has {sorted(months)})")
        else:
            print(f"✓  {agency}: Complete - has {sorted(months)}")
    
    # Combine all data
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Now we need to pivot/combine the data to create a single record per TAFS with all months
        # Group by TAFS key (BUREAU, OMB_ACCT, LINENO, Agency) and pivot months into columns
        print(f"\n=== COMBINING MONTHS INTO SINGLE RECORDS ===")
        
        # Create a TAFS key for grouping
        combined_df['TAFS_KEY'] = combined_df['BUREAU'].astype(str) + '|' + combined_df['OMB_ACCT'].astype(str) + '|' + combined_df['LINENO'].astype(str) + '|' + combined_df['Agency']
        
        # Pivot to get months as columns
        month_pivot = combined_df.pivot_table(
            index=['BUREAU', 'OMB_ACCT', 'LINENO', 'Agency', 'TAFS_KEY'],
            columns='Month',
            values=['Nov', 'Jul', 'Aug'],
            aggfunc='first'
        )
        
        # Flatten column names
        month_pivot.columns = [f"{month}" for _, month in month_pivot.columns]
        month_pivot = month_pivot.reset_index()
        
        # Clean up - remove the TAFS_KEY column we created for pivoting
        month_pivot = month_pivot.drop('TAFS_KEY', axis=1)
        
        # Add metadata columns back
        month_pivot['Source_File'] = '2012_Combined'
        
        # Fill NaN values with 0 for missing months
        for month in ['Nov', 'Jul', 'Aug']:
            if month in month_pivot.columns:
                month_pivot[month] = month_pivot[month].fillna(0)
        
        print(f"Combined data shape: {month_pivot.shape}")
        
        # Save the master table
        output_path = Path('site/data/sf133_2012_master.csv')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        month_pivot.to_csv(output_path, index=False)
        
        print(f"\n=== 2012 PROCESSING SUMMARY ===")
        print(f"Successfully processed: {successful_files} files")
        print(f"Total agencies: {len(agencies_processed)}")
        print(f"Agencies found:")
        for agency in sorted(agencies_processed):
            count = len(month_pivot[month_pivot['Agency'] == agency])
            months = sorted(month_data[agency])
            print(f"  - {agency} ({count:,} rows, months: {months})")
        
        if agencies_with_missing_months:
            print(f"\n⚠️ AGENCIES WITH MISSING MONTHS:")
            for agency, missing in agencies_with_missing_months:
                print(f"  - {agency}: Missing {sorted(missing)}")
            print(f"\nNote: 2012 only has Nov, Jul, Aug data available")
        
        print(f"\nTotal rows: {len(month_pivot):,}")
        print(f"2012 master table saved to: {output_path}")
        
        # Show available month columns
        month_columns = [col for col in month_pivot.columns if col in ['Nov', 'Jul', 'Aug']]
        print(f"Available month columns: {month_columns}")
        
        return output_path
    else:
        print("No data was successfully extracted from any files.")
        return None

if __name__ == "__main__":
    import sys
    
    # Allow specifying source directory as command line argument
    source_dir = sys.argv[1] if len(sys.argv) > 1 else 'raw_data/2012'
    parse_all_sf133_2012_data(source_dir)