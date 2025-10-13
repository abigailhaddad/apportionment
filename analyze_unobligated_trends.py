#!/usr/bin/env python3
"""
Analyze unobligated balance trends across months.
"""

import pandas as pd

# Load current master table
df = pd.read_csv('site/data/sf133_master_table.csv', low_memory=False)

# Get line 2490 (unobligated balance) data
line_2490 = df[df['Line No'] == '2490'].copy()

print('OVERALL UNOBLIGATED BALANCES (Line 2490):')
print('='*60)

# Calculate totals by month
months = [('Jun (3Q)', 'June'), ('Jul', 'July'), ('Aug', 'August')]
overall_totals = {}

for col, name in months:
    if col in line_2490.columns:
        total = line_2490[col].sum() / 1e9  # Convert to billions
        overall_totals[name] = total
        print(f'{name:8}: ${total:,.1f}B')

# Calculate changes
if 'July' in overall_totals and 'June' in overall_totals:
    jun_jul_change = overall_totals['July'] - overall_totals['June']
    print(f'\nJun→Jul change: ${jun_jul_change:,.1f}B ({jun_jul_change/overall_totals["June"]*100:+.1f}%)')
    
if 'August' in overall_totals and 'July' in overall_totals:
    jul_aug_change = overall_totals['August'] - overall_totals['July']
    print(f'Jul→Aug change: ${jul_aug_change:,.1f}B ({jul_aug_change/overall_totals["July"]*100:+.1f}%)')

# Now filter for FY2025 expiration only
print('\n\nFY2025 EXPIRATION YEAR ONLY:')
print('='*60)

# For standard agencies, Col_4 contains TAFS like "12-3456 /25"
# For OIA, Col_6 contains TAFS
fy2025_standard = line_2490[line_2490['Col_4'].str.contains('/25', na=False)]
fy2025_oia = line_2490[(line_2490['Agency'] == 'Other Independent Agencies') & 
                       (line_2490['Col_6'].str.contains('/25', na=False))]

# Combine FY2025 accounts
fy2025 = pd.concat([fy2025_standard, fy2025_oia])

fy2025_totals = {}
for col, name in months:
    if col in fy2025.columns:
        total = fy2025[col].sum() / 1e9
        fy2025_totals[name] = total
        print(f'{name:8}: ${total:,.1f}B')

# Calculate FY2025 changes
if 'July' in fy2025_totals and 'June' in fy2025_totals:
    jun_jul_change = fy2025_totals['July'] - fy2025_totals['June']
    print(f'\nJun→Jul change: ${jun_jul_change:,.1f}B ({jun_jul_change/fy2025_totals["June"]*100:+.1f}%)')
    
if 'August' in fy2025_totals and 'July' in fy2025_totals:
    jul_aug_change = fy2025_totals['August'] - fy2025_totals['July']
    print(f'Jul→Aug change: ${jul_aug_change:,.1f}B ({jul_aug_change/fy2025_totals["July"]*100:+.1f}%)')

print(f'\nFY2025 accounts: {len(fy2025):,} out of {len(line_2490):,} total line 2490 accounts')

# What percentage of unobligated is FY2025?
print('\n\nFY2025 AS PERCENTAGE OF TOTAL:')
print('='*60)
for name in ['June', 'July', 'August']:
    if name in overall_totals and name in fy2025_totals:
        pct = fy2025_totals[name] / overall_totals[name] * 100
        print(f'{name}: {pct:.1f}% of unobligated balances are FY2025 funds')

# Also check budget authority for context
print('\n\nBUDGET AUTHORITY (Line 2500) - FOR CONTEXT:')
print('='*60)
line_2500 = df[df['Line No'] == '2500'].copy()

for col, name in months:
    if col in line_2500.columns:
        total_ba = line_2500[col].sum() / 1e9
        total_unob = overall_totals.get(name, 0)
        pct = (total_unob / total_ba * 100) if total_ba > 0 else 0
        print(f'{name}: ${total_ba:,.1f}B budget authority, {pct:.1f}% unobligated')