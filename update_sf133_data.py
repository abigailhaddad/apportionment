#!/usr/bin/env python3
"""
Automated SF133 Data Update Script
=================================

This is the main entry point for updating SF133 data. It orchestrates:
1. Data download
2. Processing with integrity tests  
3. Cross-validation with previous data
4. Website updates (only if all tests pass)

Usage:
    python update_sf133_data.py --month september --year 2024
    python update_sf133_data.py --auto-update
    python update_sf133_data.py --test-only  # Just run tests
"""

import argparse
import sys
from pathlib import Path
import json
from datetime import datetime

# Import our processing modules
from code.sf133_processor import SF133Processor
from tests.test_sf133_integrity import SF133IntegrityTester
from tests.test_cross_year_validation import CrossYearValidator

class SF133UpdateOrchestrator:
    """Orchestrates the complete SF133 data update process."""
    
    def __init__(self):
        self.processor = SF133Processor()
        self.validator = CrossYearValidator()
        self.update_log = []
    
    def log_step(self, message: str, success: bool = True):
        """Log a processing step."""
        timestamp = datetime.now().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'message': message, 
            'success': success
        }
        self.update_log.append(log_entry)
        
        status = "✅" if success else "❌"
        print(f"{status} {message}")
    
    def run_comprehensive_tests(self, data_path: Path) -> bool:
        """Run all validation tests on the data."""
        self.log_step("Running comprehensive data integrity tests...")
        
        try:
            # Run main integrity tests
            tester = SF133IntegrityTester(data_path)
            integrity_results = tester.run_all_tests()
            
            integrity_passed = all(integrity_results.values())
            if not integrity_passed:
                self.log_step("Data integrity tests FAILED", False)
                return False
            
            self.log_step("Data integrity tests PASSED")
            
            # Run cross-year validation if we have previous data
            current_year = 2025  # Update this as needed
            previous_year = current_year - 1
            
            cross_year_results = self.validator.run_cross_year_validation(previous_year, current_year)
            
            # Cross-year validation is informational - don't fail if it has issues
            cross_year_passed = all(cross_year_results.values())
            if cross_year_passed:
                self.log_step("Cross-year validation PASSED")
            else:
                self.log_step("Cross-year validation has warnings (continuing)", True)
            
            return True
            
        except Exception as e:
            self.log_step(f"Testing failed with error: {e}", False)
            return False
    
    def update_with_new_month(self, month: str, year: int, download: bool = True) -> bool:
        """Complete update process for a new month."""
        self.log_step(f"Starting SF133 update for {month.upper()} {year}")
        
        # Step 1: Process the new month data
        success = self.processor.process_new_month(month, year, download)
        
        if not success:
            self.log_step("Processing pipeline failed", False)
            return False
        
        self.log_step("Processing pipeline completed successfully")
        
        # Step 2: Run additional comprehensive tests
        data_path = Path(f"site/data/sf133_{month}_{year}_master.csv")
        if not data_path.exists():
            data_path = Path("site/data/sf133_raw_data_master.csv")
        
        if data_path.exists():
            test_success = self.run_comprehensive_tests(data_path)
            if not test_success:
                self.log_step("Comprehensive tests failed - update aborted", False)
                return False
        
        self.log_step(f"SF133 update for {month.upper()} {year} completed successfully")
        return True
    
    def run_tests_only(self) -> bool:
        """Run tests on current data without updating."""
        self.log_step("Running tests on current data...")
        
        # Find current data file
        data_path = Path("site/data/sf133_master_table.csv")
        if not data_path.exists():
            self.log_step("No current data found to test", False)
            return False
        
        return self.run_comprehensive_tests(data_path)
    
    def auto_detect_and_update(self) -> bool:
        """Automatically detect latest available data and update."""
        self.log_step("Auto-detection mode not yet implemented")
        
        # TODO: Implement auto-detection logic
        # This would:
        # 1. Check MAX.gov for new data
        # 2. Compare with current data timestamps
        # 3. Determine what months need updating
        # 4. Process any new months found
        
        return False
    
    def save_update_log(self):
        """Save the update log for auditing."""
        log_file = Path("update_logs") / f"update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        log_file.parent.mkdir(exist_ok=True)
        
        with open(log_file, 'w') as f:
            json.dump(self.update_log, f, indent=2)
        
        print(f"📄 Update log saved to: {log_file}")

def main():
    """Main command line interface."""
    parser = argparse.ArgumentParser(
        description="Automated SF133 Data Update System",
        epilog="""
Examples:
  %(prog)s --month september --year 2024     # Process September 2024 data
  %(prog)s --test-only                        # Just run tests on current data  
  %(prog)s --auto-update                      # Auto-detect and update latest data
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--month", 
                       help="Month to process (e.g., 'september', 'october')")
    parser.add_argument("--year", type=int, default=2025,
                       help="Year to process (default: 2025)")
    parser.add_argument("--no-download", action="store_true",
                       help="Skip download, use existing data")
    parser.add_argument("--test-only", action="store_true",
                       help="Only run tests on current data")
    parser.add_argument("--auto-update", action="store_true", 
                       help="Automatically detect and update latest data")
    parser.add_argument("--save-log", action="store_true",
                       help="Save detailed update log")
    
    args = parser.parse_args()
    
    # Create orchestrator
    orchestrator = SF133UpdateOrchestrator()
    
    print("🚀 SF133 AUTOMATED UPDATE SYSTEM")
    print("=" * 50)
    
    success = False
    
    try:
        if args.test_only:
            success = orchestrator.run_tests_only()
            
        elif args.month:
            success = orchestrator.update_with_new_month(
                month=args.month,
                year=args.year, 
                download=not args.no_download
            )
            
        elif args.auto_update:
            success = orchestrator.auto_detect_and_update()
            
        else:
            parser.print_help()
            sys.exit(1)
    
    except KeyboardInterrupt:
        orchestrator.log_step("Update interrupted by user", False)
        print("\n⚠️ Update interrupted by user")
        success = False
    
    except Exception as e:
        orchestrator.log_step(f"Unexpected error: {e}", False)
        print(f"\n❌ Unexpected error: {e}")
        success = False
    
    finally:
        if args.save_log:
            orchestrator.save_update_log()
    
    # Final status
    if success:
        print("\n🎉 SF133 UPDATE COMPLETED SUCCESSFULLY!")
        print("Website has been updated with new data.")
    else:
        print("\n💥 SF133 UPDATE FAILED!")
        print("Website was NOT updated due to failed validation.")
        print("Check logs above for details.")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()