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
        
        # Get unique apportionments by file_id and approval_date, keeping all fields
        # Group by file_id to get one record per apportionment
        unique_apportionments = df.groupby('file_id').agg({
            'approval_date': 'first',
            'bureau': 'first',
            'account': 'first',
            'amount': 'sum',
            'funds_provided_by': 'first',
            'approver_title': 'first',
            'tas': 'first',
            'tas_full': 'first',
            'availability_period': 'first',
            'line_number': lambda x: ', '.join(str(v) for v in x.unique()[:3]),  # First 3 line numbers
            'line_description': lambda x: ' | '.join(str(v) for v in x.unique()[:3]),  # First 3 descriptions
            'iteration': 'first',
            'created_at': 'first',
            'modified_at': 'first',
            'excel_url': 'first',
            'source_url': 'first',
            'footnote_text': lambda x: ' | '.join(str(v) for v in x.dropna().unique()[:3]) if x.notna().any() else None
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
                'approver': row['approver_title'],
                'file_id': row['file_id'],
                'tas': row['tas'],
                'tas_full': row['tas_full'],
                'availability_period': row['availability_period'],
                'line_number': row['line_number'],
                'line_description': row['line_description'],
                'iteration': int(row['iteration']) if pd.notna(row['iteration']) else None,
                'created_at': row['created_at'],
                'modified_at': row['modified_at'],
                'excel_url': row['excel_url'] if pd.notna(row['excel_url']) else None,
                'source_url': row['source_url'] if pd.notna(row['source_url']) else None,
                'footnote_text': row['footnote_text'] if pd.notna(row['footnote_text']) else None
            })
        
        return recent_list
    except Exception as e:
        print(f"Error getting recent apportionments: {e}")
        import traceback
        traceback.print_exc()
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
        
        # IMPORTANT: To avoid double-counting multi-year appropriations,
        # we need to de-duplicate by TAS + availability_period
        # Each unique TAS/period should only be counted once
        
        # First, get unique TAS/period combinations with their totals
        unique_tas = df.groupby(['tas_simple', 'availability_period', 'component']).agg({
            'budget_authority': 'first',  # These should be the same for all records
            'obligations': 'first',        # with the same TAS/period
            'outlays': 'first',
            'apportionment_amount': 'sum',  # Sum apportionments across years
            'apportionment_fy': 'min',      # Get earliest fiscal year
            'availability_type': 'first',
            'account_name': 'first',
            'begin_year': 'first',
            'end_year': 'first'
        }).reset_index()
        
        # Create aggregated view (by component and fiscal year)
        aggregated = unique_tas.groupby(['apportionment_fy', 'component']).agg({
            'apportionment_amount': 'sum',
            'budget_authority': 'sum', 
            'obligations': 'sum',
            'outlays': 'sum'
        }).reset_index()
        
        # Rename columns
        aggregated.rename(columns={
            'apportionment_fy': 'fiscal_year',
            'apportionment_amount': 'appropriations'
        }, inplace=True)
        
        # Add note for FY2025
        aggregated['note'] = None
        aggregated.loc[aggregated['fiscal_year'] == 2025, 'note'] = 'FY2025 obligations/outlays through Q3 only'
        
        # Create detailed view (preserving availability periods)
        detailed = unique_tas.copy()
        detailed.rename(columns={
            'apportionment_fy': 'fiscal_year',
            'apportionment_amount': 'appropriations'
        }, inplace=True)
        
        # Add period label for display
        detailed['period_label'] = detailed.apply(lambda row: 
            f"FY{row['begin_year']}" if row['begin_year'] == row['end_year'] 
            else f"FY{row['begin_year']}-{str(row['end_year'])[2:]}", axis=1)
        
        # Sort both views
        aggregated = aggregated.sort_values(['fiscal_year', 'appropriations'], ascending=[True, False])
        detailed = detailed.sort_values(['component', 'fiscal_year', 'availability_period'], ascending=[True, True, True])
        
        # Replace NaN values with None for valid JSON
        aggregated = aggregated.where(pd.notna(aggregated), None)
        detailed = detailed.where(pd.notna(detailed), None)
        
        # Convert to list of dicts
        aggregated_list = aggregated.to_dict('records')
        detailed_list = detailed.to_dict('records')
        
        # Return both aggregated (for backward compatibility) and detailed views
        return {
            'aggregated': aggregated_list,
            'detailed': detailed_list,
            'metadata': {
                'total_aggregated_records': len(aggregated_list),
                'total_detailed_records': len(detailed_list),
                'unique_components': len(aggregated['component'].unique()),
                'fiscal_years': sorted(aggregated['fiscal_year'].unique().tolist()),
                'availability_types': sorted(detailed['availability_type'].dropna().unique().tolist())
            }
        }
        
    except Exception as e:
        print(f"Error generating spending lifecycle: {e}")
        import traceback
        traceback.print_exc()
        return {'aggregated': [], 'detailed': [], 'metadata': {}}

