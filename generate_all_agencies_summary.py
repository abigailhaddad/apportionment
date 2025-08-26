#!/usr/bin/env python3
"""
Generate obligation summary for all agencies from combined SF 133 data.
Based on generate_enhanced_summary.py but for multiple agencies.
"""

import pandas as pd
import json
from pathlib import Path

def generate_all_agencies_summary():
    """Create a summary with all agencies from the combined SF 133 data."""
    
    # Read the combined structured data
    df = pd.read_csv('data/selected_agencies_sf133_structured.csv', low_memory=False)
    
    # Convert Line No to numeric since it's stored as string
    df['Line No'] = pd.to_numeric(df['Line No'], errors='coerce')
    
    # Filter for lines we need
    # Line 2490: Unobligated Balance end of year
    # Line 2500: Budget Authority
    line_2490 = df[df['Line No'] == 2490.0].copy()
    line_2500 = df[df['Line No'] == 2500.0].copy()
    
    # Special handling for Other Independent Agencies - use Col_9 for line numbers and Col_19 for June values
    oia_2490 = df[(df['Agency'] == 'Other Independent Agencies') & (df['Col_9'] == '2490')].copy()
    oia_2500 = df[(df['Agency'] == 'Other Independent Agencies') & (df['Col_9'] == '2500')].copy()
    
    # Add OIA data if found
    if len(oia_2490) > 0 and len(oia_2500) > 0:
        line_2490 = pd.concat([line_2490[line_2490['Agency'] != 'Other Independent Agencies'], oia_2490])
        line_2500 = pd.concat([line_2500[line_2500['Agency'] != 'Other Independent Agencies'], oia_2500])
    
    # Month columns in order
    month_cols = ['Nov', 'Dec (1Q)', 'Jan', 'Feb', 'Mar (2Q)', 'Apr', 'May', 'Jun (3Q)', 'Jul', 'Aug', 'Sep (4Q)']
    
    # Find which columns have the monthly data
    actual_month_cols = []
    for col in df.columns:
        for month in month_cols:
            if month in col:
                actual_month_cols.append(col)
                break
    
    # Use the June (3Q) column for current values
    june_col = None
    for col in actual_month_cols:
        if 'Jun' in col or '3Q' in col:
            june_col = col
            break
    
    if not june_col:
        print(f"Could not find June column. Available columns: {list(df.columns)}")
        return
    
    # Merge the two lines on TAFS (Col_4 typically contains TAFS)
    # Also keep Agency, Bureau (Col_0), and Account (Col_1)
    
    # For Other Independent Agencies, use Col_19 instead of June column
    oia_mask_2490 = line_2490['Agency'] == 'Other Independent Agencies'
    oia_mask_2500 = line_2500['Agency'] == 'Other Independent Agencies'
    
    # Regular agencies - use June column
    regular_2490 = line_2490[~oia_mask_2490][['Agency', 'Col_0', 'Col_1', 'Col_4', june_col]]
    regular_2500 = line_2500[~oia_mask_2500][['Col_4', june_col]]
    
    # OIA - use Col_19 as the value column
    oia_2490 = line_2490[oia_mask_2490][['Agency', 'Col_0', 'Col_1', 'Col_4', 'Col_19']].copy()
    oia_2500 = line_2500[oia_mask_2500][['Col_4', 'Col_19']].copy()
    
    # Rename Col_19 to match June column name for consistency
    if len(oia_2490) > 0:
        oia_2490 = oia_2490.rename(columns={'Col_19': june_col})
        oia_2500 = oia_2500.rename(columns={'Col_19': june_col})
    
    # Merge regular agencies
    merged_regular = pd.merge(
        regular_2490,
        regular_2500, 
        on='Col_4', 
        suffixes=('_2490', '_2500')
    )
    
    # Merge OIA separately if it exists
    if len(oia_2490) > 0 and len(oia_2500) > 0:
        merged_oia = pd.merge(
            oia_2490,
            oia_2500,
            on='Col_4',
            suffixes=('_2490', '_2500')
        )
        # Combine both merges
        merged = pd.concat([merged_regular, merged_oia], ignore_index=True)
    else:
        merged = merged_regular
    
    # Create summary data
    summary_data = []
    for _, row in merged.iterrows():
        try:
            unob = float(row[f'{june_col}_2490'])
            ba = float(row[f'{june_col}_2500'])
            
            # Convert to millions - all values are in dollars
            unob = unob / 1_000_000
            ba = ba / 1_000_000
            
            if ba > 0:
                pct = (unob / ba * 100)
                
                # Parse TAFS to extract components
                tafs = row['Col_4']
                tafs_parts = tafs.split(' - ')[0] if ' - ' in tafs else tafs
                
                # Extract account number
                account_num = ''
                period_of_perf = ''
                expiration_year = ''
                
                # Parse the TAFS code (same logic as Education parser)
                if tafs_parts.startswith('14-91-'):
                    parts = tafs_parts.split(' ', 1)
                    code_part = parts[0]
                    year_part = parts[1] if len(parts) > 1 else ''
                    
                    code_pieces = code_part.split('-')
                    if len(code_pieces) >= 3:
                        account_num = f"{code_pieces[0]}-{code_pieces[1]}-{code_pieces[2]}"
                else:
                    parts = tafs_parts.split(' ', 1)
                    code_part = parts[0]
                    year_part = parts[1] if len(parts) > 1 else ''
                    
                    code_pieces = code_part.split('-')
                    if len(code_pieces) >= 2:
                        account_num = f"{code_pieces[0]}-{code_pieces[1]}"
                
                # Parse year/period part
                if year_part:
                    year_part = year_part.strip()
                    if '/' in year_part:
                        if year_part.startswith('/'):
                            year_val = year_part[1:]
                            if year_val == 'X':
                                period_of_perf = 'No Year'
                                expiration_year = 'No Year'
                            elif year_val.isdigit():
                                period_of_perf = f"FY20{year_val}"
                                expiration_year = f"20{year_val}"
                        else:
                            period_parts = year_part.split('/')
                            if len(period_parts) == 2:
                                start_year = period_parts[0]
                                end_year = period_parts[1]
                                
                                if start_year.isdigit() and end_year.isdigit():
                                    start_full = f"20{start_year}" if len(start_year) == 2 else start_year
                                    end_full = f"20{end_year}" if len(end_year) == 2 else end_year
                                    
                                    period_of_perf = f"FY{start_full}-FY{end_full}"
                                    expiration_year = end_full
                                elif end_year == 'X':
                                    start_full = f"20{start_year}" if len(start_year) == 2 else start_year
                                    period_of_perf = f"FY{start_full}-No Year"
                                    expiration_year = 'No Year'
                
                # Extract account name from TAFS if Col_1 is empty
                account_name = row['Col_1'] if pd.notna(row['Col_1']) else ''
                if not account_name and ' - ' in tafs:
                    # Extract the descriptive part after the dash
                    account_name = tafs.split(' - ', 1)[1]
                
                summary_data.append({
                    'Agency': row['Agency'],
                    'Bureau': row['Col_0'] if pd.notna(row['Col_0']) else '',
                    'Account': account_name,
                    'Account_Number': account_num,
                    'Period_of_Performance': period_of_perf,
                    'Expiration_Year': expiration_year,
                    'TAFS': row['Col_4'],
                    'Unobligated_Balance_M': round(unob, 1),
                    'Budget_Authority_M': round(ba, 1),
                    'Percentage_Unobligated': round(pct, 1)
                })
        except:
            continue
    
    # Create DataFrame and sort
    summary_df = pd.DataFrame(summary_data)
    if len(summary_df) == 0:
        print("No valid data found")
        return
        
    summary_df = summary_df.sort_values(['Agency', 'Budget_Authority_M'], ascending=[True, False])
    
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
    
    # Save to CSV
    output_path = Path('data/all_agencies_obligation_summary.csv')
    final_df.to_csv(output_path, index=False)
    print(f"Saved summary to: {output_path}")
    
    # Also save raw data for JavaScript (without time series for now)
    raw_output = summary_df.copy()
    raw_output['BA_TimeSeries'] = '[]'
    raw_output['Unob_TimeSeries'] = '[]'
    
    # Add formatted columns for consistency
    raw_output['Unobligated Balance (Line 2490)'] = raw_output['Unobligated_Balance_M'].apply(lambda x: f'${x:,.1f}M')
    raw_output['Budget Authority (Line 2500)'] = raw_output['Budget_Authority_M'].apply(lambda x: f'${x:,.1f}M')
    raw_output['Percentage Unobligated'] = raw_output['Percentage_Unobligated'].apply(lambda x: f'{x:.1f}%')
    
    raw_output.to_json('data/all_agencies_summary.json', orient='records')
    print("Saved JSON version for JavaScript")
    
    # Print summary by agency
    print(f"\nTotal accounts: {len(summary_df)}")
    print("\nSummary by Agency:")
    agency_summary = summary_df.groupby('Agency').agg({
        'Unobligated_Balance_M': 'sum',
        'Budget_Authority_M': 'sum',
        'TAFS': 'count'
    }).round(1)
    agency_summary['Percentage'] = (agency_summary['Unobligated_Balance_M'] / agency_summary['Budget_Authority_M'] * 100).round(1)
    agency_summary = agency_summary.rename(columns={'TAFS': 'Accounts'})
    print(agency_summary.sort_values('Budget_Authority_M', ascending=False))

if __name__ == "__main__":
    generate_all_agencies_summary()