#!/usr/bin/env python3
"""
Process Other Independent Agencies data correctly using the fixed forward-filled data.
"""

import pandas as pd
import numpy as np
from pathlib import Path

def process_oia_data():
    """Process OIA data with correct TAFS codes and structure."""
    
    # Read the fixed data with proper forward fills
    df = pd.read_csv('data/selected_agencies_sf133_structured_fixed.csv', low_memory=False)
    oia = df[df['Agency'] == 'Other Independent Agencies'].copy()
    
    print(f"Processing {len(oia)} OIA rows...")
    
    # Get lines 2490 and 2500
    line_2490 = oia[oia['Col_9'] == '2490'].copy()
    line_2500 = oia[oia['Col_9'] == '2500'].copy()
    
    print(f"Line 2490: {len(line_2490)} rows")
    print(f"Line 2500: {len(line_2500)} rows")
    
    # Merge on Col_6 (full TAFS)
    merged = pd.merge(
        line_2490[['Agency', 'Col_0', 'Col_1', 'Col_2', 'Col_4', 'Col_6', 'Col_19']],
        line_2500[['Col_6', 'Col_19']], 
        on='Col_6', 
        suffixes=('_2490', '_2500')
    )
    
    print(f"Merged: {len(merged)} rows")
    
    # Create summary data
    summary_data = []
    for _, row in merged.iterrows():
        try:
            # Values are in dollars, convert to millions
            unob = float(row['Col_19_2490']) / 1_000_000
            ba = float(row['Col_19_2500']) / 1_000_000
            
            if ba > 0:
                pct = (unob / ba * 100)
                
                # Parse TAFS and account info
                tafs_full = row['Col_6']  # e.g., "95-2300 /25 - Salaries and Expenses"
                
                # Extract account name from TAFS
                account_name = ''
                if ' - ' in str(tafs_full):
                    account_name = str(tafs_full).split(' - ', 1)[1]
                
                # Extract account number from Col_2 or TAFS
                account_num = ''
                if pd.notna(row['Col_2']):
                    # e.g., "306-00-2300   Salaries and Expenses"
                    parts = str(row['Col_2']).split()
                    if parts and '-' in parts[0]:
                        account_num = parts[0]
                elif pd.notna(tafs_full):
                    # Extract from TAFS e.g., "95-2300 /25"
                    tafs_parts = str(tafs_full).split(' - ')[0] if ' - ' in str(tafs_full) else str(tafs_full)
                    tafs_code = tafs_parts.split('/')[0].strip() if '/' in tafs_parts else tafs_parts
                    account_num = tafs_code
                
                # Add year info to account name
                year = row['Col_4']
                if pd.notna(tafs_full) and '/' in str(tafs_full):
                    year_part = str(tafs_full).split('/')[1].split()[0] if '/' in str(tafs_full) else ''
                    if year_part and account_name:
                        account_name = f"{account_name} ({account_num} /{year_part})"
                
                # Parse period and expiration year from TAFS
                # TAFS format examples:
                # "48-5721 /25 - 400 Years..."  -> single year FY2025
                # "95-2300 24/25 - Salaries..." -> multi-year FY2024-FY2025
                # "43-8050 /X - Gifts..."        -> No Year
                period_of_perf = ''
                expiration_year = ''
                
                if pd.notna(tafs_full):
                    # Split to get the code part before " - "
                    tafs_code = str(tafs_full).split(' - ')[0] if ' - ' in str(tafs_full) else str(tafs_full)
                    
                    # Look for year info after space (e.g., "95-2300 24/25" or "48-5721 /25")
                    parts = tafs_code.strip().split()
                    if len(parts) >= 2:
                        year_part = parts[-1]  # Last part should have year info
                        
                        # Handle different formats
                        if year_part == '/X':
                            period_of_perf = 'No Year'
                            expiration_year = 'No Year'
                        elif '/' in year_part:
                            # Could be "/25" or "24/25"
                            if year_part.startswith('/'):
                                # Single year like "/25"
                                yr = year_part[1:]
                                if yr.isdigit():
                                    period_of_perf = f"FY20{yr}"
                                    expiration_year = f"20{yr}"
                            else:
                                # Multi-year like "24/25"
                                years = year_part.split('/')
                                if len(years) == 2 and years[0].isdigit() and years[1].isdigit():
                                    period_of_perf = f"FY20{years[0]}-FY20{years[1]}"
                                    expiration_year = f"20{years[1]}"
                
                summary_data.append({
                    'Agency': row['Agency'],
                    'Bureau': row['Col_0'] if pd.notna(row['Col_0']) else '',
                    'Account': account_name,
                    'Account_Number': account_num,
                    'Period_of_Performance': period_of_perf,
                    'Expiration_Year': expiration_year,
                    'TAFS': tafs_full,
                    'Unobligated_Balance_M': round(unob, 1),
                    'Budget_Authority_M': round(ba, 1),
                    'Percentage_Unobligated': round(pct, 1)
                })
        except Exception as e:
            continue
    
    # Create DataFrame and sort
    summary_df = pd.DataFrame(summary_data)
    if len(summary_df) == 0:
        print("No valid OIA data found")
        return
    
    # Remove duplicates based on TAFS
    summary_df = summary_df.drop_duplicates(subset=['TAFS'])
    
    summary_df = summary_df.sort_values(['Bureau', 'Budget_Authority_M'], ascending=[True, False])
    
    # Format for display
    output_df = summary_df.copy()
    output_df['Unobligated Balance (Line 2490)'] = output_df['Unobligated_Balance_M'].apply(lambda x: f'${x:,.1f}M')
    output_df['Budget Authority (Line 2500)'] = output_df['Budget_Authority_M'].apply(lambda x: f'${x:,.1f}M')
    output_df['Percentage Unobligated'] = output_df['Percentage_Unobligated'].apply(lambda x: f'{x:.1f}%')
    
    # Select columns for output
    final_df = output_df[['Agency', 'Bureau', 'Account', 'Account_Number', 
                         'Period_of_Performance', 'Expiration_Year', 'TAFS',
                         'Unobligated Balance (Line 2490)', 
                         'Budget Authority (Line 2500)', 'Percentage Unobligated']]
    
    # Save to separate file
    output_path = Path('data/oia_obligation_summary.csv')
    final_df.to_csv(output_path, index=False)
    print(f"Saved OIA summary to: {output_path}")
    
    # Also save raw data for merging
    summary_df.to_csv('data/oia_summary_raw.csv', index=False)
    
    # Print summary
    print(f"\nTotal OIA accounts: {len(summary_df)}")
    print(f"Total Budget Authority: ${summary_df['Budget_Authority_M'].sum():.1f}M")
    print(f"Total Unobligated: ${summary_df['Unobligated_Balance_M'].sum():.1f}M")
    
    # Show ACHP specifically
    achp = summary_df[summary_df['Bureau'].str.contains('Advisory Council', na=False)]
    print(f"\nAdvisory Council on Historic Preservation:")
    print(f"  Accounts: {len(achp)}")
    if len(achp) > 0:
        print(f"  Total Budget Authority: ${achp['Budget_Authority_M'].sum():.1f}M")
        print(f"  Total Unobligated: ${achp['Unobligated_Balance_M'].sum():.1f}M")
        print(f"  Overall %: {(achp['Unobligated_Balance_M'].sum() / achp['Budget_Authority_M'].sum() * 100):.1f}%")
        
        # Show individual accounts
        print("\n  Individual accounts:")
        for _, acc in achp.iterrows():
            print(f"    {acc['Account']}: ${acc['Unobligated_Balance_M']}M / ${acc['Budget_Authority_M']}M = {acc['Percentage_Unobligated']}%")

if __name__ == "__main__":
    process_oia_data()