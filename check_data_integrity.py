#!/usr/bin/env python3
"""
Check the published FY2018-2025 summaries for the defects fixed in November 2026.

This used to compare record counts with a list of expected values. Those values came
from the faulty build, so a correct file would have failed. The checks now test the
properties that were broken; see test_data_integrity.py.
"""

import sys

from test_data_integrity import test_data_integrity, years_on_disk

if __name__ == '__main__':
    years = years_on_disk()
    passing = test_data_integrity()
    failed = sorted(set(years) - set(passing))
    if failed or not years:
        print(f'FAILED: {failed or "no years found"}')
        sys.exit(1)
    print('All years pass.')
