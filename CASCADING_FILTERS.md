# Cascading Filters Implementation

This document explains how the cascading filters work in both views of the Federal Budget website.

## How It Works

The cascading filters use native JavaScript `Set` operations and DOM events to ensure that when you select an agency, only bureaus available for that agency are shown, and so on.

### Filter Hierarchy
1. **Agency** → affects Bureau options
2. **Bureau** → affects Period options  
3. **Period** → affects Expiration Year options
4. **Percentage** → independent filter

### Key Features

1. **Automatic Clearing**: If you select an agency and then switch to a different agency, any bureau/period/year selections that are no longer valid are automatically cleared.

2. **Progressive Filtering**: Each dropdown only shows options that are actually available based on your previous selections.

3. **Native JavaScript**: Uses built-in `Array.filter()`, `Set`, and DOM events - no external libraries needed.

4. **Consistent Behavior**: Both the single-year view and multi-year comparison view use the same cascading logic.

## Example Workflow

1. Select "Department of Agriculture" → Bureau dropdown now only shows Agriculture bureaus
2. Select "Food Safety and Inspection Service" → Period dropdown now only shows periods available for that specific bureau
3. Select "Multi-Year" → Expiration Year dropdown now only shows years available for that agency/bureau/period combination
4. If you change the Agency back to "All Agencies", the Bureau/Period/Year selections are automatically reset

## Implementation Details

### Single Year View (`app.js`)
- Function: `updateDependentFilters()`
- Triggered on any filter change
- Filters data progressively for each dropdown

### Multi-Year Comparison (`comparison-app.js`)  
- Function: `updateFilterOptions()`
- Same logic but works across multiple years of data
- Triggered on filter changes via `setupFilterHandlers()`

### Data Flow
```
User selects Agency → updateDependentFilters() → 
Filter data by Agency → Generate Bureau options →
User selects Bureau → updateDependentFilters() → 
Filter data by Agency+Bureau → Generate Period options →
And so on...
```

This ensures that users never see impossible combinations and can efficiently narrow down to the data they're interested in.