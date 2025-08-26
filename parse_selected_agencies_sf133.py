#!/usr/bin/env python3
"""
Parse SF 133 TAFS detail data for selected agencies using pandas.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# List of agencies we want
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

def find_agency_in_file(file_path):
    """Try to find which agency a file belongs to."""
    try:
        # Check Agency Total sheet first - it's usually clearest
        xl_file = pd.ExcelFile(file_path)
        
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
        print(f"Error finding agency in {file_path}: {e}")
    
    return None

def parse_sf133_tafs_detail_pandas(file_path, agency_name):
    """Parse the TAFS detail sheet using pandas."""
    try:
        # Read the TAFS detail sheet
        df = pd.read_excel(file_path, sheet_name='TAFS detail', header=None)
        
        # Find the header row by looking for "Line No"
        header_row = None
        for idx in range(min(30, len(df))):
            row = df.iloc[idx]
            if any('Line No' in str(cell) if pd.notna(cell) else False for cell in row):
                header_row = idx
                break
        
        if header_row is None:
            print(f"  Could not find header row in {file_path}")
            return None
        
        # Set column names and get data
        df.columns = df.iloc[header_row].fillna('').astype(str)
        df = df.iloc[header_row + 1:].reset_index(drop=True)
        
        # Rename columns consistently - use index-based names to avoid conflicts
        new_columns = []
        for i, col in enumerate(df.columns):
            col_str = str(col).strip()
            if col_str == '' or pd.isna(col):
                new_columns.append(f'Col_{i}')
            elif 'Line No' in col_str:
                new_columns.append('Line No')
            elif any(month in col_str for month in ['Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct']):
                # Keep month columns as-is
                new_columns.append(col_str)
            else:
                # For other columns, add index to make unique
                new_columns.append(f'Col_{i}')
        
        df.columns = new_columns
        
        # Forward fill bureau, account, and TAFS info (usually in first few columns)
        # Find which columns contain these
        bureau_col = None
        account_col = None
        tafs_col = None
        
        # Usually bureau is Col_0, account is Col_1, and TAFS is around Col_3 or Col_4
        for i in range(min(6, len(df.columns))):
            col = df.columns[i]
            sample = df[col].dropna().astype(str)
            if len(sample) > 0:
                # Check if this looks like TAFS (contains hyphen and numbers)
                if any('-' in s and any(c.isdigit() for c in s) for s in sample.head(20)):
                    tafs_col = col
                # Check if this looks like account names (longer text)
                elif not bureau_col and any(len(s) > 20 for s in sample.head(20)):
                    bureau_col = col
                elif bureau_col and not account_col and any(len(s) > 20 for s in sample.head(20)):
                    account_col = col
        
        # Forward fill the identified columns
        if bureau_col:
            # Only fill non-line number values
            mask = ~df[bureau_col].astype(str).str.match(r'^\d{4}(\.\d)?$', na=True)
            df.loc[mask, bureau_col] = df.loc[mask, bureau_col].ffill()
        
        if account_col:
            mask = ~df[account_col].astype(str).str.match(r'^\d{4}(\.\d)?$', na=True)
            df.loc[mask, account_col] = df.loc[mask, account_col].ffill()
            
        if tafs_col:
            mask = ~df[tafs_col].astype(str).str.match(r'^\d{4}(\.\d)?$', na=True)
            df.loc[mask, tafs_col] = df.loc[mask, tafs_col].ffill()
        
        # Clean up
        df = df.replace('', np.nan)
        
        # Add agency and source file
        df['Agency'] = agency_name
        df['Source_File'] = Path(file_path).name
        
        # Only keep rows with Line No values
        line_no_col = next((col for col in df.columns if 'Line No' in col), None)
        if line_no_col:
            df = df[df[line_no_col].notna()]
        
        return df
        
    except Exception as e:
        print(f"  Error parsing {file_path}: {e}")
        return None

def main():
    """Process SF 133 files for selected agencies."""
    sf133_dir = Path('raw_data/sf133')
    
    # Get all Excel files
    excel_files = list(sf133_dir.glob('*.xlsx')) + list(sf133_dir.glob('*.xls'))
    print(f"Found {len(excel_files)} Excel files")
    print(f"Looking for {len(TARGET_AGENCIES)} target agencies\n")
    
    # First pass: identify which files belong to which agencies
    print("Identifying agencies in files...")
    file_agency_mapping = {}
    agencies_found = set()
    
    for file_path in excel_files:
        agency = find_agency_in_file(file_path)
        if agency:
            file_agency_mapping[file_path] = agency
            agencies_found.add(agency)
            print(f"  {file_path.name} -> {agency}")
    
    print(f"\nFound {len(agencies_found)} agencies in {len(file_agency_mapping)} files")
    print("\nAgencies found:")
    for agency in sorted(agencies_found):
        count = sum(1 for a in file_agency_mapping.values() if a == agency)
        print(f"  - {agency} ({count} files)")
    
    # Missing agencies
    missing = set(TARGET_AGENCIES) - agencies_found
    if missing:
        print("\nAgencies NOT found:")
        for agency in sorted(missing):
            print(f"  - {agency}")
    
    # Second pass: parse the files
    print("\n\nParsing files...")
    all_data = []
    successful_files = 0
    
    for file_path, agency in file_agency_mapping.items():
        print(f"\nProcessing {file_path.name} ({agency})")
        df = parse_sf133_tafs_detail_pandas(file_path, agency)
        if df is not None and len(df) > 0:
            all_data.append(df)
            successful_files += 1
            print(f"  Success: {len(df)} rows")
        else:
            print(f"  Failed or no data")
    
    # Combine all data
    if all_data:
        print("\n\nCombining all data...")
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Save the combined data
        output_path = Path('data/selected_agencies_sf133_structured.csv')
        combined_df.to_csv(output_path, index=False)
        
        print(f"\n=== FINAL SUMMARY ===")
        print(f"Successfully parsed: {successful_files} files")
        print(f"Total agencies: {len(agencies_found)}")
        print(f"Total rows: {len(combined_df):,}")
        print(f"Output saved to: {output_path}")
        
        # Create agency summary
        agency_summary = combined_df.groupby('Agency').size().sort_values(ascending=False)
        summary_path = Path('data/selected_agencies_summary.csv')
        agency_summary.to_csv(summary_path)
        print(f"Agency summary saved to: {summary_path}")
        
    else:
        print("\nNo data was successfully extracted.")

if __name__ == "__main__":
    main()