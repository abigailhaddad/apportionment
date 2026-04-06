#!/usr/bin/env python3
"""
Create year-specific obligation summary files from SF133 master data.
Automatically detects the latest available month for each year.
"""

import pandas as pd
import json
import sys
from pathlib import Path

def find_latest_month(df):
    """Find the latest month with data in the dataframe."""
    # Define month order (fiscal year: Oct -> Sep)
    fiscal_months = ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep']
    
    # Check which month columns exist and have data
    available_months = []
    for month in reversed(fiscal_months):  # Start from latest (Sep) and go backwards
        if month in df.columns:
            # Check if this month has non-zero, non-null data
            month_data = pd.to_numeric(df[month], errors='coerce')
            if month_data.notna().any() and (month_data != 0).any():
                available_months.append(month)
    
    if available_months:
        latest_month = available_months[0]  # First in reversed list = latest
        print(f"  Latest month with data: {latest_month}")
        return latest_month
    
    print("  WARNING: No month columns found with data!")
    return None

def parse_tafs_components(tafs, agency_name):
    """Extract account number, period of performance, and expiration year from TAFS."""
    # Initialize defaults
    account_num = ''
    period_of_perf = ''
    expiration_year = ''
    
    if pd.isna(tafs) or tafs == '':
        return account_num, period_of_perf, expiration_year
    
    # Split TAFS to get the code part (before any description)
    tafs_parts = str(tafs).split(' - ')[0] if ' - ' in str(tafs) else str(tafs)
    
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

