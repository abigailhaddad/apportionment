#!/usr/bin/env python3
"""
Parse Department of Education SF 133 file to extract and structure the TAFS detail tab.
"""

import pandas as pd
import sys
from pathlib import Path
import openpyxl

def parse_sf133_file(file_path):
    """Parse the Education SF 133 file TAFS detail tab into a clean dataframe."""
    
    # Use openpyxl to handle merged cells properly
    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb['TAFS detail']
    
    # Convert to dataframe, unmerging cells
    data = []
    for row in ws.iter_rows():
        data.append([cell.value for cell in row])
    
    df = pd.DataFrame(data)
    
    print(f"Raw data shape: {df.shape}")
    
    # Row 9 (index 8) has our headers
    headers = df.iloc[8].tolist()
    
    # Replace None with generic column names
    headers = [str(h) if h is not None else f'Col_{i}' for i, h in enumerate(headers)]
    
    print(f"Headers from row 9: {headers}")
    
    # Process the data starting after the header row
    clean_rows = []
    
    # Variables to forward-fill
    current_bureau = None
    current_account_code = None
    current_account_name = None
    current_tafs = None
    
    for idx in range(9, len(df)):  # Start from row 10 (index 9)
        row = df.iloc[idx]
        
        # Skip completely empty rows
        if row.isna().all():
            continue
        
        # Update bureau if found (column 0)
        if pd.notna(row[0]):
            val = str(row[0]).strip()
            if 'Office of' in val or 'Department' in val:
                current_bureau = val
        
        # Update account code if found (column 1)
        if pd.notna(row[1]):
            current_account_code = str(row[1]).strip()
        
        # Update account name if found (column 2)
        if pd.notna(row[2]):
            current_account_name = str(row[2]).strip()
        
        # Update TAFS if found (column 4)
        if pd.notna(row[4]):
            val = str(row[4]).strip()
            if '-' in val and '/' in val:  # Looks like a TAFS
                current_tafs = val
        
        # Create a row with all columns
        clean_row = {}
        
        # Add all columns with proper headers
        for col_idx in range(len(headers)):
            col_name = headers[col_idx]
            
            # For certain columns, use forward-filled values
            if col_idx == 0:  # Bureau column
                clean_row[col_name] = current_bureau
            elif col_idx == 1:  # Account Code
                clean_row[col_name] = current_account_code
            elif col_idx == 2:  # Account Name
                clean_row[col_name] = current_account_name
            elif col_idx == 4:  # TAFS
                clean_row[col_name] = current_tafs
            else:
                # For all other columns, use the actual value
                clean_row[col_name] = row[col_idx]
        
        clean_rows.append(clean_row)
    
    # Convert to DataFrame
    result_df = pd.DataFrame(clean_rows)
    
    # Remove rows where all numeric/data columns are empty
    # Keep rows that have at least some data
    numeric_cols = ['Nov', 'Dec (1Q)', 'Jan', 'Feb', 'Mar (2Q)', 'Apr', 'May', 'Jun (3Q)', 'Jul', 'Aug', 'Sep (4Q)']
    cols_to_check = [col for col in numeric_cols if col in result_df.columns]
    
    if cols_to_check:
        result_df = result_df.dropna(subset=cols_to_check, how='all')
    
    print(f"Cleaned data shape: {result_df.shape}")
    
    # Save the full structured data
    output_path = Path(file_path).parent / 'education_sf133_structured.csv'
    result_df.to_csv(output_path, index=False)
    print(f"\nSaved structured TAFS detail to: {output_path}")
    
    # Show a sample of the data
    print("\nFirst 10 rows of structured data:")
    print(result_df.head(10).to_string())
    
    print(f"\nColumn names: {list(result_df.columns)}")

if __name__ == "__main__":
    file_path = Path("data/2580778249.xlsx")
    
    if not file_path.exists():
        print(f"Error: File not found at {file_path}")
        sys.exit(1)
    
    parse_sf133_file(file_path)