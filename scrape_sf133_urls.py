#!/usr/bin/env python3
"""
Scrape SF133 URLs from MAX.gov portal pages and update sf133_urls.json.
This script finds all available fiscal year links from the main SF133 page.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from pathlib import Path

def scrape_sf133_urls():
    """Scrape all available SF133 URLs from the FACTS II portal page."""
    
    # Main page with all fiscal years
    facts_url = "https://portal.max.gov/portal/document/SF133/Budget/FACTS%20II%20-%20SF%20133%20Report%20on%20Budget%20Execution%20and%20Budgetary%20Resources.html"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    print("Scraping SF133 URLs from FACTS II page...")
    print(f"Source: {facts_url}")
    print()
    
    # Try scraping first
    sf133_links = {}
    
    try:
        # Fetch the FACTS II page
        response = requests.get(facts_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all links that contain "FY" and "SF 133"
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True)
            
            # Look for fiscal year links
            fy_match = re.search(r'FY\s*(\d{4})', text, re.IGNORECASE)
            if fy_match and 'SF 133' in text:
                year = fy_match.group(1)
                
                # Build full URL if relative
                if not href.startswith('http'):
                    if href.startswith('/'):
                        full_url = 'https://portal.max.gov' + href
                    else:
                        full_url = 'https://portal.max.gov/portal/document/SF133/Budget/' + href
                else:
                    full_url = href
                
                sf133_links[year] = full_url
                print(f"Found FY {year}: {text}")
        
        # Also check for any direct URL patterns in href attributes
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Look for FY pattern in URLs
            fy_match = re.search(r'FY%20(\d{4})', href)
            if fy_match and 'SF%20133' in href:
                year = fy_match.group(1)
                
                if not href.startswith('http'):
                    if href.startswith('/'):
                        full_url = 'https://portal.max.gov' + href
                    else:
                        full_url = 'https://portal.max.gov/portal/document/SF133/Budget/' + href
                else:
                    full_url = href
                
                if year not in sf133_links:
                    sf133_links[year] = full_url
                    print(f"Found FY {year} (from URL pattern)")
                    
    except Exception as e:
        print(f"WARNING: Web scraping failed - {e}")
        print("Falling back to known pattern...")
    
    # If scraping failed or found few results, use known pattern
    if len(sf133_links) < 5:
        print("Using known URL pattern to generate fiscal year links...")
        
        # Generate URLs for FY 1998-2025 using known pattern
        base_pattern = "https://portal.max.gov/portal/document/SF133/Budget/FY%20{year}%20-%20SF%20133%20Reports%20on%20Budget%20Execution%20and%20Budgetary%20Resources.html"
        
        for year in range(1998, 2026):
            year_str = str(year)
            url = base_pattern.format(year=year)
            sf133_links[year_str] = url
            print(f"Generated FY {year}")
    
    print(f"\nFound {len(sf133_links)} fiscal years total")
    return sf133_links

def update_urls_json(new_urls):
    """Update sf133_urls.json with newly scraped URLs."""
    
    json_file = Path('sf133_urls.json')
    
    # Load existing URLs if file exists
    if json_file.exists():
        with open(json_file, 'r') as f:
            data = json.load(f)
    else:
        data = {"sf133_urls": {}}
    
    # Update with new URLs
    original_count = len(data["sf133_urls"])
    data["sf133_urls"].update(new_urls)
    
    # Sort by year
    sorted_urls = dict(sorted(data["sf133_urls"].items(), key=lambda x: int(x[0])))
    data["sf133_urls"] = sorted_urls
    
    # Save back to file
    with open(json_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    new_count = len(data["sf133_urls"])
    added_count = new_count - original_count
    
    print(f"\nUpdated sf133_urls.json:")
    print(f"  Original URLs: {original_count}")
    print(f"  New URLs added: {added_count}")  
    print(f"  Total URLs: {new_count}")
    
    print(f"\nAll available years:")
    for year in sorted(data["sf133_urls"].keys(), key=int):
        print(f"  {year}")

if __name__ == "__main__":
    # Scrape URLs from the FACTS II page
    urls = scrape_sf133_urls()
    
    if urls:
        # Update the JSON file
        update_urls_json(urls)
        
        print(f"\n✓ Successfully updated sf133_urls.json with {len(urls)} fiscal years")
        print("You can now use these URLs with your existing download workflow!")
    else:
        print("Failed to scrape URLs. Please check your internet connection and try again.")
        exit(1)