"""generate_obligation_summary must record the month it was given, not a loop variable."""
import json
import os
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from code.generate_summary import generate_obligation_summary


def test_metadata_keeps_month_argument():
    rows = [{'Agency': 'Dept X', 'Line No': ln, 'Col_0': 'Bur', 'Col_1': 'acct',
             'Col_4': '12-3456 /25 - Salaries', 'Aug': v}
            for ln, v in ((2490, 100e6), (2500, 400e6))]
    old = os.getcwd()
    with tempfile.TemporaryDirectory() as d:
        os.chdir(d)
        try:
            pd.DataFrame(rows).to_csv('m.csv', index=False)
            generate_obligation_summary('m.csv', 2017, 'August')
            meta = json.load(open('site/data/fiscal_year_metadata.json'))
            data = json.load(open('site/data/all_agencies_summary_2017.json'))
        finally:
            os.chdir(old)
    assert meta['2017']['month'] == 'August'
    assert data[0]['Data_Month'] == 'August'


if __name__ == '__main__':
    test_metadata_keeps_month_argument()
    print('ok')
