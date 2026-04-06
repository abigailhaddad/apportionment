#!/usr/bin/env python3
"""
SF133 Data Processing System - Main Entry Point
==============================================

Simple, automated system for processing complete fiscal years of SF133 data.

Usage:
    python main.py --year 2024                           # Process FY2024 (uses config URL)
    python main.py --year 2024 --url "https://..."      # Process FY2024 with custom URL  
    python main.py --serve                               # Start development server
    python main.py --help                               # Show all options

Processing Pipeline:
    1. Download ALL SF133 files for the fiscal year from MAX.gov
    2. Parse using Raw Data sheets (more reliable than TAFS)
    3. Auto-detect available months (skip empty ones)
    4. Generate complete year dataset

Config File (sf133_urls.json):
    {
      "sf133_urls": {
        "2024": "https://portal.max.gov/.../FY%202024%20...",
        "2025": "https://portal.max.gov/.../FY%202025%20..."
      }
    }

"""

import sys
import argparse
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from code.year_processor import SF133YearProcessor
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
    parser.add_argument("--year", type=int, nargs='+',
                       help="Fiscal year(s) to process (e.g., 2024, 2025, or 2022 2023 2024)")
    parser.add_argument("--url",
                       help="MAX.gov URL for the fiscal year (optional if in config)")
    parser.add_argument("--no-download", action="store_true",
                       help="Skip download, use existing data")
    
    args = parser.parse_args()
    
    if args.serve:
        # Start development server
        print("🌐 Starting SF133 development server...")
        serve_main()
    
    elif args.year:
        # Process fiscal year data (single or multiple years)
        processor = SF133YearProcessor()
        
        if len(args.year) == 1:
            # Single year
            print(f"🔍 DEBUG: About to call process_complete_year for {args.year[0]}")
            success = processor.process_complete_year(
                year=args.year[0],
                url=args.url,
                download=not args.no_download
            )
            print(f"🔍 DEBUG: process_complete_year returned: {success}")
            sys.exit(0 if success else 1)
        else:
            # Multiple years
            print(f"🔄 Processing {len(args.year)} fiscal years: {', '.join(map(str, args.year))}")
            
            successful_years = []
            failed_years = []
            
            for year in args.year:
                print(f"\n{'='*80}")
                success = processor.process_complete_year(
                    year=year,
                    url=None,  # Always use config for multi-year
                    download=not args.no_download
                )
                if not success:
                    failed_years.append(year)
                    print(f"⚠️ FY{year} processing failed - will be excluded from website")
                else:
                    successful_years.append(year)
                    print(f"✅ FY{year} processing completed")
            
            print(f"\n{'='*80}")
            print(f"📊 PROCESSING SUMMARY:")
            print(f"✅ Successfully processed: {len(successful_years)} years ({', '.join(map(str, successful_years))})")
            
            if failed_years:
                print(f"⚠️ Failed/excluded years: {len(failed_years)} years ({', '.join(map(str, failed_years))})")
                print(f"   These years will not appear on the website")
            
            # Always exit successfully if at least one year processed successfully
            if successful_years:
                print(f"🎉 Pipeline completed - {len(successful_years)} years ready for deployment!")
                sys.exit(0)
            else:
                print(f"❌ No years processed successfully")
                sys.exit(1)
    
    else:
        # Show help and available options
        parser.print_help()
        print("\n" + "="*60)
        print("🚀 SF133 DATA PROCESSING SYSTEM")
        print("="*60)
        print()
        print("Quick Start:")
        print("  python main.py --year 2024       # Process all FY2024 data")
        print("  python main.py --serve           # Start web server")
        print()
        print("Examples:")
        print('  python main.py --year 2024 --url "https://portal.max.gov/.../FY%202024%20..."')
        print("  python main.py --year 2025 --no-download  # Use existing files")
        print()
        print("Directory Structure:")
        print("  raw_data/2024/  - FY2024 Excel files")
        print("  raw_data/2025/  - FY2025 Excel files") 
        print("  site/data/      - Processed CSV and JSON files")
        print("  sf133_urls.json - Configuration file with MAX.gov URLs")

if __name__ == "__main__":
    main()