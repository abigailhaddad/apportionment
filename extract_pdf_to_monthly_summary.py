#!/usr/bin/env python3
import pdfplumber
import re
import json
import csv
import pandas as pd
from collections import defaultdict

def extract_pdf_text_and_metadata(pdf_path):
    """
    Extract text from PDF and parse metadata with associated line items.
    Restructure to match the monthly summary CSV format.
    """
    
    # Metadata patterns based on actual PDF format
    metadata_patterns = {
        'budget_agency': r'BudgetAgency:\s*(.+)',
        'budget_bureau': r'BudgetBureau:\s*(.+)',
        'budget_account': r'BudgetAccount:\s*(.+)',
        'treasury_account': r'TreasuryAccount:\s*(.+)',
        'budget_account_id': r'BudgetAccountID:\s*([^\s]+)',
        'treasury_account_id': r'TreasuryAccountID:\s*(.+)'
    }
    
    # Pattern for line items (lines starting with 2490 or 2500)
    line_item_pattern = r'^(249[0-9]|250[0-9])\s+(.+)'
    
    results = []
    current_metadata = {}
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if not text:
                continue
                
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check for metadata patterns
                metadata_found = False
                for key, pattern in metadata_patterns.items():
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        value = re.sub(r'\s+', ' ', value)  # Clean spaces
                        current_metadata[key] = value
                        metadata_found = True
                        break
                
                # Check for line items (2490 or 2500 patterns)
                if not metadata_found:
                    line_match = re.match(line_item_pattern, line)
                    if line_match:
                        line_code = line_match.group(1)
                        line_data = line_match.group(2).strip()
                        
                        # Parse quarterly amounts from line data
                        # Format: "Description Q1_Amount Q2_Amount Q3_Amount Q4_Amount"
                        parts = line_data.split()
                        amounts = []
                        description_parts = []
                        
                        for part in parts:
                            # Try to parse as a number (with commas and decimals)
                            if re.match(r'^-?\d{1,3}(,\d{3})*(\.\d+)?$', part):
                                amounts.append(float(part.replace(',', '')))
                            else:
                                description_parts.append(part)
                        
                        description = ' '.join(description_parts)
                        
                        # Ensure we have 4 quarterly amounts
                        while len(amounts) < 4:
                            amounts.append(0.0)
                        
                        record = {
                            'page': page_num,
                            'line_code': line_code,
                            'description': description,
                            'q1_amount': amounts[0] if len(amounts) > 0 else 0.0,
                            'q2_amount': amounts[1] if len(amounts) > 1 else 0.0,
                            'q3_amount': amounts[2] if len(amounts) > 2 else 0.0,
                            'q4_amount': amounts[3] if len(amounts) > 3 else 0.0,
                            'metadata': current_metadata.copy()
                        }
                        results.append(record)
    
    return results

