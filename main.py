#!/usr/bin/env python3
"""
SF133 Data Processing System - Main Entry Point
==============================================

Complete automated system for SF133 budget execution data processing.

Usage:
    python main.py --month august --year 2025       # Process specific month
    python main.py --test-only                      # Run tests on current data
    python main.py --serve                          # Start development server
    python main.py --help                           # Show all options

Processing Pipeline:
    1. Download SF133 files from MAX.gov
    2. Parse using Raw Data sheets (more reliable than TAFS)
    3. Run comprehensive data integrity tests
    4. Generate website data files
    5. Update website only if all tests pass

"""

import sys
import argparse
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from update_sf133_data import main as update_main
from code.serve import main as serve_main

def main():
    """Main entry point with routing to appropriate functionality."""
    
    parser = argparse.ArgumentParser(
        description="SF133 Data Processing System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument("--serve", action="store_true",
                       help="Start development web server")
    parser.add_argument("--month", 
                       help="Month to process (e.g., 'august', 'september')")
    parser.add_argument("--year", type=int, default=2025,
                       help="Year to process (default: 2025)")
    parser.add_argument("--no-download", action="store_true",
                       help="Skip download, use existing data")
    parser.add_argument("--test-only", action="store_true",
                       help="Only run tests on current data")
    parser.add_argument("--save-log", action="store_true",
                       help="Save detailed update log")
    
    args = parser.parse_args()
    
    if args.serve:
        # Start development server
        print("🌐 Starting SF133 development server...")
        serve_main()
    
    elif args.month or args.test_only:
        # Process data using the main update system
        sys.argv = ["update_sf133_data.py"]
        if args.month:
            sys.argv.extend(["--month", args.month])
        if args.year != 2025:
            sys.argv.extend(["--year", str(args.year)])
        if args.no_download:
            sys.argv.append("--no-download")
        if args.test_only:
            sys.argv.append("--test-only")
        if args.save_log:
            sys.argv.append("--save-log")
        
        update_main()
    
    else:
        # Show help and available options
        parser.print_help()
        print("\n" + "="*60)
        print("🚀 SF133 DATA PROCESSING SYSTEM")
        print("="*60)
        print()
        print("Quick Start:")
        print("  python main.py --month august    # Process August data")
        print("  python main.py --test-only       # Test current data")
        print("  python main.py --serve           # Start web server")
        print()
        print("Directory Structure:")
        print("  code/           - Processing modules (numbered by order)")
        print("  tests/          - Data integrity test suites")
        print("  raw_data/       - Downloaded SF133 Excel files")
        print("  site/           - Website files and processed data")
        print("  update_sf133_data.py - Main processing orchestrator")

if __name__ == "__main__":
    main()