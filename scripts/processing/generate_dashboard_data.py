#!/usr/bin/env python3
"""
Generate optimized data files for the dashboard
Creates smaller, pre-aggregated files to improve dashboard loading performance
"""

import json
import pandas as pd
from datetime import datetime
import os

def load_json(filepath):
    """Load JSON file"""
    print(f"Loading {filepath}...")
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    # Handle both {data: [...]} and plain array formats
    if isinstance(data, dict) and 'data' in data:
        return data['data']
    return data

def get_recent_apportionments(detail_file='processed_data/appropriations/dhs_tas_aggregated_detail.csv', limit=10):
    """Get the most recent apportionment actions with full details"""
    try:
        df = pd.read_csv(detail_file)
        
        # Convert approval_date to datetime
        df['approval_date'] = pd.to_datetime(df['approval_date'])
        
        # Get unique apportionments by file_id and approval_date
        unique_apportionments = df.groupby(['file_id', 'approval_date', 'bureau', 'account', 
                                           'funds_provided_by', 'approver_title']).agg({
            'amount': 'sum'
        }).reset_index()
        
        # Sort by approval date and get most recent
        recent = unique_apportionments.nlargest(limit, 'approval_date')
        
        # Format for display
        recent_list = []
        for _, row in recent.iterrows():
            recent_list.append({
                'approval_date': row['approval_date'].isoformat(),
                'component': row['bureau'],
                'account': row['account'],
                'amount': float(row['amount']),
                'funds_source': row['funds_provided_by'],
                'approver': row['approver_title']
            })
        
        return recent_list
    except Exception as e:
        print(f"Error getting recent apportionments: {e}")
        return []

def generate_appropriations_summary(data):
    """Generate appropriations summary by component and fiscal year"""
    df = pd.DataFrame(data)
    
    # Check which field name is used for component
    component_field = 'component' if 'component' in df.columns else 'bureau'
    
    # Group by fiscal_year and component
    summary = df.groupby(['fiscal_year', component_field]).agg({
        'amount': 'sum'
    }).reset_index()
    
    # Rename to component for consistency
    if component_field != 'component':
        summary.rename(columns={component_field: 'component'}, inplace=True)
    
    # Also get account-level summary for drill-down
    account_summary = df.groupby(['fiscal_year', component_field, 'account']).agg({
        'amount': 'sum'
    }).reset_index()
    
    # Rename to component for consistency
    if component_field != 'component':
        account_summary.rename(columns={component_field: 'component'}, inplace=True)
    
    return {
        'by_component': summary.to_dict('records'),
        'by_account': account_summary.to_dict('records'),
        'total_by_year': df.groupby('fiscal_year')['amount'].sum().to_dict()
    }

def generate_spending_lifecycle():
    """Generate spending lifecycle data showing appropriations -> obligations -> outlays"""
    try:
        # Use the proper combined spending lifecycle data that matches TAS codes
        lifecycle_data = load_json('processed_data/spending_lifecycle/spending_lifecycle_data.json')
        
        if 'records' in lifecycle_data:
            records = lifecycle_data['records']
        else:
            records = lifecycle_data
            
        # Convert to DataFrame for easier processing
        df = pd.DataFrame(records)
        
        # Rename bureau to component for consistency
        if 'bureau' in df.columns:
            df['component'] = df['bureau']
        
        # Use apportionment_fy as fiscal_year for consistency
        if 'apportionment_fy' in df.columns:
            df['fiscal_year'] = df['apportionment_fy']
        
        # Group by fiscal year and component
        summary = df.groupby(['fiscal_year', 'component']).agg({
            'apportionment_amount': 'sum',
            'budget_authority': 'sum', 
            'obligations': 'sum',
            'outlays': 'sum'
        }).reset_index()
        
        # Rename for output consistency
        summary.rename(columns={'apportionment_amount': 'appropriations'}, inplace=True)
        
        return summary.to_dict('records')
    except Exception as e:
        print(f"Error generating spending lifecycle: {e}")
        return []

def generate_spending_summary(data):
    """Generate spending summary by component and category"""
    df = pd.DataFrame(data)
    
    # Map field names to standard names
    if 'total_obligations' in df.columns:
        df['obligations'] = df['total_obligations']
    elif 'obligations' not in df.columns:
        df['obligations'] = 0
        
    if 'total_outlays' in df.columns:
        df['outlays'] = df['total_outlays']
    elif 'outlays' not in df.columns:
        df['outlays'] = 0
    
    # By component
    by_component = df.groupby(['fiscal_year', 'component']).agg({
        'obligations': 'sum',
        'outlays': 'sum'
    }).reset_index()
    
    # By spending category
    if 'spending_category' in df.columns:
        category_field = 'spending_category'
    elif 'category' in df.columns:
        category_field = 'category'
    else:
        category_field = None
    
    by_category = None
    if category_field:
        by_category = df.groupby(['fiscal_year', category_field]).agg({
            'obligations': 'sum',
            'outlays': 'sum'
        }).reset_index()
        by_category.rename(columns={category_field: 'category'}, inplace=True)
    
    return {
        'by_component': by_component.to_dict('records'),
        'by_category': by_category.to_dict('records') if by_category is not None else [],
        'total_by_year': {
            'obligations': df.groupby('fiscal_year')['obligations'].sum().to_dict(),
            'outlays': df.groupby('fiscal_year')['outlays'].sum().to_dict()
        }
    }

