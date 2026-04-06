#!/usr/bin/env python3
"""
Check that 2018-2025 data hasn't changed from our fixes
"""

import pandas as pd

print('=== CHECKING 2018-2025 DATA INTEGRITY ===')
print('Comparing current record counts with expected values...')
print()

# Expected values from our earlier analysis
expected_counts = {
    2018: 29988,
    2019: 30164, 
    2020: 29641,
    2021: 32790,
    2022: 32651,
    2023: 9474,
    2024: 9557,
    2025: 8557
}

print('Year    Current   Expected  Difference  Status')
print('-' * 50)

all_good = True
for year in sorted(expected_counts.keys()):
    try:
        df = pd.read_csv(f'site/data/all_agencies_obligation_summary_{year}.csv')
        current = len(df)
        expected = expected_counts[year]
        diff = current - expected
        status = 'SAME' if diff == 0 else f'CHANGED ({diff:+d})'
        
        if diff != 0:
            all_good = False
            
        print(f'FY{year}   {current:>7,}   {expected:>8,}   {diff:>8}     {status}')
    except Exception as e:
        print(f'FY{year}   ERROR: {e}')
        all_good = False

print()
if all_good:
    print('✅ ALL GOOD: No changes to 2018-2025 data')
else:
    print('❌ CHANGES DETECTED: 2018-2025 data has been modified')
    print('This suggests our fixes may have unintended side effects.')