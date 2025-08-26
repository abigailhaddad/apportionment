# Federal Agency Budget Obligation Analysis

An interactive web tool for analyzing federal agency budget execution using SF 133 data, identifying accounts with high unobligated balances approaching expiration.

## What This Tool Does

This tool processes SF 133 (Report on Budget Execution and Budgetary Resources) data from federal agencies to:

1. **Identify unobligated balances** - Funds that have been appropriated but not yet obligated (Line 2490)
2. **Compare to total budget authority** - The total funding available to agencies (Line 2500)
3. **Calculate obligation rates** - What percentage of funds remain unobligated
4. **Highlight expiring funds** - Focus on accounts where funding expires soon and risks being returned to Treasury

The visualization helps identify which agencies/bureaus have high unobligated balances, including with FY 2025 expiration dates.

## Data Source

All data comes from the [MAX.gov FY 2025 SF 133 Reports](https://portal.max.gov/portal/document/SF133/Budget/FY%202025%20-%20SF%20133%20Reports%20on%20Budget%20Execution%20and%20Budgetary%20Resources.html) (June 2025 reporting period).

SF 133 is the standard federal report on budget execution. 

## Installation & Running

### Setup
```bash
# Clone the repository
git clone https://github.com/abigailhaddad/apportionment.git
cd apportionment

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Pipeline

```bash
# Run the complete pipeline (downloads data, processes, generates visualizations)
python3 main.py

# Start the web server
python3 serve.py

# Open http://localhost:8000 in your browser
```

## How It Works

### Data Pipeline

1. **Download** (`download_sf133_data.py`)
   - Downloads ~28 agency SF 133 Excel files from MAX.gov
   - Files are ~240MB total (not committed to repo)

2. **Parse** (`parse_sf133_files.py`)
   - Extracts TAFS detail sheets from each agency file
   - Handles varying formats across agencies
   - Special logic for Other Independent Agencies (different structure)
   - Creates master table with all line items

3. **Summarize** (`generate_summary.py`)
   - Filters for lines 2490 (Unobligated Balance) and 2500 (Budget Authority)
   - Calculates obligation percentages
   - Extracts metadata (bureau, account, expiration year)
   - Outputs JSON for web visualization

### Key SF 133 Lines

- **Line 2490**: Unobligated balance, end of period - funds not yet obligated
- **Line 2500**: Total budgetary resources (Budget Authority) - total available funding

### Web Interface

- **Bubble Chart**: Size = budget authority, Y-axis = % unobligated, Color = bureau
- **Filters**: Agency, Bureau, Period of Performance, Expiration Year
- **Aggregation**: View by individual accounts, bureau totals, or agency totals
- **Table**: Sortable/searchable with all account details

## Current Status

🚧 **Active Development** - I am still working on this tool and I don't think you should use the results yet unless you are very familiar with this data or we've talked.

## Technical Details

- **Backend**: Python (pandas, openpyxl) for data processing
- **Frontend**: D3.js for visualization, DataTables for table
- **Data Format**: SF 133 Excel → CSV → JSON
- **Agencies**: 29 major federal agencies (Legislative, Judicial, and Executive branch)