def generate_monthly_trends():
    """Generate monthly appropriations and outlays data for time series visualization"""
    try:
        # Load appropriations detail data with dates
        appr_df = pd.read_csv('processed_data/appropriations/dhs_tas_aggregated_detail.csv')
        appr_df['approval_date'] = pd.to_datetime(appr_df['approval_date'])
        appr_df['year_month'] = appr_df['approval_date'].dt.to_period('M')
        
        # Load spending lifecycle data for outlays
        lifecycle_data = load_json('processed_data/spending_lifecycle/spending_lifecycle_data.json')
        if 'records' in lifecycle_data:
            records = lifecycle_data['records']
        else:
            records = lifecycle_data
        
        outlay_df = pd.DataFrame(records)
        
        # Rename bureau to component
        if 'bureau' in outlay_df.columns:
            outlay_df['component'] = outlay_df['bureau']
        if 'bureau' in appr_df.columns and 'component' not in appr_df.columns:
            appr_df['component'] = appr_df['bureau']
        
        # Aggregate appropriations by month and component
        monthly_appr = appr_df.groupby(['year_month', 'component']).agg({
            'amount': 'sum'
        }).reset_index()
        monthly_appr['date'] = monthly_appr['year_month'].dt.to_timestamp()
        
        # For obligations, we need to handle the fact that obligations/outlays are cumulative per TAS
        # We'll only count each TAS once and distribute based on the fiscal year appropriations
        
        # First, get unique obligations by TAS (to avoid counting the same obligations multiple times)
        unique_tas_obligations = outlay_df.drop_duplicates(subset=['tas_simple'])[['tas_simple', 'component', 'obligations']]
        
        # For each unique TAS, distribute its obligations proportionally based on when it received appropriations
        monthly_obligations = []
        
        for _, tas_row in unique_tas_obligations.iterrows():
            tas = tas_row['tas_simple']
            total_obligations = tas_row['obligations']
            component = tas_row['component']
            
            # Get all appropriations for this TAS across years
            tas_apportionments = outlay_df[outlay_df['tas_simple'] == tas]
            total_apportionment = tas_apportionments['apportionment_amount'].sum()
            
            if total_apportionment > 0:
                # Distribute obligations proportionally to each fiscal year based on appropriations
                for _, apport_row in tas_apportionments.iterrows():
                    fy = apport_row['apportionment_fy']
                    fy_proportion = apport_row['apportionment_amount'] / total_apportionment
                    fy_obligations = total_obligations * fy_proportion
                    
                    # Distribute this fiscal year's portion evenly across its months
                    start_date = pd.Timestamp(f'{fy-1}-10-01')
                    end_date = pd.Timestamp(f'{fy}-09-30')
                    months = pd.date_range(start_date, end_date, freq='MS')
                    monthly_amount = fy_obligations / 12
                    
                    for month in months:
                        monthly_obligations.append({
                            'date': month,
                            'component': component,
                            'obligations': monthly_amount,
                            'fiscal_year': fy
                        })
        
        obligations_df_monthly = pd.DataFrame(monthly_obligations)
        
        # Get date range from appropriations data
        min_date = appr_df['approval_date'].min()
        max_date = appr_df['approval_date'].max()
        
        # Create complete date range (make it timezone-naive to match the data)
        all_months = pd.date_range(min_date, max_date, freq='MS', tz=None)
        all_components = list(set(appr_df['component'].unique()) | set(outlay_df['component'].unique()))
        
        # Create time series data structure
        time_series_data = {
            'monthly': [],
            'components': all_components,
            'date_range': {
                'start': min_date.isoformat(),
                'end': max_date.isoformat()
            },
            'spending_types': [
                'Personnel', 'Contracts & Services', 'Grants', 
                'Facilities', 'Supplies & Equipment', 'Travel', 'Other'
            ]
        }
        
        # Aggregate by month for time series
        for month in all_months:
            month_str = month.strftime('%Y-%m')
            month_period = month.to_period('M')
            
            # Get appropriations for this month using period comparison
            month_appr = monthly_appr[monthly_appr['year_month'] == month_period]
            appr_total = month_appr['amount'].sum()
            appr_by_component = month_appr.set_index('component')['amount'].to_dict()
            
            # Get obligations for this month - convert to period for comparison
            if len(obligations_df_monthly) > 0:
                obligations_df_monthly['month_period'] = obligations_df_monthly['date'].dt.to_period('M')
                month_obligations = obligations_df_monthly[obligations_df_monthly['month_period'] == month_period]
            else:
                month_obligations = pd.DataFrame()
            obligations_total = month_obligations['obligations'].sum()
            obligations_by_component = month_obligations.groupby('component')['obligations'].sum().to_dict()
            
            time_series_data['monthly'].append({
                'date': month_str,
                'appropriations_total': float(appr_total),
                'obligations_total': float(obligations_total),
                'appropriations_by_component': appr_by_component,
                'obligations_by_component': obligations_by_component
            })
        
        return time_series_data
        
    except Exception as e:
        print(f"Error generating monthly trends: {e}")
        import traceback
        traceback.print_exc()
        return {
            'monthly': [],
            'components': [],
            'date_range': {},
            'spending_types': []
        }

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
    
    # 5. Monthly trends data
    try:
        monthly_data = generate_monthly_trends()
        
        with open(f'{output_dir}/monthly_trends.json', 'w') as f:
            json.dump(monthly_data, f, indent=2)
        print(f"✓ Created monthly_trends.json")
    except Exception as e:
        print(f"✗ Error with monthly trends: {e}")
    
    # 6. Create a combined metadata file
    metadata = {
        'generated_at': datetime.now().isoformat(),
        'description': 'Pre-aggregated data for dashboard performance',
        'files': {
            'appropriations_summary.json': 'Appropriations by component and account with recent apportionments',
            'spending_summary.json': 'Spending by component and category', 
            'vendor_summary.json': 'Top 100 vendors and changes',
            'spending_lifecycle.json': 'Spending lifecycle from appropriations to outlays',
            'monthly_trends.json': 'Monthly time series data for appropriations and outlays'
        }
    }
    
    with open(f'{output_dir}/dashboard_metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print("\nDashboard data generation complete!")
    
    # Show file sizes
    print("\nGenerated file sizes:")
    for filename in ['appropriations_summary.json', 'spending_summary.json', 'vendor_summary.json', 'spending_lifecycle.json', 'monthly_trends.json']:
        filepath = f'{output_dir}/{filename}'
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print(f"  {filename}: {size/1024:.1f} KB")

if __name__ == '__main__':
    main()