def create_year_summary(master_file_path, fiscal_year):
    """Create obligation summary from a year-specific master SF133 file."""
    
    print(f"\n{'='*80}")
    print(f"Processing FY{fiscal_year} - {master_file_path.name}")
    print('='*80)
    
    # Read the master table
    print("Reading master table...")
    df = pd.read_csv(master_file_path, low_memory=False)
    print(f"  Total rows: {len(df):,}")
    print(f"  Agencies: {df['Agency'].nunique()}")
    
    # Find the latest month with data
    latest_month = find_latest_month(df)
    if not latest_month:
        print("ERROR: No month data found!")
        return None
    
    # Convert LINENO to numeric for filtering
    df['LINENO'] = pd.to_numeric(df['LINENO'], errors='coerce')
    
    # Process each agency type
    summary_data = []
    
    # Process standard agencies (non-OIA)
    standard_agencies = df[df['Agency'] != 'Other Independent Agencies'].copy()
    if len(standard_agencies) > 0:
        # Filter for lines 2490 and 2500
        line_2490 = standard_agencies[standard_agencies['LINENO'] == 2490.0].copy()
        line_2500 = standard_agencies[standard_agencies['LINENO'] == 2500.0].copy()
        
        print(f"  Standard agencies - Line 2490: {len(line_2490)} accounts")
        print(f"  Standard agencies - Line 2500: {len(line_2500)} accounts")
        
        # Merge on TAFS
        if len(line_2490) > 0 and len(line_2500) > 0:
            merged = pd.merge(
                line_2490[['Agency', 'BUREAU', 'TAFS', latest_month]],
                line_2500[['Agency', 'TAFS', latest_month]], 
                on=['Agency', 'TAFS'], 
                suffixes=('_2490', '_2500')
            )
            
            print(f"  After merge: {len(merged)} accounts")
            
            # Process each row
            for _, row in merged.iterrows():
                try:
                    unob = float(row[f'{latest_month}_2490']) / 1_000_000
                    ba = float(row[f'{latest_month}_2500']) / 1_000_000
                    
                    if ba == 0:
                        pct = 0.0 if unob == 0 else 100.0
                    else:
                        pct = (unob / ba * 100)
                    
                    # Parse TAFS components
                    account_num, period_of_perf, expiration_year = parse_tafs_components(
                        row['TAFS'], row['Agency']
                    )
                    
                    # Extract account name from TAFS (after ' - ')
                    account_name = ''
                    if ' - ' in str(row['TAFS']):
                        account_name = str(row['TAFS']).split(' - ', 1)[1]
                    
                    summary_data.append({
                        'Agency': row['Agency'],
                        'Bureau': row['BUREAU'] if pd.notna(row['BUREAU']) else '',
                        'Account': account_name,
                        'Account_Number': account_num,
                        'Period_of_Performance': period_of_perf,
                        'Expiration_Year': expiration_year,
                        'TAFS': row['TAFS'],
                        'Unobligated_Balance_M': round(unob, 1),
                        'Budget_Authority_M': round(ba, 1),
                        'Percentage_Unobligated': round(pct, 1)
                    })
                except Exception as e:
                    print(f"    ERROR processing {row['Agency']} - {row['TAFS']}: {e}")
                    continue
    
    # Process Other Independent Agencies separately (if any)
    oia = df[df['Agency'] == 'Other Independent Agencies'].copy()
    if len(oia) > 0:
        print(f"\nProcessing Other Independent Agencies ({len(oia)} rows)...")
        # Add OIA processing here if needed - similar to above but adapted for OIA structure
    
    # Create final summary DataFrame
    summary_df = pd.DataFrame(summary_data)
    if len(summary_df) == 0:
        print("ERROR: No valid data found in summary")
        return None
    
    # Sort by Agency and Budget Authority
    summary_df = summary_df.sort_values(['Agency', 'Budget_Authority_M'], ascending=[True, False])
    
    # Create formatted output
    output_df = summary_df.copy()
    output_df['Unobligated Balance (Line 2490)'] = output_df['Unobligated_Balance_M'].apply(lambda x: f'${x:,.1f}M' if pd.notna(x) else '0.0')
    output_df['Budget Authority (Line 2500)'] = output_df['Budget_Authority_M'].apply(lambda x: f'${x:,.1f}M' if pd.notna(x) else '0.0')
    output_df['Percentage Unobligated'] = output_df['Percentage_Unobligated'].apply(lambda x: f'{x:.1f}%' if pd.notna(x) else '0.0')
    
    # Select columns for final output
    final_df = output_df[['Agency', 'Bureau', 'Account', 'Account_Number', 
                         'Period_of_Performance', 'Expiration_Year', 'TAFS',
                         'Unobligated Balance (Line 2490)', 
                         'Budget Authority (Line 2500)', 'Percentage Unobligated']]
    
    # Save CSV output
    output_filename = f'all_agencies_obligation_summary_{fiscal_year}.csv'
    output_path = Path(f'site/data/{output_filename}')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_df.to_csv(output_path, index=False)
    print(f"\n✅ Saved summary CSV to: {output_path}")
    
    # Create JSON for web app
    json_data = summary_df.copy()
    
    # Add formatted columns for consistency with existing web app
    json_data['Unobligated Balance (Line 2490)'] = json_data['Unobligated_Balance_M'].apply(lambda x: f'${x:,.1f}M')
    json_data['Budget Authority (Line 2500)'] = json_data['Budget_Authority_M'].apply(lambda x: f'${x:,.1f}M')
    json_data['Percentage Unobligated'] = json_data['Percentage_Unobligated'].apply(lambda x: f'{x:.1f}%')
    
    # Add fiscal year and placeholder time series data
    json_data['Fiscal_Year'] = fiscal_year
    json_data['BA_TimeSeries'] = '[]'
    json_data['Unob_TimeSeries'] = '[]'
    
    # Save JSON
    json_filename = f'all_agencies_summary_{fiscal_year}.json'
    json_path = Path(f'site/data/{json_filename}')
    json_data.to_json(json_path, orient='records')
    print(f"✅ Saved JSON for web app to: {json_path}")
    
    # Create/update metadata file with fiscal year -> month mapping
    metadata_path = Path('site/data/fiscal_year_metadata.json')
    metadata = {}
    
    # Load existing metadata if it exists
    if metadata_path.exists():
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
    
    # Convert month abbreviation to full name
    month_mapping = {
        'Oct': 'October', 'Nov': 'November', 'Dec': 'December',
        'Jan': 'January', 'Feb': 'February', 'Mar': 'March',
        'Apr': 'April', 'May': 'May', 'Jun': 'June',
        'Jul': 'July', 'Aug': 'August', 'Sep': 'September'
    }
    
    full_month = month_mapping.get(latest_month, latest_month)
    
    # Update metadata for this fiscal year
    metadata[str(fiscal_year)] = {
        'month': full_month,
        'display_month': latest_month
    }
    
    # Save updated metadata
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"✅ Updated fiscal year metadata: {metadata_path}")
    
    # Print summary statistics
    print(f"\n=== SUMMARY STATISTICS ===")
    print(f"Total accounts: {len(summary_df):,}")
    print(f"Total agencies: {summary_df['Agency'].nunique()}")
    print(f"Data month: {latest_month} {fiscal_year}")
    
    # Overall totals
    total_unob = summary_df['Unobligated_Balance_M'].sum()
    total_ba = summary_df['Budget_Authority_M'].sum()
    total_pct = (total_unob / total_ba * 100) if total_ba > 0 else 0
    
    print(f"\nOVERALL TOTALS:")
    print(f"  Unobligated: ${total_unob:,.1f}M")
    print(f"  Budget Authority: ${total_ba:,.1f}M")
    print(f"  Percentage Unobligated: {total_pct:.1f}%")
    
    return output_path

