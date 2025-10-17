#!/usr/bin/env python3
"""
Year-based validation coordinator.
Runs both test suites and deploys only years that pass both sets of tests.
Generates monthly data ONLY for approved years.
"""

import sys
import json
from pathlib import Path

# Import the test functions
from run_tests import test_year_data_completeness
from test_website_data_structure import test_csv_structure
from create_monthly_summaries import create_monthly_summaries
from create_year_summaries import create_year_summary

def main():
    """Run both test suites and find years that pass both."""
    
    print("🔍 YEAR-BASED VALIDATION COORDINATOR")
    print("=" * 60)
    print("Running both test suites to find years that pass all validations...")
    print()
    
    # Run the first test suite (data completeness)
    print("📊 RUNNING DATA COMPLETENESS TESTS")
    print("-" * 40)
    try:
        completeness_passing_years = test_year_data_completeness()
        if not isinstance(completeness_passing_years, list):
            print("❌ ERROR: Completeness test didn't return year list")
            return 1
    except Exception as e:
        print(f"❌ ERROR: Completeness tests failed: {e}")
        return 1
    
    print()
    
    # Run the second test suite (structure validation)  
    print("🏗️  RUNNING STRUCTURE VALIDATION TESTS")
    print("-" * 40)
    try:
        structure_passing_years = test_csv_structure()
        if not isinstance(structure_passing_years, list):
            print("❌ ERROR: Structure test didn't return year list")
            return 1
    except Exception as e:
        print(f"❌ ERROR: Structure tests failed: {e}")
        return 1
    
    print()
    
    # Find intersection (years that pass both tests)
    passing_both = set(completeness_passing_years) & set(structure_passing_years)
    passing_both_sorted = sorted(list(passing_both))
    
    print("=" * 60)
    print("📋 VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Years passing completeness tests: {completeness_passing_years}")
    print(f"Years passing structure tests:    {structure_passing_years}")
    print(f"Years passing BOTH tests:        {passing_both_sorted}")
    print()
    
    if len(passing_both_sorted) == 0:
        print("❌ DEPLOYMENT BLOCKED: No years pass both test suites!")
        print("Fix data issues before deploying.")
        return 1
    else:
        print(f"✅ DEPLOYMENT APPROVED: {len(passing_both_sorted)} years ready for production")
        print(f"Deploying years: {passing_both_sorted}")
        
        # Create a file listing the approved years for deployment scripts
        approved_years_file = Path('site/data/approved_years.json')
        with open(approved_years_file, 'w') as f:
            json.dump({
                'approved_years': passing_both_sorted,
                'completeness_passing': completeness_passing_years,
                'structure_passing': structure_passing_years
            }, f, indent=2)
        print(f"📄 Approved years list saved to: {approved_years_file}")
        
        # Generate monthly data ONLY for approved years
        print()
        print("🗓️  GENERATING MONTHLY DATA FOR APPROVED YEARS")
        print("=" * 60)
        
        # Clean up any existing data files to ensure we only have approved data
        site_data_dir = Path('site/data')
        
        # Clean up monthly CSV files
        existing_monthly_files = list(site_data_dir.glob('all_agencies_monthly_summary_*.csv'))
        if existing_monthly_files:
            print(f"🧹 Cleaning up {len(existing_monthly_files)} existing monthly CSV files...")
            for file in existing_monthly_files:
                file.unlink()
                print(f"  Removed: {file.name}")
        
        # Clean up year-specific JSON summary files
        existing_json_files = list(site_data_dir.glob('all_agencies_summary_*.json'))
        # Keep the main summary file (all_agencies_summary.json) but remove year-specific ones
        year_specific_json = [f for f in existing_json_files if f.name != 'all_agencies_summary.json']
        if year_specific_json:
            print(f"🧹 Cleaning up {len(year_specific_json)} existing year-specific JSON files...")
            for file in year_specific_json:
                file.unlink()
                print(f"  Removed: {file.name}")
        
        # Clean up year-specific CSV obligation summary files
        existing_obligation_files = list(site_data_dir.glob('all_agencies_obligation_summary_*.csv'))
        if existing_obligation_files:
            print(f"🧹 Cleaning up {len(existing_obligation_files)} existing obligation summary files...")
            for file in existing_obligation_files:
                file.unlink()
                print(f"  Removed: {file.name}")
        
        successful_monthly_years = []
        total_monthly_files = 0
        
        for year in passing_both_sorted:
            print(f"\n--- Generating monthly data for FY{year} ---")
            
            # Check if master file exists for this year
            master_file = site_data_dir / f'sf133_{year}_master.csv'
            if not master_file.exists():
                print(f"⚠️  WARNING: No master file found for FY{year}: {master_file}")
                print(f"   Skipping monthly data generation for FY{year}")
                continue
            
            try:
                output_files = create_monthly_summaries(master_file, year)
                if output_files:
                    successful_monthly_years.append(year)
                    total_monthly_files += len(output_files)
                    print(f"✅ Generated {len(output_files)} monthly files for FY{year}")
                else:
                    print(f"⚠️  No monthly data generated for FY{year}")
            except Exception as e:
                print(f"❌ ERROR generating monthly data for FY{year}: {e}")
                continue
        
        print()
        print("=" * 60)
        print("📊 MONTHLY DATA GENERATION SUMMARY")
        print("=" * 60)
        print(f"Years with monthly data: {successful_monthly_years}")
        print(f"Total monthly files generated: {total_monthly_files}")
        
        if successful_monthly_years:
            print("✅ Monthly data generation completed successfully!")
            
            # Generate year summaries for successful years
            print()
            print("📋 GENERATING YEAR SUMMARIES FOR APPROVED YEARS")
            print("=" * 60)
            
            successful_year_summaries = []
            for year in successful_monthly_years:
                print(f"\n--- Generating year summary for FY{year} ---")
                master_file = site_data_dir / f'sf133_{year}_master.csv'
                
                try:
                    create_year_summary(master_file, year)
                    successful_year_summaries.append(year)
                    print(f"✅ Generated year summary for FY{year}")
                except Exception as e:
                    print(f"❌ ERROR generating year summary for FY{year}: {e}")
                    continue
            
            print()
            print("=" * 60)
            print("📊 YEAR SUMMARY GENERATION SUMMARY")
            print("=" * 60)
            print(f"Years with summaries: {successful_year_summaries}")
            print(f"Total year summaries generated: {len(successful_year_summaries)}")
            
            if successful_year_summaries:
                print("✅ Year summary generation completed successfully!")
            else:
                print("⚠️  No year summaries were generated")
                
        else:
            print("⚠️  No monthly data was generated (may be due to missing master files)")
        
        return 0

if __name__ == "__main__":
    sys.exit(main())