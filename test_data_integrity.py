#!/usr/bin/env python3
"""
Integrity checks for the published SF 133 summaries, FY2018 onward.

These stop the defects found in November 2026 from coming back:
  * rows labelled with the wrong agency (one label per workbook)
  * the same account counted several times (duplicate downloads, DEFC workbooks,
    allocation accounts folded into their parent account)
  * line 2500 published under the name "Budget Authority"

They read only the files in site/data, so they run in CI without the raw workbooks.
The workbook-level checks (exact duplicates, DEFC, tie-out to the Agency Total pivot)
run when the data is built; their results are stored in selection_report_<year>.json and
checked here.
"""

import json
import sys
from pathlib import Path

import pandas as pd

from summary_columns import read_summary_csv, TBR, TBR_LEGACY, BA_TOTAL

DATA = Path('site/data')
FIRST_YEAR = 2018
EXPECTED_WORKBOOKS = 29          # one per agency workbook on MAX.gov; see selection_report_<year>.json


def years_on_disk():
    years = []
    for f in DATA.glob('all_agencies_obligation_summary_*.csv'):
        y = f.stem.replace('all_agencies_obligation_summary_', '')
        if y.isdigit() and int(y) >= FIRST_YEAR:
            years.append(int(y))
    return sorted(years)


def check_year(year):
    """Return a list of problems for one fiscal year (empty means it passes)."""
    problems = []
    csv_path = DATA / f'all_agencies_obligation_summary_{year}.csv'
    raw_header = pd.read_csv(csv_path, nrows=0).columns
    if TBR_LEGACY in raw_header:
        problems.append(f'uses the old column name "{TBR_LEGACY}" for line 2500')
    df = read_summary_csv(csv_path)

    # One row per account
    dup = df.duplicated(['Agency', 'TAFS'], keep=False)
    if dup.any():
        problems.append(f'{int(dup.sum())} rows repeat an agency and TAFS')
    per_tafs = df.groupby('TAFS')['Agency'].nunique()
    multi = per_tafs[per_tafs > 1]
    if len(multi):
        problems.append(f'{len(multi)} TAFS appear under more than one agency, e.g. {multi.index[0]}')

    # Government-wide totals should be in the trillions, not tens of trillions. The old FY2018 file,
    # with every account counted four times, summed to about $30 trillion.
    unob_total = pd.to_numeric(df['Unobligated Balance (Line 2490)'].astype(str).str.replace(r'[$,M]', '', regex=True), errors='coerce').sum() / 1e3
    tbr_total = pd.to_numeric(df[TBR].astype(str).str.replace(r'[$,M]', '', regex=True), errors='coerce').sum() / 1e3
    if not 5_000 <= tbr_total <= 20_000:
        problems.append(f'total budgetary resources are ${tbr_total:,.0f}B, outside $5,000B-$20,000B')
    if unob_total > tbr_total:
        problems.append(f'total unobligated balance (${unob_total:,.0f}B) exceeds total budgetary resources (${tbr_total:,.0f}B)')

    if BA_TOTAL not in df.columns:
        problems.append(f'missing the column "{BA_TOTAL}"')

    # The JSON uses the corrected names too
    json_path = DATA / f'all_agencies_summary_{year}.json'
    if json_path.exists():
        cols = pd.read_json(json_path, orient='records').columns
        if 'Budget_Authority_M' in cols:
            problems.append('JSON still has Budget_Authority_M')
        if 'Total_Budgetary_Resources_M' not in cols:
            problems.append('JSON is missing Total_Budgetary_Resources_M')

    # What the build recorded
    report_path = DATA / f'selection_report_{year}.json'
    if not report_path.exists():
        problems.append('no selection_report file')
    else:
        rep = json.loads(report_path.read_text())
        kept = rep['kept']
        if len(kept) != EXPECTED_WORKBOOKS:
            problems.append(f'{len(kept)} workbooks used, expected {EXPECTED_WORKBOOKS}')
        hashes = [k['content_hash'] for k in kept]
        if len(set(hashes)) != len(hashes):
            problems.append('two workbooks used have identical contents')
        for k in kept:
            t = k.get('tieout')
            if not t:
                problems.append(f"{k['file']}: no tie-out recorded")
            elif t['mismatches'] or t['n_agencies_raw'] != t['n_agencies_pivot']:
                problems.append(f"{k['file']}: Raw Data does not tie to the Agency Total pivot")
    return problems


def test_data_integrity():
    """Run the checks on every year from FY2018. Returns the list of passing years."""
    print('Testing data integrity (FY2018 onward)...')
    passing = []
    for year in years_on_disk():
        problems = check_year(year)
        if problems:
            print(f'  FY{year}: FAIL')
            for p in problems:
                print(f'    - {p}')
        else:
            print(f'  FY{year}: ok')
            passing.append(year)
    return passing


if __name__ == '__main__':
    years = years_on_disk()
    passing = test_data_integrity()
    failed = sorted(set(years) - set(passing))
    if failed or not years:
        print(f'\nFAILED: {failed or "no years found"}')
        sys.exit(1)
    print('\nAll years pass.')