def generate_vendor_summary(data, top_n=100):
    """Generate vendor summary - only top vendors to reduce size"""
    df = pd.DataFrame(data)
    
    # Debug: print columns
    print(f"Vendor data columns: {df.columns.tolist()[:10]}...")
    
    # Check for vendor/recipient name field
    vendor_field = 'vendor_name' if 'vendor_name' in df.columns else 'recipient_name'
    if vendor_field not in df.columns:
        print(f"Warning: neither vendor_name nor recipient_name column found")
        return {'top_vendors': [], 'by_year': {}}
    
    # Rename to vendor_name for consistency
    if vendor_field != 'vendor_name':
        df['vendor_name'] = df[vendor_field]
    
    # Map obligations field
    if 'total_obligations' in df.columns:
        df['obligations'] = df['total_obligations']
    elif 'obligations' not in df.columns:
        print(f"Warning: no obligations field found in vendor data")
        df['obligations'] = 0
    
    # Get top vendors by total obligations across all years
    vendor_totals = df.groupby('vendor_name')['obligations'].sum().sort_values(ascending=False)
    top_vendors = vendor_totals.head(top_n).index.tolist()
    
    # Filter to only top vendors
    df_top = df[df['vendor_name'].isin(top_vendors)]
    
    # Summary by vendor and year
    vendor_summary = df_top.groupby(['fiscal_year', 'vendor_name']).agg({
        'obligations': 'sum'
    }).reset_index()
    
    # Also get component breakdown for top vendors
    vendor_component = df_top.groupby(['fiscal_year', 'vendor_name', 'component']).agg({
        'obligations': 'sum'
    }).reset_index()
    
    # Get new vendors by year (vendors that appear in year Y but not Y-1)
    years = sorted(df['fiscal_year'].unique())
    new_vendors = {}
    for i, year in enumerate(years):
        year_vendors = set(df[df['fiscal_year'] == year]['vendor_name'].unique())
        if i > 0:
            prev_year_vendors = set(df[df['fiscal_year'] == years[i-1]]['vendor_name'].unique())
            new_this_year = year_vendors - prev_year_vendors
            # Get amounts for new vendors
            new_vendor_amounts = df[(df['fiscal_year'] == year) & 
                                  (df['vendor_name'].isin(new_this_year))].groupby('vendor_name')['obligations'].sum()
            # Only keep vendors with > $1M
            significant_new = new_vendor_amounts[new_vendor_amounts > 1000000].to_dict()
            new_vendors[str(year)] = [
                {'vendor': v, 'amount': a} 
                for v, a in sorted(significant_new.items(), key=lambda x: x[1], reverse=True)[:20]
            ]
    
    return {
        'top_vendors': vendor_summary.to_dict('records'),
        'vendor_components': vendor_component.to_dict('records'),
        'new_vendors_by_year': new_vendors,
        'vendor_count_by_year': df.groupby('fiscal_year')['vendor_name'].nunique().to_dict()
    }

def main():
    """Generate all dashboard data files"""
    
    # Create output directory
    output_dir = 'processed_data/dashboard'
    os.makedirs(output_dir, exist_ok=True)
    
    print("Generating dashboard data files...")
    
    # 1. Appropriations summary
    try:
        appropriations_data = load_json('processed_data/appropriations/dhs_budget_flat.json')
        appropriations_summary = generate_appropriations_summary(appropriations_data)
        
        # Add recent apportionments
        appropriations_summary['recent_apportionments'] = get_recent_apportionments()
        
        with open(f'{output_dir}/appropriations_summary.json', 'w') as f:
            json.dump(appropriations_summary, f, indent=2)
        print(f"✓ Created appropriations_summary.json")
    except Exception as e:
        print(f"✗ Error with appropriations: {e}")
    
    # 2. Spending summary
    try:
        spending_data = load_json('processed_data/usaspending/spending_flat.json')
        spending_summary = generate_spending_summary(spending_data)
        
        with open(f'{output_dir}/spending_summary.json', 'w') as f:
            json.dump(spending_summary, f, indent=2)
        print(f"✓ Created spending_summary.json")
    except Exception as e:
        print(f"✗ Error with spending: {e}")
    
    # 3. Vendor summary (top 100 only)
    try:
        vendor_data = load_json('processed_data/usaspending/awards_flat.json')
        vendor_summary = generate_vendor_summary(vendor_data, top_n=100)
        
        with open(f'{output_dir}/vendor_summary.json', 'w') as f:
            json.dump(vendor_summary, f, indent=2)
        print(f"✓ Created vendor_summary.json")
    except Exception as e:
        print(f"✗ Error with vendors: {e}")
    
    # 4. Spending lifecycle summary  
    try:
        lifecycle_data = generate_spending_lifecycle()
        
        with open(f'{output_dir}/spending_lifecycle.json', 'w') as f:
            json.dump(lifecycle_data, f, indent=2)
        print(f"✓ Created spending_lifecycle.json")
    except Exception as e:
        print(f"✗ Error with spending lifecycle: {e}")
    
    # 5. Create a combined metadata file
    metadata = {
        'generated_at': datetime.now().isoformat(),
        'description': 'Pre-aggregated data for dashboard performance',
        'files': {
            'appropriations_summary.json': 'Appropriations by component and account with recent apportionments',
            'spending_summary.json': 'Spending by component and category', 
            'vendor_summary.json': 'Top 100 vendors and changes',
            'spending_lifecycle.json': 'Spending lifecycle from appropriations to outlays'
        }
    }
    
    with open(f'{output_dir}/dashboard_metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print("\nDashboard data generation complete!")
    
    # Show file sizes
    print("\nGenerated file sizes:")
    for filename in ['appropriations_summary.json', 'spending_summary.json', 'vendor_summary.json', 'spending_lifecycle.json']:
        filepath = f'{output_dir}/{filename}'
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print(f"  {filename}: {size/1024:.1f} KB")

if __name__ == '__main__':
    main()