def restructure_to_monthly_format(pdf_records):
    """
    Restructure PDF data to match the monthly summary CSV format:
    Month,Fiscal_Year,Agency,Bureau,Account,Account_Number,Period_of_Performance,Expiration_Year,TAFS,Unobligated Balance (Line 2490),Budget Authority (Line 2500),Percentage Unobligated
    """
    
    monthly_records = []
    
    # Group records by metadata (each unique combination of agency/bureau/account)
    grouped_records = defaultdict(list)
    
    for record in pdf_records:
        # Create a key based on metadata
        metadata = record['metadata']
        key = (
            metadata.get('budget_agency', ''),
            metadata.get('budget_bureau', ''),
            metadata.get('budget_account', ''),
            metadata.get('budget_account_id', '')
        )
        grouped_records[key].append(record)
    
    # Process each group
    for (agency, bureau, account, account_id), records in grouped_records.items():
        
        # Find line 2490 (Unobligated Balance) and 2500 (Budget Authority) records
        line_2490_records = [r for r in records if r['line_code'] == '2490']
        line_2500_records = [r for r in records if r['line_code'] == '2500']
        
        # Skip groups without both line types
        if not line_2490_records or not line_2500_records:
            continue
        
        # For each quarter, create a record
        quarters = ['Q1', 'Q2', 'Q3', 'Q4']
        quarter_months = {'Q1': 'Dec', 'Q2': 'Mar', 'Q3': 'Jun', 'Q4': 'Sep'}  # Typical fiscal quarters
        
        for i, quarter in enumerate(quarters):
            # Get amounts for this quarter
            unobligated_balance = 0.0
            budget_authority = 0.0
            
            if line_2490_records:
                unobligated_balance = line_2490_records[0][f'q{i+1}_amount']
            
            if line_2500_records:
                budget_authority = line_2500_records[0][f'q{i+1}_amount']
            
            # Skip if both amounts are zero
            if unobligated_balance == 0 and budget_authority == 0:
                continue
            
            # Calculate percentage
            percentage_unobligated = 0.0
            if budget_authority > 0:
                percentage_unobligated = (unobligated_balance / budget_authority) * 100
            
            # Format amounts as strings with M suffix (millions)
            unob_formatted = f"${unobligated_balance/1000000:.1f}M" if unobligated_balance != 0 else "$0.0M"
            budget_formatted = f"${budget_authority/1000000:.1f}M" if budget_authority != 0 else "$0.0M"
            
            # Clean up account ID (remove leading zeros and format)
            clean_account_id = account_id
            if account_id:
                # Convert "001-13-0477" to "02-0477" format (remove first part, keep last two)
                parts = account_id.split('-')
                if len(parts) >= 3:
                    clean_account_id = f"{parts[1]}-{parts[2]}"
            
            # Create the monthly record
            monthly_record = {
                'Month': quarter_months[quarter],
                'Fiscal_Year': 2017,  # From PDF header
                'Agency': agency.replace('Branch', ' Branch') if agency else 'Legislative Branch',
                'Bureau': bureau or '',
                'Account': account or '',
                'Account_Number': clean_account_id or '',
                'Period_of_Performance': 'No Year',  # Default from existing data
                'Expiration_Year': 'No Year',        # Default from existing data
                'TAFS': f"{clean_account_id} /X - {account}" if clean_account_id and account else '',
                'Unobligated Balance (Line 2490)': unob_formatted,
                'Budget Authority (Line 2500)': budget_formatted,
                'Percentage Unobligated': f"{percentage_unobligated:.1f}%"
            }
            
            monthly_records.append(monthly_record)
    
    return monthly_records

def main():
    pdf_path = 'sample_sf133.pdf'
    
    try:
        print(f"Extracting and restructuring data from {pdf_path}...")
        
        # Extract raw PDF data
        pdf_records = extract_pdf_text_and_metadata(pdf_path)
        print(f"Extracted {len(pdf_records)} raw records from PDF")
        
        # Restructure to monthly format
        monthly_records = restructure_to_monthly_format(pdf_records)
        print(f"Restructured to {len(monthly_records)} monthly records")
        
        # Save as CSV in the same format as existing monthly summaries
        if monthly_records:
            df = pd.DataFrame(monthly_records)
            output_file = 'pdf_monthly_summary_2017.csv'
            df.to_csv(output_file, index=False)
            print(f"Saved to {output_file}")
            
            # Show sample records
            print(f"\nSample records:")
            print(df.head().to_string())
            
            print(f"\nColumn alignment check with existing monthly summary:")
            existing_cols = ['Month', 'Fiscal_Year', 'Agency', 'Bureau', 'Account', 'Account_Number', 
                           'Period_of_Performance', 'Expiration_Year', 'TAFS', 
                           'Unobligated Balance (Line 2490)', 'Budget Authority (Line 2500)', 
                           'Percentage Unobligated']
            pdf_cols = list(df.columns)
            
            print(f"Existing format columns: {existing_cols}")
            print(f"PDF extraction columns: {pdf_cols}")
            print(f"Columns match: {existing_cols == pdf_cols}")
        else:
            print("No records to save")
                
    except FileNotFoundError:
        print(f"Error: Could not find {pdf_path}")
    except Exception as e:
        print(f"Error processing PDF: {e}")

if __name__ == "__main__":
    main()