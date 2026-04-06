# SF133 Federal Budget Data Processing System

Automated system for processing complete fiscal years of federal agency budget execution data using SF133 reports. Downloads all agency files for entire fiscal years from MAX.gov, processes using reliable Raw Data sheets, and generates comprehensive datasets spanning 2018-2025.

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
   - Handles consolidated files to prevent double-counting
   - Preserves exact financial accuracy

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
- **Bubble Chart**: Budget authority vs. unobligated percentages
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
- **Financial Totals**: Checks for reasonable budget authority and unobligated balances

## 📁 File Structure
```
├── main.py                       # Main entry point and router
├── create_year_summaries.py      # Summary file generator
├── validate_years.py             # Year coverage validator  
├── sf133_urls.json              # MAX.gov URL configuration
├── code/
│   ├── year_processor.py         # Year-based processing engine
│   ├── parse_sf133_raw_data.py   # Raw Data sheet parser
│   ├── download_sf133_data.py    # Data downloader
│   └── serve.py                 # Development web server
├── site/
│   ├── data/                    # Processed data (CSV/JSON)
│   │   ├── sf133_YYYY_master.csv # Year-specific master files
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