def main():
    """Main function to process all available years."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Create year-specific obligation summaries")
    parser.add_argument("--year", type=int, help="Specific fiscal year to process (e.g., 2024)")
    parser.add_argument("--all-years", action="store_true", help="Process all available years")
    
    args = parser.parse_args()
    
    data_dir = Path('site/data')
    
    if args.year:
        # Process specific year
        master_file = data_dir / f'sf133_{args.year}_master.csv'
        if master_file.exists():
            create_year_summary(master_file, args.year)
        else:
            print(f"ERROR: Master file not found: {master_file}")
            print("Available master files:")
            for f in sorted(data_dir.glob('sf133_*_master.csv')):
                print(f"  {f.name}")
            sys.exit(1)
    
    elif args.all_years:
        # Process all available years
        master_files = list(data_dir.glob('sf133_*_master.csv'))
        
        if not master_files:
            print("ERROR: No year-specific master files found in site/data/")
            print("Expected files like: sf133_2023_master.csv, sf133_2024_master.csv, etc.")
            sys.exit(1)
        
        print(f"Found {len(master_files)} master files:")
        for f in sorted(master_files):
            print(f"  {f.name}")
        
        success_count = 0
        for master_file in sorted(master_files):
            # Extract year from filename (e.g., sf133_2024_master.csv -> 2024)
            try:
                year_match = master_file.name.split('_')[1]
                year = int(year_match)
                
                result = create_year_summary(master_file, year)
                if result:
                    success_count += 1
                    
            except (IndexError, ValueError) as e:
                print(f"WARNING: Could not extract year from {master_file.name}: {e}")
                continue
        
        print(f"\n{'='*80}")
        print(f"🎉 Successfully processed {success_count}/{len(master_files)} years!")
        print('='*80)
    
    else:
        # Default: process most recent year
        master_files = sorted(data_dir.glob('sf133_*_master.csv'), reverse=True)
        if master_files:
            latest_file = master_files[0]
            try:
                year = int(latest_file.name.split('_')[1])
                print(f"Processing most recent year: FY{year}")
                create_year_summary(latest_file, year)
            except (IndexError, ValueError):
                print(f"ERROR: Could not extract year from {latest_file.name}")
                sys.exit(1)
        else:
            print("ERROR: No master files found in site/data/")
            print("Usage:")
            print("  python create_year_summaries.py --year 2024")
            print("  python create_year_summaries.py --all-years")
            sys.exit(1)

if __name__ == "__main__":
    main()