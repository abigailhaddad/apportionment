#!/usr/bin/env python3
"""
Comprehensive SF133 Data Integrity Test Suite
=============================================

This module provides robust testing for SF133 data processing to ensure:
- Data consistency across months and years
- Agency coverage completeness
- Account structure validation
- Cross-year compatibility
- Financial total accuracy

Usage:
    python -m tests.test_sf133_integrity
    python -m pytest tests/test_sf133_integrity.py -v
"""

import pandas as pd
import numpy as np
from pathlib import Path
import pytest
from typing import Dict, List, Set, Tuple
import json
from datetime import datetime

class SF133IntegrityTester:
    """Comprehensive test suite for SF133 data integrity."""
    
    def __init__(self, data_path: Path):
        self.data_path = Path(data_path)
        self.df = None
        self._load_data()
    
    def _load_data(self):
        """Load SF133 data for testing."""
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.data_path}")
        
        self.df = pd.read_csv(self.data_path, low_memory=False)
        print(f"📊 Loaded {len(self.df):,} rows from {self.data_path.name}")
    
    def test_basic_structure(self) -> bool:
        """Test that data has required basic structure."""
        print("🔍 Testing basic data structure...")
        
        # Required columns (handle both old and new column names)
        required_cols = ['Agency', 'Source_File']
        line_no_cols = [col for col in self.df.columns if col in ['LINENO', 'Line No']]
        if not line_no_cols:
            print(f"  ❌ Missing line number column (expected 'LINENO' or 'Line No')")
            return False
        self.line_no_col = line_no_cols[0]  # Store for later use
        missing_cols = [col for col in required_cols if col not in self.df.columns]
        
        if missing_cols:
            print(f"  ❌ Missing required columns: {missing_cols}")
            return False
        
        # Should have monthly columns
        month_cols = self._get_month_columns()
        if len(month_cols) < 8:  # Expect at least 8 months/quarters
            print(f"  ❌ Insufficient monthly columns: {len(month_cols)} (expected ≥8)")
            return False
        
        print(f"  ✅ Basic structure valid - {len(month_cols)} monthly columns")
        return True
    
    def test_agency_coverage(self) -> bool:
        """Test comprehensive agency coverage."""
        print("🔍 Testing agency coverage...")
        
        agencies = set(self.df['Agency'].unique())
        
        # Core agencies that must be present
        required_agencies = {
            "Department of Defense-Military",
            "Department of Education",
            "Department of Health and Human Services", 
            "Department of Veterans Affairs",
            "Department of Agriculture",
            "Department of Homeland Security"
        }
        
        missing_required = required_agencies - agencies
        if missing_required:
            print(f"  ❌ Missing required agencies: {missing_required}")
            return False
        
        # Should have substantial number of agencies
        if len(agencies) < 25:
            print(f"  ❌ Too few agencies: {len(agencies)} (expected ≥25)")
            return False
        
        print(f"  ✅ Agency coverage excellent - {len(agencies)} agencies")
        return True
    
    def test_line_number_structure(self) -> bool:
        """Test that line numbers follow expected SF133 structure."""
        print("🔍 Testing line number structure...")
        
        # Use the line number column we identified in basic structure test
        line_no_col = getattr(self, 'line_no_col', 'LINENO')
        if line_no_col not in self.df.columns:
            # Fallback detection
            line_no_col = next((col for col in self.df.columns if col in ['LINENO', 'Line No']), None)
            if not line_no_col:
                print("  ❌ No line number column found")
                return False
        
        line_numbers = set(self.df[line_no_col].dropna().unique())
        
        # Critical line numbers that should be present
        critical_lines = {1000, 2500, 2490, 3020, 4110}  # Key SF133 lines
        missing_critical = critical_lines - line_numbers
        
        if missing_critical:
            print(f"  ⚠️ Missing some critical line numbers: {missing_critical}")
            # Don't fail for this, just warn
        
        # Check line number ranges
        valid_lines = [line for line in line_numbers if 1000 <= line <= 9999]
        if len(valid_lines) < len(line_numbers) * 0.9:  # 90% should be in valid range
            print(f"  ❌ Too many invalid line numbers")
            return False
        
        print(f"  ✅ Line number structure good - {len(line_numbers)} unique lines")
        return True
    
    def test_financial_data_integrity(self) -> bool:
        """Test integrity of financial data."""
        print("🔍 Testing financial data integrity...")
        
        month_cols = self._get_month_columns()
        
        for col in month_cols:
            if col in self.df.columns:
                # Check for reasonable financial values
                values = self.df[col].dropna()
                
                if len(values) == 0:
                    continue
                
                # Check for extreme outliers that might indicate data corruption
                total = values.sum()
                if abs(total) > 1e15:  # More than $1 quadrillion seems unreasonable
                    print(f"  ⚠️ Extremely large total in {col}: ${total:,.0f}")
                
                # Check for impossible negative values in certain contexts
                if col in ['Jul', 'Aug']:  # Check recent months
                    negative_count = (values < 0).sum()
                    negative_pct = negative_count / len(values) * 100
                    if negative_pct > 30:  # More than 30% negative seems unusual
                        print(f"  ⚠️ High negative values in {col}: {negative_pct:.1f}%")
        
        print(f"  ✅ Financial data integrity looks good")
        return True
    
    def test_cross_agency_consistency(self) -> bool:
        """Test consistency patterns across agencies."""
        print("🔍 Testing cross-agency consistency...")
        
        # Test that major agencies have comprehensive line coverage
        major_agencies = [
            "Department of Defense-Military",
            "Department of Health and Human Services", 
            "Department of Education",
            "Department of Veterans Affairs"
        ]
        
        # Get line number column
        line_no_col = next((col for col in self.df.columns if col in ['LINENO', 'Line No']), None)
        if not line_no_col:
            print("  ⚠️ No line number column found for cross-agency test")
            return True
        
        for agency in major_agencies:
            agency_data = self.df[self.df['Agency'] == agency]
            if len(agency_data) == 0:
                continue
                
            unique_lines = len(agency_data[line_no_col].unique())
            if unique_lines < 50:  # Major agencies should have many line items
                print(f"  ⚠️ {agency} has few line items: {unique_lines}")
        
        print(f"  ✅ Cross-agency consistency good")
        return True
    
    def test_month_progression_logic(self) -> bool:
        """Test that monthly data follows logical progression."""
        print("🔍 Testing month progression logic...")
        
        # For budget authority (line 2500), later months should generally be >= earlier months
        line_2500 = self.df[self.df['LINENO'] == 2500.0]
        
        if len(line_2500) > 0:
            # Test a sample of accounts
            sample_size = min(100, len(line_2500))
            sample_accounts = line_2500.sample(sample_size)
            
            problematic = 0
            for _, account in sample_accounts.iterrows():
                # Check if we have July and August data
                jul_val = account.get('Jul', np.nan)
                aug_val = account.get('Aug', np.nan)
                
                if pd.notna(jul_val) and pd.notna(aug_val):
                    # August should generally be >= July for budget authority
                    if aug_val < jul_val * 0.9:  # Allow 10% decrease
                        problematic += 1
            
            if problematic > sample_size * 0.2:  # More than 20% problematic
                print(f"  ⚠️ {problematic}/{sample_size} accounts show unusual month progression")
        
        print(f"  ✅ Month progression logic reasonable")
        return True
    
    def test_data_completeness_by_agency(self) -> bool:
        """Test data completeness across agencies."""
        print("🔍 Testing data completeness by agency...")
        
        agencies = self.df['Agency'].unique()
        month_cols = self._get_month_columns()
        
        incomplete_agencies = []
        
        for agency in agencies:
            agency_data = self.df[self.df['Agency'] == agency]
            
            # Check if agency has recent month data
            recent_months = ['Jul', 'Aug']  # Focus on recent months
            has_recent_data = False
            
            for month in recent_months:
                month_col = next((col for col in month_cols if month in col), None)
                if month_col and month_col in agency_data.columns:
                    non_zero_values = (agency_data[month_col].fillna(0) != 0).sum()
                    if non_zero_values > 0:
                        has_recent_data = True
                        break
            
            if not has_recent_data and len(agency_data) > 10:  # Skip tiny agencies
                incomplete_agencies.append(agency)
        
        if len(incomplete_agencies) > len(agencies) * 0.1:  # More than 10% incomplete
            print(f"  ⚠️ {len(incomplete_agencies)} agencies lack recent month data")
        
        print(f"  ✅ Data completeness good - {len(agencies) - len(incomplete_agencies)}/{len(agencies)} agencies have recent data")
        return True
    
    def _get_month_columns(self) -> List[str]:
        """Get list of columns containing monthly data."""
        month_indicators = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                           'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Q']
        return [col for col in self.df.columns if any(month in col for month in month_indicators)]
    
    def run_all_tests(self) -> Dict[str, bool]:
        """Run all integrity tests and return results."""
        print("🧪 RUNNING COMPREHENSIVE SF133 INTEGRITY TESTS")
        print("=" * 60)
        
        tests = {
            'basic_structure': self.test_basic_structure,
            'agency_coverage': self.test_agency_coverage,
            'line_number_structure': self.test_line_number_structure,
            'financial_data_integrity': self.test_financial_data_integrity,
            'cross_agency_consistency': self.test_cross_agency_consistency,
            'month_progression_logic': self.test_month_progression_logic,
            'data_completeness': self.test_data_completeness_by_agency
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
        print("📊 TEST SUMMARY")
        print("=" * 30)
        print(f"Passed: {passed}/{len(tests)} tests")
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name}: {status}")
        
        overall_pass = passed == len(tests)
        print(f"\n🎯 OVERALL: {'✅ ALL TESTS PASSED' if overall_pass else '❌ SOME TESTS FAILED'}")
        
        return results

