#!/usr/bin/env python3
"""
Main orchestration script for Federal Agency Budget Obligation Analysis.
Run this to process all SF133 data from scratch.
"""

import sys
from pathlib import Path

def main():
    """Main pipeline for processing SF133 data."""
    print("Federal Agency Budget Obligation Analysis Pipeline")
    print("=" * 50)
    
    # Step 1: Download SF133 files from MAX.gov
    print("\nStep 1: Downloading SF133 files from MAX.gov...")
    from download_sf133_data import download_sf133_files
    success = download_sf133_files()
    if not success:
        print("ERROR: Failed to download SF133 files")
        sys.exit(1)
    
    # Step 2: Parse all SF133 files into master table
    print("\nStep 2: Parsing all SF133 files into master table...")
    from parse_sf133_files import parse_all_sf133_files
    master_file = parse_all_sf133_files()
    if not master_file:
        print("ERROR: Failed to parse SF133 files")
        sys.exit(1)
    
    # Step 3: Generate final summary from master table
    print("\nStep 3: Generating obligation summary...")
    from generate_summary import generate_obligation_summary
    summary_file = generate_obligation_summary(master_file)
    if not summary_file:
        print("ERROR: Failed to generate summary")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print(f"SUCCESS! Pipeline completed.")
    print(f"\nGenerated files:")
    print(f"  - Master table: {master_file}")
    print(f"  - Final summary: {summary_file}")
    print(f"  - JSON for web app: data/all_agencies_summary.json")
    print("\nTo view the data:")
    print("  1. Run: python3 serve.py")
    print("  2. Open: http://localhost:8000")

if __name__ == "__main__":
    main()