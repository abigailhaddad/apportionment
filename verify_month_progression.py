#!/usr/bin/env python3
"""
Verify that the August files contain consistent Jun/Jul data 
and reasonable Aug progression.
"""

import pandas as pd

# Load the current (August-parsed) master table
aug_master = pd.read_csv('site/data/sf133_master_table.csv', low_memory=False)

# Check a variety of accounts across Jun/Jul/Aug
test_accounts = [
    'Department of Agriculture',
    'Department of Defense-Military', 
    'Department of Health and Human Services',
    'Social Security Administration',
    'Department of Education',
    'Department of Veterans Affairs'
]

print('Checking month progression in August files:')
print('=' * 60)

for agency in test_accounts:
    agency_df = aug_master[(aug_master['Agency'] == agency) & (aug_master['Line No'] == '2500')]
    
    if len(agency_df) == 0:
        print(f'\n{agency}: No line 2500 data found')
        continue
        
    # Take first few accounts
    print(f'\n{agency}:')
    for idx, row in agency_df.head(3).iterrows():
        account_name = row['Col_4'][:60] if pd.notna(row['Col_4']) else 'Unknown'
        print(f'\n  Account: {account_name}...')
        
        # Show Jun/Jul/Aug progression
        jun_val = row['Jun (3Q)'] if 'Jun (3Q)' in row else None
        jul_val = row['Jul'] if 'Jul' in row else None
        aug_val = row['Aug'] if 'Aug' in row else None
        
        print(f'    Jun: ${jun_val/1e6:>12,.1f}M' if pd.notna(jun_val) and jun_val != 0 else '    Jun:         $0.0M')
        print(f'    Jul: ${jul_val/1e6:>12,.1f}M' if pd.notna(jul_val) and jul_val != 0 else '    Jul:         $0.0M')
        print(f'    Aug: ${aug_val/1e6:>12,.1f}M' if pd.notna(aug_val) and aug_val != 0 else '    Aug:         $0.0M')
        
        # Calculate changes
        if pd.notna(jul_val) and pd.notna(aug_val) and jul_val != 0:
            change = (aug_val - jul_val) / jul_val * 100
            print(f'    Jul→Aug: {change:+.1f}%')

print('\n' + '=' * 60)
print('SUMMARY STATISTICS:')

# Overall totals by month
jun_total = aug_master[aug_master['Line No'] == '2500']['Jun (3Q)'].sum() / 1e9
jul_total = aug_master[aug_master['Line No'] == '2500']['Jul'].sum() / 1e9
aug_total = aug_master[aug_master['Line No'] == '2500']['Aug'].sum() / 1e9

print(f'\nTotal Budget Authority (Line 2500):')
print(f'  June:   ${jun_total:>10,.1f}B')
print(f'  July:   ${jul_total:>10,.1f}B')
print(f'  August: ${aug_total:>10,.1f}B')

if jul_total > 0:
    print(f'\n  Jul→Aug change: {(aug_total - jul_total) / jul_total * 100:+.1f}%')

# Count accounts with data
jun_count = (aug_master[(aug_master['Line No'] == '2500') & (aug_master['Jun (3Q)'] != 0)]['Jun (3Q)']).count()
jul_count = (aug_master[(aug_master['Line No'] == '2500') & (aug_master['Jul'] != 0)]['Jul']).count()
aug_count = (aug_master[(aug_master['Line No'] == '2500') & (aug_master['Aug'] != 0)]['Aug']).count()

print(f'\nAccounts with non-zero values:')
print(f'  June:   {jun_count:,}')
print(f'  July:   {jul_count:,}')
print(f'  August: {aug_count:,}')