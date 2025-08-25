#!/usr/bin/env python3
"""
Download and parse the FAST Book from Treasury to get budget account metadata
"""
import requests
import pandas as pd
import os
from datetime import datetime

def download_fast_book():
    """Download Part II of the FAST Book (Excel file with account symbols)"""
    
    # Treasury FAST Book URLs
    base_url = "https://tfx.treasury.gov"
    
    # FAST Book Part II and III download URL
    fast_book_urls = [
        "https://tfx.treasury.gov/media/60111/download?inline"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    # Create data directory if it doesn't exist
    os.makedirs('../raw_data/fast_book', exist_ok=True)
    
    # Try each URL
    for url in fast_book_urls:
        print(f"Trying to download from: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                # Save the file
                filename = f"../raw_data/fast_book/fast_book_part2_{datetime.now().strftime('%Y%m%d')}.xlsx"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                print(f"Successfully downloaded to: {filename}")
                return filename
            else:
                print(f"  Status {response.status_code}")
        except Exception as e:
            print(f"  Error: {e}")
    
    # If direct download fails, provide instructions
    print("\n⚠️  Could not download FAST Book automatically.")
    print("Please manually download Part II from:")
    print("https://tfx.treasury.gov/reference-books/fast-book")
    print("And save it as: ../raw_data/fast_book/fast_book_part2.xlsx")
    return None

def parse_fast_book(filename):
    """Parse the FAST Book Excel file to extract account metadata"""
    
    if not filename or not os.path.exists(filename):
        print(f"File not found: {filename}")
        return None
    
    print(f"\nParsing FAST Book: {filename}")
    
    try:
        # Read the Excel file
        # FAST Book Part II typically has sheets for different fund types
        xl_file = pd.ExcelFile(filename)
        print(f"Available sheets: {xl_file.sheet_names}")
        
        # Combine all sheets into one dataframe
        all_accounts = []
        
        for sheet_name in xl_file.sheet_names:
            print(f"\nProcessing sheet: {sheet_name}")
            
            # Skip intro sheets
            if 'Intro' in sheet_name:
                continue
                
            # Read with different header rows to find the right structure
            for header_row in [0, 1, 2, 3]:
                try:
                    df = pd.read_excel(filename, sheet_name=sheet_name, header=header_row)
                    
                    # Check if we have meaningful column names
                    cols = list(df.columns)
                    if any('AID' in str(col) or 'Agency' in str(col) or 'TAS' in str(col) for col in cols):
                        print(f"  Found headers at row {header_row}")
                        print(f"  Columns: {cols[:10]}")
                        print(f"  Shape: {df.shape}")
                        
                        # Add sheet name as fund type indicator
                        df['fund_type_sheet'] = sheet_name
                        
                        # Preview first few rows
                        if len(df) > 0:
                            print(f"  First row sample: {df.iloc[0].to_dict()}")
                        
                        all_accounts.append(df)
                        break
                except Exception as e:
                    continue
        
        # Combine all accounts
        combined_df = pd.concat(all_accounts, ignore_index=True)
        
        # Save as CSV for easier use
        output_file = "../raw_data/fast_book/fast_book_accounts.csv"
        combined_df.to_csv(output_file, index=False)
        print(f"\nSaved parsed data to: {output_file}")
        
        return combined_df
        
    except Exception as e:
        print(f"Error parsing file: {e}")
        return None

def extract_education_accounts(df):
    """Extract Department of Education-specific accounts from FAST Book data"""
    
    if df is None:
        return None
    
    # DHS agency code is typically 070
    # But let's check for any column that might contain agency codes
    possible_agency_cols = ['Agency Code', 'agency_code', 'Agency', 'AGENCY', 
                           'Agency Identifier', 'AID', 'Agency ID']
    
    agency_col = None
    for col in possible_agency_cols:
        if col in df.columns:
            agency_col = col
            break
    
    if agency_col:
        # Filter for Department of Education - need to check the actual agency name
        # Also try using the AID column if it exists
        if 'AID' in df.columns:
            # Use AID column for filtering - Education is typically 018 or 18
            education_df = df[(df['AID'] == 18) | (df['AID'] == '18') | (df['AID'] == '018')].copy()
        else:
            # Use agency name
            education_df = df[df[agency_col].str.contains('Department of Education', case=False, na=False)].copy()
        
        print(f"\nFound {len(education_df)} Department of Education accounts")
        
        # Also check what unique agency values we have
        print(f"Sample agency values for debugging:")
        
        # Save Education-specific accounts
        education_output = "../raw_data/fast_book/education_fast_book_accounts.csv"
        education_df.to_csv(education_output, index=False)
        print(f"Saved Department of Education accounts to: {education_output}")
        
        return education_df
    else:
        print("Could not find agency code column")
        print(f"Available columns: {list(df.columns)}")
        return None

def main():
    """Main function to download and process FAST Book"""
    
    # Download FAST Book
    filename = download_fast_book()
    
    if not filename:
        # Check if we have a manually downloaded file
        manual_file = "../raw_data/fast_book/fast_book_part2.xlsx"
        if os.path.exists(manual_file):
            print(f"\nUsing manually downloaded file: {manual_file}")
            filename = manual_file
        else:
            print("\nPlease download the FAST Book manually and run this script again.")
            return
    
    # Parse the FAST Book
    df = parse_fast_book(filename)
    
    if df is not None:
        # Extract Department of Education accounts
        education_df = extract_education_accounts(df)
        
        # Print summary
        if education_df is not None:
            print("\n=== Department of Education FAST Book Summary ===")
            print(f"Total Department of Education accounts: {len(education_df)}")
            if 'fund_type_sheet' in education_df.columns:
                print("\nAccounts by fund type:")
                print(education_df['fund_type_sheet'].value_counts())

if __name__ == "__main__":
    main()