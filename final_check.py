import pandas as pd

# Load and check summary
df = pd.read_csv('site/data/all_agencies_obligation_summary.csv')
print(f'Total accounts: {len(df):,}')
print(f'Agencies: {df["Agency"].nunique()}')

# Parse values
df['BA'] = df['Budget Authority (Line 2500)'].str.replace('$','').str.replace(',','').str.replace('M','').astype(float)
df['Unob'] = df['Unobligated Balance (Line 2490)'].str.replace('$','').str.replace(',','').str.replace('M','').astype(float)

print(f'\nTotals:')
print(f'Budget Authority: ${df["BA"].sum()/1000:,.1f}B')
print(f'Unobligated: ${df["Unob"].sum()/1000:,.1f}B ({df["Unob"].sum()/df["BA"].sum()*100:.1f}%)')

# Check a few key accounts
print(f'\nSpot checks:')
for agency in ['Department of Defense-Military', 'Social Security Administration']:
    row = df[df['Agency']==agency].iloc[0]
    print(f'\n{agency}: {row["Account"]}')
    print(f'  BA: {row["Budget Authority (Line 2500)"]} ({row["Percentage Unobligated"]} unobligated)')
    
# Check for any weird values
print(f'\n\nData quality checks:')
print(f'Accounts with negative BA: {len(df[df["BA"] < 0])}')
print(f'Accounts with >100% unobligated: {len(df[(df["Unob"] > df["BA"]) & (df["BA"] > 0)])}')
print(f'Zero budget authority accounts: {len(df[df["BA"] == 0])}')