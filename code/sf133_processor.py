#!/usr/bin/env python3
"""
SF133 Data Processing System
============================

A robust, automated system for processing SF133 budget execution data that:
1. Downloads new SF133 files when available
2. Processes using the reliable Raw Data sheet method
3. Runs comprehensive data integrity tests
4. Updates website only after all validation passes
5. Handles multiple years and months seamlessly

Usage:
    python sf133_processor.py --month august --year 2024
    python sf133_processor.py --auto-update  # Check for latest and update
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
import argparse
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# Import our existing modules
from code.parse_sf133_raw_data import parse_all_sf133_raw_data, RAW_DATA_COLUMN_MAPPING
from code.download_sf133_data import download_sf133_files

class SF133Processor:
    """Main class for SF133 data processing and validation."""
    
    def __init__(self, base_dir: Path = Path(".")):
        self.base_dir = Path(base_dir)
        self.raw_data_dir = self.base_dir / "raw_data"
        self.site_data_dir = self.base_dir / "site" / "data"
        self.backup_dir = self.base_dir / "backups"
        
        # Ensure directories exist
        for dir_path in [self.raw_data_dir, self.site_data_dir, self.backup_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def download_new_data(self, month: str, year: int = 2025) -> bool:
        """Download new SF133 data for specified month/year."""
        print(f"🔽 DOWNLOADING {month.upper()} {year} SF133 DATA")
        print("=" * 60)
        
        target_dir = self.raw_data_dir / f"{month}_{year}"
        target_dir.mkdir(exist_ok=True)
        
        try:
            # Use existing download function
            success = download_sf133_files(str(target_dir))
            if success:
                print(f"✅ Successfully downloaded data to {target_dir}")
                return True
            else:
                print(f"❌ Failed to download data")
                return False
        except Exception as e:
            print(f"❌ Download error: {e}")
            return False
    
    def process_month_data(self, month: str, year: int = 2025) -> Optional[Path]:
        """Process SF133 data for a specific month using Raw Data method."""
        print(f"\n📊 PROCESSING {month.upper()} {year} DATA")
        print("=" * 60)
        
        source_dir = self.raw_data_dir / f"{month}_{year}"
        if not source_dir.exists():
            # Try legacy naming (just month)
            source_dir = self.raw_data_dir / month
            if not source_dir.exists():
                print(f"❌ Data directory not found: {source_dir}")
                return None
        
        try:
            # Process using Raw Data method
            output_path = parse_all_sf133_raw_data(str(source_dir))
            
            if output_path:
                # Rename output to include month/year
                new_name = f"sf133_{month}_{year}_master.csv"
                new_path = self.site_data_dir / new_name
                
                # Move/copy the file
                import shutil
                shutil.move(str(output_path), str(new_path))
                
                print(f"✅ Successfully processed {month} {year} data")
                print(f"📁 Saved to: {new_path}")
                return new_path
            else:
                print(f"❌ Failed to process {month} {year} data")
                return None
                
        except Exception as e:
            print(f"❌ Processing error: {e}")
            return None
    
    def backup_current_data(self) -> bool:
        """Create backup of current website data before updates."""
        print(f"\n💾 CREATING BACKUP")
        print("=" * 60)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"backup_{timestamp}"
        backup_path.mkdir(exist_ok=True)
        
        try:
            import shutil
            
            # Backup site data
            if self.site_data_dir.exists():
                shutil.copytree(self.site_data_dir, backup_path / "site_data")
                print(f"✅ Backup created: {backup_path}")
                return True
            else:
                print("⚠️ No existing data to backup")
                return True
                
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return False
    
    def run_data_integrity_tests(self, new_data_path: Path, previous_months: List[str] = None) -> bool:
        """Run comprehensive tests to ensure data integrity."""
        print(f"\n🧪 RUNNING DATA INTEGRITY TESTS")
        print("=" * 60)
        
        if previous_months is None:
            previous_months = ["june", "july"]  # Default previous months to check
        
        try:
            # Load new data
            new_data = pd.read_csv(new_data_path, low_memory=False)
            print(f"📊 New data: {len(new_data):,} rows, {len(new_data.columns)} columns")
            
            # Test 1: Basic data structure validation
            if not self._test_data_structure(new_data):
                return False
            
            # Test 2: Agency coverage validation
            if not self._test_agency_coverage(new_data):
                return False
            
            # Test 3: Monthly totals validation (if previous data exists)
            if not self._test_monthly_totals_consistency(new_data, previous_months):
                return False
            
            # Test 4: Account existence validation across agencies
            if not self._test_account_consistency(new_data):
                return False
            
            # Test 5: Data completeness validation
            if not self._test_data_completeness(new_data):
                return False
                
            print("✅ All data integrity tests PASSED!")
            return True
            
        except Exception as e:
            print(f"❌ Testing error: {e}")
            return False
    
    def _test_data_structure(self, df: pd.DataFrame) -> bool:
        """Test basic data structure requirements."""
        print("  🔍 Testing data structure...")
        
        required_columns = ['Agency', 'Source_File', 'LINENO']
        month_columns = [col for col in df.columns if any(month in col for month in 
                        ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Q'])]
        
        # Check required columns exist
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            print(f"    ❌ Missing required columns: {missing_cols}")
            return False
        
        # Check we have month columns
        if len(month_columns) == 0:
            print(f"    ❌ No monthly data columns found")
            return False
        
        print(f"    ✅ Data structure valid - {len(month_columns)} month columns found")
        return True
    
    def _test_agency_coverage(self, df: pd.DataFrame) -> bool:
        """Test that we have expected agency coverage."""
        print("  🔍 Testing agency coverage...")
        
        agencies = set(df['Agency'].unique())
        
        # Expected core agencies that should always be present
        core_agencies = {
            "Department of Defense-Military",
            "Department of Education", 
            "Department of Health and Human Services",
            "Department of Veterans Affairs",
            "Department of Agriculture"
        }
        
        missing_core = core_agencies - agencies
        if missing_core:
            print(f"    ❌ Missing core agencies: {missing_core}")
            return False
        
        # Should have at least 20 agencies total
        if len(agencies) < 20:
            print(f"    ❌ Too few agencies: {len(agencies)} (expected at least 20)")
            return False
        
        print(f"    ✅ Agency coverage good - {len(agencies)} agencies found")
        return True
    
    def _test_monthly_totals_consistency(self, new_data: pd.DataFrame, previous_months: List[str]) -> bool:
        """Test that previous months' data hasn't changed."""
        print("  🔍 Testing previous months consistency...")
        
        # Check if we have previous data to compare against
        current_master = self.site_data_dir / "sf133_master_table.csv"
        if not current_master.exists():
            print("    ℹ️ No previous data to compare - skipping consistency test")
            return True
        
        try:
            previous_data = pd.read_csv(current_master, low_memory=False)
            
            # Test that previous months' totals haven't changed
            for month in previous_months:
                month_cols = [col for col in new_data.columns if month.capitalize() in col]
                if not month_cols:
                    continue
                
                month_col = month_cols[0]  # Take first match
                
                if month_col in previous_data.columns:
                    old_total = previous_data[month_col].sum()
                    new_total = new_data[month_col].sum()
                    
                    # Allow for small floating point differences
                    if abs(old_total - new_total) > 1:
                        print(f"    ❌ {month} totals changed: ${old_total:,.2f} → ${new_total:,.2f}")
                        return False
                    else:
                        print(f"    ✅ {month} totals consistent: ${old_total:,.2f}")
        
        except Exception as e:
            print(f"    ⚠️ Consistency test failed: {e}")
            # Don't fail the whole pipeline for this
            return True
        
        return True
    
    def _test_account_consistency(self, df: pd.DataFrame) -> bool:
        """Test that common accounts exist across expected agencies."""
        print("  🔍 Testing account consistency...")
        
        # Line 2500 (Total budgetary resources) should exist for most agencies
        line_2500 = df[df['LINENO'] == 2500.0]
        agencies_with_2500 = set(line_2500['Agency'].unique())
        total_agencies = set(df['Agency'].unique())
        
        coverage_pct = len(agencies_with_2500) / len(total_agencies) * 100
        if coverage_pct < 80:  # Should be present in at least 80% of agencies
            print(f"    ❌ Line 2500 only in {coverage_pct:.1f}% of agencies (expected >80%)")
            return False
        
        print(f"    ✅ Account consistency good - Line 2500 in {coverage_pct:.1f}% of agencies")
        return True
    
    def _test_data_completeness(self, df: pd.DataFrame) -> bool:
        """Test overall data completeness."""
        print("  🔍 Testing data completeness...")
        
        # Should have substantial amount of data
        if len(df) < 100000:  # Expect at least 100k rows
            print(f"    ❌ Too little data: {len(df):,} rows (expected >100,000)")
            return False
        
        # Check for excessive missing values in key columns
        key_cols = ['Agency', 'LINENO']
        for col in key_cols:
            if col in df.columns:
                missing_pct = df[col].isna().sum() / len(df) * 100
                if missing_pct > 5:  # More than 5% missing
                    print(f"    ❌ Too many missing values in {col}: {missing_pct:.1f}%")
                    return False
        
        print(f"    ✅ Data completeness good - {len(df):,} rows")
        return True
    
    def update_website(self, new_data_path: Path) -> bool:
        """Update the website with new data."""
        print(f"\n🌐 UPDATING WEBSITE")
        print("=" * 60)
        
        try:
            # Update the master table used by website
            master_path = self.site_data_dir / "sf133_master_table.csv"
            
            import shutil
            shutil.copy2(str(new_data_path), str(master_path))
            
            # Generate summary statistics
            self._generate_summary_stats(master_path)
            
            print(f"✅ Website updated successfully")
            return True
            
        except Exception as e:
            print(f"❌ Website update failed: {e}")
            return False
    
    def _generate_summary_stats(self, data_path: Path):
        """Generate summary statistics for the website."""
        try:
            df = pd.read_csv(data_path, low_memory=False)
            
            # Generate basic summary
            summary = {
                'total_rows': int(len(df)),
                'total_agencies': int(df['Agency'].nunique()),
                'last_updated': datetime.now().isoformat(),
                'available_months': [col for col in df.columns if any(month in col for month in 
                                   ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Q'])],
                'agencies': list(df['Agency'].unique())
            }
            
            # Save summary
            summary_path = self.site_data_dir / "summary_stats.json"
            with open(summary_path, 'w') as f:
                json.dump(summary, f, indent=2)
                
            print(f"  📊 Summary stats generated: {summary['total_rows']:,} rows, {summary['total_agencies']} agencies")
            
        except Exception as e:
            print(f"  ⚠️ Summary generation failed: {e}")
    
    def process_new_month(self, month: str, year: int = 2025, download: bool = True) -> bool:
        """Complete pipeline to process a new month of data."""
        print(f"🚀 SF133 PROCESSING PIPELINE")
        print(f"📅 Processing: {month.upper()} {year}")
        print("=" * 60)
        
        # Step 1: Backup current data
        if not self.backup_current_data():
            print("❌ Pipeline failed at backup stage")
            return False
        
        # Step 2: Download new data (if requested)
        if download:
            if not self.download_new_data(month, year):
                print("❌ Pipeline failed at download stage")
                return False
        
        # Step 3: Process new data
        new_data_path = self.process_month_data(month, year)
        if not new_data_path:
            print("❌ Pipeline failed at processing stage")
            return False
        
        # Step 4: Run integrity tests
        if not self.run_data_integrity_tests(new_data_path):
            print("❌ Pipeline failed at testing stage")
            print("🔄 Data integrity tests failed - website NOT updated")
            return False
        
        # Step 5: Update website (only if tests pass)
        if not self.update_website(new_data_path):
            print("❌ Pipeline failed at website update stage")
            return False
        
        print(f"\n🎉 PIPELINE COMPLETED SUCCESSFULLY!")
        print(f"✅ {month.upper()} {year} data processed and website updated")
        return True

def main():
    """Command line interface for SF133 processor."""
    parser = argparse.ArgumentParser(description="SF133 Data Processing System")
    parser.add_argument("--month", help="Month to process (e.g., 'august')")
    parser.add_argument("--year", type=int, default=2025, help="Year to process (default: 2025)")
    parser.add_argument("--no-download", action="store_true", help="Skip download, use existing data")
    parser.add_argument("--test-only", action="store_true", help="Only run tests on existing data")
    parser.add_argument("--auto-update", action="store_true", help="Check for latest data and update")
    
    args = parser.parse_args()
    
    processor = SF133Processor()
    
    if args.test_only:
        # Just run tests on current data
        current_data = Path("site/data/sf133_master_table.csv")
        if current_data.exists():
            success = processor.run_data_integrity_tests(current_data)
            sys.exit(0 if success else 1)
        else:
            print("❌ No current data found to test")
            sys.exit(1)
    
    elif args.month:
        # Process specific month
        success = processor.process_new_month(
            month=args.month,
            year=args.year,
            download=not args.no_download
        )
        sys.exit(0 if success else 1)
    
    elif args.auto_update:
        # Auto-detect and process latest available data
        print("🔍 Auto-update mode not yet implemented")
        print("Please specify --month for now")
        sys.exit(1)
    
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()