#!/usr/bin/env python3
"""
Merge the correctly processed OIA data into the main all_agencies summary.
"""

import pandas as pd
from pathlib import Path

def merge_oia_data():
    """Merge OIA data into the main summary."""
    
    # Read the main summary (excluding OIA)
    main_df = pd.read_csv('data/all_agencies_obligation_summary.csv')
    
    # Remove any existing OIA data
    main_df = main_df[main_df['Agency'] != 'Other Independent Agencies']
    print(f"Main summary without OIA: {len(main_df)} rows")
    
    # Read the correct OIA data
    oia_df = pd.read_csv('data/oia_obligation_summary.csv')
    print(f"OIA data: {len(oia_df)} rows")
    
    # Merge the dataframes
    combined_df = pd.concat([main_df, oia_df], ignore_index=True)
    
    # Sort by Agency
    combined_df = combined_df.sort_values(['Agency'], ascending=[True])
    
    # Save the combined summary
    combined_df.to_csv('data/all_agencies_obligation_summary.csv', index=False)
    print(f"\nSaved combined summary: {len(combined_df)} total rows")
    
    # Also update the JSON version
    # Read the raw OIA data
    oia_raw = pd.read_csv('data/oia_summary_raw.csv')
    
    # Read existing JSON data
    import json
    with open('data/all_agencies_summary.json', 'r') as f:
        all_data = json.loads(f.read())
    
    # Remove OIA entries
    all_data = [d for d in all_data if d['Agency'] != 'Other Independent Agencies']
    
    # Add OIA entries with time series placeholders
    for _, row in oia_raw.iterrows():
        oia_entry = row.to_dict()
        oia_entry['BA_TimeSeries'] = '[]'
        oia_entry['Unob_TimeSeries'] = '[]'
        # Add formatted columns
        oia_entry['Unobligated Balance (Line 2490)'] = f"${oia_entry['Unobligated_Balance_M']:,.1f}M"
        oia_entry['Budget Authority (Line 2500)'] = f"${oia_entry['Budget_Authority_M']:,.1f}M"
        oia_entry['Percentage Unobligated'] = f"{oia_entry['Percentage_Unobligated']:.1f}%"
        all_data.append(oia_entry)
    
    # Save updated JSON
    with open('data/all_agencies_summary.json', 'w') as f:
        json.dump(all_data, f)
    print("Updated JSON summary")
    
    # Print summary
    print(f"\nOther Independent Agencies in final summary: {len(combined_df[combined_df['Agency'] == 'Other Independent Agencies'])} accounts")

if __name__ == "__main__":
    # First need to extract Budget_Authority_M from the formatted columns
    oia_df = pd.read_csv('data/oia_obligation_summary.csv')
    
    # Extract numeric values from formatted strings
    oia_df['Budget_Authority_M'] = oia_df['Budget Authority (Line 2500)'].str.replace('[\$,M]', '', regex=True).astype(float)
    oia_df['Unobligated_Balance_M'] = oia_df['Unobligated Balance (Line 2490)'].str.replace('[\$,M]', '', regex=True).astype(float)
    oia_df['Percentage_Unobligated'] = oia_df['Percentage Unobligated'].str.replace('%', '').astype(float)
    
    # Check if main summary has the numeric columns
    main_df = pd.read_csv('data/all_agencies_obligation_summary.csv')
    if 'Budget_Authority_M' not in main_df.columns:
        main_df['Budget_Authority_M'] = main_df['Budget Authority (Line 2500)'].str.replace('[\$,M]', '', regex=True).astype(float)
        main_df['Unobligated_Balance_M'] = main_df['Unobligated Balance (Line 2490)'].str.replace('[\$,M]', '', regex=True).astype(float) 
        main_df['Percentage_Unobligated'] = main_df['Percentage Unobligated'].str.replace('%', '').astype(float)
    
    merge_oia_data()