#!/usr/bin/env python3
"""
Generate enhanced obligation summary with monthly time series data.
"""

import pandas as pd
import json
from pathlib import Path

def generate_enhanced_summary():
    """Create an enhanced summary with monthly time series for sparklines."""
    
    # Read the structured data
    df = pd.read_csv('data/education_sf133_structured.csv')
    
    # Filter for lines we need
    # Line 1900: Budget authority total
    # Line 2490: Unobligated Balance end of year
    line_1900 = df[df['Line No'] == 1900.0].copy()
    line_2490 = df[df['Line No'] == 2490.0].copy()
    line_2500 = df[df['Line No'] == 2500.0].copy()  # Keep for percentage calculation
    
    # Month columns in order
    month_cols = ['Nov', 'Dec (1Q)', 'Jan', 'Feb', 'Mar (2Q)', 'Apr', 'May', 'Jun (3Q)', 'Jul', 'Aug', 'Sep (4Q)']
    
    # First create the base summary like before
    merged = pd.merge(
        line_2490[['Col_0', 'Col_1', 'Col_4', 'Jun (3Q)']],
        line_2500[['Col_4', 'Jun (3Q)']], 
        on='Col_4', 
        suffixes=('_2490', '_2500')
    )
    
    # Now add time series data
    time_series_data = {}
    
    # Get budget authority time series (line 1900)
    for _, row in line_1900.iterrows():
        tafs = row['Col_4']
        if pd.notna(tafs):
            ba_series = []
            for month in month_cols:
                val = row.get(month, 0)
                if pd.notna(val):
                    try:
                        ba_series.append(float(val) / 1_000_000)  # Convert to millions
                    except:
                        ba_series.append(0)
                else:
                    ba_series.append(0)
            
            if tafs not in time_series_data:
                time_series_data[tafs] = {}
            time_series_data[tafs]['budget_authority'] = ba_series
    
    # Get unobligated balance time series (line 2490)
    for _, row in line_2490.iterrows():
        tafs = row['Col_4']
        if pd.notna(tafs):
            unob_series = []
            for month in month_cols:
                val = row.get(month, 0)
                if pd.notna(val):
                    try:
                        unob_series.append(float(val) / 1_000_000)  # Convert to millions
                    except:
                        unob_series.append(0)
                else:
                    unob_series.append(0)
            
            if tafs not in time_series_data:
                time_series_data[tafs] = {}
            time_series_data[tafs]['unobligated'] = unob_series
    
    # Create enhanced summary data
    summary_data = []
    for _, row in merged.iterrows():
        try:
            unob = float(row['Jun (3Q)_2490'])
            ba = float(row['Jun (3Q)_2500'])
            
            if ba > 0:
                pct = (unob / ba * 100)
                
                # Parse TAFS to extract components (reuse existing logic)
                tafs = row['Col_4']
                tafs_parts = tafs.split(' - ')[0] if ' - ' in tafs else tafs
                
                # Extract account number
                account_num = ''
                period_of_perf = ''
                expiration_year = ''
                
                # Parse the TAFS code
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
                
                # Get time series for this TAFS
                ts_data = time_series_data.get(tafs, {})
                
                summary_data.append({
                    'Department': 'Department of Education',
                    'Bureau': row['Col_0'] if pd.notna(row['Col_0']) else '',
                    'Account': row['Col_1'] if pd.notna(row['Col_1']) else '',
                    'Account_Number': account_num,
                    'Period_of_Performance': period_of_perf,
                    'Expiration_Year': expiration_year,
                    'TAFS': row['Col_4'],
                    'Unobligated_Balance_M': round(unob / 1_000_000, 1),
                    'Budget_Authority_M': round(ba / 1_000_000, 1),
                    'Percentage_Unobligated': round(pct, 1),
                    'BA_TimeSeries': json.dumps(ts_data.get('budget_authority', [])),
                    'Unob_TimeSeries': json.dumps(ts_data.get('unobligated', []))
                })
        except:
            continue
    
    # Create DataFrame and sort
    summary_df = pd.DataFrame(summary_data)
    if len(summary_df) == 0:
        print("No valid data found")
        return
        
    summary_df = summary_df.sort_values('Budget_Authority_M', ascending=False)
    
    # Format for display
    output_df = summary_df.copy()
    output_df['Unobligated Balance (Line 2490)'] = output_df['Unobligated_Balance_M'].apply(lambda x: f'${x:,.1f}M')
    output_df['Budget Authority (Line 2500)'] = output_df['Budget_Authority_M'].apply(lambda x: f'${x:,.1f}M')
    output_df['Percentage Unobligated'] = output_df['Percentage_Unobligated'].apply(lambda x: f'{x:.1f}%')
    
    # Select columns for output
    final_df = output_df[['Department', 'Bureau', 'Account', 'Account_Number', 
                         'Period_of_Performance', 'Expiration_Year', 'TAFS',
                         'Unobligated Balance (Line 2490)', 
                         'Budget Authority (Line 2500)', 'Percentage Unobligated',
                         'BA_TimeSeries', 'Unob_TimeSeries']]
    
    # Save to CSV
    output_path = Path('data/education_obligation_summary_enhanced.csv')
    final_df.to_csv(output_path, index=False)
    print(f"Saved enhanced summary to: {output_path}")
    
    # Also save raw data for JavaScript
    summary_df.to_json('data/education_summary_enhanced.json', orient='records')
    print("Saved JSON version for JavaScript")
    
    # Print summary
    print(f"\nTotal accounts: {len(summary_df)}")
    print(f"Accounts with time series data: {len([1 for _, row in summary_df.iterrows() if row['BA_TimeSeries'] != '[]'])}")

if __name__ == "__main__":
    generate_enhanced_summary()