"""Column names in the summary CSVs, and a reader that accepts the old one.

Line 2500 is total budgetary resources. The FY2012-2017 files were published before
this was corrected and still name that column "Budget Authority (Line 2500)".
"""
import pandas as pd

TBR = 'Total Budgetary Resources (Line 2500)'
TBR_LEGACY = 'Budget Authority (Line 2500)'
BA_TOTAL = 'Budget Authority Total (Line 1900)'
FIRST_YEAR_WITH_LINE_1900 = 2018


def read_summary_csv(path, **kwargs):
    """Read a summary CSV, renaming the legacy line 2500 header to its real name."""
    df = pd.read_csv(path, **kwargs)
    return df.rename(columns={TBR_LEGACY: TBR})
