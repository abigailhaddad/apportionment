#!/usr/bin/env python3
"""
Download SF 133 reports for Department of Education from MAX.gov portal
SF 133 reports contain budget execution data including obligations and unobligated balances
"""
import requests
import pandas as pd
import os
from datetime import datetime
import re
from bs4 import BeautifulSoup
import time

def get_sf133_links():
    """Get all SF 133 report links from the MAX portal page"""
    
    base_url = "https://portal.max.gov/portal/document/SF133/Budget/"
    page_url = base_url + "FY%202025%20-%20SF%20133%20Reports%20on%20Budget%20Execution%20and%20Budgetary%20Resources.html"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    print(f"Fetching SF 133 links from: {page_url}")
    
    try:
        response = requests.get(page_url, headers=headers, timeout=30)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all Excel file links
            excel_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if '.xlsx' in href or '.xls' in href:
                    # Get the text description
                    text = link.get_text(strip=True)
                    
                    # Build full URL if relative
                    if not href.startswith('http'):
                        if href.startswith('/'):
                            href = 'https://portal.max.gov' + href
                        else:
                            href = base_url + href
                    
                    excel_links.append({
                        'url': href,
                        'description': text,
                        'filename': href.split('/')[-1]
                    })
            
            print(f"Found {len(excel_links)} Excel files")
            
            # Print all links for debugging
            print("\n=== ALL EXCEL FILES FOUND ===")
            for i, link in enumerate(excel_links):
                print(f"{i+1}. {link['description']}")
                print(f"   File: {link['filename']}")
                print(f"   URL: {link['url']}")
                print()
            
            return excel_links
        else:
            print(f"Error fetching page: Status {response.status_code}")
            return []
    except Exception as e:
        print(f"Error: {e}")
        return []

def identify_education_files(links):
    """Identify which files contain Department of Education data"""
    
    print("\n=== IDENTIFYING EDUCATION FILES ===")
    education_files = []
    
    for link in links:
        # Check if filename or description mentions Education
        # SF 133 files might be organized by agency or might be government-wide
        desc_lower = link['description'].lower()
        file_lower = link['filename'].lower()
        
        print(f"\nChecking: {link['description']}")
        
        # Pattern 1: File specifically for Education
        if 'education' in desc_lower or 'education' in file_lower or '018' in desc_lower:
            education_files.append(link)
            print(f"  ✓ Found Education-specific file: {link['filename']}")
        
        # Pattern 2: Government-wide file that would contain Education data
        elif 'all' in desc_lower or 'government' in desc_lower or 'combined' in desc_lower:
            education_files.append(link)
            print(f"  ✓ Found government-wide file: {link['filename']}")
        
        # Pattern 3: Monthly files (e.g., "December 2024")
        elif any(month in desc_lower for month in ['january', 'february', 'march', 'april', 'may', 'june', 
                                                   'july', 'august', 'september', 'october', 'november', 'december']):
            education_files.append(link)
            print(f"  ✓ Found monthly file: {link['filename']}")
        
        # Pattern 4: FY files
        elif 'fy' in file_lower or 'fiscal year' in desc_lower:
            education_files.append(link)
            print(f"  ✓ Found fiscal year file: {link['filename']}")
        else:
            print(f"  ✗ Not selected")
    
    return education_files

