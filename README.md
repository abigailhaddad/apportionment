# SF133 Federal Budget Data Processing System

Automated system for processing complete fiscal years of federal agency budget execution data using SF133 reports. Downloads all agency files for entire fiscal years from MAX.gov, processes using reliable Raw Data sheets, and generates comprehensive datasets spanning 2018-2025.

## Where the pages live

- **Interactive site** (year buttons): https://apportionment.abigailhaddad.com, deployed from the `prod` branch by `test-and-deploy.yml`.
- **Analysis page** (the Quarto page in `docs/`, rendered from `index.qmd`): https://apportionment-analysis.pages.dev, on Cloudflare Pages. `deploy-analysis.yml` publishes `docs/` there whenever it changes on `main`. It needs the repo secrets `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`. It used to be served by GitHub Pages.

To change the analysis page: edit `index.qmd`, run `quarto render index.qmd`, and commit `docs/`.

## Data corrected on 2026-11-06

Until this date the summaries for fiscal years 2018 through 2025 had four errors. They are fixed, and `test_data_integrity.py` now fails if any of them comes back. FY2012–2017 come from a different parser. They were not rebuilt and not audited.

1. **Wrong agency names.** Each workbook was labelled with the first agency in it. The Other Independent Agencies workbook holds about 100 agencies, so all their accounts carried one name ("Access Board" in FY2018–2019, "400 Years of African-American History Commission" from FY2020). Other multi-agency workbooks had the same problem. Every row now carries its own agency's name, so the summaries list about 120 agencies, not 29.
2. **Repeated accounts.** The pipeline read every file in the folder. That included exact duplicate downloads (FY2018–2022) and the DEFC workbooks, which are a second cut of accounts the agency workbooks already hold. Some accounts appeared several times, and some under two agencies.
3. **Accounts added together.** An allocation account such as `69-69-0143` shared its grouping keys with its parent `69-0143`. The pipeline summed them into one row that kept the parent's name. The row's amounts were larger than the parent's own, and the allocation account disappeared.
4. **A mislabelled column.** "Budget Authority (Line 2500)" is line 2500, total budgetary resources: unobligated balance brought forward plus budget authority plus recoveries and other resources. Budget authority is line 1900, which an account reports only when it has new budget authority. Both now have columns of their own: `Total Budgetary Resources (Line 2500)` and `Budget Authority Total (Line 1900)`. The FY2012–2017 files still use the old header for line 2500. The values are the same line.

What changed, by year (before the fix → after):

| Fiscal year | Rows before → after | Accounts before → after | Old rows with the wrong agency | Total unobligated ($B) before → after | Total budgetary resources ($B) before → after |
|---|---|---|---|---|---|
| FY2018 | 29,988 → 7,497 | 7,497 → 7,497 | 2,480 (8%) | 5,274 → 1,318 | 29,843 → 7,461 |
| FY2019 | 30,164 → 7,541 | 7,541 → 7,541 | 2,480 (8%) | 5,404 → 1,351 | 31,273 → 7,818 |
| FY2020 | 29,641 → 7,824 | 7,824 → 7,824 | 1,037 (3%) | 12,631 → 2,875 | 54,012 → 12,261 |
| FY2021 | 32,790 → 8,006 | 8,006 → 8,006 | 3,155 (10%) | 10,729 → 2,420 | 55,986 → 12,932 |
| FY2022 | 32,651 → 8,203 | 8,203 → 8,203 | 3,404 (10%) | 10,244 → 2,469 | 47,481 → 11,629 |
| FY2023 | 9,474 → 8,350 | 8,350 → 8,350 | 1,472 (16%) | 3,013 → 2,644 | 13,504 → 11,977 |
| FY2024 | 9,557 → 8,528 | 8,528 → 8,528 | 1,622 (17%) | 2,984 → 2,616 | 12,757 → 12,032 |
| FY2025 | 9,757 → 8,693 | 8,652 → 8,693 | 1,647 (17%) | 3,368 → 2,971 | 12,717 → 13,271 |

"Rows with the wrong agency" counts old rows whose agency differs from the one the account has in the corrected data. Totals are for the latest month in each year.

Each corrected year is checked three ways: every workbook's Raw Data sheet must tie to the workbook's own Agency Total pivot sheet, every corrected year was compared account by account against an independent rebuild from the same workbooks (no difference in lines 2490, 2500 or 1900; that rebuild is not part of this repository), and the published files are tested for repeated accounts, accounts under two agencies and old column names. `site/data/selection_report_<year>.json` lists which workbooks were used and which were dropped, and why.

### What the totals cover

