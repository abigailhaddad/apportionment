#!/usr/bin/env python3
"""
Tests for the Raw Data parser, on small workbooks built here.

Run with: python3 test_parser.py   (or pytest test_parser.py)
Each test covers a defect the pipeline had before 2026-11-06.
"""

import sys
import tempfile
from pathlib import Path

import pandas as pd

from code.parse_sf133_raw_data import (
    parse_sf133_raw_data, select_workbooks, check_combined, normalize_agency, detect_file_units,
)
from code.summary_lines import merge_lines

COLS = ['AGENCY', 'BUREAU', 'OMB_ACCT', 'TAFS', 'TRAG', 'TRACCT', 'ALLOC', 'FY1', 'FY2',
        'LINENO', 'CRED_IND', 'AMT_OCT', 'AMT4']


def make_workbook(path, rows, units='(Dollars)', extra_cols=None):
    """Write a workbook with the sheets the parser reads."""
    raw = pd.DataFrame(rows, columns=COLS + (extra_cols or []))
    header = pd.DataFrame([['SF 133 Report on Budget Execution'], [units]])
    with pd.ExcelWriter(path) as xw:
        header.to_excel(xw, sheet_name='TAFS detail', header=False, index=False)
        raw.to_excel(xw, sheet_name='Raw Data', index=False)
    return path


def row(agency, tafs, line, amt, bureau='B', acct='021-04-0100', trag=1, tracct=100, fy1=None, fy2='X'):
    return [agency, bureau, acct, tafs, trag, tracct, None, fy1, fy2, line, 'NON-FINANCING ACCOUNTS', 0, amt]


def test_each_row_gets_its_own_agency():
    with tempfile.TemporaryDirectory() as d:
        wb = make_workbook(Path(d) / 'oia.xlsx', [
            row('Access Board', '95-0100 /X - Salaries', 2490, 5.0),
            row('Federal Deposit Insurance Corporation', '51-4596 /X - Deposit Insurance Fund', 2490, 7.0),
        ])
        df, info = parse_sf133_raw_data(wb)
        labels = dict(zip(df['TAFS'], df['Agency']))
        assert labels['51-4596 /X - Deposit Insurance Fund'] == 'Federal Deposit Insurance Corporation'
        assert labels['95-0100 /X - Salaries'] == 'Access Board'
        assert info['agencies'] == ['Access Board', 'Federal Deposit Insurance Corporation']


def test_allocation_account_is_not_added_into_its_parent():
    with tempfile.TemporaryDirectory() as d:
        wb = make_workbook(Path(d) / 'dot.xlsx', [
            row('Department of Transportation', '69-0143 /X - National Infrastructure Investments', 2490, 35.0, trag=69, tracct=143),
            row('Department of Transportation', '69-69-0143 /X - National Infrastructure Investments', 2490, 1000.0, trag=69, tracct=143),
        ])
        df, _ = parse_sf133_raw_data(wb)
        by_tafs = dict(zip(df['TAFS'], df['AMT4'] if 'AMT4' in df else df['Sep']))
        assert by_tafs['69-0143 /X - National Infrastructure Investments'] == 35.0
        assert by_tafs['69-69-0143 /X - National Infrastructure Investments'] == 1000.0


def test_defc_workbook_is_skipped():
    with tempfile.TemporaryDirectory() as d:
        wb = make_workbook(Path(d) / 'defc.xlsx', [
            row('Department of Transportation', '69-0143 /X - X', 2490, 1.0, trag=69, tracct=143) + ['L'],
        ], extra_cols=['DEFC'])
        df, info = parse_sf133_raw_data(wb)
        assert df is None and info['status'] == 'defc'


def test_old_xls_files_are_reported_not_parsed():
    df, info = parse_sf133_raw_data(Path('Ab_Sign_Rpt_2025_02.xls'))
    assert df is None and info['status'] == 'old_xls_format'


def test_units_must_be_stated():
    with tempfile.TemporaryDirectory() as d:
        wb = make_workbook(Path(d) / 'units.xlsx', [row('Access Board', '95-0100 /X - S', 2490, 5.0)], units='(Millions)')
        try:
            detect_file_units(wb)
        except ValueError:
            return
        raise AssertionError('a workbook with no thousands/dollars header should raise')


def test_thousands_are_multiplied():
    with tempfile.TemporaryDirectory() as d:
        wb = make_workbook(Path(d) / 'k.xlsx', [row('Access Board', '95-0100 /X - S', 2490, 5.0)], units='(Thousands)')
        df, _ = parse_sf133_raw_data(wb)
        assert df['Sep'].iloc[0] == 5000.0


def _parsed(d, name, rows):
    path = make_workbook(Path(d) / name, rows)
    df, info = parse_sf133_raw_data(path)
    return path, df, info


def test_exact_duplicate_workbooks_are_dropped_and_overlaps_stop_the_run():
    with tempfile.TemporaryDirectory() as d:
        r = [row('Access Board', '95-0100 /X - S', 2490, 5.0)]
        a = _parsed(d, 'a.xlsx', r)
        b = _parsed(d, 'b.xlsx', r)
        kept, report = select_workbooks([a, b])
        assert len(kept) == 1 and len(report['dropped_duplicate']) == 1
        # same agency, same number of rows, different numbers: someone has to choose
        c = _parsed(d, 'c.xlsx', [row('Access Board', '95-0100 /X - S', 2490, 6.0)])
        try:
            select_workbooks([a, c])
        except ValueError:
            return
        raise AssertionError('overlapping workbooks with different contents should stop the run')


def test_a_tafs_under_two_agencies_stops_the_run():
    df = pd.DataFrame({'TAFS': ['1 /X - A', '1 /X - A'], 'Agency': ['A', 'B'], 'BUREAU': ['b', 'b'],
                       'OMB_ACCT': ['o', 'o'], 'LINENO': [2490, 2490]})
    try:
        check_combined(df)
    except ValueError:
        return
    raise AssertionError('the same TAFS under two agencies should raise')


def test_summary_lines_refuse_to_double_count():
    df = pd.DataFrame({'Agency': ['A', 'A'], 'BUREAU': ['b', 'b'], 'TAFS': ['t', 't'],
                       'LINENO': [2490, 2490], 'Sep': [1.0, 2.0]})
    try:
        merge_lines(df, 'Sep')
    except ValueError:
        return
    raise AssertionError('two rows for one agency, TAFS and line should raise')


def test_summary_lines_join_budget_authority_only_where_reported():
    df = pd.DataFrame({
        'Agency': ['A'] * 5, 'BUREAU': ['b'] * 5, 'TAFS': ['t1', 't1', 't1', 't2', 't2'],
        'LINENO': [2490, 2500, 1900, 2490, 2500], 'Sep': [10.0, 40.0, 25.0, 3.0, 3.0]})
    m = merge_lines(df, 'Sep').set_index('TAFS')
    assert m.loc['t1', 'tbr'] == 40.0 and m.loc['t1', 'ba_total'] == 25.0
    assert pd.isna(m.loc['t2', 'ba_total'])


def test_agency_names():
    assert normalize_agency('Department of Defense--Military Programs') == 'Department of Defense-Military'
    assert normalize_agency('Access Board') == 'Access Board'
    assert normalize_agency('  Access   Board ') == 'Access Board'


if __name__ == '__main__':
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith('test_') and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f'ok   {name}')
        except Exception as e:
            failed += 1
            print(f'FAIL {name}: {type(e).__name__}: {e}')
    print(f'\n{len(tests) - failed} passed, {failed} failed')
    sys.exit(1 if failed else 0)