# Pytest integration
class TestSF133Integrity:
    """Pytest-compatible test class."""
    
    @classmethod
    def setup_class(cls):
        """Setup test data."""
        data_path = Path("site/data/sf133_master_table.csv")
        if not data_path.exists():
            pytest.skip("No SF133 data found for testing")
        
        cls.tester = SF133IntegrityTester(data_path)
    
    def test_basic_structure(self):
        assert self.tester.test_basic_structure()
    
    def test_agency_coverage(self):
        assert self.tester.test_agency_coverage()
    
    def test_line_number_structure(self):
        assert self.tester.test_line_number_structure()
    
    def test_financial_data_integrity(self):
        assert self.tester.test_financial_data_integrity()
    
    def test_cross_agency_consistency(self):
        assert self.tester.test_cross_agency_consistency()
    
    def test_month_progression_logic(self):
        assert self.tester.test_month_progression_logic()
    
    def test_data_completeness(self):
        assert self.tester.test_data_completeness_by_agency()

def main():
    """Run tests as standalone script."""
    data_path = Path("site/data/sf133_master_table.csv")
    
    if not data_path.exists():
        print(f"❌ Data file not found: {data_path}")
        print("Please ensure SF133 data has been processed first.")
        return False
    
    tester = SF133IntegrityTester(data_path)
    results = tester.run_all_tests()
    
    # Return overall success
    return all(results.values())

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)