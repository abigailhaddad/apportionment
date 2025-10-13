#!/usr/bin/env python3
"""
SF133 Year-Based Data Processing System
======================================

Simple, automated system for processing full years of SF133 data:
1. Downloads all files for a fiscal year from MAX.gov
2. Processes all available months using Raw Data sheets
3. Auto-detects and skips empty months
4. Generates complete year dataset

Usage:
    python year_processor.py --year 2024 --url "https://portal.max.gov/.../FY%202024%20..."
    python year_processor.py --year 2024  # Uses config file
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
import argparse
import sys
from datetime import datetime
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

from code.download_sf133_data import download_sf133_files
from code.parse_sf133_raw_data import parse_all_sf133_raw_data

class SF133YearProcessor:
    """Process complete fiscal year of SF133 data."""
    
    def __init__(self, base_dir: Path = Path(".")):
        self.base_dir = Path(base_dir)
        self.raw_data_dir = self.base_dir / "raw_data"
        self.site_data_dir = self.base_dir / "site" / "data"
        
        # Load URL config
        self.config_path = self.base_dir / "sf133_urls.json"
        self.urls = self._load_config()
        
        # Ensure directories exist
        for dir_path in [self.raw_data_dir, self.site_data_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def _load_config(self) -> dict:
        """Load SF133 URLs from config file."""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {"sf133_urls": {}}
    
    def download_year_data(self, year: int, url: str = None) -> bool:
        """Download all SF133 files for a fiscal year."""
        print(f"🔽 DOWNLOADING FY{year} SF133 DATA")
        print("=" * 60)
        
        # Get URL from config or parameter
        if url is None:
            year_str = str(year)
            if year_str not in self.urls.get("sf133_urls", {}):
                print(f"❌ No URL configured for year {year}")
                print(f"Available years: {list(self.urls.get('sf133_urls', {}).keys())}")
                return False
            url = self.urls["sf133_urls"][year_str]
        
        # Set up target directory
        target_dir = self.raw_data_dir / str(year)
        target_dir.mkdir(exist_ok=True)
        
        print(f"Source: {url}")
        print(f"Target: {target_dir}")
        
        try:
            success = download_sf133_files(str(target_dir), url)
            if success:
                print(f"✅ Successfully downloaded FY{year} data")
                return True
            else:
                print(f"❌ Failed to download FY{year} data")
                return False
        except Exception as e:
            print(f"❌ Download error: {e}")
            return False
    
    def process_year_data(self, year: int) -> Optional[Path]:
        """Process all available months for a fiscal year."""
        print(f"\n📊 PROCESSING FY{year} DATA")
        print("=" * 60)
        
        source_dir = self.raw_data_dir / str(year)
        if not source_dir.exists():
            print(f"❌ Data directory not found: {source_dir}")
            return None
        
        try:
            # Process all files in the year directory
            output_path = parse_all_sf133_raw_data(str(source_dir))
            
            if output_path:
                # Rename to year-specific file
                year_output = self.site_data_dir / f"sf133_{year}_master.csv"
                
                import shutil
                shutil.move(str(output_path), str(year_output))
                
                # Auto-detect and validate available months
                print(f"🔍 DEBUG: About to call _analyze_year_data for {year}")
                validation_passed = self._analyze_year_data(year_output, year)
                print(f"🔍 DEBUG: _analyze_year_data returned: {validation_passed}")
                
                if validation_passed:
                    print(f"✅ Successfully processed FY{year} data")
                    print(f"📁 Saved to: {year_output}")
                    return year_output
                else:
                    print(f"❌ FY{year} data validation failed - incomplete data detected")
                    return None
            else:
                print(f"❌ Failed to process FY{year} data")
                return None
                
        except Exception as e:
            print(f"❌ Processing error: {e}")
            return None
    
    def _analyze_year_data(self, data_path: Path, year: int):
        """Analyze the processed data and report available months."""
        try:
            df = pd.read_csv(data_path, low_memory=False)
            
            # Load baseline TAFS data (use 2025 as benchmark if available)
            print("🔍 DEBUG: Loading baseline TAFS data...")
            baseline_tafs = self._load_baseline_tafs_data()
            print(f"🔍 DEBUG: Baseline loaded: {bool(baseline_tafs.get('tafs_by_agency'))}")
            
            # Fiscal Year Quarter Mapping
            FISCAL_QUARTERS = {
                'Q1': ['Oct', 'Nov', 'Dec'],  # Dec (1Q) is quarter-end
                'Q2': ['Jan', 'Feb', 'Mar'],  # Mar (2Q) is quarter-end  
                'Q3': ['Apr', 'May', 'Jun'],  # Jun (3Q) is quarter-end
                'Q4': ['Jul', 'Aug', 'Sep']   # Sep (4Q) is quarter-end (fiscal year end)
            }
            
            # All expected months in fiscal year order
            ALL_MONTHS = ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep']
            
            print(f"\n📅 FY{year} MONTH ANALYSIS:")
            print("-" * 50)
            print("Fiscal Year Quarter Mapping:")
            for quarter, months in FISCAL_QUARTERS.items():
                print(f"  {quarter}: {', '.join(months)}")
            print("-" * 50)
            
            # Find month and quarter columns
            month_data = {}
            quarter_data = {}
            
            # Check individual month columns
            for month in ALL_MONTHS:
                matching_cols = [col for col in df.columns if col == month]
                if matching_cols:
                    total = df[matching_cols[0]].sum()
                    month_data[month] = {
                        'column': matching_cols[0],
                        'total': total,
                        'has_data': abs(total) > 1000
                    }
            
            # Check quarterly columns  
            quarter_cols = {
                'Q1': [col for col in df.columns if 'Dec (1Q)' in col or col == 'Dec (1Q)'],
                'Q2': [col for col in df.columns if 'Mar (2Q)' in col or col == 'Mar (2Q)'], 
                'Q3': [col for col in df.columns if 'Jun (3Q)' in col or col == 'Jun (3Q)'],
                'Q4': [col for col in df.columns if 'Sep (4Q)' in col or col == 'Sep (4Q)']
            }
            
            for quarter, cols in quarter_cols.items():
                if cols:
                    total = df[cols[0]].sum()
                    quarter_data[quarter] = {
                        'column': cols[0], 
                        'total': total,
                        'has_data': abs(total) > 1000
                    }
            
            # Report findings
            available_months = []
            missing_months = []
            
            for month in ALL_MONTHS:
                if month in month_data:
                    data = month_data[month]
                    if data['has_data']:
                        available_months.append(month)
                        print(f"  {month:3}: ${data['total']/1e9:>8.1f}B ✅")
                    else:
                        missing_months.append(month)
                        print(f"  {month:3}: ${data['total']:>12.0f} (empty)")
                else:
                    missing_months.append(month)
                    print(f"  {month:3}: No column found ❌")
            
            # Report quarterly data
            print(f"\nQuarterly Totals:")
            for quarter, data in quarter_data.items():
                if data['has_data']:
                    print(f"  {quarter}: ${data['total']/1e9:>8.1f}B ✅ ({data['column']})")
                else:
                    print(f"  {quarter}: ${data['total']:>12.0f} (empty)")
            
            # Validation for completed fiscal years
            current_year = datetime.now().year
            is_current_fiscal_year = year >= current_year  # FY starts in Oct, so FY2025 starts Oct 2024
            
            print(f"\n📊 Summary:")
            print(f"  Available months: {len(available_months)} ({', '.join(available_months)})")
            print(f"  Missing months: {len(missing_months)} ({', '.join(missing_months)})")
            print(f"  Total agencies: {df['Agency'].nunique()}")
            print(f"  Total rows: {len(df):,}")
            
            # VALIDATION: Historical years should be complete (except October, which often has no data)
            critical_missing_months = [m for m in missing_months if m != 'Oct']
            if not is_current_fiscal_year and len(critical_missing_months) > 0:
                print(f"\n❌ VALIDATION FAILED:")
                print(f"  FY{year} is a completed fiscal year but is missing {len(critical_missing_months)} months:")
                print(f"  Missing: {', '.join(critical_missing_months)}")
                print(f"  This indicates incomplete or corrupted data.")
                return False
            elif not is_current_fiscal_year and 'Oct' in missing_months:
                print(f"\n⚠️ Note: October data missing (common - often no spending in first month)")
                # Don't return early - continue to TAFS validation
            elif is_current_fiscal_year and len(missing_months) > 0:
                print(f"\n⚠️ Current fiscal year - missing future months is expected:")
                print(f"  Missing: {', '.join(missing_months)}")
            
            # Save summary
            summary = {
                'fiscal_year': year,
                'is_current_year': is_current_fiscal_year,
                'available_months': available_months,
                'missing_months': missing_months,
                'quarter_mapping': FISCAL_QUARTERS,
                'quarter_data': {q: {'total': d['total'], 'has_data': d['has_data']} for q, d in quarter_data.items()},
                'total_agencies': int(df['Agency'].nunique()),
                'total_rows': int(len(df)),
                'processed_date': datetime.now().isoformat(),
                'data_file': f"sf133_{year}_master.csv",
                'validation_passed': is_current_fiscal_year or len([m for m in missing_months if m != 'Oct']) == 0
            }
            
            summary_path = self.site_data_dir / f"summary_{year}.json"
            with open(summary_path, 'w') as f:
                json.dump(summary, f, indent=2)
            
            # TAFS Coverage Validation
            print("🔍 DEBUG: About to run TAFS validation...")
            tafs_validation_passed, tafs_coverage = self._validate_tafs_coverage(df, year, baseline_tafs)
            print(f"🔍 DEBUG: TAFS validation completed, result: {tafs_validation_passed}")
            
            # Update summary with TAFS coverage
            summary['tafs_coverage'] = tafs_coverage
            summary['validation_passed'] = summary['validation_passed'] and tafs_validation_passed
            
            # Re-save summary with TAFS data
            with open(summary_path, 'w') as f:
                json.dump(summary, f, indent=2)
            
            print(f"📄 Summary saved to: {summary_path}")
            
            return summary['validation_passed']
            
        except Exception as e:
            print(f"⚠️ Analysis failed: {e}")
            return False
    
    def _load_baseline_tafs_data(self) -> dict:
        """Load baseline TAFS account data for comparison (always use FY2025 as benchmark)."""
        baseline = {'tafs_by_agency': {}, 'total_accounts': 0}
        
        # Always use FY2025 as the baseline for TAFS validation
        baseline_file = self.site_data_dir / 'sf133_2025_master.csv'
        baseline_year = 2025
        
        if not baseline_file.exists():
            print(f"⚠️ FY2025 baseline file not found: {baseline_file}")
            return baseline
        
        try:
            baseline_df = pd.read_csv(baseline_file, low_memory=False)
            
            # Extract unique TAFS accounts by agency
            if 'TAFS' in baseline_df.columns and 'Agency' in baseline_df.columns:
                tafs_by_agency = baseline_df.groupby('Agency')['TAFS'].nunique().to_dict()
                total_accounts = baseline_df['TAFS'].nunique()
                
                baseline = {
                    'tafs_by_agency': tafs_by_agency,
                    'total_accounts': total_accounts,
                    'baseline_year': baseline_year,
                    'baseline_file': baseline_file.name
                }
                
        except Exception as e:
            print(f"⚠️ Could not load baseline TAFS data: {e}")
        
        return baseline
    
    def _validate_tafs_coverage(self, df: pd.DataFrame, year: int, baseline_tafs: dict, min_coverage_pct: float = 80.0):
        """Validate that the year has adequate TAFS account coverage compared to baseline."""
        print(f"🔍 DEBUG: _validate_tafs_coverage called for year {year}")
        print(f"🔍 DEBUG: baseline_tafs has tafs_by_agency: {'tafs_by_agency' in baseline_tafs}")
        
        if not baseline_tafs or 'tafs_by_agency' not in baseline_tafs:
            print("⚠️ No baseline TAFS data available for comparison")
            return True, {}
        
        baseline_year = baseline_tafs.get('baseline_year', 'unknown')
        print(f"\n📊 TAFS ACCOUNT COVERAGE ANALYSIS (vs FY{baseline_year} baseline):")
        print("-" * 60)
        
        # Current year TAFS accounts by agency
        if 'TAFS' not in df.columns or 'Agency' not in df.columns:
            print("❌ Missing TAFS or Agency columns for validation")
            return False, {}
        
        current_tafs_by_agency = df.groupby('Agency')['TAFS'].nunique().to_dict()
        current_total = df['TAFS'].nunique()
        
        # Calculate coverage by agency
        agency_coverage = {}
        overall_issues = []
        
        print(f"{'Agency':<40} {'Baseline':<8} {'Current':<8} {'Coverage':<10} {'Status'}")
        print("-" * 80)
        
        for agency, baseline_count in baseline_tafs['tafs_by_agency'].items():
            current_count = current_tafs_by_agency.get(agency, 0)
            coverage_pct = (current_count / baseline_count * 100) if baseline_count > 0 else 0
            
            agency_coverage[agency] = {
                'baseline_accounts': baseline_count,
                'current_accounts': current_count,
                'coverage_percent': coverage_pct
            }
            
            status = "✅" if coverage_pct >= min_coverage_pct else "❌"
            if coverage_pct < min_coverage_pct:
                overall_issues.append(f"{agency}: {coverage_pct:.1f}%")
            
            print(f"{agency:<40} {baseline_count:<8} {current_count:<8} {coverage_pct:>6.1f}%    {status}")
        
        # Overall coverage
        baseline_total = baseline_tafs['total_accounts']
        overall_coverage_pct = (current_total / baseline_total * 100) if baseline_total > 0 else 0
        
        print("-" * 80)
        print(f"{'OVERALL':<40} {baseline_total:<8} {current_total:<8} {overall_coverage_pct:>6.1f}%")
        
        # Validation result
        validation_passed = len(overall_issues) == 0 and overall_coverage_pct >= min_coverage_pct
        
        if validation_passed:
            print(f"\n✅ TAFS Coverage Validation PASSED")
            print(f"   All agencies have ≥{min_coverage_pct}% account coverage")
        else:
            print(f"\n⚠️ TAFS Coverage Issues Detected:")
            if overall_coverage_pct < min_coverage_pct:
                print(f"   Overall coverage ({overall_coverage_pct:.1f}%) below threshold ({min_coverage_pct}%)")
            for issue in overall_issues:
                print(f"   {issue}")
        
        coverage_summary = {
            'validation_passed': validation_passed,
            'overall_coverage_percent': overall_coverage_pct,
            'baseline_total_accounts': baseline_total,
            'current_total_accounts': current_total,
            'agency_coverage': agency_coverage,
            'agencies_below_threshold': overall_issues,
            'threshold_percent': min_coverage_pct
        }
        
        return validation_passed, coverage_summary
    
    def process_complete_year(self, year: int, url: str = None, download: bool = True) -> bool:
        """Complete pipeline to download and process a full fiscal year."""
        print(f"🚀 SF133 YEAR PROCESSING PIPELINE")
        print(f"📅 Fiscal Year: {year}")
        print("=" * 60)
        
        # Step 1: Download data (if requested)
        if download:
            if not self.download_year_data(year, url):
                print("❌ Pipeline failed at download stage")
                return False
        
        # Step 2: Process year data
        output_path = self.process_year_data(year)
        if not output_path:
            print("❌ Pipeline failed at processing stage")
            return False
        
        print(f"\n🎉 PIPELINE COMPLETED SUCCESSFULLY!")
        print(f"✅ FY{year} data processed and ready")
        return True

def main():
    """Command line interface."""
    parser = argparse.ArgumentParser(description="SF133 Year-Based Processing System")
    parser.add_argument("--year", type=int, required=True, help="Fiscal year to process (e.g., 2024)")
    parser.add_argument("--url", help="MAX.gov URL for the fiscal year (optional if in config)")
    parser.add_argument("--no-download", action="store_true", help="Skip download, use existing data")
    
    args = parser.parse_args()
    
    processor = SF133YearProcessor()
    
    success = processor.process_complete_year(
        year=args.year,
        url=args.url,
        download=not args.no_download
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()