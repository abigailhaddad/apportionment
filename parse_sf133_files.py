#!/usr/bin/env python3
"""
Parse all SF133 files into a master table.
Handles all agencies including Other Independent Agencies with their special structure.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# List of expected agencies
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

def find_agency_in_file(file_path, xl_file):
    """Try to find which agency a file belongs to - check multiple sheets."""
    try:
        # Check Agency Total sheet first - it's usually clearest
        if 'Agency Total' in xl_file.sheet_names:
            df = pd.read_excel(file_path, sheet_name='Agency Total', header=None, nrows=10)
            # Look in first 10 rows
            for i in range(len(df)):
                for j in range(min(5, len(df.columns))):
                    val = df.iloc[i, j]
                    if pd.notna(val) and isinstance(val, str):
                        # Check against our target agencies
                        val_normalized = str(val).replace('--', '-').lower()
                        for agency in TARGET_AGENCIES:
                            agency_normalized = agency.lower()
                            if agency_normalized in val_normalized:
                                return agency
                            # Handle partial matches
                            if agency == "Department of Defense-Military" and "defense" in val_normalized and "military" in val_normalized:
                                return agency
                            # Handle the double-dash cases
                            if agency == "Corps of Engineers-Civil Works" and "corps of engineers" in val_normalized and "civil" in val_normalized:
                                return agency
                            if agency == "Other Defense Civil Programs" and "other defense" in val_normalized and "civil" in val_normalized:
                                return agency
        
        # If not found, check TAFS detail sheet
        if 'TAFS detail' in xl_file.sheet_names:
            df = pd.read_excel(file_path, sheet_name='TAFS detail', header=None, nrows=20)
            for i in range(len(df)):
                for j in range(min(5, len(df.columns))):
                    val = df.iloc[i, j]
                    if pd.notna(val) and isinstance(val, str):
                        val_normalized = str(val).replace('--', '-').lower()
                        for agency in TARGET_AGENCIES:
                            agency_normalized = agency.lower()
                            if agency_normalized in val_normalized:
                                return agency
                            # Handle special cases
                            if agency == "Corps of Engineers-Civil Works" and "corps of engineers" in val_normalized and "civil" in val_normalized:
                                return agency
                            if agency == "Other Defense Civil Programs" and "other defense" in val_normalized and "civil" in val_normalized:
                                return agency
                                
    except Exception as e:
        print(f"  Error finding agency: {e}")
    
    return None

def parse_sf133_tafs_detail(file_path):
    """Parse the TAFS detail sheet from an SF 133 file using pandas for speed."""
    print(f"Processing: {file_path.name}")
    
    try:
        # First, get list of sheet names without loading entire file
        xl_file = pd.ExcelFile(file_path, engine='openpyxl')
        sheet_names = xl_file.sheet_names
        
        # Try to find agency name first
        agency_name = find_agency_in_file(file_path, xl_file)
        
        if not agency_name:
            print(f"  Could not identify agency")
            agency_name = "Unknown Agency"
        else:
            # Clean up agency name
            agency_name = agency_name.replace('--', '-').strip()
            print(f"  Agency: {agency_name}")
        
        # Find the TAFS detail sheet
        tafs_sheet = None
        for sheet_name in sheet_names:
            if 'TAFS' in sheet_name and 'detail' in sheet_name.lower():
                tafs_sheet = sheet_name
                break
        
        if not tafs_sheet:
            print(f"  No TAFS detail sheet found")
            xl_file.close()
            return None
        
        # Read the TAFS detail sheet directly with pandas
        df = pd.read_excel(file_path, sheet_name=tafs_sheet, header=None)
        
        # Find the header row by looking for "Line No" or "Lineno"
        header_row = None
        for idx in range(min(30, len(df))):
            row = df.iloc[idx]
            # Standard agencies have "Line No", OIA might have it in different columns
            if any(('Line No' in str(cell) or 'Lineno' in str(cell)) if pd.notna(cell) else False for cell in row):
                header_row = idx
                break
        
        if header_row is None:
            print(f"  Could not find header row")
            xl_file.close()
            return None
        
        # Set column names from header row
        df.columns = df.iloc[header_row].fillna('')
        df = df.iloc[header_row + 1:].reset_index(drop=True)
        
        # Clean up column names - use index-based names to avoid conflicts
        new_columns = []
        for i, col in enumerate(df.columns):
            col_str = str(col).strip()
            if col_str == '' or pd.isna(col):
                new_columns.append(f'Col_{i}')
            elif 'Line No' in col_str or 'Lineno' in col_str:
                new_columns.append('Line No')
            elif any(month in col_str for month in ['Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct']):
                # Keep month columns as-is
                new_columns.append(col_str)
            else:
                # For other columns, add index to make unique
                new_columns.append(f'Col_{i}')
        
        df.columns = new_columns
        
        # Forward fill logic based on agency type
        if 'Other Independent Agencies' in agency_name:
            # OIA has unique structure
            # Col_6 contains TAFS like "95-2300 /25 - Salaries and Expenses"
            # Col_2 contains account info like "306-00-2300   Salaries and Expenses"
            fill_columns = ['Col_2', 'Col_6']
            for col in fill_columns:
                if col in df.columns:
                    # Only fill if not a line number
                    mask = df[col].astype(str).str.match(r'^\d{4}(\.\d)?$', na=False)
                    df.loc[~mask, col] = df.loc[~mask, col].ffill()
        else:
            # Standard agencies - forward fill bureau, account, TAFS columns
            # Usually Col_0 = Bureau, Col_1 = Account, Col_4 = TAFS
            fill_columns = ['Col_0', 'Col_1', 'Col_4']
            for col in fill_columns:
                if col in df.columns:
                    # Only fill if not a line number
                    mask = df[col].astype(str).str.match(r'^\d{4}(\.\d)?$', na=False)
                    df.loc[~mask, col] = df.loc[~mask, col].ffill()
        
        # Clean up the data
        df = df.replace('', np.nan)
        
        # Add metadata
        df['Agency'] = agency_name
        df['Source_File'] = Path(file_path).name
        
        # Only keep rows with Line No values (or Col_9 for OIA)
        if 'Other Independent Agencies' in agency_name:
            # OIA uses Col_9 for line numbers
            if 'Col_9' in df.columns:
                df = df[df['Col_9'].notna()]
        else:
            # Standard agencies use 'Line No' column
            line_no_col = next((col for col in df.columns if 'Line No' in col), None)
            if line_no_col:
                df = df[df[line_no_col].notna()]
        
        xl_file.close()
        return df
        
    except Exception as e:
        print(f"  Error processing {file_path}: {str(e)}")
        return None

def parse_all_sf133_files():
    """Process all SF 133 files and create a consolidated dataset."""
    sf133_dir = Path('raw_data/sf133')
    
    # Ensure data directory exists
    data_dir = Path('data')
    data_dir.mkdir(exist_ok=True)
    
    # Get all Excel files
    excel_files = list(sf133_dir.glob('*.xlsx')) + list(sf133_dir.glob('*.xls'))
    print(f"Found {len(excel_files)} Excel files to process\n")
    
    # Process each file
    all_data = []
    successful_files = 0
    agencies_processed = set()
    
    for file_path in excel_files:
        try:
            df = parse_sf133_tafs_detail(file_path)
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
        output_path = Path('data/sf133_master_table.csv')
        combined_df.to_csv(output_path, index=False)
        
        print(f"\n=== SUMMARY ===")
        print(f"Successfully processed: {successful_files} files")
        print(f"Total agencies: {len(agencies_processed)}")
        print(f"Agencies found:")
        for agency in sorted(agencies_processed):
            count = len(combined_df[combined_df['Agency'] == agency])
            print(f"  - {agency} ({count:,} rows)")
        print(f"\nTotal rows: {len(combined_df):,}")
        print(f"Master table saved to: {output_path}")
        
        # Also print any "Unknown Agency" files for debugging
        unknown = combined_df[combined_df['Agency'] == 'Unknown Agency']['Source_File'].unique()
        if len(unknown) > 0:
            print(f"\nFiles with unidentified agencies:")
            for f in unknown:
                print(f"  - {f}")
        
        return output_path
    else:
        print("No data was successfully extracted from any files.")
        return None

if __name__ == "__main__":
    parse_all_sf133_files()