"""Pull the three SF 133 lines the site uses out of a master table.

Line 2490  Unob Bal: end of year (total)          -> Unobligated_Balance_M
Line 2500  Total budgetary resources              -> Total_Budgetary_Resources_M
Line 1900  Budget authority total (disc. and mand.) -> Budget_Authority_Total_M

Line 2500 used to be published as "Budget Authority". It is total budgetary
resources: unobligated balance brought forward plus budget authority plus
recoveries and other resources. Budget authority is line 1900, which only
accounts with new budget authority report, so it is blank for the rest.
"""
import pandas as pd


def _one_line(df, lineno, month, name):
    t = df[df['LINENO'] == lineno][['Agency', 'BUREAU', 'TAFS', month]].copy()
    dup = t.duplicated(['Agency', 'TAFS'], keep=False)
    if dup.any():
        raise ValueError(
            f"Line {lineno}: {int(dup.sum())} rows share an agency and TAFS with another row "
            f"(e.g. {t[dup]['TAFS'].iloc[0]}). Summaries would double count them.")
    return t.rename(columns={month: name})


def merge_lines(df, month):
    """One row per (Agency, TAFS) that has both line 2490 and line 2500.

    Line 1900 is joined on when the account reports it, and is NaN otherwise.
    Values are in dollars.
    """
    unob = _one_line(df, 2490, month, 'unob')
    tbr = _one_line(df, 2500, month, 'tbr')[['Agency', 'TAFS', 'tbr']]
    ba = _one_line(df, 1900, month, 'ba_total')[['Agency', 'TAFS', 'ba_total']]
    merged = unob.merge(tbr, on=['Agency', 'TAFS'], how='inner')
    merged = merged.merge(ba, on=['Agency', 'TAFS'], how='left')
    return merged
