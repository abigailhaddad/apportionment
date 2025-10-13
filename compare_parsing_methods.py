#!/usr/bin/env python3
"""
Compare the Raw Data extraction method with the original TAFS detail method.
This validates that we get consistent data from both approaches.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

def load_datasets():
    """Load both datasets for comparison."""
    # Original TAFS detail extraction
    original_path = Path('site/data/sf133_master_table.csv')
    raw_data_path = Path('site/data/sf133_raw_data_master.csv')
    
    if not original_path.exists():
        print(f"❌ Original dataset not found at {original_path}")
        return None, None
        
    if not raw_data_path.exists():
        print(f"❌ Raw data dataset not found at {raw_data_path}")
        return None, None
    
    print("📊 Loading datasets...")
    original_df = pd.read_csv(original_path)
    raw_data_df = pd.read_csv(raw_data_path)
    
    print(f"Original (TAFS detail): {original_df.shape[0]:,} rows, {original_df.shape[1]} columns")
    print(f"Raw Data: {raw_data_df.shape[0]:,} rows, {raw_data_df.shape[1]} columns")
    
    return original_df, raw_data_df

def compare_agencies(original_df, raw_data_df):
    """Compare agency coverage between datasets."""
    print("\n🏢 AGENCY COMPARISON:")
    
    original_agencies = set(original_df['Agency'].unique())
    raw_data_agencies = set(raw_data_df['Agency'].unique())
    
    print(f"Original dataset agencies: {len(original_agencies)}")
    print(f"Raw data dataset agencies: {len(raw_data_agencies)}")
    
    # Agencies in both
    common_agencies = original_agencies & raw_data_agencies
    print(f"Common agencies: {len(common_agencies)}")
    
    # Agencies only in original
    only_original = original_agencies - raw_data_agencies
    if only_original:
        print(f"Only in original: {only_original}")
    
    # Agencies only in raw data
    only_raw = raw_data_agencies - original_agencies  
    if only_raw:
        print(f"Only in raw data: {only_raw}")
    
    return common_agencies

def compare_monthly_columns(original_df, raw_data_df):
    """Compare monthly data columns between datasets."""
    print("\n📅 MONTHLY COLUMN COMPARISON:")
    
    # Get month columns from both datasets
    original_month_cols = [col for col in original_df.columns if any(month in col for month in ['Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Q'])]
    raw_data_month_cols = [col for col in raw_data_df.columns if any(month in col for month in ['Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Q'])]
    
    print(f"Original month columns: {original_month_cols}")
    print(f"Raw data month columns: {raw_data_month_cols}")
    
    return original_month_cols, raw_data_month_cols

def test_specific_values(original_df, raw_data_df, common_agencies):
    """Test that specific values match between datasets."""
    print("\n🔍 VALUE COMPARISON TEST:")
    
    # Test values we identified earlier
    test_cases = [
        {'agency': 'Department of Education', 'file': '2580778249.xlsx', 'jun_value': '55037088.11', 'jul_value': '13250900102.56', 'aug_value': '13397291675.62'},
    ]
    
    for test_case in test_cases:
        agency = test_case['agency']
        file_name = test_case['file']
        
        if agency not in common_agencies:
            print(f"⚠️ {agency} not in both datasets, skipping")
            continue
            
        print(f"\n🧪 Testing {agency} ({file_name}):")
        
        # Find matching rows in both datasets
        orig_rows = original_df[(original_df['Agency'] == agency) & (original_df['Source_File'] == file_name)]
        raw_rows = raw_data_df[(raw_data_df['Agency'] == agency) & (raw_data_df['Source_File'] == file_name)]
        
        print(f"  Original dataset: {len(orig_rows)} rows")
        print(f"  Raw data dataset: {len(raw_rows)} rows")
        
        if len(orig_rows) == 0 or len(raw_rows) == 0:
            print(f"  ⚠️ No matching rows found")
            continue
        
        # Test specific values
        test_values = [
            ('Jun', test_case['jun_value']),
            ('Jul', test_case['jul_value']), 
            ('Aug', test_case['aug_value'])
        ]
        
        for month, expected_value in test_values:
            # Find columns that match this month
            orig_cols = [col for col in orig_rows.columns if month in col]
            raw_cols = [col for col in raw_rows.columns if month in col]
            
            orig_found = False
            raw_found = False
            
            # Check original dataset
            for col in orig_cols:
                if orig_rows[col].astype(str).str.contains(expected_value, na=False).any():
                    orig_found = True
                    print(f"    ✅ {month} value {expected_value} found in original column '{col}'")
                    break
            
            # Check raw data dataset  
            for col in raw_cols:
                if raw_rows[col].astype(str).str.contains(expected_value, na=False).any():
                    raw_found = True
                    print(f"    ✅ {month} value {expected_value} found in raw data column '{col}'")
                    break
            
            if not orig_found:
                print(f"    ❌ {month} value {expected_value} NOT found in original dataset")
            if not raw_found:
                print(f"    ❌ {month} value {expected_value} NOT found in raw data dataset")
                
            if orig_found and raw_found:
                print(f"    🎯 {month} value matches in both datasets!")

def compare_row_counts_by_agency(original_df, raw_data_df, common_agencies):
    """Compare row counts by agency between datasets."""
    print("\n📊 ROW COUNT COMPARISON BY AGENCY:")
    
    comparison_data = []
    
    for agency in sorted(common_agencies):
        orig_count = len(original_df[original_df['Agency'] == agency])
        raw_count = len(raw_data_df[raw_data_df['Agency'] == agency])
        
        difference = raw_count - orig_count
        pct_diff = (difference / orig_count * 100) if orig_count > 0 else 0
        
        comparison_data.append({
            'Agency': agency,
            'Original': orig_count,
            'Raw_Data': raw_count,
            'Difference': difference,
            'Pct_Change': pct_diff
        })
        
        if abs(pct_diff) > 10:  # Flag significant differences
            print(f"⚠️ {agency}: {orig_count:,} → {raw_count:,} ({difference:+,}, {pct_diff:+.1f}%)")
        elif difference != 0:
            print(f"ℹ️ {agency}: {orig_count:,} → {raw_count:,} ({difference:+,}, {pct_diff:+.1f}%)")
        else:
            print(f"✅ {agency}: {orig_count:,} rows (exact match)")
    
    # Summary statistics
    comparison_df = pd.DataFrame(comparison_data)
    print(f"\n📈 SUMMARY STATISTICS:")
    print(f"Agencies with exact row match: {len(comparison_df[comparison_df['Difference'] == 0])}/{len(comparison_df)}")
    print(f"Average row count change: {comparison_df['Pct_Change'].mean():+.1f}%")
    print(f"Total rows - Original: {comparison_df['Original'].sum():,}")
    print(f"Total rows - Raw Data: {comparison_df['Raw_Data'].sum():,}")
    
    return comparison_df

def main():
    """Main comparison function."""
    print("🔍 COMPARING SF133 PARSING METHODS")
    print("=" * 50)
    
    # Load datasets
    original_df, raw_data_df = load_datasets()
    if original_df is None or raw_data_df is None:
        return
    
    # Compare agencies
    common_agencies = compare_agencies(original_df, raw_data_df)
    
    # Compare monthly columns
    compare_monthly_columns(original_df, raw_data_df)
    
    # Test specific values
    test_specific_values(original_df, raw_data_df, common_agencies)
    
    # Compare row counts
    comparison_df = compare_row_counts_by_agency(original_df, raw_data_df, common_agencies)
    
    print("\n🎯 CONCLUSION:")
    if len(comparison_df[comparison_df['Difference'] == 0]) == len(comparison_df):
        print("✅ Perfect match! Raw Data method produces identical results.")
    elif comparison_df['Pct_Change'].abs().mean() < 5:
        print("✅ Very close match! Raw Data method is reliable.")
    elif comparison_df['Pct_Change'].abs().mean() < 20:
        print("⚠️ Moderate differences found. Review needed.")
    else:
        print("❌ Significant differences found. Investigation required.")

if __name__ == "__main__":
    main()