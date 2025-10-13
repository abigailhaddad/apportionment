# SF133 Federal Budget Data Processing System

A robust, automated system for processing federal agency budget execution data using SF133 reports. This system downloads, processes, validates, and publishes budget data with comprehensive integrity testing to ensure accuracy across multiple years.

## 🚀 Quick Start

### New Month Data Update
```bash
# Process new month data (downloads, processes, tests, updates website)
python update_sf133_data.py --month september --year 2024

# Test existing data without updating
python update_sf133_data.py --test-only

# Process existing downloaded data without re-downloading
python update_sf133_data.py --month august --no-download
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

1. **`update_sf133_data.py`** - Main orchestrator script
   - Downloads new SF133 data when available
   - Processes using robust Raw Data method
   - Runs comprehensive validation tests
   - Updates website only after all tests pass

2. **`sf133_processor.py`** - Data processing engine
   - Downloads data from MAX.gov
   - Processes using Raw Data sheets (more reliable than TAFS detail)
   - Handles multiple years and consolidated files
   - Creates standardized monthly columns

3. **`parse_sf133_raw_data.py`** - Raw Data sheet parser
   - Uses Raw Data sheets instead of TAFS detail (better cross-year compatibility)
   - Standardized column mapping (AMT_JUL → Jul, AMT3 → Jun (3Q), etc.)
   - Handles consolidated files to prevent double-counting
   - Preserves exact financial accuracy

4. **Testing Framework**
   - `tests/test_sf133_integrity.py` - Data integrity validation
   - `tests/test_cross_year_validation.py` - Cross-year compatibility testing
   - Validates agency coverage, account structures, financial reasonableness

### Key Improvements Over Legacy System

✅ **Automated Pipeline** - Single command processes everything safely  
✅ **Raw Data Method** - More reliable than TAFS detail parsing  
✅ **Comprehensive Testing** - Prevents data corruption or loss  
✅ **Cross-Year Validation** - Ensures compatibility when adding new years  
✅ **Backup System** - Automatic backups before updates  
✅ **Standardized Columns** - Clean field names instead of "Col_0", "Col_1"

## 🔍 Data Processing Details

### SF133 Data Source
- Downloads from [MAX.gov SF133 Reports](https://portal.max.gov/portal/document/SF133/Budget/)
- Processes 25+ federal agency files per month
- Uses "Raw Data" sheets for maximum compatibility

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

### Key SF133 Line Numbers
- **Line 1000**: Unobligated Balance brought forward
- **Line 2490**: Unobligated Balance, end of period  
- **Line 2500**: Total budgetary resources
- **Line 3020**: Outlays (gross)
- **Line 4110**: Outlays (total)

## 🧪 Testing & Validation

### Data Integrity Tests
```bash
# Run comprehensive tests
python -m tests.test_sf133_integrity

# Cross-year validation
python tests/test_cross_year_validation.py --compare 2024 2025
```

**Tests Include:**
- ✅ Agency coverage validation (25+ agencies expected)
- ✅ Account structure consistency  
- ✅ Financial total reasonableness
- ✅ Month progression logic
- ✅ Data completeness by agency
- ✅ Line number structure validation

### Validation Criteria
- **Agency Coverage**: Must include all major agencies (Defense, HHS, Education, etc.)
- **Data Completeness**: >100k rows expected, <5% missing values in key fields
- **Financial Consistency**: Previous months' totals must remain unchanged
- **Account Consistency**: Core line numbers (2500, 2490) must exist across agencies

## 📊 Website & Visualization

The system generates an interactive website showing:
- **Bubble Chart**: Budget authority vs. unobligated percentages
- **Agency/Bureau Filtering** 
- **Expiration Year Analysis** (focus on FY2025 expiring funds)
- **Monthly Progression** (June → July → August trends)

```bash
# Start web server
python serve.py
# Visit http://localhost:8000
```

## 🔄 Automated Updates

### Safe Update Process
1. **Backup** current data
2. **Download** new SF133 files  
3. **Process** using Raw Data method
4. **Test** data integrity comprehensively
5. **Validate** against previous months
6. **Update** website only if all tests pass

### Failure Handling
- If ANY test fails, website is NOT updated
- Previous data remains unchanged
- Detailed logs saved for debugging
- Easy rollback to previous version

## 📁 File Structure
```
├── update_sf133_data.py          # Main update orchestrator
├── sf133_processor.py            # Core processing engine  
├── parse_sf133_raw_data.py       # Raw Data sheet parser
├── download_sf133_data.py        # Data downloader
├── tests/
│   ├── test_sf133_integrity.py   # Data integrity tests
│   └── test_cross_year_validation.py  # Cross-year tests
├── site/
│   ├── data/                     # Processed data (CSV/JSON)
│   └── index.html               # Web interface
├── raw_data/                    # Downloaded SF133 files
└── backups/                     # Automatic backups
```

## 🚨 Important Notes

- **Always run tests** before using new data in production
- **Previous months' data must remain unchanged** when adding new months
- **Cross-year validation** ensures compatibility when adding new fiscal years  
- **Backup system** protects against data corruption
- **Raw Data method** is more reliable than legacy TAFS detail parsing

## 📈 Production Usage

```bash
# Monthly update (recommended)
python update_sf133_data.py --month september --year 2024 --save-log

# Emergency testing
python update_sf133_data.py --test-only

# Cross-year validation when adding new fiscal year
python tests/test_cross_year_validation.py --compare 2024 2025 --report
```

## 🔧 Development

### Running Tests
```bash
# All tests
python -m pytest tests/ -v

# Specific test
python tests/test_sf133_integrity.py

# Cross-year validation
python tests/test_cross_year_validation.py --compare 2024 2025
```

---

**Status**: ✅ **Production Ready** - Comprehensive testing and validation system ensures data integrity across years and months.