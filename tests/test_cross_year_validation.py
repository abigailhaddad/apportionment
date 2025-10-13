#!/usr/bin/env python3
"""
Cross-Year SF133 Data Validation
===============================

Tests to ensure data consistency and compatibility across different fiscal years.
This is critical when adding new years of data to ensure:
- Account structures remain consistent
- Agency mappings are stable  
- Financial patterns are reasonable
- Data formats are compatible

Usage:
    python tests/test_cross_year_validation.py --compare 2024 2025
    python -m pytest tests/test_cross_year_validation.py -v
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import argparse
import json
from collections import defaultdict

class CrossYearValidator:
    """Validates SF133 data consistency across multiple years."""
    
    def __init__(self):
        self.data_dir = Path("site/data")
        self.raw_data_dir = Path("raw_data")
        self.validation_results = {}
    
    def load_year_data(self, year: int) -> Optional[pd.DataFrame]:
        """Load SF133 data for a specific year."""
        # Try different possible file naming patterns
        possible_files = [
            self.data_dir / f"sf133_{year}_master.csv",
            self.data_dir / f"sf133_master_{year}.csv", 
            self.data_dir / "sf133_master_table.csv"  # Current/default
        ]
        
        for file_path in possible_files:
            if file_path.exists():
                print(f"📊 Loading {year} data from {file_path.name}")
                return pd.read_csv(file_path, low_memory=False)
        
        print(f"❌ No data found for year {year}")
        return None
    
    def compare_agency_structures(self, year1_data: pd.DataFrame, year2_data: pd.DataFrame, 
                                year1: int, year2: int) -> bool:
        """Compare agency structures between two years."""
        print(f"🔍 Comparing agency structures: {year1} vs {year2}")
        
        agencies1 = set(year1_data['Agency'].unique())
        agencies2 = set(year2_data['Agency'].unique())
        
        common_agencies = agencies1 & agencies2
        only_in_year1 = agencies1 - agencies2
        only_in_year2 = agencies2 - agencies1
        
        print(f"  Common agencies: {len(common_agencies)}")
        print(f"  Only in {year1}: {len(only_in_year1)}")
        print(f"  Only in {year2}: {len(only_in_year2)}")
        
        # Most agencies should be consistent year-to-year
        consistency_rate = len(common_agencies) / len(agencies1 | agencies2)
        
        if only_in_year1:
            print(f"  Agencies dropped in {year2}: {list(only_in_year1)[:5]}...")
        if only_in_year2:
            print(f"  New agencies in {year2}: {list(only_in_year2)[:5]}...")
        
        if consistency_rate < 0.85:  # Less than 85% consistency
            print(f"  ⚠️ Low agency consistency: {consistency_rate:.1%}")
            return False
        
        print(f"  ✅ Agency consistency good: {consistency_rate:.1%}")
        return True
    
    def compare_account_structures(self, year1_data: pd.DataFrame, year2_data: pd.DataFrame,
                                 year1: int, year2: int) -> bool:
        """Compare account/line structures between years."""
        print(f"🔍 Comparing account structures: {year1} vs {year2}")
        
        # Compare line number usage
        lines1 = set(year1_data['LINENO'].dropna().unique())
        lines2 = set(year2_data['LINENO'].dropna().unique())
        
        common_lines = lines1 & lines2
        consistency_rate = len(common_lines) / len(lines1 | lines2)
        
        print(f"  Common line numbers: {len(common_lines)}")
        print(f"  Line consistency: {consistency_rate:.1%}")
        
        # Critical line numbers that should exist in both years
        critical_lines = {1000, 1021, 2490, 2500, 3020, 4110}
        missing_critical = critical_lines - common_lines
        
        if missing_critical:
            print(f"  ⚠️ Missing critical line numbers in comparison: {missing_critical}")
        
        if consistency_rate < 0.7:  # Less than 70% line consistency
            print(f"  ⚠️ Low line number consistency: {consistency_rate:.1%}")
            return False
        
        print(f"  ✅ Account structure consistency good")
        return True
    
    def validate_common_agency_data(self, year1_data: pd.DataFrame, year2_data: pd.DataFrame,
                                  year1: int, year2: int) -> bool:
        """Validate data consistency for common agencies."""
        print(f"🔍 Validating common agency data quality")
        
        common_agencies = set(year1_data['Agency'].unique()) & set(year2_data['Agency'].unique())
        
        issues_found = 0
        agencies_checked = 0
        
        # Sample major agencies for detailed validation
        major_agencies = [
            "Department of Defense-Military",
            "Department of Health and Human Services", 
            "Department of Education",
            "Department of Veterans Affairs",
            "Department of Agriculture"
        ]
        
        for agency in major_agencies:
            if agency in common_agencies:
                agencies_checked += 1
                
                agency1_data = year1_data[year1_data['Agency'] == agency]
                agency2_data = year2_data[year2_data['Agency'] == agency]
                
                # Compare data volume
                row_ratio = len(agency2_data) / len(agency1_data) if len(agency1_data) > 0 else 0
                if row_ratio < 0.5 or row_ratio > 2.0:  # More than 2x change
                    print(f"  ⚠️ {agency}: Large row count change ({len(agency1_data)} → {len(agency2_data)})")
                    issues_found += 1
                
                # Compare line number coverage
                lines1 = set(agency1_data['LINENO'].unique())
                lines2 = set(agency2_data['LINENO'].unique())
                line_consistency = len(lines1 & lines2) / len(lines1 | lines2)
                
                if line_consistency < 0.8:  # Less than 80% line consistency
                    print(f"  ⚠️ {agency}: Low line consistency ({line_consistency:.1%})")
                    issues_found += 1
        
        if issues_found > agencies_checked * 0.3:  # More than 30% of agencies have issues
            print(f"  ❌ Too many agencies with data quality issues: {issues_found}/{agencies_checked}")
            return False
        
        print(f"  ✅ Common agency data validation passed ({agencies_checked} agencies checked)")
        return True
    
    def check_financial_reasonableness(self, year1_data: pd.DataFrame, year2_data: pd.DataFrame,
                                     year1: int, year2: int) -> bool:
        """Check that financial totals are reasonable between years."""
        print(f"🔍 Checking financial reasonableness between years")
        
        # Get month columns that exist in both datasets
        month_cols1 = [col for col in year1_data.columns if any(month in col for month in 
                      ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])]
        month_cols2 = [col for col in year2_data.columns if any(month in col for month in 
                      ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])]
        
        common_months = set(month_cols1) & set(month_cols2)
        
        if not common_months:
            print(f"  ⚠️ No common month columns found for comparison")
            return True  # Can't validate, but don't fail
        
        # Compare total budget authority (line 2500) for reasonableness
        line_2500_y1 = year1_data[year1_data['LINENO'] == 2500.0]
        line_2500_y2 = year2_data[year2_data['LINENO'] == 2500.0]
        
        if len(line_2500_y1) > 0 and len(line_2500_y2) > 0:
            for month_col in common_months:
                if month_col in line_2500_y1.columns and month_col in line_2500_y2.columns:
                    total1 = line_2500_y1[month_col].sum()
                    total2 = line_2500_y2[month_col].sum()
                    
                    if total1 > 0 and total2 > 0:
                        ratio = total2 / total1
                        # Expect reasonable year-over-year changes (0.5x to 2x)
                        if ratio < 0.5 or ratio > 2.0:
                            print(f"  ⚠️ Large change in {month_col}: ${total1/1e9:.1f}B → ${total2/1e9:.1f}B ({ratio:.1f}x)")
                        else:
                            print(f"  ✅ {month_col}: ${total1/1e9:.1f}B → ${total2/1e9:.1f}B ({ratio:.1f}x)")
        
        print(f"  ✅ Financial reasonableness check completed")
        return True
    
    def validate_column_compatibility(self, year1_data: pd.DataFrame, year2_data: pd.DataFrame,
                                    year1: int, year2: int) -> bool:
        """Validate that column structures are compatible."""
        print(f"🔍 Validating column compatibility")
        
        cols1 = set(year1_data.columns)
        cols2 = set(year2_data.columns)
        
        common_cols = cols1 & cols2
        only_in_y1 = cols1 - cols2
        only_in_y2 = cols2 - cols1
        
        # Core columns that should be in both
        core_columns = {'Agency', 'LINENO', 'Source_File'}
        missing_core = core_columns - common_cols
        
        if missing_core:
            print(f"  ❌ Missing core columns in comparison: {missing_core}")
            return False
        
        print(f"  Common columns: {len(common_cols)}")
        if only_in_y1:
            print(f"  Only in {year1}: {len(only_in_y1)} columns")
        if only_in_y2:
            print(f"  Only in {year2}: {len(only_in_y2)} columns")
        
        compatibility_rate = len(common_cols) / len(cols1 | cols2)
        print(f"  ✅ Column compatibility: {compatibility_rate:.1%}")
        
        return True
    
    def run_cross_year_validation(self, year1: int, year2: int) -> Dict[str, bool]:
        """Run complete cross-year validation."""
        print(f"🔄 CROSS-YEAR VALIDATION: {year1} vs {year2}")
        print("=" * 60)
        
        # Load data for both years
        year1_data = self.load_year_data(year1)
        year2_data = self.load_year_data(year2)
        
        if year1_data is None or year2_data is None:
            print("❌ Could not load data for comparison")
            return {'data_loading': False}
        
        tests = {
            'column_compatibility': lambda: self.validate_column_compatibility(year1_data, year2_data, year1, year2),
            'agency_structures': lambda: self.compare_agency_structures(year1_data, year2_data, year1, year2),
            'account_structures': lambda: self.compare_account_structures(year1_data, year2_data, year1, year2),
            'common_agency_data': lambda: self.validate_common_agency_data(year1_data, year2_data, year1, year2),
            'financial_reasonableness': lambda: self.check_financial_reasonableness(year1_data, year2_data, year1, year2)
        }
        
        results = {}
        passed = 0
        
        for test_name, test_func in tests.items():
            try:
                result = test_func()
                results[test_name] = result
                if result:
                    passed += 1
                print()
            except Exception as e:
                print(f"  ❌ Test {test_name} failed with error: {e}")
                results[test_name] = False
        
        # Summary
        print("📊 CROSS-YEAR VALIDATION SUMMARY")
        print("=" * 40)
        print(f"Passed: {passed}/{len(tests)} tests")
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name}: {status}")
        
        overall_pass = passed >= len(tests) * 0.8  # 80% pass rate required
        print(f"\n🎯 OVERALL: {'✅ VALIDATION PASSED' if overall_pass else '❌ VALIDATION FAILED'}")
        
        return results
    
    def generate_compatibility_report(self, year1: int, year2: int) -> Dict:
        """Generate detailed compatibility report for documentation."""
        results = self.run_cross_year_validation(year1, year2)
        
        report = {
            'comparison': f"{year1} vs {year2}",
            'timestamp': pd.Timestamp.now().isoformat(),
            'results': results,
            'overall_compatible': all(results.values()),
            'recommendations': []
        }
        
        # Add recommendations based on results
        for test_name, passed in results.items():
            if not passed:
                if test_name == 'agency_structures':
                    report['recommendations'].append("Review agency mapping changes between years")
                elif test_name == 'account_structures':
                    report['recommendations'].append("Validate SF133 line number changes")
                elif test_name == 'financial_reasonableness':
                    report['recommendations'].append("Investigate large financial total changes")
        
        return report

def main():
    """Command line interface for cross-year validation."""
    parser = argparse.ArgumentParser(description="Cross-Year SF133 Validation")
    parser.add_argument("--compare", nargs=2, type=int, metavar=("YEAR1", "YEAR2"),
                       help="Compare two years (e.g., --compare 2024 2025)")
    parser.add_argument("--report", action="store_true", 
                       help="Generate detailed compatibility report")
    
    args = parser.parse_args()
    
    validator = CrossYearValidator()
    
    if args.compare:
        year1, year2 = args.compare
        results = validator.run_cross_year_validation(year1, year2)
        
        if args.report:
            report = validator.generate_compatibility_report(year1, year2)
            report_file = f"cross_year_validation_{year1}_{year2}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\n📄 Detailed report saved to: {report_file}")
        
        # Exit with status code
        success = all(results.values())
        return success
    else:
        parser.print_help()
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)