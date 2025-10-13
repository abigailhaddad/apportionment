#!/usr/bin/env python3
"""
Parse SF133 files using Raw Data sheet instead of TAFS detail sheet.
This should be more reliable and consistent across different file formats and years.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Column mapping from Raw Data sheet to standardized month names
RAW_DATA_COLUMN_MAPPING = {
    # Monthly columns (individual months)
    'AMT_OCT': 'Oct',
    'AMT_NOV': 'Nov', 
    'AMT_DEC': 'Dec',
    'AMT_JAN': 'Jan',
    'AMT_FEB': 'Feb',
    'AMT_MAR': 'Mar',
    'AMT_APR': 'Apr',
    'AMT_MAY': 'May',
    'AMT_JUN': 'Jun',
    'AMT_JUL': 'Jul',
    'AMT_AUG': 'Aug',
    'AMT_SEP': 'Sep',
    
    # Quarterly columns (cumulative amounts)
    'AMT1': 'Dec (1Q)',  # December = 1st Quarter end
    'AMT2': 'Mar (2Q)',  # March = 2nd Quarter end  
    'AMT3': 'Jun (3Q)',  # June = 3rd Quarter end
    'AMT4': 'Sep (4Q)',  # September = 4th Quarter end (fiscal year end)
    
    # Note: Some months may not have individual columns in all files,
    # but quarterly columns should always be present
}

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

def parse_sf133_raw_data(file_path):
    """Parse the Raw Data sheet from an SF 133 file."""
    print(f"Processing Raw Data: {file_path.name}")
    
    # Skip consolidated files that contain multiple agencies to avoid double-counting
    consolidated_files = ['2668331098.xlsx']  # Known consolidated file with multiple agencies
    if file_path.name in consolidated_files:
        print(f"  Skipping consolidated file to avoid double-counting agencies")
        return None
    
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
        
        # Rename columns according to our mapping
        columns_to_rename = {}
        available_month_columns = []
        
        for raw_col, standard_col in RAW_DATA_COLUMN_MAPPING.items():
            if raw_col in df.columns:
                columns_to_rename[raw_col] = standard_col
                available_month_columns.append(standard_col)
        
        # Apply column renaming
        df = df.rename(columns=columns_to_rename)
        
        print(f"  Available month columns: {available_month_columns}")
        
        # Add metadata columns
        df['Agency'] = agency_name
        df['Source_File'] = Path(file_path).name
        
        # Apply TAFS detail equivalent filtering
        # 1. Keep only rows with valid line numbers (LINENO column)  
        if 'LINENO' in df.columns:
            df = df[df['LINENO'].notna()]
            print(f"  Rows with line numbers: {len(df)}")
            
            # 2. Filter to standard line number ranges that appear in TAFS detail
            # TAFS detail typically shows line numbers like 1000-5000 range
            # Filter out any unusual/administrative line numbers outside normal budget reporting
            numeric_line_nos = pd.to_numeric(df['LINENO'], errors='coerce')
            standard_lines = df[(numeric_line_nos >= 1000) & (numeric_line_nos <= 9999)]
            print(f"  Rows with standard line numbers (1000-9999): {len(standard_lines)}")
            df = standard_lines
            
            # 3. Aggregate to match TAFS detail level: preserve the same granularity as original
            # The TAFS detail sheet preserves fiscal year detail, so we need to include those fields
            grouping_cols = ['BUREAU', 'OMB_ACCT', 'LINENO']
            
            # Add all the key fields that create unique combinations in TAFS detail
            additional_fields = ['TRACCT', 'TRAG', 'ALLOC', 'FY1', 'FY2', 'LINE_DESC']
            for field in additional_fields:
                if field in df.columns:
                    grouping_cols.append(field)
            
            if len(grouping_cols) >= 3:  # We need at least Bureau, Account, Line Number
                print(f"  Aggregating by: {grouping_cols}")
                
                # Identify month columns to sum
                month_cols = [col for col in df.columns if col in RAW_DATA_COLUMN_MAPPING.values()]
                
                # Create aggregation dictionary
                agg_dict = {}
                for col in df.columns:
                    if col in month_cols:
                        agg_dict[col] = 'sum'  # Sum monthly amounts
                    elif col in grouping_cols:
                        continue  # These are grouping columns
                    elif col in ['Agency', 'Source_File']:
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

def parse_all_sf133_raw_data(source_dir='raw_data/august'):
    """Process all SF 133 files using Raw Data sheets."""
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
    
    for file_path in excel_files:
        try:
            df = parse_sf133_raw_data(file_path)
            if df is not None and len(df) > 0:
                all_data.append(df)
                successful_files += 1
                agencies_processed.add(df['Agency'].iloc[0])
                print(f"  Success: {len(df)} rows")
            else:
                print(f"  Skipping - no data extracted")
        except Exception as e:
            print(f"  Error processing {file_path.name}: {str(e)}")
        print()
    
    # Combine all data
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Save the master table
        output_path = Path('site/data/sf133_raw_data_master.csv')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        combined_df.to_csv(output_path, index=False)
        
        print(f"\n=== RAW DATA PROCESSING SUMMARY ===")
        print(f"Successfully processed: {successful_files} files")
        print(f"Total agencies: {len(agencies_processed)}")
        print(f"Agencies found:")
        for agency in sorted(agencies_processed):
            count = len(combined_df[combined_df['Agency'] == agency])
            print(f"  - {agency} ({count:,} rows)")
        print(f"\nTotal rows: {len(combined_df):,}")
        print(f"Raw data master table saved to: {output_path}")
        
        # Show available month columns
        month_columns = [col for col in combined_df.columns if any(month in col for month in ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Q'])]
        print(f"\nAvailable month columns: {month_columns}")
        
        return output_path
    else:
        print("No data was successfully extracted from any files.")
        return None

if __name__ == "__main__":
    import sys
    
    # Allow specifying source directory as command line argument
    source_dir = sys.argv[1] if len(sys.argv) > 1 else 'raw_data/august'
    parse_all_sf133_raw_data(source_dir)