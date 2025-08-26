#!/usr/bin/env python3
"""
Download SF133 data files from MAX.gov portal.
Fetches all agency Excel files from the FY 2025 SF 133 report page.
"""

import requests
from bs4 import BeautifulSoup
from pathlib import Path
import time
from urllib.parse import urljoin
import re

def download_sf133_files():
    """Download all SF133 Excel files from MAX.gov."""
    
    # Base URL and page URL
    base_url = "https://portal.max.gov"
    page_url = "https://portal.max.gov/portal/document/SF133/Budget/FY%202025%20-%20SF%20133%20Reports%20on%20Budget%20Execution%20and%20Budgetary%20Resources.html"
    
    # Create raw data directory
    raw_data_dir = Path('raw_data/sf133')
    raw_data_dir.mkdir(parents=True, exist_ok=True)
    
    print("Downloading SF133 files from MAX.gov...")
    print(f"Source: {page_url}")
    print()
    
    # Headers to appear more like a browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        # Fetch the main page
        print("Fetching main page...")
        response = requests.get(page_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all Excel file links - they have .xlsx or .xls in href
        excel_links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '.xlsx' in href or '.xls' in href:
                # Get the text description - might be empty
                text = link.get_text(strip=True)
                
                # Build full URL if relative
                if not href.startswith('http'):
                    if href.startswith('/'):
                        full_url = 'https://portal.max.gov' + href
                    else:
                        full_url = urljoin(base_url + '/portal/document/SF133/Budget/', href)
                else:
                    full_url = href
                
                # Extract filename from URL
                filename = href.split('/')[-1]
                
                excel_links.append({
                    'url': full_url,
                    'description': text if text else filename,
                    'filename': filename
                })
        
        print(f"Found {len(excel_links)} Excel files")
        
        # Map known file IDs to agency names
        known_agencies = {
            '2580778228.xlsx': 'Legislative Branch',
            '2580778229.xlsx': 'Judicial Branch', 
            '2580778230.xlsx': 'Department of Agriculture',
            '2580778231.xlsx': 'Department of Commerce',
            '2580778232.xlsx': 'Department of Defense-Military',
            '2580778234.xlsx': 'Department of Education',
            '2580778235.xlsx': 'Department of Energy',
            '2580778237.xlsx': 'Department of Health and Human Services',
            '2580778238.xlsx': 'Department of Homeland Security',
            '2580778239.xlsx': 'Department of Housing and Urban Development',
            '2580778240.xlsx': 'Department of the Interior',
            '2580778242.xlsx': 'Other Independent Agencies',
            '2580778243.xlsx': 'Department of Justice',
            '2580778244.xlsx': 'Department of Labor',
            '2580778245.xlsx': 'Department of State',
            '2580778246.xlsx': 'Department of Transportation',
            '2580778247.xlsx': 'Department of the Treasury',
            '2580778248.xlsx': 'Department of Veterans Affairs',
            '2580778249.xlsx': 'Corps of Engineers-Civil Works',
            '2580778250.xlsx': 'Other Defense Civil Programs',
            '2580778251.xlsx': 'Environmental Protection Agency',
            '2580778252.xlsx': 'Executive Office of the President',
            '2580778253.xlsx': 'General Services Administration',
            '2580778254.xlsx': 'International Assistance Programs',
            '2580778255.xlsx': 'National Aeronautics and Space Administration',
            '2580778258.xlsx': 'National Science Foundation',
            '2580778259.xlsx': 'Office of Personnel Management',
            '2580778260.xlsx': 'Small Business Administration',
            '2580778262.xlsx': 'Social Security Administration'
        }
        
        # Download each file
        downloaded = 0
        skipped = 0
        failed = 0
        
        for link in excel_links:
            filename = link['filename']
            url = link['url']
            
            # Get agency name from mapping or use filename
            agency_name = known_agencies.get(filename, link['description'])
            
            filepath = raw_data_dir / filename
            
            # Skip if already downloaded
            if filepath.exists():
                print(f"  [{downloaded + skipped + failed + 1}/{len(excel_links)}] Already downloaded: {filename} ({agency_name})")
                skipped += 1
                continue
            
            print(f"  [{downloaded + skipped + failed + 1}/{len(excel_links)}] Downloading: {filename} ({agency_name})")
            print(f"    URL: {url}")
            
            try:
                # Download the file
                file_response = requests.get(url, headers=headers, timeout=60)
                file_response.raise_for_status()
                
                # Check if it's actually an Excel file
                content_type = file_response.headers.get('Content-Type', '')
                # Excel files start with PK (ZIP format)
                if file_response.content[:2] == b'PK' or 'excel' in content_type or 'spreadsheet' in content_type:
                    # Save the file
                    with open(filepath, 'wb') as f:
                        f.write(file_response.content)
                    
                    downloaded += 1
                    print(f"    Success! Saved {len(file_response.content)/1024/1024:.1f} MB")
                else:
                    print(f"    Failed - not an Excel file (Content-Type: {content_type})")
                    failed += 1
                    
            except Exception as e:
                print(f"    ERROR: {str(e)}")
                failed += 1
            
            # Small delay between downloads
            time.sleep(1)
        
        print(f"\n=== DOWNLOAD SUMMARY ===")
        print(f"Downloaded: {downloaded} files")
        print(f"Skipped (already exist): {skipped} files")
        print(f"Failed: {failed} files")
        print(f"Total files in directory: {len(list(raw_data_dir.glob('*.xlsx'))) + len(list(raw_data_dir.glob('*.xls')))}")
        
        return downloaded > 0 or len(list(raw_data_dir.glob('*.xlsx'))) > 0
        
    except Exception as e:
        print(f"ERROR: Failed to download SF133 files - {e}")
        return False

def clean_raw_data_directory():
    """Remove all existing Excel files from raw data directory."""
    raw_data_dir = Path('raw_data/sf133')
    
    if raw_data_dir.exists():
        excel_files = list(raw_data_dir.glob('*.xlsx')) + list(raw_data_dir.glob('*.xls'))
        if excel_files:
            print(f"\nCleaning up {len(excel_files)} existing files...")
            for file in excel_files:
                file.unlink()
            print("  Cleanup complete")
    
    # Ensure directory exists
    raw_data_dir.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    success = download_sf133_files()
    
    if not success:
        print("\nFailed to download files. Please check your internet connection and try again.")
        exit(1)