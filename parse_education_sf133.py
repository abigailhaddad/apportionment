#!/usr/bin/env python3
"""
Parse Department of Education SF 133 file to extract obligation data.
"""

import pandas as pd
import sys
from pathlib import Path

def parse_sf133_file(file_path):
    """Parse the Education SF 133 file to extract obligation data."""
    
    # Read the TAFS detail sheet
    df = pd.read_excel(file_path, sheet_name='TAFS detail', header=None)
    
    results = []
    current_bureau = None
    current_account = None
    current_tafs = None
    
    # Process each row
    for idx in range(df.shape[0]):
        row = df.iloc[idx]
        
        # Check for bureau name (usually in column 0)
        if pd.notna(row[0]) and 'Office of' in str(row[0]):
            current_bureau = str(row[0]).strip()
            continue
            
        # Check for account info (column 1 and 2)
        if pd.notna(row[1]) and pd.notna(row[2]) and '-' in str(row[1]):
            current_account = f"{row[1]} - {row[2]}"
            continue
            
        # Check for TAFS (column 4)
        if pd.notna(row[4]) and '-' in str(row[4]) and len(str(row[4])) > 10:
            current_tafs = str(row[4]).strip()
            continue
        
        # Look for line items
        line_no = str(row[7]) if pd.notna(row[7]) else ''
        
        if line_no == '2490':  # Unobligated balance
            # Value is usually in column 10 or nearby
            for col in range(8, min(15, df.shape[1])):
                if pd.notna(row[col]) and isinstance(row[col], (int, float)) and row[col] != 0:
                    if current_tafs and 'unobligated' not in results[-1] if results else True:
                        if not results or results[-1].get('tafs') != current_tafs:
                            results.append({
                                'bureau': current_bureau,
                                'account': current_account,
                                'tafs': current_tafs,
                                'unobligated': row[col]
                            })
                        else:
                            results[-1]['unobligated'] = row[col]
                    break
                    
        elif line_no == '2500':  # Budget authority
            # Value is usually in column 10 or nearby
            for col in range(8, min(15, df.shape[1])):
                if pd.notna(row[col]) and isinstance(row[col], (int, float)) and row[col] != 0:
                    if current_tafs:
                        if not results or results[-1].get('tafs') != current_tafs:
                            results.append({
                                'bureau': current_bureau,
                                'account': current_account,
                                'tafs': current_tafs,
                                'budget_authority': row[col]
                            })
                        else:
                            results[-1]['budget_authority'] = row[col]
                    break
    
    # Create summary DataFrame
    summary_data = []
    for item in results:
        if 'unobligated' in item and 'budget_authority' in item:
            pct_unobligated = (item['unobligated'] / item['budget_authority'] * 100) if item['budget_authority'] > 0 else 0
            summary_data.append({
                'Bureau': item['bureau'],
                'Account': item['account'],
                'TAFS': item['tafs'],
                'Unobligated Balance (2490)': item['unobligated'],
                'Budget Authority (2500)': item['budget_authority'],
                'Percent Unobligated': round(pct_unobligated, 2)
            })
    
    summary_df = pd.DataFrame(summary_data)
    
    if len(summary_df) > 0:
        print("\nDepartment of Education SF 133 Obligation Summary")
        print("=" * 80)
        print(summary_df.to_string(index=False))
        
        # Save to CSV
        output_path = Path(file_path).parent / 'education_obligation_summary.csv'
        summary_df.to_csv(output_path, index=False)
        print(f"\nSaved to: {output_path}")
        
        # Print totals
        total_unobligated = summary_df['Unobligated Balance (2490)'].sum()
        total_budget_auth = summary_df['Budget Authority (2500)'].sum()
        total_obligated = total_budget_auth - total_unobligated
        total_pct = (total_unobligated / total_budget_auth * 100) if total_budget_auth > 0 else 0
        
        print(f"\nTotals:")
        print(f"Total Budget Authority: ${total_budget_auth:,.0f}")
        print(f"Total Obligated: ${total_obligated:,.0f}")
        print(f"Total Unobligated: ${total_unobligated:,.0f}")
        print(f"Overall Percent Unobligated: {total_pct:.2f}%")
    else:
        print("No complete account data found (need both line 2490 and 2500)")

if __name__ == "__main__":
    file_path = Path("data/2580778249.xlsx")
    
    if not file_path.exists():
        print(f"Error: File not found at {file_path}")
        sys.exit(1)
    
    parse_sf133_file(file_path)