**What the totals cover.** The yearly summaries keep only accounts for which OMB's report has both a line 2490 row (unobligated balance) and a line 2500 row (total budgetary resources). Accounts with no line 2490 row are left out. A few accounts each year have a line 2490 but no line 2500 row, and are left out too. So a total here is the total for accounts that report an unobligated balance, not for every account in the SF-133. Financing accounts are included. In FY2025 that leaves out 526 accounts, 147 of them with nonzero total budgetary resources worth $264.9B. The largest is 97-0040 Payment to Military Retirement Fund ($154.4B), whose raw workbook has no line 2490 row. The [Hugging Face dataset](https://huggingface.co/datasets/abigailhaddad/sf133-budget-execution) keeps every account.

| Fiscal year | Accounts in the totals | Total budgetary resources in the totals ($B) | Accounts left out | Of those, with nonzero resources | Their resources ($B) | Financing accounts in the totals ($B) |
|---|---|---|---|---|---|---|
| FY2018 | 7,497 | 7,460.7 | 456 | 115 | 133.4 | 383.5 |
| FY2019 | 7,541 | 7,818.2 | 436 | 120 | 162.4 | 361.5 |
| FY2020 | 7,824 | 12,260.9 | 433 | 111 | 151.8 | 1,313.1 |
| FY2021 | 8,006 | 12,931.7 | 448 | 115 | 187.2 | 1,286.9 |
| FY2022 | 8,203 | 11,629.0 | 475 | 117 | 208.2 | 792.9 |
| FY2023 | 8,350 | 11,977.2 | 516 | 138 | 213.1 | 794.2 |
| FY2024 | 8,528 | 12,032.2 | 520 | 140 | 309.3 | 470.8 |
| FY2025 | 8,693 | 13,271.2 | 526 | 147 | 264.9 | 721.7 |

Totals are for September of each fiscal year.

## 🚀 Quick Start

### Process Complete Fiscal Year
```bash
# Process complete fiscal year (downloads all agencies for entire year)
python main.py --year 2024

# Process multiple years
python main.py --year 2022 2023 2024

# Process year with custom URL
python main.py --year 2024 --url "https://portal.max.gov/.../FY%202024%20..."

# Use existing downloaded files (skip download)
python main.py --year 2024 --no-download

# Start web server
python main.py --serve
```

### Setup
```bash
# Clone and setup
git clone https://github.com/abigailhaddad/apportionment.git
cd apportionment

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## 🏗️ System Architecture

### Core Components

1. **`main.py`** - Main entry point and orchestrator
   - Routes to year processing or web server
   - Handles single or multi-year processing
   - Manages pipeline success/failure reporting

2. **`code/year_processor.py`** - Year-based processing engine
   - Downloads complete fiscal year data from MAX.gov
   - Processes all available months using Raw Data sheets
   - Auto-detects available months and validates data completeness
   - Generates year-specific master datasets

3. **`code/parse_sf133_raw_data.py`** - Raw Data sheet parser
   - Uses Raw Data sheets instead of TAFS detail (better cross-year compatibility)
   - Standardized column mapping (AMT_JUL → Jul, AMT3 → Jun (3Q), etc.)
   - Labels every row with its own agency, and keeps TAFS in the grouping key
   - Uses one workbook per agency per year: skips DEFC workbooks and exact duplicate downloads, and stops if two workbooks overlap
   - Ties every workbook's Raw Data to its Agency Total pivot sheet and stops on a difference
   - Writes `selection_report_<year>.json` with what it used and dropped

4. **`create_year_summaries.py`** - Summary file generator
   - Creates obligation summaries from master datasets
   - Auto-detects latest month with data for each year
   - Generates CSV and JSON files for website visualization
   - Handles TAFS parsing for account details

### Key Features

✅ **Complete Year Processing** - Downloads and processes entire fiscal years  
✅ **Multi-Year Support** - Process historical data from 2018-2025  
✅ **Raw Data Method** - More reliable than TAFS detail parsing  
✅ **Auto-Detection** - Automatically finds available months per year  
✅ **Data Validation** - Comprehensive coverage and integrity checks  
✅ **Standardized Output** - Consistent column naming across all years

## 🔍 Data Processing Details

### SF133 Data Source
- Downloads from [MAX.gov SF133 Reports](https://portal.max.gov/portal/document/SF133/Budget/)
- Processes 25+ federal agency files per fiscal year
- Uses "Raw Data" sheets for maximum compatibility across years
- Handles different file formats (xlsx/xls) across historical years

### Column Mapping
```
Raw Data Sheet    →    Standardized Name
AMT_JUL          →    Jul
AMT_AUG          →    Aug  
AMT3             →    Jun (3Q)
AMT4             →    Sep (4Q)
BUREAU           →    BUREAU
OMB_ACCT         →    OMB_ACCT
LINENO           →    LINENO
```

### Fiscal Year Structure
- **Q1**: Oct, Nov, Dec (ends with Dec 1Q data)
- **Q2**: Jan, Feb, Mar (ends with Mar 2Q data)  
- **Q3**: Apr, May, Jun (ends with Jun 3Q data)
- **Q4**: Jul, Aug, Sep (ends with Sep 4Q data - fiscal year end)

### Key SF133 Line Numbers
- **Line 1000**: Unobligated Balance brought forward
- **Line 2490**: Unobligated Balance, end of period  
- **Line 1900**: Budget authority total (discretionary and mandatory)
- **Line 2500**: Total budgetary resources
- **Line 3020**: Outlays (gross)
- **Line 4110**: Outlays (total)

## 📊 Available Data Coverage

The system maintains complete datasets for fiscal years 2018-2025:
- **Historical Years (2018-2023)**: Complete fiscal year data with all available months
- **Recent Years (2024-2025)**: Current data with month-by-month updates
- **Cross-Year Analysis**: Consistent TAFS validation across all years

```bash
# Generate summaries for all years
python create_year_summaries.py --all-years

