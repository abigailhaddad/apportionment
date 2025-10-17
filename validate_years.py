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
    
    import os
    
    # Detect if running in GitHub Actions
    is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
    mode = "VALIDATION-ONLY" if is_github_actions else "LOCAL CLEANUP"
    
    print("🔍 YEAR-BASED VALIDATION COORDINATOR")
    print("=" * 60)
    print(f"Mode: {mode}")
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
        structure_result = test_csv_structure()
        structure_passing_years = structure_result['passing_years']
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
        print("❌ VALIDATION FAILED: No years pass both test suites!")
        if is_github_actions:
            print("GitHub Actions will fail - fix data issues before deploying.")
        else:
            print("Fix data issues before deploying.")
        return 1
    else:
        if is_github_actions:
            print(f"✅ VALIDATION PASSED: {len(passing_both_sorted)} years ready for production")
            print(f"Validated years: {passing_both_sorted}")
            print("GitHub Actions will proceed with deployment.")
        else:
            print(f"✅ LOCAL VALIDATION: {len(passing_both_sorted)} years pass validation")
            print(f"Years to keep: {passing_both_sorted}")
        
        # Create a file listing the approved years for deployment scripts
        approved_years_file = Path('site/data/approved_years.json')
        with open(approved_years_file, 'w') as f:
            json.dump({
                'approved_years': passing_both_sorted,
                'completeness_passing': completeness_passing_years,
                'structure_passing': structure_passing_years
            }, f, indent=2)
        print(f"📄 Approved years list saved to: {approved_years_file}")
        
        if is_github_actions:
            # In GitHub Actions, just validate - don't modify files
            print()
            print("🔒 GITHUB ACTIONS MODE: Validation complete, no file modifications")
            print("=" * 60)
            print("✅ All tests passed - GitHub Actions will proceed with deployment")
            return 0
        
        # LOCAL MODE: Clean up non-passing years and regenerate monthly data
        print()
        print("🧹 LOCAL MODE: Cleaning up non-passing years and regenerating data")
        print("=" * 60)
        
        # Clean up data files for non-passing years only
        site_data_dir = Path('site/data')
        
        # Get all years that have any data files
        all_data_years = set()
        for pattern in ['all_agencies_obligation_summary_*.csv', 'all_agencies_summary_*.json', 'all_agencies_monthly_summary_*.csv']:
            for file in site_data_dir.glob(pattern):
                # Extract year from various filename patterns
                filename = file.name
                if '_summary_' in filename and filename.endswith('.json'):
                    year_str = filename.replace('all_agencies_summary_', '').replace('.json', '')
                elif 'obligation_summary_' in filename and filename.endswith('.csv'):
                    year_str = filename.replace('all_agencies_obligation_summary_', '').replace('.csv', '')
                elif 'monthly_summary_' in filename and filename.endswith('.csv'):
                    parts = filename.replace('all_agencies_monthly_summary_', '').replace('.csv', '').split('_')
                    year_str = parts[0]
                else:
                    continue
                    
                if year_str.isdigit():
                    all_data_years.add(int(year_str))
        
        # Find years to remove (years that have data but don't pass validation)
        years_to_remove = all_data_years - set(passing_both_sorted)
        
        if years_to_remove:
            print(f"🧹 Removing data for {len(years_to_remove)} non-passing years: {sorted(years_to_remove)}")
            
            # Remove year-specific CSV files
            for year in years_to_remove:
                csv_file = site_data_dir / f'all_agencies_obligation_summary_{year}.csv'
                if csv_file.exists():
                    csv_file.unlink()
                    print(f"  Removed: {csv_file.name}")
            
            # Remove year-specific JSON files
            for year in years_to_remove:
                json_file = site_data_dir / f'all_agencies_summary_{year}.json'
                if json_file.exists():
                    json_file.unlink()
                    print(f"  Removed: {json_file.name}")
            
            # Remove monthly files for non-passing years
            monthly_files = list(site_data_dir.glob('all_agencies_monthly_summary_*.csv'))
            for file in monthly_files:
                filename = file.name
                parts = filename.replace('all_agencies_monthly_summary_', '').replace('.csv', '').split('_')
                if parts and parts[0].isdigit():
                    year = int(parts[0])
                    if year in years_to_remove:
                        file.unlink()
                        print(f"  Removed: {file.name}")
        else:
            print("✅ No non-passing years to clean up")
        
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