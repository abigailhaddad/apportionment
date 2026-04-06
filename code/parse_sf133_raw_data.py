#!/usr/bin/env python3
"""
Parse SF133 files using Raw Data sheet instead of TAFS detail sheet.
This should be more reliable and consistent across different file formats and years.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

def detect_file_units(file_path):
    """
    Detect if a file uses thousands or dollars as units by checking the TAFS detail sheet.
    Returns a multiplier: 1000 for thousands, 1 for dollars.
    """
    try:
        # Check the TAFS detail sheet for unit indicators
        df_tafs = pd.read_excel(file_path, sheet_name='TAFS detail', engine='openpyxl', nrows=5)
        
        # Convert all text to string and search for unit indicators
        text_content = ' '.join([
            str(val).lower() for row in df_tafs.values 
            for val in row if pd.notna(val)
        ])
        
        if 'thousand' in text_content:
            print(f"  📊 UNITS: Detected 'thousands' - applying 1000x multiplier")
            return 1000
        elif 'dollar' in text_content:
            print(f"  📊 UNITS: Detected 'dollars' - no multiplier needed")
            return 1
        else:
            print(f"  ⚠️  UNITS: Could not detect units, assuming dollars")
            return 1
            
    except Exception as e:
        print(f"  ⚠️  UNITS: Error detecting units ({e}), assuming dollars")
        return 1

# Column mapping from Raw Data sheet to standardized month names
RAW_DATA_COLUMN_MAPPING = {
    # Monthly columns (individual months) - these exist for some months
    'AMT_OCT': 'Oct',
    'AMT_NOV': 'Nov', 
    'AMT_DEC': 'Dec',  # Usually not present as individual column
    'AMT_JAN': 'Jan',
    'AMT_FEB': 'Feb',
    'AMT_MAR': 'Mar',  # Usually not present as individual column
    'AMT_APR': 'Apr',
    'AMT_MAY': 'May',
    'AMT_JUN': 'Jun',  # Usually not present as individual column
    'AMT_JUL': 'Jul',
    'AMT_AUG': 'Aug',
    'AMT_SEP': 'Sep',  # Usually not present as individual column
    
    # Quarterly columns - these represent the missing individual months
    'AMT1': 'Dec',  # December = 1st Quarter end
    'AMT2': 'Mar',  # March = 2nd Quarter end  
    'AMT3': 'Jun',  # June = 3rd Quarter end
    'AMT4': 'Sep',  # September = 4th Quarter end (fiscal year end)
}

# List of expected agencies (same as original)
TARGET_AGENCIES = [
    "Legislative Branch",
    "Judicial Branch", 
    "Department of Agriculture",
    "Department of Commerce",
    "Department of Defense-Military",
    "Department of Education",
    "Department of Energy",
    "Department of Health and Human Services",
    "Department of Homeland Security",
    "Department of Housing and Urban Development",
    "Department of the Interior",
    "Department of Justice",
    "Department of Labor",
    "Department of State",
    "Department of Transportation",
    "Department of the Treasury",
    "Department of Veterans Affairs",
    "Corps of Engineers-Civil Works",
    "Other Defense Civil Programs",
    "Environmental Protection Agency",
    "Executive Office of the President",
    "General Services Administration",
    "International Assistance Programs",
    "National Aeronautics and Space Administration",
    "National Science Foundation",
    "Office of Personnel Management",
    "Small Business Administration",
    "Social Security Administration",
    "Other Independent Agencies"
]

def find_agency_from_raw_data(df):
    """Find agency name from Raw Data sheet."""
    if len(df) > 0 and 'AGENCY' in df.columns:
        # Get the most common agency name (should be consistent across all rows)
        agency_names = df['AGENCY'].dropna().unique()
        if len(agency_names) > 0:
            agency_name = agency_names[0]
            
            # Clean up and match against target agencies
            agency_normalized = str(agency_name).replace('--', '-').lower()
            for target_agency in TARGET_AGENCIES:
                target_normalized = target_agency.lower()
                if target_normalized in agency_normalized:
                    return target_agency
                # Handle special cases
                if target_agency == "Department of Defense-Military" and "defense" in agency_normalized and ("military" in agency_normalized or "dod" in agency_normalized):
                    return target_agency
                if target_agency == "Corps of Engineers-Civil Works" and "corps of engineers" in agency_normalized and "civil" in agency_normalized:
                    return target_agency
                if target_agency == "Other Defense Civil Programs" and "other defense" in agency_normalized and "civil" in agency_normalized:
                    return target_agency
                    
            # If no exact match, return the original name
            return str(agency_name).strip()
    
    return "Unknown Agency"

def parse_sf133_raw_data(file_path):
    """Parse the Raw Data sheet from an SF 133 file."""
    print(f"Processing Raw Data: {file_path.name}")
    
    # Skip consolidated files that contain multiple agencies to avoid double-counting
    consolidated_files = ['2668331098.xlsx']  # Known consolidated file with multiple agencies
    if file_path.name in consolidated_files:
        print(f"  Skipping consolidated file to avoid double-counting agencies")
        return None
    
    try:
        # Check if Raw Data sheet exists
        xl_file = pd.ExcelFile(file_path, engine='openpyxl')
        sheet_names = xl_file.sheet_names
        
        if 'Raw Data' not in sheet_names:
            print(f"  No Raw Data sheet found")
            xl_file.close()
            return None
        
        # Detect units before reading Raw Data sheet
        unit_multiplier = detect_file_units(file_path)
        
        # Read Raw Data sheet
        df = pd.read_excel(file_path, sheet_name='Raw Data')
        
        if len(df) == 0:
            print(f"  Raw Data sheet is empty")
            xl_file.close()
            return None
        
        print(f"  Raw data dimensions: {df.shape}")
        
        # Apply unit multiplier to numeric columns (amounts)
        if unit_multiplier != 1:
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            for col in numeric_columns:
                # Skip metadata columns like LINENO, RPT_YR, etc.
                if col not in ['LINENO', 'RPT_YR', 'TRAG', 'TRACCT', 'ALLOC', 'FY1', 'FY2', 'SECTION_NO', 'LINE_TYPE']:
                    df[col] = df[col] * unit_multiplier
            print(f"  📊 Applied {unit_multiplier}x multiplier to {len(numeric_columns)} numeric columns")
        
        # Find agency name
        agency_name = find_agency_from_raw_data(df)
        print(f"  Agency: {agency_name}")
        
        # Rename columns according to our mapping
        columns_to_rename = {}
        available_month_columns = []
        
        for raw_col, standard_col in RAW_DATA_COLUMN_MAPPING.items():
            if raw_col in df.columns:
                columns_to_rename[raw_col] = standard_col
                available_month_columns.append(standard_col)
        
        # Apply column renaming
        df = df.rename(columns=columns_to_rename)
        
        print(f"  Available month columns: {available_month_columns}")
        
        # Add metadata columns
        df['Agency'] = agency_name
        df['Source_File'] = Path(file_path).name
        
        # Apply TAFS detail equivalent filtering
        # 1. Keep only rows with valid line numbers (LINENO column)  
        if 'LINENO' in df.columns:
            df = df[df['LINENO'].notna()]
            print(f"  Rows with line numbers: {len(df)}")
            
            # 2. Filter to standard line number ranges that appear in TAFS detail
            # TAFS detail typically shows line numbers like 1000-5000 range
            # Filter out any unusual/administrative line numbers outside normal budget reporting
            numeric_line_nos = pd.to_numeric(df['LINENO'], errors='coerce')
            standard_lines = df[(numeric_line_nos >= 1000) & (numeric_line_nos <= 9999)]
            print(f"  Rows with standard line numbers (1000-9999): {len(standard_lines)}")
            df = standard_lines
            
            # 3. Aggregate to match TAFS detail level: derive fiscal year info from TAFS for consistent grouping
            # Group by core fields that create unique TAFS entries for the website
            grouping_cols = ['BUREAU', 'OMB_ACCT', 'LINENO']
            
            # Parse fiscal year components from TAFS to match FY1/FY2 exactly
            def parse_tafs_to_match_fy1_fy2(tafs):
                """Extract FY1 and FY2 equivalents from TAFS string to match existing columns."""
                if pd.isna(tafs) or tafs == '':
                    return '', ''
                
                # Clean the TAFS string first to remove carriage returns and other special characters
                tafs_str = str(tafs)
                tafs_str = tafs_str.replace('_x000D_\n', '').replace('_x000D_', '').replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
                tafs_str = ' '.join(tafs_str.split()).strip()
                
                # Remove description part: "17-1804 /20 - Operation and Maintenance, Navy" -> "17-1804 /20"
                if ' - ' in tafs_str:
                    code_part = tafs_str.split(' - ')[0].strip()
                else:
                    code_part = tafs_str.strip()
                
                # Look for period pattern after account number
                # Examples: "17-1804 /20", "73-0100 12/13", "12-2500 /X"
                parts = code_part.split()
                if len(parts) >= 2:
                    period_part = parts[-1]  # Last part should be the period
                    
                    if period_part == '/X':
                        # /X pattern -> FY1='', FY2='X'
                        return '', 'X'
                    elif period_part.startswith('/'):
                        # Single year: "/20" -> FY1='', FY2='20'
                        year = period_part[1:].strip()
                        return '', year
                    elif '/' in period_part and not period_part.startswith('/'):
                        # Multi-year: "12/13" -> FY1='12', FY2='13' 
                        year_parts = period_part.split('/')
                        if len(year_parts) == 2:
                            fy1 = year_parts[0].strip()
                            fy2 = year_parts[1].strip()
                            return fy1, fy2
                
                # Fallback: couldn't parse
                return '', ''
            
            # Generate derived fiscal year fields from TAFS parsing
            print("  Parsing fiscal year components from TAFS...")
            df['DERIVED_FY1'] = df['TAFS'].apply(lambda x: parse_tafs_to_match_fy1_fy2(x)[0])
            df['DERIVED_FY2'] = df['TAFS'].apply(lambda x: parse_tafs_to_match_fy1_fy2(x)[1])
            
            # LOGGING: Check derived field completeness
            total_records = len(df)
            empty_fy1 = (df['DERIVED_FY1'] == '').sum()
            empty_fy2 = (df['DERIVED_FY2'] == '').sum()
            print(f"  📊 DERIVED_FY1: {total_records - empty_fy1:,} populated, {empty_fy1:,} empty ({empty_fy1/total_records*100:.1f}% empty)")
            print(f"  📊 DERIVED_FY2: {total_records - empty_fy2:,} populated, {empty_fy2:,} empty ({empty_fy2/total_records*100:.1f}% empty)")
            
            # Show examples of derived values
            sample_derived = df[['TAFS', 'DERIVED_FY1', 'DERIVED_FY2']].head(10)
            print(f"  📋 Sample derived values:")
            for _, row in sample_derived.iterrows():
                print(f"    TAFS: '{row['TAFS']}' → FY1: '{row['DERIVED_FY1']}', FY2: '{row['DERIVED_FY2']}'")
            
            # Check for problematic patterns
            both_empty = ((df['DERIVED_FY1'] == '') & (df['DERIVED_FY2'] == '')).sum()
            print(f"  ⚠️  Records with BOTH FY1 and FY2 empty: {both_empty:,} ({both_empty/total_records*100:.1f}%)")
            
            # Derive ALLOC from TAFS (bureau code)
            def derive_alloc_from_tafs(tafs):
                """Extract bureau code from TAFS string - handles both 2-part and 3-part codes."""
                if pd.isna(tafs) or tafs == '':
                    return ''
                
                # Clean the TAFS string first to remove carriage returns
                tafs_str = str(tafs)
                tafs_str = tafs_str.replace('_x000D_\n', '').replace('_x000D_', '').replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
                tafs_str = ' '.join(tafs_str.split()).strip()
                
                # Remove description part if present
                if ' - ' in tafs_str:
                    code_part = tafs_str.split(' - ')[0].strip()
                else:
                    code_part = tafs_str.strip()
                
                # Remove period part: "14-91-0400 /24" -> "14-91-0400"
                if ' /' in code_part:
                    account_part = code_part.split(' /')[0].strip()
                elif ' ' in code_part and not code_part.split()[1].startswith('/'):
                    # Handle cases like "14-91-0400 16/21"
                    account_part = code_part.split()[0].strip()
                else:
                    account_part = code_part.strip()
                
                # Extract bureau code based on TAFS format
                parts = account_part.split('-')
                
                if len(parts) >= 3:
                    # 3-part format: "14-91-0400" -> bureau code is "91" (middle part)
                    return parts[1].strip()
                elif len(parts) == 2:
                    # 2-part format: "48-1550" -> bureau code is "48" (first part = agency code)
                    # For 2-part codes, we use the agency code as the bureau identifier
                    return parts[0].strip()
                else:
                    # Single part or invalid format
                    return ''
            
            print("  Deriving ALLOC from TAFS...")
            df['DERIVED_ALLOC'] = df['TAFS'].apply(derive_alloc_from_tafs)
            
            # LOGGING: Check ALLOC derivation completeness
            empty_alloc = (df['DERIVED_ALLOC'] == '').sum()
            print(f"  📊 DERIVED_ALLOC: {total_records - empty_alloc:,} populated, {empty_alloc:,} empty ({empty_alloc/total_records*100:.1f}% empty)")
            
            # Show unique ALLOC values (limited)
            unique_allocs = df['DERIVED_ALLOC'].unique()
            print(f"  📋 Unique DERIVED_ALLOC values: {len(unique_allocs)} total")
            print(f"    Examples: {list(unique_allocs[:10])}")
            
            # Check for records missing ALL derived fields
            all_derived_empty = ((df['DERIVED_FY1'] == '') & (df['DERIVED_FY2'] == '') & (df['DERIVED_ALLOC'] == '')).sum()
            print(f"  🚨 Records missing ALL derived fields: {all_derived_empty:,} ({all_derived_empty/total_records*100:.1f}%)")
            
            # VALIDATION: If FY1/FY2 exist, derived fields MUST match exactly
            if 'FY1' in df.columns and 'FY2' in df.columns:
                print("  🔍 Validating TAFS parsing against existing FY1/FY2 fields...")
                
                # Clean and normalize fields for comparison 
                def normalize_fy_field(field):
                    """Normalize FY field for comparison: handle decimal, leading zeros, etc."""
                    if pd.isna(field) or field == '' or str(field) == 'nan':
                        return ''
                    
                    field_str = str(field).strip()
                    
                    # Handle decimal values: '12.0' -> '12'
                    if '.' in field_str:
                        try:
                            field_float = float(field_str)
                            if field_float == int(field_float):
                                field_str = str(int(field_float))
                        except ValueError:
                            pass
                    
                    # Handle leading zeros: '06' vs '6' should be equivalent
                    if field_str.isdigit():
                        field_str = str(int(field_str)).zfill(2) if len(field_str) <= 2 else field_str
                    
                    # Handle special values
                    if field_str.upper() == 'X':
                        return 'X'
                        
                    return field_str
                
                df['FY1_CLEAN'] = df['FY1'].apply(normalize_fy_field)
                df['FY2_CLEAN'] = df['FY2'].apply(normalize_fy_field)
                df['DERIVED_FY1_CLEAN'] = df['DERIVED_FY1'].apply(normalize_fy_field)
                df['DERIVED_FY2_CLEAN'] = df['DERIVED_FY2'].apply(normalize_fy_field)
                
                # Find rows where original FY1/FY2 have actual data (not empty/nan)
                has_fy1_data = (df['FY1_CLEAN'] != '') & (df['FY1_CLEAN'] != 'nan')
                has_fy2_data = (df['FY2_CLEAN'] != '') & (df['FY2_CLEAN'] != 'nan')
                
                # Check normalized matches where original data exists
                fy1_matches = df.loc[has_fy1_data, 'FY1_CLEAN'] == df.loc[has_fy1_data, 'DERIVED_FY1_CLEAN']
                fy2_matches = df.loc[has_fy2_data, 'FY2_CLEAN'] == df.loc[has_fy2_data, 'DERIVED_FY2_CLEAN']
                
                fy1_match_rate = fy1_matches.mean() * 100 if len(fy1_matches) > 0 else 100
                fy2_match_rate = fy2_matches.mean() * 100 if len(fy2_matches) > 0 else 100
                
                print(f"     FY1 validation: {fy1_match_rate:.1f}% ({len(fy1_matches)} records tested)")
                print(f"     FY2 validation: {fy2_match_rate:.1f}% ({len(fy2_matches)} records tested)")
                
                # STRICT VALIDATION: Must be 100% match or we fail
                if fy1_match_rate < 100 or fy2_match_rate < 100:
                    print("  ❌ VALIDATION FAILED: TAFS parsing does not match FY1/FY2 exactly")
                    print("     Showing mismatches:")
                    
                    if fy1_match_rate < 100:
                        mismatches = df[has_fy1_data & ~fy1_matches][['TAFS', 'FY1_CLEAN', 'DERIVED_FY1_CLEAN']].head(3)
                        for _, row in mismatches.iterrows():
                            print(f"       FY1: '{row['FY1_CLEAN']}' vs '{row['DERIVED_FY1_CLEAN']}' from {row['TAFS']}")
                    
                    if fy2_match_rate < 100:
                        mismatches = df[has_fy2_data & ~fy2_matches][['TAFS', 'FY2_CLEAN', 'DERIVED_FY2_CLEAN']].head(3)
                        for _, row in mismatches.iterrows():
                            print(f"       FY2: '{row['FY2_CLEAN']}' vs '{row['DERIVED_FY2_CLEAN']}' from {row['TAFS']}")
                    
                    raise ValueError("TAFS parsing validation failed - derived fields do not match FY1/FY2")
                
                print("  ✅ TAFS parsing validation PASSED - using derived fields for grouping")
            else:
                print("  📝 No FY1/FY2 columns found - using derived fields (older year)")
            
            # VALIDATION: If ALLOC exists, derived ALLOC MUST match exactly for non-missing values
            if 'ALLOC' in df.columns:
                print("  🔍 Validating ALLOC derivation against existing ALLOC field...")
                
                # Clean and normalize ALLOC fields for comparison
                df['ALLOC_CLEAN'] = df['ALLOC'].apply(normalize_fy_field)
                df['DERIVED_ALLOC_CLEAN'] = df['DERIVED_ALLOC'].apply(normalize_fy_field)
                
                # Find rows where original ALLOC has actual data (not empty/nan)
                has_alloc_data = (df['ALLOC_CLEAN'] != '') & (df['ALLOC_CLEAN'] != 'nan')
                
                # Check normalized matches where original data exists
                alloc_matches = df.loc[has_alloc_data, 'ALLOC_CLEAN'] == df.loc[has_alloc_data, 'DERIVED_ALLOC_CLEAN']
                
                alloc_match_rate = alloc_matches.mean() * 100 if len(alloc_matches) > 0 else 100
                
                print(f"     ALLOC validation: {alloc_match_rate:.1f}% ({len(alloc_matches)} records tested)")
                
                # STRICT VALIDATION: Must be 100% match or we fail
                if alloc_match_rate < 100:
                    print("  ❌ VALIDATION FAILED: ALLOC derivation does not match existing ALLOC exactly")
                    print("     Showing mismatches:")
                    
                    mismatches = df[has_alloc_data & ~alloc_matches][['TAFS', 'ALLOC_CLEAN', 'DERIVED_ALLOC_CLEAN']].head(3)
                    for _, row in mismatches.iterrows():
                        print(f"       ALLOC: '{row['ALLOC_CLEAN']}' vs '{row['DERIVED_ALLOC_CLEAN']}' from {row['TAFS']}")
                    
                    raise ValueError("ALLOC derivation validation failed - derived ALLOC does not match existing ALLOC")
                
                print("  ✅ ALLOC derivation validation PASSED - using derived ALLOC for grouping")
            else:
                print("  📝 No ALLOC column found - using derived ALLOC (older year)")
            
            # Always use derived fields for consistent grouping across all years
            # This mimics the old logic that used ['BUREAU', 'OMB_ACCT', 'LINENO', 'FY1', 'FY2', 'ALLOC', ...]
            grouping_cols.extend(['DERIVED_FY1', 'DERIVED_FY2', 'DERIVED_ALLOC'])
            
            # Also include other fields that help distinguish account variations
            additional_fields = ['TRACCT', 'TRAG']
            for field in additional_fields:
                if field in df.columns:
                    grouping_cols.append(field)
            
            print(f"  Final grouping columns: {grouping_cols}")
            print(f"  Checking for NaN values in grouping columns...")
            for col in grouping_cols:
                nan_count = df[col].isna().sum()
                if nan_count > 0:
                    print(f"    {col}: {nan_count} NaN values")
                else:
                    print(f"    {col}: No NaN values")
            
            if len(grouping_cols) >= 3:  # We need at least Bureau, Account, Line Number
                print(f"  🔄 STARTING AGGREGATION:")
                print(f"    Grouping by: {grouping_cols}")
                print(f"    Input records: {len(df):,}")
                
                # Check for empty derived fields before grouping
                for col in ['DERIVED_FY1', 'DERIVED_FY2', 'DERIVED_ALLOC']:
                    if col in grouping_cols:
                        empty_count = (df[col] == '').sum()
                        print(f"    {col} empty values: {empty_count:,} ({empty_count/len(df)*100:.1f}%)")
                
                # Filter out rows with NaN values in any grouping column
                before_filter = len(df)
                df_filtered = df.dropna(subset=grouping_cols)
                after_filter = len(df_filtered)
                
                if after_filter < before_filter:
                    print(f"    📉 Filtered out {before_filter - after_filter:,} rows with NaN values in grouping columns")
                    print(f"    📊 Records after NaN filter: {after_filter:,}")
                
                # Show expected vs actual grouping behavior
                unique_groups_before = df_filtered.groupby(grouping_cols).ngroups
                print(f"    🎯 Expected output groups: {unique_groups_before:,}")
                print(f"    📈 Aggregation ratio: {after_filter/unique_groups_before:.1f} records per group")
                
                if after_filter == 0:
                    print(f"  ERROR: No rows remaining after filtering NaN values in grouping columns")
                    return None
                
                # Identify month columns to sum
                month_cols = [col for col in df_filtered.columns if col in RAW_DATA_COLUMN_MAPPING.values()]
                print(f"  Month columns to aggregate: {month_cols}")
                
                # Create aggregation dictionary
                agg_dict = {}
                for col in df_filtered.columns:
                    if col in month_cols:
                        agg_dict[col] = 'sum'  # Sum monthly amounts
                    elif col in grouping_cols:
                        continue  # These are grouping columns
                    elif col in ['Agency', 'Source_File']:
                        agg_dict[col] = 'first'  # Keep metadata
                    else:
                        agg_dict[col] = 'first'  # Take first value for other descriptive fields
                
                # Group and aggregate
                print(f"    🔄 Performing aggregation...")
                df = df_filtered.groupby(grouping_cols, as_index=False).agg(agg_dict)
                print(f"    ✅ AGGREGATION COMPLETE:")
                print(f"      📊 Output records: {len(df):,}")
                print(f"      📉 Compression ratio: {after_filter/len(df):.1f}:1 (input:output)")
                print(f"      🎯 Actual groups created: {len(df):,}")
                
                # Check if over-aggregation occurred
                if after_filter/len(df) > 50:  # More than 50:1 compression is suspicious
                    print(f"      🚨 WARNING: Very high compression ratio - possible over-aggregation!")
                    print(f"      🔍 This suggests derived fields may not be differentiating records properly")
                
                # Show sample of grouped data
                print(f"    📋 Sample grouped records:")
                sample_cols = ['BUREAU', 'OMB_ACCT', 'DERIVED_FY1', 'DERIVED_FY2', 'DERIVED_ALLOC']
                available_cols = [col for col in sample_cols if col in df.columns]
                for i, (_, row) in enumerate(df[available_cols].head(5).iterrows()):
                    print(f"      {i+1}. {dict(row)}")
                
                print(f"  📊 Final aggregated data: {len(df):,} records (was {before_filter:,})")
            
        else:
            print(f"  Warning: No LINENO column found")
        
        xl_file.close()
        return df
        
    except Exception as e:
        print(f"  Error processing {file_path}: {str(e)}")
        return None

def parse_all_sf133_raw_data(source_dir='raw_data/august'):
    """Process all SF 133 files using Raw Data sheets."""
    sf133_dir = Path(source_dir)
    
    # Ensure data directory exists
    output_data_dir = Path('data')
    output_data_dir.mkdir(exist_ok=True)
    
    # Get all Excel files
    excel_files = list(sf133_dir.glob('*.xlsx')) + list(sf133_dir.glob('*.xls'))
    print(f"Found {len(excel_files)} Excel files to process\n")
    
    # Process each file
    all_data = []
    successful_files = 0
    agencies_processed = set()
    
    for file_path in excel_files:
        try:
            df = parse_sf133_raw_data(file_path)
            if df is not None and len(df) > 0:
                all_data.append(df)
                successful_files += 1
                agencies_processed.add(df['Agency'].iloc[0])
                print(f"  Success: {len(df)} rows")
            else:
                print(f"  Skipping - no data extracted")
        except Exception as e:
            print(f"  Error processing {file_path.name}: {str(e)}")
        print()
    
    # Combine all data
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Clean corrupted characters from text fields
        def clean_text_field(text):
            """Clean corrupted characters from text fields."""
            if pd.isna(text):
                return text
            text_str = str(text)
            # Remove various forms of corrupted line endings and special characters
            text_str = text_str.replace('_x000D_\n', '').replace('_x000D_', '').replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
            # Clean up multiple spaces
            text_str = ' '.join(text_str.split())
            return text_str
        
        # Apply cleaning to all text columns that might contain corrupted data
        text_columns = ['TAFS', 'BUREAU', 'AGENCY_TITLE', 'BUREAU_TITLE', 'OMB_ACCOUNT', 'LINE_DESC']
        for col in text_columns:
            if col in combined_df.columns:
                combined_df[col] = combined_df[col].apply(clean_text_field)
        
        # Save the master table
        output_path = Path('site/data/sf133_raw_data_master.csv')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        combined_df.to_csv(output_path, index=False)
        
        print(f"\n=== RAW DATA PROCESSING SUMMARY ===")
        print(f"Successfully processed: {successful_files} files")
        print(f"Total agencies: {len(agencies_processed)}")
        print(f"Agencies found:")
        for agency in sorted(agencies_processed):
            count = len(combined_df[combined_df['Agency'] == agency])
            print(f"  - {agency} ({count:,} rows)")
        print(f"\nTotal rows: {len(combined_df):,}")
        print(f"Raw data master table saved to: {output_path}")
        
        # Show available month columns
        month_columns = [col for col in combined_df.columns if any(month in col for month in ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Q'])]
        print(f"\nAvailable month columns: {month_columns}")
        
        return output_path
    else:
        print("No data was successfully extracted from any files.")
        return None

if __name__ == "__main__":
    import sys
    
    # Allow specifying source directory as command line argument
    source_dir = sys.argv[1] if len(sys.argv) > 1 else 'raw_data/august'
    parse_all_sf133_raw_data(source_dir)