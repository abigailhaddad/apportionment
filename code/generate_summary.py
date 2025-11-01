#!/usr/bin/env python3
"""
Generate obligation summary for all agencies from the master SF133 table.
Creates the final summary CSV and JSON files needed for the web application.
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path

def parse_tafs_components(tafs, agency_name):
    """Extract account number, period of performance, and expiration year from TAFS."""
    # Initialize defaults
    account_num = ''
    period_of_perf = ''
    expiration_year = ''
    
    # Split TAFS to get the code part (before any description)
    tafs_parts = tafs.split(' - ')[0] if ' - ' in tafs else tafs
    
    # Special handling for OIA TAFS format
    if agency_name == 'Other Independent Agencies':
        # OIA format examples:
        # "48-5721 /25 - 400 Years..." -> account: 48-5721, year: 2025
        # "95-2300 24/25 - Salaries..." -> account: 95-2300, years: 2024-2025
        parts = tafs_parts.strip().split()
        if parts:
            account_num = parts[0]  # First part is account number
            
            # Look for year info
            if len(parts) >= 2:
                year_part = parts[1]
                if year_part == '/X':
                    period_of_perf = 'No Year'
                    expiration_year = 'No Year'
                elif '/' in year_part:
                    if year_part.startswith('/'):
                        # Single year like "/25"
                        yr = year_part[1:]
                        if yr.isdigit():
                            period_of_perf = f"FY20{yr}"
                            expiration_year = f"20{yr}"
                    else:
                        # Multi-year like "24/25"
                        yrs = year_part.split('/')
                        if len(yrs) == 2 and yrs[0].isdigit() and yrs[1].isdigit():
                            start = f"20{yrs[0]}" if len(yrs[0]) == 2 else yrs[0]
                            end = f"20{yrs[1]}" if len(yrs[1]) == 2 else yrs[1]
                            period_of_perf = f"FY{start}-FY{end}"
                            expiration_year = end
    else:
        # Standard agency format
        # Parse the TAFS code
        parts = tafs_parts.split(' ', 1)
        code_part = parts[0]
        year_part = parts[1] if len(parts) > 1 else ''
        
        # Extract account number
        code_pieces = code_part.split('-')
        if len(code_pieces) >= 2:
            account_num = '-'.join(code_pieces[:3]) if len(code_pieces) >= 3 else '-'.join(code_pieces[:2])
        
        # Parse year/period part
        if year_part:
            year_part = year_part.strip()
            if '/' in year_part:
                if year_part.startswith('/'):
                    # Format: /25 or /X
                    year_val = year_part[1:]
                    if year_val == 'X':
                        period_of_perf = 'No Year'
                        expiration_year = 'No Year'
                    elif year_val.isdigit():
                        period_of_perf = f"FY20{year_val}"
                        expiration_year = f"20{year_val}"
                else:
                    # Format: 21/25 or 25/26
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
    
    return account_num, period_of_perf, expiration_year

def generate_obligation_summary(master_table_path, fiscal_year=None, month=None):
    """Create obligation summary from the master SF133 table.
    
    Args:
        master_table_path: Path to the master CSV file
        fiscal_year: Fiscal year for naming output files (e.g., 2024)
        month: Month of the data (e.g., 'September', 'August')
    """
    
    # Read the master table
    print("Reading master table...")
    df = pd.read_csv(master_table_path, low_memory=False)
    print(f"  Total rows: {len(df):,}")
    print(f"  Agencies: {df['Agency'].nunique()}")
    
    # Convert Line No to numeric for standard agencies
    if 'Line No' in df.columns:
        df['Line No'] = pd.to_numeric(df['Line No'], errors='coerce')
    
    # Process each agency type
    summary_data = []
    
    # Process standard agencies (non-OIA)
    standard_agencies = df[df['Agency'] != 'Other Independent Agencies'].copy()
    if len(standard_agencies) > 0:
        # Filter for lines 2490 and 2500
        line_2490 = standard_agencies[standard_agencies['Line No'] == 2490.0].copy()
        line_2500 = standard_agencies[standard_agencies['Line No'] == 2500.0].copy()
        
        # Find the latest month column (looking for Aug first, then Jul, etc.)
        month_col = None
        month_order = ['Aug', 'Jul', 'Jun', 'May', 'Apr', 'Mar', 'Feb', 'Jan', 'Dec', 'Nov', 'Oct', 'Sep']
        
        for month in month_order:
            for col in standard_agencies.columns:
                if month in col and col != f'{month} AMT':  # Avoid OIA columns
                    month_col = col
                    break
            if month_col:
                break
        
        if month_col:
            print(f"  Using month column: {month_col}")
            # Merge on TAFS (Col_4)
            merged = pd.merge(
                line_2490[['Agency', 'Col_0', 'Col_1', 'Col_4', month_col]],
                line_2500[['Agency', 'Col_4', month_col]], 
                on=['Agency', 'Col_4'], 
                suffixes=('_2490', '_2500')
            )
            
            print(f"  Standard agencies - Line 2490: {len(line_2490)} accounts")
            print(f"  Standard agencies - Line 2500: {len(line_2500)} accounts")
            print(f"  After merge: {len(merged)} accounts")
            
            # Process each row
            for _, row in merged.iterrows():
                try:
                    unob = float(row[f'{month_col}_2490']) / 1_000_000
                    ba = float(row[f'{month_col}_2500']) / 1_000_000
                    
                    if ba == 0:
                        pct = 0.0 if unob == 0 else 100.0
                    else:
                        pct = (unob / ba * 100)
                    
                    # Parse TAFS components
                    account_num, period_of_perf, expiration_year = parse_tafs_components(
                        row['Col_4'], row['Agency']
                    )
                    
                    # Extract account name from TAFS (preferred) or Col_1 (fallback)
                    account_name = ''
                    if ' - ' in str(row['Col_4']):
                        account_name = str(row['Col_4']).split(' - ', 1)[1]
                    if not account_name:
                        account_name = row['Col_1'] if pd.notna(row['Col_1']) else ''
                    
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
                except Exception as e:
                    print(f"    ERROR processing {row['Agency']} - {row['Col_4']}: {e}")
                    continue
    
    # Process Other Independent Agencies separately
    oia = df[df['Agency'] == 'Other Independent Agencies'].copy()
    if len(oia) > 0:
        print(f"\nProcessing Other Independent Agencies ({len(oia)} rows)...")
        
        # OIA uses Col_9 for line numbers (stored as strings like '2490.0')
        # Convert Col_9 to numeric for comparison
        oia['Col_9_numeric'] = pd.to_numeric(oia['Col_9'], errors='coerce')
        
        # Filter for lines 2490 and 2500
        line_2490 = oia[oia['Col_9_numeric'] == 2490.0].copy()
        line_2500 = oia[oia['Col_9_numeric'] == 2500.0].copy()
        
        print(f"  OIA Line 2490: {len(line_2490)} rows")
        print(f"  OIA Line 2500: {len(line_2500)} rows")
        
        # Find the AMT column for OIA (Aug AMT, Jul AMT, etc.)
        amt_col = None
        for month in month_order:
            test_col = f'{month} AMT'
            if test_col in oia.columns:
                amt_col = test_col
                break
                
        print(f"  OIA using column: {amt_col}")
        
        # Merge on Col_6 (TAFS)
        if len(line_2490) > 0 and len(line_2500) > 0 and amt_col:
            merged_oia = pd.merge(
                line_2490[['Agency', 'Col_0', 'Col_1', 'Col_2', 'Col_4', 'Col_6', amt_col]],
                line_2500[['Col_6', amt_col]], 
                on='Col_6', 
                suffixes=('_2490', '_2500')
            )
            
            print(f"  OIA After merge: {len(merged_oia)} accounts")
            
            # Process each OIA row
            for _, row in merged_oia.iterrows():
                try:
                    # Values are in dollars, convert to millions
                    unob = float(row[f'{amt_col}_2490']) / 1_000_000
                    ba = float(row[f'{amt_col}_2500']) / 1_000_000
                    
                    if ba == 0:
                        pct = 0.0 if unob == 0 else 100.0
                    else:
                        pct = (unob / ba * 100)
                    
                    # Parse TAFS and get account info
                    tafs_full = row['Col_6']  # e.g., "95-2300 /25 - Salaries and Expenses"
                    
                    # Extract account name
                    account_name = ''
                    if ' - ' in str(tafs_full):
                        account_name = str(tafs_full).split(' - ', 1)[1]
                    
                    # Parse TAFS components
                    account_num, period_of_perf, expiration_year = parse_tafs_components(
                        tafs_full, 'Other Independent Agencies'
                    )
                    
                    # Get bureau/agency name
                    bureau = ''
                    
                    # For OIA, bureau info might be in Col_2 after the account number
                    if pd.notna(row['Col_2']):
                        # Format: "247-00-5721   400 Years of African-American History Commission"
                        col2_str = str(row['Col_2']).strip()
                        parts = col2_str.split(None, 1)  # Split on first whitespace
                        if len(parts) > 1:
                            bureau = parts[1].strip()
                    
                    # If still no bureau and we have account name from TAFS, use that
                    if not bureau and account_name:
                        # The account name might be the bureau for OIA
                        bureau = account_name
                    
                    summary_data.append({
                        'Agency': 'Other Independent Agencies',
                        'Bureau': bureau,
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
                    print(f"    ERROR processing {row['Agency']} - {row['Col_4']}: {e}")
                    continue
    
    # Create final summary DataFrame
    summary_df = pd.DataFrame(summary_data)
    if len(summary_df) == 0:
        print("ERROR: No valid data found in summary")
        return None
    
    # Sort by Agency and Budget Authority
    summary_df = summary_df.sort_values(['Agency', 'Budget_Authority_M'], ascending=[True, False])
    
    # Create formatted output
    output_df = summary_df.copy()
    output_df['Unobligated Balance (Line 2490)'] = output_df['Unobligated_Balance_M'].apply(lambda x: f'${x:,.1f}M' if pd.notna(x) and not np.isinf(x) else '')
    output_df['Budget Authority (Line 2500)'] = output_df['Budget_Authority_M'].apply(lambda x: f'${x:,.1f}M' if pd.notna(x) and not np.isinf(x) else '')
    output_df['Percentage Unobligated'] = output_df['Percentage_Unobligated'].apply(lambda x: f'{x:.1f}%' if pd.notna(x) and not np.isinf(x) else '')
    
    # Select columns for final output
    final_df = output_df[['Agency', 'Bureau', 'Account', 'Account_Number', 
                         'Period_of_Performance', 'Expiration_Year', 'TAFS',
                         'Unobligated Balance (Line 2490)', 
                         'Budget Authority (Line 2500)', 'Percentage Unobligated']]
    
    # Save CSV output to site/data directory
    if fiscal_year:
        output_filename = f'all_agencies_obligation_summary_{fiscal_year}.csv'
        json_filename = f'all_agencies_summary_{fiscal_year}.json'
    else:
        output_filename = 'all_agencies_obligation_summary.csv'
        json_filename = 'all_agencies_summary.json'
    
    output_path = Path(f'site/data/{output_filename}')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_df.to_csv(output_path, index=False)
    print(f"\nSaved summary CSV to: {output_path}")
    
    # Create JSON for web app
    json_data = summary_df.copy()
    
    # Add formatted columns for consistency with existing web app
    json_data['Unobligated Balance (Line 2490)'] = json_data['Unobligated_Balance_M'].apply(lambda x: f'${x:,.1f}M' if pd.notna(x) and not np.isinf(x) else '')
    json_data['Budget Authority (Line 2500)'] = json_data['Budget_Authority_M'].apply(lambda x: f'${x:,.1f}M' if pd.notna(x) and not np.isinf(x) else '')
    json_data['Percentage Unobligated'] = json_data['Percentage_Unobligated'].apply(lambda x: f'{x:.1f}%' if pd.notna(x) and not np.isinf(x) else '')
    
    # Add fiscal year, month, and placeholder time series data
    json_data['Fiscal_Year'] = fiscal_year if fiscal_year else 'Unknown'
    json_data['Data_Month'] = month if month else 'Unknown'
    json_data['BA_TimeSeries'] = '[]'
    json_data['Unob_TimeSeries'] = '[]'
    
    # Save JSON to site/data directory
    json_path = Path(f'site/data/{json_filename}')
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_data.to_json(json_path, orient='records')
    print(f"Saved JSON for web app to: {json_path}")
    
    # Create/update metadata file with fiscal year -> month mapping
    metadata_path = Path('site/data/fiscal_year_metadata.json')
    metadata = {}
    
    # Load existing metadata if it exists
    if metadata_path.exists():
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
    
    # Update metadata for this fiscal year
    if fiscal_year and month:
        metadata[str(fiscal_year)] = {
            'month': month,
            'display_month': month[:3] if month else 'Unknown'  # First 3 letters (Sep, Aug, etc.)
        }
        
        # Save updated metadata
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"Updated fiscal year metadata: {metadata_path}")
    
    # Report on filtering/drops
    print(f"\n=== FILTERING SUMMARY ===")
    
    # Check what was dropped
    all_2490 = len(df[df['Line No'] == 2490.0]) if 'Line No' in df.columns else 0
    oia_2490 = len(df[(df['Agency'] == 'Other Independent Agencies') & 
                      (pd.to_numeric(df['Col_9'], errors='coerce') == 2490.0)]) if 'Col_9' in df.columns else 0
    total_2490 = all_2490 + oia_2490
    
    print(f"Total line 2490 accounts in master table: ~{total_2490}")
    print(f"Total accounts in final summary: {len(summary_df)}")
    print(f"Accounts dropped: ~{total_2490 - len(summary_df)}")
    print(f"  (Due to merge requirements, zero budget authority, or processing errors)")
    
    # Print summary statistics
    print(f"\n=== FINAL SUMMARY ===")
    print(f"Total accounts: {len(summary_df):,}")
    print(f"Total agencies: {summary_df['Agency'].nunique()}")
    print("\nBy Agency:")
    
    agency_summary = summary_df.groupby('Agency').agg({
        'Unobligated_Balance_M': 'sum',
        'Budget_Authority_M': 'sum',
        'TAFS': 'count'
    }).round(1)
    agency_summary['Percentage'] = (agency_summary['Unobligated_Balance_M'] / agency_summary['Budget_Authority_M'] * 100).round(1)
    agency_summary = agency_summary.rename(columns={'TAFS': 'Accounts'})
    
    # Sort by budget authority
    agency_summary = agency_summary.sort_values('Budget_Authority_M', ascending=False)
    
    # Print top agencies
    for agency, row in agency_summary.head(10).iterrows():
        print(f"  {agency}: ${row['Budget_Authority_M']:,.1f}M budget, "
              f"{row['Accounts']} accounts, {row['Percentage']:.1f}% unobligated")
    
    if len(agency_summary) > 10:
        print(f"  ... and {len(agency_summary) - 10} more agencies")
    
    # Overall totals
    total_unob = summary_df['Unobligated_Balance_M'].sum()
    total_ba = summary_df['Budget_Authority_M'].sum()
    total_pct = (total_unob / total_ba * 100) if total_ba > 0 else 0
    
    print(f"\nOVERALL TOTALS:")
    print(f"  Unobligated: ${total_unob:,.1f}M")
    print(f"  Budget Authority: ${total_ba:,.1f}M")
    print(f"  Percentage Unobligated: {total_pct:.1f}%")
    
    return output_path

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate obligation summary from SF133 master data")
    parser.add_argument("--year", type=int, help="Fiscal year to process (e.g., 2024)")
    parser.add_argument("--month", help="Month of the data (e.g., 'September', 'August')")
    parser.add_argument("--all-years", action="store_true", help="Process all available years")
    parser.add_argument("--master-file", help="Specific master file path")
    
    args = parser.parse_args()
    
    if args.master_file:
        # Use specific file
        master_path = Path(args.master_file)
        if master_path.exists():
            generate_obligation_summary(master_path, args.year, args.month)
        else:
            print(f"ERROR: Master file not found: {master_path}")
            sys.exit(1)
    
    elif args.all_years:
        # Process all available year-specific master files
        data_dir = Path('site/data')
        master_files = list(data_dir.glob('sf133_*_master.csv'))
        
        if not master_files:
            print("ERROR: No year-specific master files found in site/data/")
            print("Expected files like: sf133_2023_master.csv, sf133_2024_master.csv, etc.")
            sys.exit(1)
        
        print(f"Found {len(master_files)} master files:")
        for f in sorted(master_files):
            print(f"  {f.name}")
        
        for master_file in sorted(master_files):
            # Extract year from filename (e.g., sf133_2024_master.csv -> 2024)
            try:
                year_match = master_file.name.split('_')[1]
                year = int(year_match)
                print(f"\n{'='*80}")
                print(f"Processing FY{year} ({master_file.name})")
                print('='*80)
                generate_obligation_summary(master_file, year, args.month)
            except (IndexError, ValueError) as e:
                print(f"WARNING: Could not extract year from {master_file.name}: {e}")
                continue
    
    elif args.year:
        # Process specific year
        master_file = Path(f'site/data/sf133_{args.year}_master.csv')
        if master_file.exists():
            print(f"Processing FY{args.year} ({master_file.name})")
            generate_obligation_summary(master_file, args.year, args.month)
        else:
            print(f"ERROR: Master file not found: {master_file}")
            print("Available master files:")
            data_dir = Path('site/data')
            for f in sorted(data_dir.glob('sf133_*_master.csv')):
                print(f"  {f.name}")
            sys.exit(1)
    
    else:
        # Default behavior - look for generic master table first, then try current year
        master_table = Path('site/data/sf133_master_table.csv')
        if master_table.exists():
            print("Using generic master table (sf133_master_table.csv)")
            generate_obligation_summary(master_table, None, args.month)
        else:
            # Try to find the most recent year
            data_dir = Path('site/data')
            master_files = sorted(data_dir.glob('sf133_*_master.csv'), reverse=True)
            if master_files:
                latest_file = master_files[0]
                try:
                    year = int(latest_file.name.split('_')[1])
                    print(f"No generic master table found, using latest year: FY{year} ({latest_file.name})")
                    generate_obligation_summary(latest_file, year, args.month)
                except (IndexError, ValueError):
                    print(f"ERROR: Could not extract year from {latest_file.name}")
                    sys.exit(1)
            else:
                print("ERROR: No master table found.")
                print("Run 'python main.py --year YYYY' to process data first, or")
                print("run 'python generate_summary.py --all-years' to process all available years.")
                sys.exit(1)