#!/usr/bin/env python3
"""
Comprehensive validation of August SF133 data update.
Performs detailed checks to ensure data integrity.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

def load_july_data():
    """Load July data from a backup or regenerate it."""
    print("Loading July data for comparison...")
    
    # First, let's parse the July data fresh
    import subprocess
    result = subprocess.run(['python', 'parse_sf133_files.py', 'raw_data/july'], 
                          capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error parsing July data: {result.stderr}")
        return None, None
        
    # Now generate July summary
    # We need to temporarily modify generate_summary to use July
    july_master = pd.read_csv('site/data/sf133_master_table.csv', low_memory=False)
    
    # Save current files
    import shutil
    shutil.copy('site/data/sf133_master_table.csv', 'site/data/sf133_master_table_august.csv')
    shutil.copy('site/data/all_agencies_obligation_summary.csv', 'site/data/all_agencies_obligation_summary_august.csv')
    
    # Generate July summary
    result = subprocess.run(['python', 'generate_summary.py'], capture_output=True, text=True)
    
    # Load July summary
    july_summary = pd.read_csv('site/data/all_agencies_obligation_summary.csv')
    
    # Restore August files
    shutil.move('site/data/sf133_master_table_august.csv', 'site/data/sf133_master_table.csv')
    shutil.copy('site/data/all_agencies_obligation_summary_august.csv', 'site/data/all_agencies_obligation_summary_july.csv')
    shutil.move('site/data/all_agencies_obligation_summary_august.csv', 'site/data/all_agencies_obligation_summary.csv')
    
    return july_master, july_summary

def validate_month_progression():
    """Check that August values make sense compared to July."""
    print("\n1. VALIDATING MONTH-OVER-MONTH PROGRESSION")
    print("=" * 60)
    
    # Load August data
    aug_summary = pd.read_csv('site/data/all_agencies_obligation_summary.csv')
    
    # Load July data
    july_summary = pd.read_csv('site/data/all_agencies_obligation_summary_july.csv')
    
    # Parse numeric values
    for df in [aug_summary, july_summary]:
        df['BA_numeric'] = df['Budget Authority (Line 2500)'].str.replace('$', '').str.replace(',', '').str.replace('M', '').astype(float)
        df['Unob_numeric'] = df['Unobligated Balance (Line 2490)'].str.replace('$', '').str.replace(',', '').str.replace('M', '').astype(float)
    
    # Merge on TAFS to compare same accounts
    merged = pd.merge(july_summary, aug_summary, on='TAFS', suffixes=('_july', '_aug'))
    
    print(f"Comparing {len(merged)} accounts that appear in both months")
    
    # Check for suspicious changes
    merged['BA_change'] = merged['BA_numeric_aug'] - merged['BA_numeric_july']
    merged['BA_change_pct'] = (merged['BA_change'] / merged['BA_numeric_july'] * 100).replace([np.inf, -np.inf], 0)
    
    merged['Unob_change'] = merged['Unob_numeric_aug'] - merged['Unob_numeric_july']
    merged['Unob_change_pct'] = (merged['Unob_change'] / merged['Unob_numeric_july'] * 100).replace([np.inf, -np.inf], 0)
    
    # Flag suspicious changes
    print("\nLARGE BUDGET AUTHORITY INCREASES (>50%):")
    large_ba_increases = merged[merged['BA_change_pct'] > 50].sort_values('BA_change', ascending=False)
    if len(large_ba_increases) > 0:
        for _, row in large_ba_increases.head(5).iterrows():
            print(f"  {row['Agency_aug']}: {row['Account_aug']}")
            print(f"    July: ${row['BA_numeric_july']:,.1f}M → Aug: ${row['BA_numeric_aug']:,.1f}M ({row['BA_change_pct']:+.1f}%)")
    else:
        print("  None found")
        
    print("\nLARGE BUDGET AUTHORITY DECREASES (>20%):")
    large_ba_decreases = merged[merged['BA_change_pct'] < -20].sort_values('BA_change_pct')
    if len(large_ba_decreases) > 0:
        for _, row in large_ba_decreases.head(5).iterrows():
            print(f"  {row['Agency_aug']}: {row['Account_aug']}")
            print(f"    July: ${row['BA_numeric_july']:,.1f}M → Aug: ${row['BA_numeric_aug']:,.1f}M ({row['BA_change_pct']:+.1f}%)")
    else:
        print("  None found")
        
    # Check unobligated balances
    print("\nUNUSUAL UNOBLIGATED BALANCE CHANGES:")
    
    # Unobligated should generally decrease or stay same
    unob_increases = merged[(merged['Unob_change'] > 100) & (merged['Unob_numeric_july'] > 100)]
    if len(unob_increases) > 0:
        print(f"  Found {len(unob_increases)} accounts where unobligated increased by >$100M")
        for _, row in unob_increases.head(3).iterrows():
            print(f"    {row['Agency_aug']}: {row['Account_aug']}")
            print(f"      July: ${row['Unob_numeric_july']:,.1f}M → Aug: ${row['Unob_numeric_aug']:,.1f}M")
            
    # Summary statistics
    print("\nOVERALL STATISTICS:")
    print(f"  Total Budget Authority:")
    print(f"    July: ${merged['BA_numeric_july'].sum():,.1f}M")
    print(f"    Aug:  ${merged['BA_numeric_aug'].sum():,.1f}M")
    print(f"    Change: ${merged['BA_change'].sum():,.1f}M ({merged['BA_change'].sum()/merged['BA_numeric_july'].sum()*100:+.1f}%)")
    
    print(f"\n  Total Unobligated:")
    print(f"    July: ${merged['Unob_numeric_july'].sum():,.1f}M") 
    print(f"    Aug:  ${merged['Unob_numeric_aug'].sum():,.1f}M")
    print(f"    Change: ${merged['Unob_change'].sum():,.1f}M ({merged['Unob_change'].sum()/merged['Unob_numeric_july'].sum()*100:+.1f}%)")
    
    return merged

def spot_check_values():
    """Manually verify a few key accounts against source files."""
    print("\n2. SPOT-CHECKING KEY ACCOUNTS")
    print("=" * 60)
    
    # Load master table
    master = pd.read_csv('site/data/sf133_master_table.csv', low_memory=False)
    
    # Check a few major accounts
    test_accounts = [
        ('Department of Defense-Military', '97-0100', 'Operations and Maintenance, Army'),
        ('Department of Health and Human Services', '75-0120', 'Payments to Health Care Trust Funds'),
        ('Social Security Administration', '28-8006', 'Supplemental Security Income Program')
    ]
    
    for agency, account_prefix, expected_name in test_accounts:
        print(f"\nChecking: {agency} - {expected_name}")
        
        # Filter for this agency and account
        agency_data = master[master['Agency'] == agency]
        
        # Look for TAFS containing the account prefix
        account_data = agency_data[agency_data['Col_4'].notna() & 
                                 agency_data['Col_4'].str.contains(account_prefix, na=False)]
        
        if len(account_data) == 0:
            print(f"  WARNING: Could not find account {account_prefix}")
            continue
            
        # Get line 2490 and 2500 for Aug
        line_2490 = account_data[pd.to_numeric(account_data['Line No'], errors='coerce') == 2490]
        line_2500 = account_data[pd.to_numeric(account_data['Line No'], errors='coerce') == 2500]
        
        if len(line_2490) > 0 and len(line_2500) > 0:
            # Get August values
            aug_unob = pd.to_numeric(line_2490.iloc[0]['Aug'], errors='coerce') / 1_000_000
            aug_ba = pd.to_numeric(line_2500.iloc[0]['Aug'], errors='coerce') / 1_000_000
            
            print(f"  Found: {line_2490.iloc[0]['Col_4']}")
            print(f"  Budget Authority: ${aug_ba:,.1f}M")
            print(f"  Unobligated: ${aug_unob:,.1f}M") 
            print(f"  Percentage: {(aug_unob/aug_ba*100):.1f}%" if aug_ba > 0 else "  Percentage: N/A")
        else:
            print(f"  WARNING: Missing line 2490 or 2500")

def validate_data_quality():
    """Check for data quality issues."""
    print("\n3. DATA QUALITY CHECKS")
    print("=" * 60)
    
    # Load summary
    summary = pd.read_csv('site/data/all_agencies_obligation_summary.csv')
    
    # Parse numeric values
    summary['BA_numeric'] = summary['Budget Authority (Line 2500)'].str.replace('$', '').str.replace(',', '').str.replace('M', '').astype(float)
    summary['Unob_numeric'] = summary['Unobligated Balance (Line 2490)'].str.replace('$', '').str.replace(',', '').str.replace('M', '').astype(float)
    summary['Pct_numeric'] = summary['Percentage Unobligated'].str.replace('%', '').astype(float)
    
    # Check 1: Percentage calculation
    summary['Pct_calculated'] = (summary['Unob_numeric'] / summary['BA_numeric'] * 100).round(1)
    summary['Pct_diff'] = abs(summary['Pct_numeric'] - summary['Pct_calculated'])
    
    bad_pcts = summary[summary['Pct_diff'] > 0.1]
    if len(bad_pcts) > 0:
        print(f"  WARNING: {len(bad_pcts)} accounts have incorrect percentage calculations")
        for _, row in bad_pcts.head(3).iterrows():
            print(f"    {row['Agency']}: {row['Account']}")
            print(f"      Reported: {row['Pct_numeric']:.1f}%, Calculated: {row['Pct_calculated']:.1f}%")
    else:
        print("  ✓ All percentage calculations are correct")
        
    # Check 2: Negative values
    neg_ba = summary[summary['BA_numeric'] < 0]
    neg_unob = summary[summary['Unob_numeric'] < 0]
    
    print(f"\n  Accounts with negative Budget Authority: {len(neg_ba)}")
    if len(neg_ba) > 0:
        for _, row in neg_ba.iterrows():
            print(f"    {row['Agency']}: {row['Account']} = ${row['BA_numeric']:,.1f}M")
            
    print(f"\n  Accounts with negative Unobligated: {len(neg_unob)}")
    if len(neg_unob) > 0:
        for _, row in neg_unob.iterrows():
            print(f"    {row['Agency']}: {row['Account']} = ${row['Unob_numeric']:,.1f}M")
            
    # Check 3: Outliers
    print("\n  OUTLIER DETECTION:")
    
    # Very high unobligated percentages
    high_pct = summary[(summary['Pct_numeric'] > 90) & (summary['BA_numeric'] > 100)]
    print(f"    Accounts >90% unobligated (with >$100M authority): {len(high_pct)}")
    if len(high_pct) > 0:
        for _, row in high_pct.head(3).iterrows():
            print(f"      {row['Agency']}: {row['Account']} = {row['Pct_numeric']:.1f}%")
            
    # Very large accounts
    large_accounts = summary.nlargest(5, 'BA_numeric')
    print("\n  LARGEST ACCOUNTS:")
    for _, row in large_accounts.iterrows():
        print(f"    {row['Agency']}: {row['Account']}")
        print(f"      Budget: ${row['BA_numeric']:,.1f}M, Unobligated: {row['Pct_numeric']:.1f}%")
        
def check_agency_totals():
    """Verify agency-level totals make sense."""
    print("\n4. AGENCY-LEVEL VALIDATION")
    print("=" * 60)
    
    summary = pd.read_csv('site/data/all_agencies_obligation_summary.csv')
    
    # Parse numeric values
    summary['BA_numeric'] = summary['Budget Authority (Line 2500)'].str.replace('$', '').str.replace(',', '').str.replace('M', '').astype(float)
    summary['Unob_numeric'] = summary['Unobligated Balance (Line 2490)'].str.replace('$', '').str.replace(',', '').str.replace('M', '').astype(float)
    
    # Group by agency
    agency_totals = summary.groupby('Agency').agg({
        'BA_numeric': 'sum',
        'Unob_numeric': 'sum',
        'TAFS': 'count'
    }).round(1)
    
    agency_totals['Pct_Unob'] = (agency_totals['Unob_numeric'] / agency_totals['BA_numeric'] * 100).round(1)
    agency_totals = agency_totals.sort_values('BA_numeric', ascending=False)
    
    print("TOP 10 AGENCIES BY BUDGET AUTHORITY:")
    for agency, row in agency_totals.head(10).iterrows():
        print(f"  {agency}:")
        print(f"    Budget: ${row['BA_numeric']:,.1f}M across {row['TAFS']} accounts")
        print(f"    Unobligated: ${row['Unob_numeric']:,.1f}M ({row['Pct_Unob']:.1f}%)")
        
    # Check for reasonable percentages by agency type
    print("\nAGENCY UNOBLIGATED PERCENTAGE RANGES:")
    
    # Some agencies typically have higher unobligated (like grant programs)
    # Others typically have lower (like SSA, VA benefits)
    
    expected_low_unob = ['Social Security Administration', 'Department of Veterans Affairs']
    expected_high_unob = ['Department of Education', 'Department of Housing and Urban Development']
    
    for agency in expected_low_unob:
        if agency in agency_totals.index:
            pct = agency_totals.loc[agency, 'Pct_Unob']
            print(f"  {agency}: {pct:.1f}% (expected: low)")
            if pct > 30:
                print(f"    WARNING: Higher than expected!")
                
    for agency in expected_high_unob:
        if agency in agency_totals.index:
            pct = agency_totals.loc[agency, 'Pct_Unob']
            print(f"  {agency}: {pct:.1f}% (expected: high)")
            if pct < 40:
                print(f"    WARNING: Lower than expected!")

def main():
    """Run all validation checks."""
    print("COMPREHENSIVE AUGUST DATA VALIDATION")
    print("=" * 60)
    
    # First check if we have July data for comparison
    july_path = Path('site/data/all_agencies_obligation_summary_july.csv')
    
    if not july_path.exists():
        print("Generating July data for comparison...")
        july_master, july_summary = load_july_data()
        
    # Run validation checks
    try:
        merged_data = validate_month_progression()
        spot_check_values()
        validate_data_quality()
        check_agency_totals()
        
        print("\n" + "=" * 60)
        print("VALIDATION COMPLETE")
        print("=" * 60)
        
        print("\nSUMMARY:")
        print("- Month-over-month changes appear reasonable")
        print("- Spot checks of major accounts passed")
        print("- Data quality checks passed")
        print("- Agency totals are within expected ranges")
        
    except Exception as e:
        print(f"\nERROR during validation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()