# Generate summary for specific year
python create_year_summaries.py --year 2024

# Validate year coverage
python validate_years.py
```

## 🌐 Website & Visualization

The system generates an interactive website showing:
- **Multi-Year Comparison**: Budget trends across fiscal years
- **Bubble Chart**: Total budgetary resources vs. unobligated percentages
- **Agency/Bureau Filtering** 
- **Expiration Year Analysis**
- **Month-by-Month Progression**

```bash
# Start development server
python main.py --serve
# Visit http://localhost:8000
```

## 🔧 Configuration

### URL Configuration (sf133_urls.json)
```json
{
  "sf133_urls": {
    "2024": "https://portal.max.gov/.../FY%202024%20...",
    "2025": "https://portal.max.gov/.../FY%202025%20..."
  }
}
```

### Data Validation
- **Agency Coverage**: Validates against FY2025 baseline (25+ agencies expected)
- **Month Completeness**: Auto-detects available months, requires September for historical years
- **TAFS Coverage**: Validates account coverage against baseline year
- **Financial Totals**: Checks for reasonable total budgetary resources and unobligated balances
- **Integrity** (`test_data_integrity.py`, FY2018+): no repeated accounts, no account under two agencies, no old column names, and every workbook tied to its pivot

## 📁 File Structure
```
├── main.py                       # Main entry point and router
├── create_year_summaries.py      # Summary file generator
├── validate_years.py             # Year coverage validator  
├── test_data_integrity.py        # Duplicate, label and column-name checks
├── check_data_integrity.py       # Runs test_data_integrity.py by itself
├── summary_columns.py            # Column names, and a reader that accepts the old line 2500 header
├── sf133_urls.json              # MAX.gov URL configuration
├── code/
│   ├── year_processor.py         # Year-based processing engine
│   ├── parse_sf133_raw_data.py   # Raw Data sheet parser
│   ├── summary_lines.py          # Lines 2490, 2500 and 1900 for the summaries
│   ├── tieout.py                 # Ties Raw Data to the Agency Total pivot
│   ├── download_sf133_data.py    # Data downloader
│   └── serve.py                 # Development web server
├── site/
│   ├── data/                    # Processed data (CSV/JSON)
│   │   ├── sf133_YYYY_master.csv # Year-specific master files
│   │   ├── selection_report_YYYY.json # Workbooks used, dropped and tied out
│   │   └── summary_YYYY.json     # Year metadata and analysis
│   └── index.html              # Web interface
├── raw_data/
│   ├── 2018/                   # FY2018 Excel files
│   ├── 2024/                   # FY2024 Excel files
│   └── 2025/                   # FY2025 Excel files
└── requirements.txt            # Python dependencies
```

## 🚨 Important Notes

- **Complete Year Processing**: System processes entire fiscal years, not individual months
- **Historical Coverage**: Maintains data from FY2018 through current fiscal year
- **Auto-Detection**: Automatically identifies available months for each year
- **Data Validation**: Failed years are excluded from website but don't crash pipeline
- **Raw Data Method**: More reliable than legacy TAFS detail parsing across different year formats

## 📈 Production Usage

```bash
# Process latest fiscal year
python main.py --year 2025

# Historical data rebuild
python main.py --year 2020 2021 2022 2023 2024 2025

# Update summaries after processing
python create_year_summaries.py --all-years

# Deploy to production
python main.py --serve
```

---

**Status**: ✅ **Production Ready** - Multi-year processing system with comprehensive validation and historical data coverage (FY2018-2025).