def download_sf133_file(link, output_dir):
    """Download a single SF 133 file"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    filename = link['filename']
    filepath = os.path.join(output_dir, filename)
    
    # Skip if already downloaded
    if os.path.exists(filepath):
        print(f"Already downloaded: {filename}")
        return filepath
    
    print(f"Downloading: {filename}")
    print(f"From: {link['url']}")
    
    try:
        response = requests.get(link['url'], headers=headers, timeout=60)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(response.content)
            print(f"Successfully downloaded: {filename}")
            return filepath
        else:
            print(f"Error downloading: Status {response.status_code}")
            return None
    except Exception as e:
        print(f"Error downloading {filename}: {e}")
        return None

def extract_education_data(filepath):
    """Extract Department of Education data from SF 133 file"""
    
    print(f"\nExtracting Education data from: {os.path.basename(filepath)}")
    
    try:
        # Read Excel file - SF 133 reports often have multiple sheets
        xl_file = pd.ExcelFile(filepath)
        print(f"Available sheets: {xl_file.sheet_names}")
        
        education_data = []
        
        # Focus on Raw Data sheet which contains all the data
        if 'Raw Data' in xl_file.sheet_names:
            df = pd.read_excel(filepath, sheet_name='Raw Data')
            
            # Check columns
            print(f"  Columns in Raw Data: {df.columns.tolist()[:10]}...")
            
            # Department of Education is typically "Department of Education" in AGENCY_TITLE
            # or "91" in AGENCY column
            if 'AGENCY_TITLE' in df.columns:
                # Filter for Education
                education_rows = df[
                    df['AGENCY_TITLE'].astype(str).str.contains('Department of Education', case=False, na=False) |
                    (df['AGENCY'].astype(str) == '91')  # Education agency code
                ]
                
                if len(education_rows) > 0:
                    education_rows['source_sheet'] = 'Raw Data'
                    education_rows['source_file'] = os.path.basename(filepath)
                    education_data.append(education_rows)
                    print(f"  Found {len(education_rows)} Education rows")
                    
                    # Show unique agencies in the file for debugging
                    unique_agencies = df['AGENCY_TITLE'].value_counts().head(10)
                    print(f"  Top agencies in file: {unique_agencies.to_dict()}")
                else:
                    print("  No Education rows found")
                    # Show what agencies are in the file
                    if 'AGENCY_TITLE' in df.columns:
                        unique_agencies = df['AGENCY_TITLE'].value_counts().head(10)
                        print(f"  Agencies in file: {unique_agencies.to_dict()}")
        
        if education_data:
            combined_df = pd.concat(education_data, ignore_index=True)
            return combined_df
        else:
            print("  No Education data found")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"Error processing file: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

def parse_sf133_lines(df):
    """Parse SF 133 line items for key budget execution data"""
    
    if df.empty:
        return pd.DataFrame()
    
    print("\nParsing SF 133 line items...")
    
    # Key SF 133 lines we need
    key_lines = {
        '1901': 'Total budgetary resources',
        '2190': 'Obligations incurred (cumulative)',
        '2204': 'Unobligated balance, end of period',
        '2412': 'Unexpired unobligated balance, end of period',
        '2413': 'Expired unobligated balance, end of period'
    }
    
    # Find line number column
    line_cols = [col for col in df.columns if 'line' in str(col).lower()]
    
    if line_cols:
        line_col = line_cols[0]
        
        # Filter for key lines
        key_data = df[df[line_col].astype(str).isin(key_lines.keys())].copy()
        
        # Add line descriptions
        key_data['line_description'] = key_data[line_col].astype(str).map(key_lines)
        
        print(f"Extracted {len(key_data)} key line items")
        return key_data
    else:
        print("Could not find line number column")
        return df

def main():
    """Main function to download and process SF 133 data for Education"""
    
    # Create data directory
    output_dir = '../raw_data/sf133'
    os.makedirs(output_dir, exist_ok=True)
    
    # Get SF 133 links
    links = get_sf133_links()
    
    if not links:
        print("\n⚠️  Could not fetch SF 133 links automatically.")
        print("Please check if you need to authenticate to access MAX.gov")
        print("You may need to manually download files from:")
        print("https://portal.max.gov/portal/document/SF133/Budget/")
        return
    
    # Identify Education-relevant files
    education_files = identify_education_files(links)
    
    if not education_files:
        print("\nNo Education-specific files found. Will check all files to find Education data...")
        # Check all files to find the Education one
        education_files = links  # Get all files
    
    print(f"\nWill process {len(education_files)} files to find Education data")
    
    # Download files and track which ones have Education data
    all_education_data = []
    file_summary = []
    
    for i, link in enumerate(education_files):
        print(f"\n--- Processing file {i+1} of {len(education_files)} ---")
        filepath = download_sf133_file(link, output_dir)
        
        if filepath:
            # Extract Education data
            education_df = extract_education_data(filepath)
            
            # Track file info
            file_info = {
                'filename': link['filename'],
                'url': link['url'],
                'has_education_data': not education_df.empty,
                'education_rows': len(education_df) if not education_df.empty else 0
            }
            file_summary.append(file_info)
            
            if not education_df.empty:
                print(f"  ✓ This file contains Education data!")
                # Parse key lines
                parsed_df = parse_sf133_lines(education_df)
                all_education_data.append(parsed_df)
        
        time.sleep(0.5)  # Be nice to the server
    
    # Save file summary
    summary_df = pd.DataFrame(file_summary)
    summary_df.to_csv(os.path.join(processed_dir, 'sf133_file_check_summary.csv'), index=False)
    print(f"\nSaved file summary to sf133_file_check_summary.csv")
    
    # Combine all Education data
    if all_education_data:
        final_df = pd.concat(all_education_data, ignore_index=True)
        
        # Save processed data
        processed_dir = '../processed_data/sf133'
        os.makedirs(processed_dir, exist_ok=True)
        
        output_file = os.path.join(processed_dir, 'education_sf133_data.csv')
        final_df.to_csv(output_file, index=False)
        
        print(f"\n=== Summary ===")
        print(f"Total Education SF 133 records: {len(final_df)}")
        if 'line_description' in final_df.columns:
            print("\nRecords by line item:")
            print(final_df['line_description'].value_counts())
        
        print(f"\nSaved to: {output_file}")
    else:
        print("\nNo Education data extracted from files")

if __name__ == "__main__":
    main()