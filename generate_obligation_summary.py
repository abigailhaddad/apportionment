#!/usr/bin/env python3
"""
Generate obligation summary table from structured SF 133 data.
"""

import pandas as pd
from pathlib import Path

def generate_obligation_summary():
    """Create a clean obligation summary table from the structured SF 133 data."""
    
    # Read the structured data
    df = pd.read_csv('data/education_sf133_structured.csv')
    
    # Filter for lines 2490 (Unobligated Balance) and 2500 (Budget Authority)
    line_2490 = df[df['Line No'] == 2490.0].copy()
    line_2500 = df[df['Line No'] == 2500.0].copy()
    
    # Merge on TAFS (Col_4) to get matching pairs
    merged = pd.merge(
        line_2490[['Col_0', 'Col_1', 'Col_4', 'Jun (3Q)']],
        line_2500[['Col_4', 'Jun (3Q)']], 
        on='Col_4', 
        suffixes=('_2490', '_2500')
    )
    
    # Calculate summary data
    summary_data = []
    for _, row in merged.iterrows():
        try:
            unob = float(row['Jun (3Q)_2490'])
            ba = float(row['Jun (3Q)_2500'])
            
            if ba > 0:
                pct = (unob / ba * 100)
                
                summary_data.append({
                    'Account': row['Col_1'] if pd.notna(row['Col_1']) else '',
                    'TAFS': row['Col_4'],
                    'Bureau': row['Col_0'] if pd.notna(row['Col_0']) else '',
                    'Unobligated_Balance_M': round(unob / 1_000_000, 1),
                    'Budget_Authority_M': round(ba / 1_000_000, 1),
                    'Percentage_Unobligated': round(pct, 1)
                })
        except:
            continue
    
    # Create DataFrame and sort by budget authority (descending)
    summary_df = pd.DataFrame(summary_data)
    if len(summary_df) == 0:
        print("No valid data found")
        return
        
    summary_df = summary_df.sort_values('Budget_Authority_M', ascending=False)
    
    # Format the output table
    output_df = summary_df.copy()
    output_df['Account_Display'] = output_df['Account'] + '\n' + output_df['Bureau']
    output_df['Unobligated Balance (Line 2490)'] = output_df['Unobligated_Balance_M'].apply(lambda x: f'${x:,.1f}M')
    output_df['Budget Authority (Line 2500)'] = output_df['Budget_Authority_M'].apply(lambda x: f'${x:,.1f}M')
    output_df['Percentage Unobligated'] = output_df['Percentage_Unobligated'].apply(lambda x: f'{x:.1f}%')
    
    # Select final columns
    final_df = output_df[['Account_Display', 'Unobligated Balance (Line 2490)', 
                         'Budget Authority (Line 2500)', 'Percentage Unobligated']]
    final_df.columns = ['Account', 'Unobligated Balance\n(Line 2490)', 
                        'Budget Authority\n(Line 2500)', 'Percentage\nUnobligated']
    
    # Save to CSV
    output_path = Path('data/education_obligation_summary_july.csv')
    final_df.to_csv(output_path, index=False)
    print(f"Saved summary to: {output_path}")
    
    # Print the table
    print("\nDepartment of Education - Obligation Summary (June 2025)")
    print("=" * 100)
    print(final_df.to_string(index=False))
    
    # Find specific account
    loan_account = summary_df[summary_df['TAFS'].str.contains('91-0243 /25', na=False)]
    if not loan_account.empty:
        print("\n" + "=" * 100)
        print("Federal Direct Student Loan Program Account (91-0243 /25):")
        row = loan_account.iloc[0]
        print(f"  Unobligated Balance: ${row['Unobligated_Balance_M']:,.1f}M")
        print(f"  Budget Authority: ${row['Budget_Authority_M']:,.1f}M")
        print(f"  Percentage Unobligated: {row['Percentage_Unobligated']:.1f}%")
    
    # Print totals
    total_unob = summary_df['Unobligated_Balance_M'].sum()
    total_ba = summary_df['Budget_Authority_M'].sum()
    total_pct = (total_unob / total_ba * 100) if total_ba > 0 else 0
    
    print("\n" + "=" * 100)
    print(f"TOTALS: Unobligated: ${total_unob:,.1f}M | Budget Authority: ${total_ba:,.1f}M | Percentage: {total_pct:.1f}%")

if __name__ == "__main__":
    generate_obligation_summary()