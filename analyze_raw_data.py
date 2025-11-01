#!/usr/bin/env python3
"""
Analyze raw SF133 data to understand what's missing in 2013-2017.
Check TAFS overlap, month coverage, and fund types across years.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

def analyze_year_data(year):
    """Analyze raw SF133 data for a specific year."""
    master_file = Path(f'site/data/sf133_{year}_master.csv')
    
    if not master_file.exists():
        print(f"❌ FY{year}: Master file not found")
        return None
    
    print(f"\n{'='*60}")
    print(f"📊 ANALYZING FY{year} RAW DATA")
    print('='*60)
    
    try:
        # Read the master file
        df = pd.read_csv(master_file, low_memory=False)
        
        # Basic stats
        print(f"📁 File size: {master_file.stat().st_size / 1024 / 1024:.1f} MB")
        print(f"📝 Total rows: {len(df):,}")
        print(f"🏛️  Unique agencies: {df['AGENCY_TITLE'].nunique()}")
        print(f"🏢 Unique bureaus: {df['BUREAU'].nunique()}")
        print(f"📋 Unique TAFS: {df['TAFS'].nunique()}")
        
        # Check month coverage
        print(f"\n📅 MONTH COVERAGE:")
        fiscal_months = ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep']
        available_months = []
        month_data_counts = {}
        
        for month in fiscal_months:
            if month in df.columns:
                # Count non-zero, non-null values
                month_values = pd.to_numeric(df[month], errors='coerce')
                non_zero_count = ((month_values != 0) & month_values.notna()).sum()
                month_data_counts[month] = non_zero_count
                if non_zero_count > 0:
                    available_months.append(month)
                    print(f"  ✅ {month}: {non_zero_count:,} non-zero values")
                else:
                    print(f"  ❌ {month}: No data")
            else:
                print(f"  ❌ {month}: Column missing")
        
        print(f"  📊 Months with data: {len(available_months)}/12")
        latest_month = available_months[-1] if available_months else None
        print(f"  📅 Latest month: {latest_month}")
        
        # Analyze TAFS patterns
        print(f"\n🔍 TAFS ANALYSIS:")
        tafs_list = df['TAFS'].dropna().unique()
        
        # Check for different fund types based on TAFS patterns
        current_year_tafs = []
        multi_year_tafs = []
        no_year_tafs = []
        
        for tafs in tafs_list:
            tafs_str = str(tafs).strip()
            if '/X' in tafs_str:
                no_year_tafs.append(tafs)
            elif '/' in tafs_str and not tafs_str.endswith('/X'):
                if tafs_str.count('/') == 1 and not tafs_str.split('/')[-1].strip() == 'X':
                    parts = tafs_str.split('/')
                    if len(parts) == 2:
                        last_part = parts[-1].strip().split(' ')[0]  # Get year part before description
                        if len(last_part) == 2 and last_part.isdigit():
                            current_year_tafs.append(tafs)
                        elif '/' in parts[-1] or len(last_part) > 2:
                            multi_year_tafs.append(tafs)
            # Multi-year pattern like "21/25"
            elif any(f'/{i}' in tafs_str for i in range(10, 30)):
                multi_year_tafs.append(tafs)
        
        print(f"  🎯 Current year funds: {len(current_year_tafs)}")
        print(f"  📅 Multi-year funds: {len(multi_year_tafs)}")  
        print(f"  ♾️  No-year funds: {len(no_year_tafs)}")
        print(f"  ❓ Other/unclear: {len(tafs_list) - len(current_year_tafs) - len(multi_year_tafs) - len(no_year_tafs)}")
        
        # Check line numbers (budget execution categories)
        print(f"\n📊 LINE NUMBER ANALYSIS:")
        if 'LINENO' in df.columns:
            df['LINENO'] = pd.to_numeric(df['LINENO'], errors='coerce')
            line_counts = df['LINENO'].value_counts().sort_index()
            print(f"  📋 Unique line numbers: {df['LINENO'].nunique()}")
            print(f"  🎯 Line 2490 (Unobligated): {line_counts.get(2490.0, 0):,} records")
            print(f"  🎯 Line 2500 (Budget Authority): {line_counts.get(2500.0, 0):,} records")
            
            # Show top line numbers
            print(f"  📈 Top line numbers:")
            for line_no, count in line_counts.head(5).items():
                print(f"    Line {line_no}: {count:,} records")
        
        # Sample TAFS examples
        print(f"\n📋 SAMPLE TAFS (first 10):")
        for i, tafs in enumerate(tafs_list[:10]):
            print(f"  {i+1:2d}. {tafs}")
        
        return {
            'year': year,
            'total_rows': len(df),
            'unique_tafs': len(tafs_list),
            'unique_agencies': df['AGENCY_TITLE'].nunique(),
            'months_with_data': len(available_months),
            'latest_month': latest_month,
            'current_year_funds': len(current_year_tafs),
            'multi_year_funds': len(multi_year_tafs),
            'no_year_funds': len(no_year_tafs),
            'tafs_list': set(tafs_list),
            'file_size_mb': master_file.stat().st_size / 1024 / 1024
        }
        
    except Exception as e:
        print(f"❌ Error analyzing FY{year}: {e}")
        return None

def compare_tafs_overlap(year_data_dict):
    """Compare TAFS overlap between years."""
    print(f"\n{'='*80}")
    print(f"🔍 TAFS OVERLAP ANALYSIS")
    print('='*80)
    
    years = sorted(year_data_dict.keys())
    
    if 2012 in year_data_dict:
        baseline_tafs = year_data_dict[2012]['tafs_list']
        print(f"📊 Using FY2012 as baseline ({len(baseline_tafs):,} TAFS)")
        
        for year in years:
            if year == 2012:
                continue
                
            if year in year_data_dict:
                current_tafs = year_data_dict[year]['tafs_list']
                
                # Calculate overlap
                overlap = baseline_tafs & current_tafs
                only_in_2012 = baseline_tafs - current_tafs
                only_in_current = current_tafs - baseline_tafs
                
                overlap_pct = (len(overlap) / len(baseline_tafs)) * 100
                
                print(f"\n📈 FY{year} vs FY2012:")
                print(f"  🎯 TAFS in FY{year}: {len(current_tafs):,}")
                print(f"  🔗 Overlap with 2012: {len(overlap):,} ({overlap_pct:.1f}%)")
                print(f"  ➖ Only in 2012: {len(only_in_2012):,}")
                print(f"  ➕ Only in FY{year}: {len(only_in_current):,}")
                
                # Show examples of missing TAFS
                if len(only_in_2012) > 0:
                    print(f"  📋 Examples only in 2012: {list(only_in_2012)[:3]}")

def main():
    """Analyze raw data across multiple years."""
    print("🔍 SF133 Raw Data Analysis")
    print("Analyzing TAFS coverage, months, and fund types across years")
    
    years_to_analyze = [2012, 2013, 2014, 2015, 2016, 2017, 2018]
    year_data = {}
    
    # Analyze each year
    for year in years_to_analyze:
        result = analyze_year_data(year)
        if result:
            year_data[year] = result
    
    # Summary comparison
    print(f"\n{'='*80}")
    print(f"📊 SUMMARY COMPARISON")
    print('='*80)
    
    print(f"{'Year':<6} {'Rows':<10} {'TAFS':<8} {'Agencies':<9} {'Months':<7} {'Latest':<8} {'Size(MB)':<9}")
    print("-" * 80)
    
    for year in sorted(year_data.keys()):
        data = year_data[year]
        print(f"FY{year:<4} {data['total_rows']:<10,} {data['unique_tafs']:<8,} "
              f"{data['unique_agencies']:<9} {data['months_with_data']:<7} "
              f"{data['latest_month'] or 'None':<8} {data['file_size_mb']:<9.1f}")
    
    # Fund type comparison
    print(f"\n📊 FUND TYPE BREAKDOWN:")
    print(f"{'Year':<6} {'Current':<8} {'Multi':<8} {'NoYear':<8} {'Total':<8}")
    print("-" * 50)
    
    for year in sorted(year_data.keys()):
        data = year_data[year]
        total = data['current_year_funds'] + data['multi_year_funds'] + data['no_year_funds']
        print(f"FY{year:<4} {data['current_year_funds']:<8} {data['multi_year_funds']:<8} "
              f"{data['no_year_funds']:<8} {total:<8}")
    
    # TAFS overlap analysis
    compare_tafs_overlap(year_data)

if __name__ == "__main__":
    main()