#!/usr/bin/env python3
"""Fix OIA data by properly forward filling the TAFS column."""

import pandas as pd
import numpy as np

# Read the current data
df = pd.read_csv('data/selected_agencies_sf133_structured.csv', low_memory=False)
oia = df[df['Agency'] == 'Other Independent Agencies'].copy()

print(f"Total OIA rows: {len(oia)}")

# Check what's in Col_6 before forward fill
print("\nCol_6 non-null values before forward fill:")
print(f"  Non-null count: {oia['Col_6'].notna().sum()}")
print(f"  Sample values:")
for val in oia['Col_6'].dropna().head(10):
    print(f"    {val}")

# Forward fill Col_6 (and Col_2 for account numbers)
# Only fill if the value is not a line number
mask_line = oia['Col_6'].astype(str).str.match(r'^\d{4}(\.\d)?$', na=False)
oia.loc[~mask_line, 'Col_6'] = oia.loc[~mask_line, 'Col_6'].ffill()

# Also forward fill Col_2
mask_line2 = oia['Col_2'].astype(str).str.match(r'^\d{4}(\.\d)?$', na=False)
oia.loc[~mask_line2, 'Col_2'] = oia.loc[~mask_line2, 'Col_2'].ffill()

print("\nCol_6 non-null values after forward fill:")
print(f"  Non-null count: {oia['Col_6'].notna().sum()}")

# Now check the ACHP $2.1M row again
achp_2490 = oia[(oia['Col_9'] == '2490') & (oia['Col_19'] == '2080809.19')]
if len(achp_2490) > 0:
    print("\nACHP $2.1M row after forward fill:")
    row = achp_2490.iloc[0]
    print(f"  Col_0 (Bureau): {row['Col_0']}")
    print(f"  Col_1 (Account): {row['Col_1']}")
    print(f"  Col_2 (Account #): {row['Col_2']}")
    print(f"  Col_4 (Year): {row['Col_4']}")
    print(f"  Col_6 (TAFS): {row['Col_6']}")

# Save the fixed data
# First update the main dataframe
df.loc[df['Agency'] == 'Other Independent Agencies'] = oia

# Save
df.to_csv('data/selected_agencies_sf133_structured_fixed.csv', index=False)
print("\nSaved fixed data to: data/selected_agencies_sf133_structured_fixed.csv")

# Show some statistics
oia_fixed = df[df['Agency'] == 'Other Independent Agencies']
line_2490 = oia_fixed[oia_fixed['Col_9'] == '2490']
line_2500 = oia_fixed[oia_fixed['Col_9'] == '2500']

print(f"\nFixed data statistics:")
print(f"  Line 2490 with Col_6: {line_2490['Col_6'].notna().sum()} / {len(line_2490)}")
print(f"  Line 2500 with Col_6: {line_2500['Col_6'].notna().sum()} / {len(line_2500)}")

# Check unique TAFS codes
unique_tafs = oia_fixed['Col_6'].dropna().unique()
print(f"\nUnique TAFS codes: {len(unique_tafs)}")
print("Sample TAFS codes:")
for tafs in unique_tafs[:10]:
    if '/' in str(tafs) and '-' in str(tafs):
        print(f"  {tafs}")