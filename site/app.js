// Federal Agency Obligation Summary - DataTables Implementation

let dataTable;
let obligationData = [];
let columnFilters = {};
let agencyData = [];
let bureauData = [];
let agencyColorScale;
let showBureauAggregates = false;
let aggregationLevel = 'agency'; // 'individual', 'bureau', or 'agency'
let currentFiscalYear = null; // Track the currently selected fiscal year
let availableYears = []; // Track available fiscal years
let fiscalYearMetadata = {}; // Store month information for each fiscal year

// Define agency colors - using d3 color schemes
const AGENCY_COLORS = {
    "Legislative Branch": "#1f77b4",
    "Judicial Branch": "#ff7f0e", 
    "Department of Agriculture": "#2ca02c",
    "Department of Commerce": "#d62728",
    "Department of Defense-Military": "#9467bd",
    "Department of Education": "#8c564b",
    "Department of Energy": "#e377c2",
    "Department of Health and Human Services": "#7f7f7f",
    "Department of Homeland Security": "#bcbd22",
    "Department of Housing and Urban Development": "#17becf",
    "Department of the Interior": "#aec7e8",
    "Department of Justice": "#ffbb78",
    "Department of Labor": "#98df8a",
    "Department of State": "#ff9896",
    "Department of Transportation": "#c5b0d5",
    "Department of the Treasury": "#c49c94",
    "Department of Veterans Affairs": "#f7b6d2",
    "Corps of Engineers-Civil Works": "#c7c7c7",
    "Other Defense Civil Programs": "#dbdb8d",
    "Environmental Protection Agency": "#9edae5",
    "Executive Office of the President": "#393b79",
    "General Services Administration": "#5254a3",
    "International Assistance Programs": "#6b6ecf",
    "National Aeronautics and Space Administration": "#9c9ede",
    "National Science Foundation": "#637939",
    "Office of Personnel Management": "#8ca252",
    "Small Business Administration": "#b5cf6b",
    "Social Security Administration": "#cedb9c",
    "Other Independent Agencies": "#e7cb94"
};

// Define patterns for accessibility
const PATTERN_DEFINITIONS = [
    { id: 'dots', path: 'M 0,4 l 4,0 M 2,0 l 0,4', strokeWidth: 1 },
    { id: 'stripes', path: 'M 0,4 l 8,0', strokeWidth: 1 },
    { id: 'diagonals', path: 'M 0,8 l 8,-8 M 0,0 l 8,-8 M 0,16 l 8,-8', strokeWidth: 1 },
    { id: 'crosshatch', path: 'M 0,4 l 8,0 M 4,0 l 0,8', strokeWidth: 1 },
    { id: 'waves', path: 'M 0,4 Q 2,2 4,4 T 8,4', strokeWidth: 1.5 },
    { id: 'circles', path: 'M 4,4 m -2,0 a 2,2 0 1,0 4,0 a 2,2 0 1,0 -4,0', strokeWidth: 0.5, fill: true },
    { id: 'zigzag', path: 'M 0,4 L 2,0 L 4,4 L 6,0 L 8,4', strokeWidth: 1 },
    { id: 'dashes', path: 'M 0,4 l 3,0 M 5,4 l 3,0', strokeWidth: 1.5 },
    { id: 'vertical-stripes', path: 'M 4,0 l 0,8', strokeWidth: 1 },
    { id: 'diagonal-stripes-reverse', path: 'M 8,8 l -8,-8 M 8,0 l -8,-8 M 8,16 l -8,-8', strokeWidth: 1 },
    { id: 'squares', path: 'M 1,1 l 2,0 l 0,2 l -2,0 Z M 5,5 l 2,0 l 0,2 l -2,0 Z', strokeWidth: 0.5, fill: true },
    { id: 'triangles', path: 'M 2,6 L 4,2 L 6,6 Z', strokeWidth: 0.5, fill: true },
    { id: 'diamonds', path: 'M 4,1 L 7,4 L 4,7 L 1,4 Z', strokeWidth: 1 },
    { id: 'hexagons', path: 'M 2,4 L 2,2 L 4,1 L 6,2 L 6,4 L 4,5 Z', strokeWidth: 1 },
    { id: 'plus', path: 'M 4,2 l 0,4 M 2,4 l 4,0', strokeWidth: 1.5 },
    { id: 'x-marks', path: 'M 2,2 l 4,4 M 6,2 l -4,4', strokeWidth: 1 },
    { id: 'dots-large', path: 'M 4,4 m -1.5,0 a 1.5,1.5 0 1,0 3,0 a 1.5,1.5 0 1,0 -3,0', strokeWidth: 0.5, fill: true }
];

// Create a mapping of unique colors to patterns
const COLOR_TO_PATTERN = {};
const uniqueColors = [...new Set(Object.values(AGENCY_COLORS))];
uniqueColors.forEach((color, index) => {
    if (index < PATTERN_DEFINITIONS.length) {
        COLOR_TO_PATTERN[color] = PATTERN_DEFINITIONS[index].id;
    }
});


// Format currency values
function formatCurrency(value) {
    return '$' + value.toFixed(1).replace(/\B(?=(\d{3})+(?!\d))/g, ',') + 'M';
}

// Format percentage with color coding
function formatPercentage(value) {
    return `<span class="percentage-cell">${value.toFixed(1)}%</span>`;
}

// Load CSV data for a specific fiscal year
async function loadData(fiscalYear = null) {
    try {
        // Determine which file to load
        let csvFile;
        if (fiscalYear) {
            csvFile = `data/all_agencies_obligation_summary_${fiscalYear}.csv`;
            console.log(`Loading data for FY${fiscalYear}...`);
        } else {
            csvFile = 'data/all_agencies_obligation_summary.csv';
            console.log('Loading default data file...');
        }
        
        const response = await fetch(csvFile);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status} for ${csvFile}`);
        }
        
        const csvText = await response.text();
        console.log('CSV loaded successfully, length:', csvText.length);
        
        // Parse CSV
        const lines = csvText.split('\n');
        const headers = lines[0].split(',');
        
        obligationData = [];
        for (let i = 1; i < lines.length; i++) {
            if (lines[i].trim() === '') continue;
            
            // Handle CSV parsing with proper quote handling
            const values = parseCSVLine(lines[i]);
            if (values.length !== headers.length) continue;
            
            const row = {};
            headers.forEach((header, index) => {
                row[header.trim()] = values[index];
            });
            
            // Convert numeric values
            row.unobligatedValue = parseFloat(row['Unobligated Balance (Line 2490)'].replace(/[$,M]/g, ''));
            row.budgetAuthorityValue = parseFloat(row['Budget Authority (Line 2500)'].replace(/[$,M]/g, ''));
            row.percentageValue = parseFloat(row['Percentage Unobligated'].replace('%', ''));
            
            
            obligationData.push(row);
        }
        
        // Calculate agency and bureau-level aggregations
        aggregateAgencyData();
        aggregateBureauData();
        
        // Calculate summary statistics
        updateSummaryStats();
        
        // Populate main filters
        populateMainFilters();
        
        // Initialize DataTable
        initializeDataTable();
        
        // Initialize bubble chart
        initializeBubbleChart();
        
        // Add event listener for download button after DataTable is initialized
        $('#downloadCSV').on('click', function() {
            downloadCSV();
        });
        
        // Update current fiscal year
        if (fiscalYear) {
            currentFiscalYear = fiscalYear;
            updateYearSelectorUI();
        }
        
        // Only update filters if this is the initial load (no previous filter state to preserve)
        if (!window.filterStatePreserved) {
            updateFiltersFromUI();
        }
        
    } catch (error) {
        console.error('Error loading data:', error);
        const fileName = fiscalYear ? `all_agencies_obligation_summary_${fiscalYear}.csv` : 'all_agencies_obligation_summary.csv';
        console.error(`Failed to load: data/${fileName}`);
        console.error('Make sure you are running the server with ./serve.py or python3 serve.py');
        alert(`Error loading data for ${fiscalYear ? `FY${fiscalYear}` : 'default year'}. Please ensure you are running the server with ./serve.py and the data file exists.`);
        
        // Remove loading state from year buttons
        if (fiscalYear) {
            const yearBtn = document.querySelector(`.year-btn[data-year="${fiscalYear}"]`);
            if (yearBtn) {
                yearBtn.classList.remove('loading');
            }
        }
    }
}

// Parse CSV line handling quoted values
function parseCSVLine(line) {
    const result = [];
    let current = '';
    let inQuotes = false;
    
    for (let i = 0; i < line.length; i++) {
        const char = line[i];
        
        if (char === '"') {
            inQuotes = !inQuotes;
        } else if (char === ',' && !inQuotes) {
            result.push(current.trim().replace(/^"|"$/g, ''));
            current = '';
        } else {
            current += char;
        }
    }
    
    if (current) {
        result.push(current.trim().replace(/^"|"$/g, ''));
    }
    
    return result;
}


// Aggregate data by agency
function aggregateAgencyData() {
    const agencyMap = new Map();
    
    obligationData.forEach(row => {
        const agency = row.Agency || 'Other';
        const period = row.Period_of_Performance || 'Unknown';
        const expiration = row.Expiration_Year || 'Unknown';
        const key = `${agency}|${period}|${expiration}`;
        
        if (!agencyMap.has(key)) {
            agencyMap.set(key, {
                name: agency,
                period: period,
                expiration: expiration,
                budgetAuthority: 0,
                unobligated: 0,
                accountCount: 0,
                bureaus: new Set()
            });
        }
        
        const agencyInfo = agencyMap.get(key);
        agencyInfo.budgetAuthority += row.budgetAuthorityValue;
        agencyInfo.unobligated += row.unobligatedValue;
        agencyInfo.accountCount += 1;
        if (row.Bureau) {
            agencyInfo.bureaus.add(row.Bureau);
        }
    });
    
    // Convert to array and calculate percentages
    agencyData = Array.from(agencyMap.values()).map(agency => ({
        ...agency,
        bureauCount: agency.bureaus.size,
        percentageUnobligated: agency.budgetAuthority > 0 ? 
            (agency.unobligated / agency.budgetAuthority * 100) : 0
    }));
    
    // Sort by budget authority descending
    agencyData.sort((a, b) => b.budgetAuthority - a.budgetAuthority);
}

// Aggregate data by bureau/period/expiration
function aggregateBureauData() {
    const bureauMap = new Map();
    
    obligationData.forEach(row => {
        const agency = row.Agency || 'Other';
        const bureau = row.Bureau || 'Other';
        const period = row.Period_of_Performance || 'Unknown';
        const expiration = row.Expiration_Year || 'Unknown';
        const key = `${agency}|${bureau}|${period}|${expiration}`;
        
        if (!bureauMap.has(key)) {
            bureauMap.set(key, {
                agency: agency,
                name: bureau,
                period: period,
                expiration: expiration,
                budgetAuthority: 0,
                unobligated: 0,
                accountCount: 0
            });
        }
        
        const bureauInfo = bureauMap.get(key);
        bureauInfo.budgetAuthority += row.budgetAuthorityValue;
        bureauInfo.unobligated += row.unobligatedValue;
        bureauInfo.accountCount += 1;
    });
    
    // Convert to array and calculate percentages
    bureauData = Array.from(bureauMap.values()).map(bureau => ({
        ...bureau,
        percentageUnobligated: bureau.budgetAuthority > 0 ? 
            (bureau.unobligated / bureau.budgetAuthority * 100) : 0
    }));
    
    // Sort by budget authority descending
    bureauData.sort((a, b) => b.budgetAuthority - a.budgetAuthority);
}

// Update summary statistics
function updateSummaryStats() {
    const totalBudget = obligationData.reduce((sum, row) => sum + row.budgetAuthorityValue, 0);
    const totalUnobligated = obligationData.reduce((sum, row) => sum + row.unobligatedValue, 0);
    const overallPercentage = totalBudget > 0 ? (totalUnobligated / totalBudget * 100) : 0;
    
    $('#totalBudget').text(formatCurrency(totalBudget));
    $('#totalUnobligated').text(formatCurrency(totalUnobligated));
    $('#overallPercentage').text(overallPercentage.toFixed(1) + '%');
    $('#accountCount').text(obligationData.length);
}

// Initialize multi-select dropdown functionality
function initializeMultiSelectDropdown(filterId, options, defaultSelected = []) {
    const $filter = $(`#${filterId}`);
    const $button = $filter.find('button');
    const $menu = $filter.find('.dropdown-menu');
    const $options = $filter.find('.filter-options');
    const $search = $filter.find('.filter-search');
    
    // Populate options
    $options.empty();
    options.forEach(option => {
        const checked = defaultSelected.length === 0 || defaultSelected.includes(option) ? 'checked' : '';
        $options.append(`
            <label class="d-block px-2 py-1 mb-0">
                <input type="checkbox" value="${option}" ${checked}> ${option}
            </label>
        `);
    });
    
    // Toggle dropdown
    $button.on('click', function(e) {
        e.stopPropagation();
        $('.filter-dropdown-menu').not($menu).hide();
        $menu.toggle();
    });
    
    // Search functionality
    $search.on('input', function() {
        const searchTerm = $(this).val().toLowerCase();
        $options.find('label').each(function() {
            const text = $(this).text().toLowerCase();
            $(this).toggle(text.includes(searchTerm));
        });
    });
    
    // Select all / Clear all
    $filter.find('.select-all').on('click', function(e) {
        e.preventDefault();
        $options.find('input[type="checkbox"]').prop('checked', true);
        updateButtonText();
    });
    
    $filter.find('.clear-all').on('click', function(e) {
        e.preventDefault();
        $options.find('input[type="checkbox"]').prop('checked', false);
        updateButtonText();
    });
    
    // Update button text based on selection
    function updateButtonText() {
        const checked = $options.find('input[type="checkbox"]:checked');
        const total = $options.find('input[type="checkbox"]').length;
        
        if (checked.length === 0) {
            $button.text('None selected');
        } else if (checked.length === total) {
            $button.text($button.text().replace(/\d+ selected|None selected/, '').replace('All ', 'All ').trim());
        } else if (checked.length === 1) {
            $button.text(checked.first().parent().text().trim());
        } else {
            $button.text(`${checked.length} selected`);
        }
    }
    
    // Handle checkbox changes
    $options.on('change', 'input[type="checkbox"]', function() {
        updateButtonText();
        updateFiltersFromUI();
    });
    
    // Close dropdown when clicking outside
    $(document).on('click', function(e) {
        if (!$(e.target).closest($filter).length) {
            $menu.hide();
        }
    });
    
    return updateButtonText;
}

// Update dependent filter dropdowns based on current selections (cascading filters)
function updateDependentFilters() {
    const selectedAgency = $('#mainAgencyFilter').val();
    const selectedBureau = $('#mainBureauFilter').val();
    const selectedPeriod = $('#mainPeriodFilter').val();
    
    
    // Start with all data and progressively filter for each dropdown
    let filteredForBureaus = obligationData;
    let filteredForPeriods = obligationData;
    let filteredForYears = obligationData;
    
    // For bureaus: filter by agency only (if agency is selected)
    if (selectedAgency && selectedAgency !== '') {
        filteredForBureaus = filteredForBureaus.filter(row => row.Agency === selectedAgency);
    }
    
    // For periods: filter by agency and bureau (if selected)
    if (selectedAgency && selectedAgency !== '') {
        filteredForPeriods = filteredForPeriods.filter(row => row.Agency === selectedAgency);
    }
    if (selectedBureau && selectedBureau !== '') {
        filteredForPeriods = filteredForPeriods.filter(row => row.Bureau === selectedBureau);
    }
    
    // For years: filter by agency, bureau, and period (if selected)
    if (selectedAgency && selectedAgency !== '') {
        filteredForYears = filteredForYears.filter(row => row.Agency === selectedAgency);
    }
    if (selectedBureau && selectedBureau !== '') {
        filteredForYears = filteredForYears.filter(row => row.Bureau === selectedBureau);
    }
    if (selectedPeriod && selectedPeriod !== '') {
        filteredForYears = filteredForYears.filter(row => row.Period_of_Performance === selectedPeriod);
    }
    
    // Update Bureau dropdown (cascaded from Agency)
    const bureaus = [...new Set(filteredForBureaus.map(row => row.Bureau))].filter(b => b).sort();
    
    const $bureauFilter = $('#mainBureauFilter');
    const currentBureau = $bureauFilter.val();
    $bureauFilter.empty().append('<option value="">All Bureaus</option>');
    bureaus.forEach(bureau => {
        $bureauFilter.append(`<option value="${bureau}">${bureau}</option>`);
    });
    
    // Clear bureau selection if it's no longer available
    if (currentBureau && currentBureau !== '' && !bureaus.includes(currentBureau)) {
        $bureauFilter.val('');
    } else if (bureaus.includes(currentBureau)) {
        $bureauFilter.val(currentBureau);
    }
    
    // Update filter hint
    if (selectedAgency && selectedAgency !== '') {
        $('#bureauFilterHint').text(`(${bureaus.length} available)`);
    } else {
        $('#bureauFilterHint').text('');
    }
    
    // Update Period dropdown (cascaded from Agency + Bureau)
    const periods = [...new Set(filteredForPeriods.map(row => row.Period_of_Performance))].filter(p => p).sort();
    const $periodFilter = $('#mainPeriodFilter');
    const currentPeriod = $periodFilter.val();
    $periodFilter.empty().append('<option value="">All Periods</option>');
    periods.forEach(period => {
        $periodFilter.append(`<option value="${period}">${period}</option>`);
    });
    
    // Clear period selection if it's no longer available
    if (currentPeriod && !periods.includes(currentPeriod)) {
        $periodFilter.val('');
    } else if (periods.includes(currentPeriod)) {
        $periodFilter.val(currentPeriod);
    }
    
    // Update filter hint
    if (selectedAgency || selectedBureau) {
        $('#periodFilterHint').text(`(${periods.length} available)`);
    } else {
        $('#periodFilterHint').text('');
    }
    
    // Update Year dropdown (cascaded from Agency + Bureau + Period)
    const years = [...new Set(filteredForYears.map(row => row.Expiration_Year))].filter(y => y).sort();
    const $yearFilter = $('#mainExpirationFilter');
    const currentYear = $yearFilter.val();
    $yearFilter.empty().append('<option value="">All Years</option>');
    years.forEach(year => {
        $yearFilter.append(`<option value="${year}">${year}</option>`);
    });
    
    // Preserve current selection if it exists in the new list, otherwise clear it
    if (currentYear !== null && currentYear !== undefined) {
        if (currentYear === '' || years.includes(currentYear)) {
            $yearFilter.val(currentYear);
        } else {
            // Clear selection if it's no longer available
            $yearFilter.val('');
        }
    } else {
        // Default to current fiscal year if available, otherwise no default
        const defaultYear = currentFiscalYear ? currentFiscalYear.toString() : '2025';
        if (years.includes(defaultYear)) {
            $yearFilter.val(defaultYear);
        } else if (years.includes('2025')) {
            $yearFilter.val('2025');
        }
    }
    
    // Update filter hint
    if (selectedAgency || selectedBureau || selectedPeriod) {
        $('#yearFilterHint').text(`(${years.length} available)`);
    } else {
        $('#yearFilterHint').text('');
    }
}

// Populate main filter dropdowns
function populateMainFilters() {
    // Get unique values
    const agencies = [...new Set(obligationData.map(row => row.Agency))].filter(a => a).sort();
    
    // Populate agency dropdown
    const $agencyFilter = $('#mainAgencyFilter');
    agencies.forEach(agency => {
        $agencyFilter.append(`<option value="${agency}">${agency}</option>`);
    });
    
    // No default agency selection - start with "All Agencies"
    
    // Initialize other dropdowns with all available options (will be filtered on selection)
    updateDependentFilters();
    
    // Set default expiration year to match current fiscal year if available
    if ($('#mainExpirationFilter').val() === null || $('#mainExpirationFilter').val() === '') {
        const defaultYear = currentFiscalYear ? currentFiscalYear.toString() : '2025';
        if ($('#mainExpirationFilter option[value="' + defaultYear + '"]').length > 0) {
            $('#mainExpirationFilter').val(defaultYear);
        }
    }
    
    // Clear any existing handlers first
    $('#mainAgencyFilter, #mainBureauFilter, #mainPeriodFilter, #mainExpirationFilter, #mainPercentageFilter').off('change');
    
    // Set up change handlers with cascading filter updates
    $('#mainAgencyFilter').on('change', function() {
        updateDependentFilters(); // Update dependent dropdowns first
        updateFiltersFromUI();    // Then update the data display
    });
    
    $('#mainBureauFilter').on('change', function() {
        updateDependentFilters(); // Update dependent dropdowns first  
        updateFiltersFromUI();    // Then update the data display
    });
    
    $('#mainPeriodFilter').on('change', function() {
        updateDependentFilters(); // Update dependent dropdowns first
        updateFiltersFromUI();    // Then update the data display
    });
    
    $('#mainExpirationFilter, #mainPercentageFilter').on('change', function() {
        updateFiltersFromUI();    // These don't affect other dropdowns
    });
    
    // Don't trigger filter update here - DataTable isn't initialized yet
    
    // Set up aggregation level change handler
    $('#aggregationLevel').on('change', function() {
        aggregationLevel = $(this).val();
        
        // Update both table and chart
        if (aggregationLevel === 'agency') {
            showAggregatedTable('agency');
        } else if (aggregationLevel === 'bureau') {
            showAggregatedTable('bureau');
        } else {
            showDetailedTable();
        }
        initializeBubbleChart();
    });
}

// Update filters from UI and display active filter badges
function updateFiltersFromUI() {
    // Get selected values from single-select dropdowns
    // Treat empty string ("All") as no filter, not as a filter value
    const agencyVal = $('#mainAgencyFilter').val();
    const bureauVal = $('#mainBureauFilter').val();
    const periodVal = $('#mainPeriodFilter').val();
    const yearVal = $('#mainExpirationFilter').val();
    
    const agencies = agencyVal && agencyVal !== '' ? [agencyVal] : [];
    const bureaus = bureauVal && bureauVal !== '' ? [bureauVal] : [];
    const periods = periodVal && periodVal !== '' ? [periodVal] : [];
    const years = yearVal && yearVal !== '' ? [yearVal] : [];
    
    // Get percentage range
    const percentVal = $('#mainPercentageFilter').val();
    const percentRange = percentVal && percentVal !== '' ? percentVal : null;
    
    // Update column filters
    columnFilters.Agency = agencies.length > 0 ? agencies : null;
    columnFilters.Bureau = bureaus.length > 0 ? bureaus : null;
    columnFilters.Period_of_Performance = periods.length > 0 ? periods : null;
    columnFilters.Expiration_Year = years.length > 0 ? years : null;
    columnFilters.Percentage_Range = percentRange;
    
    // Helper function to get filtered data based on all current filters
    const getFilteredData = (includeAgency, includeBureau, includePeriod, includeYear) => {
        let filtered = obligationData;
        
        if (includeAgency && agencies.length > 0) {
            filtered = filtered.filter(row => agencies.includes(row.Agency));
        }
        if (includeBureau && bureaus.length > 0) {
            filtered = filtered.filter(row => bureaus.includes(row.Bureau));
        }
        if (includePeriod && periods.length > 0) {
            filtered = filtered.filter(row => periods.includes(row.Period_of_Performance));
        }
        if (includeYear && years.length > 0) {
            filtered = filtered.filter(row => years.includes(row.Expiration_Year));
        }
        if (percentRange) {
            filtered = filtered.filter(row => {
                const [min, max] = percentRange.split('-').map(v => parseFloat(v));
                return row.percentageValue >= min && row.percentageValue <= max;
            });
        }
        
        return filtered;
    };
    
    // Note: Dynamic filtering of dropdown options is disabled for now to fix dropdown functionality
    // The Bureau, Period, and Expiration Year dropdowns will show all available options
    // regardless of other filter selections
    
    
    // Apply all filters
    applyAllFilters();
    
    // Update the filter display
    updateActiveFiltersDisplay();
}

// Update the active filters display under the title
function updateActiveFiltersDisplay() {
    const $display = $('#activeFiltersDisplay');
    const filterTexts = [];
    
    // Get selected values
    const agency = $('#mainAgencyFilter').val();
    const bureau = $('#mainBureauFilter').val();
    const period = $('#mainPeriodFilter').val();
    const year = $('#mainExpirationFilter').val();
    
    // Add filter texts
    if (agency) {
        filterTexts.push(agency);
    } else {
        filterTexts.push('All Agencies');
    }
    
    if (bureau) {
        filterTexts.push(bureau);
    } else {
        filterTexts.push('All Bureaus');
    }
    
    if (period) {
        filterTexts.push(period);
    } else {
        filterTexts.push('All Periods');
    }
    
    if (year) {
        filterTexts.push(`Expiration Year ${year}`);
    } else {
        filterTexts.push('All Expiration Years');
    }
    
    // Check percentage filter
    const percentRange = $('#mainPercentageFilter').val();
    if (percentRange) {
        const displayText = $('#mainPercentageFilter option:selected').text();
        filterTexts.push('Unobligated: ' + displayText);
    }
    
    // Update display
    $display.text(filterTexts.join(' • '));
}

// Update active filter badges display
function updateActiveFilterBadges() {
    const $activeFilters = $('#activeFilters');
    $activeFilters.empty();
    
    const filters = [];
    
    // Get selected values from dropdowns
    const selectedAgency = $('#mainAgencyFilter').val();
    const selectedBureau = $('#mainBureauFilter').val();
    const selectedPeriod = $('#mainPeriodFilter').val();
    const selectedYear = $('#mainExpirationFilter').val();
    
    // Add filter badges for each type
    const agencies = selectedAgency ? [selectedAgency] : [];
    const allAgencies = $('#mainAgencyFilter').find('option').length - 1; // -1 for "All Agencies" option
    if (agencies.length > 0 && agencies.length < allAgencies) {
        agencies.forEach(agency => {
            filters.push({
                type: 'Agency',
                value: agency,
                id: 'mainAgencyFilter',
                filterValue: agency
            });
        });
    }
    
    const bureaus = selectedBureau ? [selectedBureau] : [];
    if (bureaus.length > 0) {
        bureaus.forEach(bureau => {
            filters.push({
                type: 'Bureau',
                value: bureau,
                id: 'mainBureauFilter',
                filterValue: bureau
            });
        });
    }
    
    const periods = selectedPeriod ? [selectedPeriod] : [];
    if (periods.length > 0) {
        periods.forEach(period => {
            filters.push({
                type: 'Period',
                value: period,
                id: 'mainPeriodFilter',
                filterValue: period
            });
        });
    }
    
    const years = selectedYear ? [selectedYear] : [];
    if (years.length > 0) {
        years.forEach(year => {
            filters.push({
                type: 'Year',
                value: year,
                id: 'mainExpirationFilter',
                filterValue: year
            });
        });
    }
    
    const percentRange = $('#mainPercentageFilter').val();
    if (percentRange) {
        filters.push({
            type: '% Range',
            value: $('#mainPercentageFilter option:selected').text(),
            id: 'mainPercentageFilter',
            filterValue: ''
        });
    }
    
    if (filters.length === 0) {
        $activeFilters.html('<span style="color: #999;">No filters active</span>');
    } else {
        filters.forEach(filter => {
            const $badge = $(`<span class="filter-badge">
                ${filter.type}: ${filter.value}
                <span class="remove-filter" data-filter-id="${filter.id}" data-filter-value="${filter.filterValue || ''}">×</span>
            </span>`);
            $activeFilters.append($badge);
        });
        
        // Set up remove filter handlers
        $('.remove-filter').on('click', function() {
            const filterId = $(this).data('filter-id');
            const filterValue = $(this).data('filter-value');
            
            // For single-select dropdowns, just clear the value
            if (filterId === 'mainAgencyFilter' || filterId === 'mainBureauFilter' || 
                filterId === 'mainPeriodFilter' || filterId === 'mainExpirationFilter') {
                $(`#${filterId}`).val('').trigger('change');
                return; // Exit early for single selects
            }
            
            // For percentage filter (still uses checkboxes)
            $(`#${filterId}`).find(`input[type="checkbox"][value="${filterValue}"]`).prop('checked', false);
            
            // Update button text
            const $filter = $(`#${filterId}`);
            const checked = $filter.find('.filter-options input[type="checkbox"]:checked');
            const total = $filter.find('.filter-options input[type="checkbox"]').length;
            const $button = $filter.find('button');
            
            if (checked.length === 0) {
                $button.text('None selected');
            } else if (checked.length === total) {
                $button.text('All Ranges');
            } else if (checked.length === 1) {
                $button.text(checked.first().parent().text().trim());
            } else {
                $button.text(`${checked.length} ranges`);
            }
            
            updateFiltersFromUI();
        });
    }
}

// Initialize DataTable
function initializeDataTable() {
    // Destroy existing DataTable if it exists
    if ($.fn.DataTable.isDataTable('#obligationTable')) {
        $('#obligationTable').DataTable().destroy();
        $('#obligationTable').empty();
    }
    
    dataTable = $('#obligationTable').DataTable({
        data: obligationData,
        columns: [
            { 
                data: 'Agency',
                render: function(data, type, row) {
                    if (type === 'display' && data) {
                        const color = AGENCY_COLORS[data] || '#999';
                        return `<span style="display: inline-block; width: 12px; height: 12px; 
                                background-color: ${color}; border-radius: 50%; margin-right: 8px;"></span>${data}`;
                    }
                    return data || '';
                }
            },
            { 
                data: 'Bureau',
                render: function(data) {
                    return data || '';
                }
            },
            { 
                data: 'Account',
                render: function(data) {
                    return data || '';
                }
            },
            { 
                data: 'Account_Number',
                render: function(data, type) {
                    if (type === 'display' && data) {
                        // Format account number for USASpending URL
                        // Examples: "96-3122" becomes "096-3122", "020-0500" stays "020-0500"
                        const parts = data.split('-');
                        if (parts.length === 2) {
                            let formattedAccount = data;
                            // Add leading zero to first part if it's 2 digits
                            if (parts[0].length === 2) {
                                formattedAccount = '0' + parts[0] + '-' + parts[1];
                            }
                            const url = `https://www.usaspending.gov/federal_account/${formattedAccount}`;
                            return `<a href="${url}" target="_blank" rel="noopener noreferrer" 
                                     title="View on USASpending.gov" style="color: #0066cc; text-decoration: underline;">${data}</a>`;
                        }
                        // Return without link if format doesn't match expected pattern
                        return data;
                    }
                    return data || '';
                }
            },
            { 
                data: 'Period_of_Performance',
                render: function(data) {
                    return data || '';
                }
            },
            { 
                data: 'Expiration_Year',
                render: function(data, type, row) {
                    if (type === 'display') {
                        if (data === '2025') {
                            return `<span class="badge bg-warning text-dark">${data}</span>`;
                        } else if (data === 'No Year') {
                            return `<span class="badge bg-info">${data}</span>`;
                        }
                        return data || '';
                    }
                    return data;
                }
            },
            { 
                data: 'Unobligated Balance (Line 2490)',
                className: 'text-end',
                type: 'num',
                render: function(data, type, row) {
                    if (type === 'sort' || type === 'type') {
                        return row.unobligatedValue;
                    }
                    return data;
                }
            },
            { 
                data: 'Budget Authority (Line 2500)',
                className: 'text-end',
                type: 'num',
                render: function(data, type, row) {
                    if (type === 'sort' || type === 'type') {
                        return row.budgetAuthorityValue;
                    }
                    return data;
                }
            },
            { 
                data: 'percentageValue',
                className: 'text-center',
                render: function(data) {
                    return formatPercentage(data);
                }
            }
        ],
        pageLength: 25,
        lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "All"]],
        order: [[7, 'desc']], // Sort by Budget Authority descending
        language: {
            search: "Search accounts:",
            lengthMenu: "Show _MENU_ accounts per page",
            info: "Showing _START_ to _END_ of _TOTAL_ accounts",
            infoFiltered: "(filtered from _MAX_ total accounts)"
        },
        dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>rtip',
        rowCallback: function(row, data) {
            // Highlight rows expiring in 2025
            if (data.Expiration_Year === '2025') {
                $(row).addClass('expiring-soon');
            } else if (data.Expiration_Year === 'No Year') {
                $(row).addClass('no-year');
            }
        },
    });
}

// Column filters removed - all filtering now done through top filter section


// Apply all filters (column filters + percentage filter)
function applyAllFilters() {
    // Remove existing custom filter
    $.fn.dataTable.ext.search = [];
    
    // Add new filter function that combines all filters
    $.fn.dataTable.ext.search.push(function(settings, data, dataIndex) {
        let show = true;
        
        // Check Agency filter
        if (columnFilters.Agency && columnFilters.Agency.length > 0) {
            const agencyValue = data[0];
            if (!columnFilters.Agency.includes(agencyValue)) {
                show = false;
            }
        }
        
        // Check Bureau filter
        if (show && columnFilters.Bureau && columnFilters.Bureau.length > 0) {
            const bureauValue = data[1];
            if (!columnFilters.Bureau.includes(bureauValue)) {
                show = false;
            }
        }
        
        // Check Period filter
        if (show && columnFilters.Period_of_Performance && columnFilters.Period_of_Performance.length > 0) {
            const periodValue = data[4];
            if (!columnFilters.Period_of_Performance.includes(periodValue)) {
                show = false;
            }
        }
        
        // Check Expiration Year filter
        if (show && columnFilters.Expiration_Year && columnFilters.Expiration_Year.length > 0) {
            const yearValue = data[5];
            if (!columnFilters.Expiration_Year.includes(yearValue)) {
                show = false;
            }
        }
        
        // Check percentage range filter
        if (show && columnFilters.Percentage_Range) {
            const percentage = parseFloat(data[8].replace(/<[^>]*>/g, '').replace('%', ''));
            const [min, max] = columnFilters.Percentage_Range.split('-').map(v => parseFloat(v));
            
            if (!(percentage >= min && percentage <= max)) {
                show = false;
            }
        }
        
        return show;
    });
    
    // Redraw table based on current aggregation level
    if (aggregationLevel === 'agency') {
        // Remove the custom filter temporarily for aggregated view
        $.fn.dataTable.ext.search = [];
        showAggregatedTable('agency');
    } else if (aggregationLevel === 'bureau') {
        // Remove the custom filter temporarily for aggregated view
        $.fn.dataTable.ext.search = [];
        showAggregatedTable('bureau');
    } else {
        // Individual accounts - need to refresh the data with current filters
        showDetailedTable();
    }
    
    // Update bubble chart
    initializeBubbleChart();
}

// Update statistics based on filtered data
function updateFilteredStats() {
    // For aggregated views, use all data in the table (no filter applied)
    const dataToUse = (aggregationLevel === 'agency' || aggregationLevel === 'bureau') 
        ? dataTable.rows().data() 
        : dataTable.rows({ filter: 'applied' }).data();
    
    let totalBudget = 0;
    let totalUnobligated = 0;
    let count = 0;
    const uniqueAgencies = new Set();
    const uniqueBureaus = new Set();
    
    dataToUse.each(function(row) {
        totalBudget += row.budgetAuthorityValue;
        totalUnobligated += row.unobligatedValue;
        count++;
        
        // Track unique agencies and bureaus
        if (row.Agency) uniqueAgencies.add(row.Agency);
        if (row.Bureau) uniqueBureaus.add(row.Bureau);
    });
    
    const overallPercentage = totalBudget > 0 ? (totalUnobligated / totalBudget * 100) : 0;
    
    // Update display
    $('#totalBudget').text(formatCurrency(totalBudget));
    $('#totalUnobligated').text(formatCurrency(totalUnobligated));
    $('#overallPercentage').text(overallPercentage.toFixed(1) + '%');
    
    // For aggregated views, show the count of unique entities
    let entityType, entityCount;
    if (aggregationLevel === 'agency') {
        entityCount = uniqueAgencies.size;
        entityType = entityCount === 1 ? 'agency' : 'agencies';
        $('#accountCount').text(entityCount + ' ' + entityType);
    } else if (aggregationLevel === 'bureau') {
        entityCount = uniqueBureaus.size;
        entityType = entityCount === 1 ? 'bureau' : 'bureaus';
        $('#accountCount').text(entityCount + ' ' + entityType);
    } else {
        entityCount = count;
        entityType = 'accounts';
        $('#accountCount').text(count);
    }
    
    // Announce to screen readers
    const announcement = `Showing ${entityCount} ${entityType}. Total budget authority: ${formatCurrency(totalBudget)}, Total unobligated: ${formatCurrency(totalUnobligated)}, ${overallPercentage.toFixed(1)}% unobligated.`;
    $('#ariaLiveRegion').text(announcement);
}

// Update bubble chart title based on filters
function updateBubbleChartTitle() {
    const titleElement = $('#bubbleChartTitle');
    let title = "Budget Authority vs. Unobligated Balance";
    
    // Add filter context to title
    const agency = $('#mainAgencyFilter').val();
    const bureau = $('#mainBureauFilter').val();
    
    if (agency || bureau) {
        title += " - ";
        if (agency) title += agency;
        if (bureau) title += (agency ? ", " : "") + bureau;
    }
    
    titleElement.text(title);
}

// Initialize bubble chart
function initializeBubbleChart() {
    const container = d3.select('#bubble-chart');
    container.selectAll('*').remove();
    
    // Update the title
    updateBubbleChartTitle();
    
    // Get dimensions
    const margin = {top: 20, right: 40, bottom: 60, left: 40};
    const width = container.node().getBoundingClientRect().width - margin.left - margin.right;
    const height = 400 - margin.top - margin.bottom;
    
    // Show data based on aggregation level
    let dataToShow, bubbleLabel;
    
    if (aggregationLevel === 'agency') {
        // Show agency-level aggregated data
        const filteredAgencyData = getFilteredAgencyData(true); // true for bubble chart
        dataToShow = filteredAgencyData.filter(d => d.budgetAuthority > 0);
        bubbleLabel = d => d.name;
    } else if (aggregationLevel === 'bureau') {
        // Show bureau-level aggregated data
        const filteredBureauData = getFilteredBureauData(true); // true for bubble chart
        dataToShow = filteredBureauData.filter(d => d.budgetAuthority > 0);
        bubbleLabel = d => d.name;
    } else {
        // Show individual accounts
        dataToShow = getFilteredAccountData(true).filter(d => d.budgetAuthorityValue > 0); // true for bubble chart
        bubbleLabel = d => d.Account || 'Unknown';
    }
    
    // Create scales
    const xScale = d3.scaleLinear()
        .domain([0, 100])
        .range([0, width]);
    
    // Size scale for bubbles
    const maxBudget = d3.max(dataToShow, d => d.budgetAuthority || d.budgetAuthorityValue || 0);
    const sizeScale = d3.scaleSqrt()
        .domain([0, maxBudget])
        .range([5, 40]);
    
    // Create force simulation for jittering
    const simulation = d3.forceSimulation(dataToShow)
        .force('x', d3.forceX(d => xScale(d.percentageUnobligated || d.percentageValue || 0)).strength(1))
        .force('y', d3.forceY(height / 2).strength(0.1))
        .force('collide', d3.forceCollide(d => sizeScale(d.budgetAuthority || d.budgetAuthorityValue || 0) + 2))
        .stop();
    
    // Run simulation
    for (let i = 0; i < 120; ++i) simulation.tick();
    
    // Create SVG
    const svg = container
        .append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom);
    
    // Add defs for patterns
    const defs = svg.append('defs');
    
    // Create patterns
    PATTERN_DEFINITIONS.forEach((pattern) => {
        const patternEl = defs.append('pattern')
            .attr('id', `pattern-${pattern.id}`)
            .attr('patternUnits', 'userSpaceOnUse')
            .attr('width', 8)
            .attr('height', 8);
        
        if (pattern.fill) {
            patternEl.append('circle')
                .attr('cx', 4)
                .attr('cy', 4)
                .attr('r', 2)
                .attr('fill', 'rgba(0,0,0,0.3)');
        } else {
            patternEl.append('path')
                .attr('d', pattern.path)
                .attr('stroke', 'rgba(0,0,0,0.3)')
                .attr('stroke-width', pattern.strokeWidth)
                .attr('fill', 'none');
        }
    });
    
    const g = svg.append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);
    
    // Add grid
    g.append('g')
        .attr('class', 'grid')
        .attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(xScale)
            .tickSize(-height)
            .tickFormat(''));
    
    // Add x-axis only
    g.append('g')
        .attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(xScale)
            .tickFormat(d => Math.round(d) + '%'));
    
    // Add axis label
    g.append('text')
        .attr('class', 'axis-label')
        .attr('text-anchor', 'middle')
        .attr('x', width / 2)
        .attr('y', height + 45)
        .text('Percentage Unobligated');
    
    // Remove any existing tooltips first
    d3.selectAll('.tooltip').remove();
    
    // Create tooltip
    const tooltip = d3.select('body').append('div')
        .attr('class', 'tooltip')
        .style('opacity', 0)
        .style('position', 'absolute')
        .style('background', 'rgba(0, 0, 0, 0.8)')
        .style('color', 'white')
        .style('padding', '10px')
        .style('border-radius', '4px')
        .style('font-size', '12px')
        .style('pointer-events', 'none');
    
    // Add bubble groups for two-color design
    const bubbleGroups = g.selectAll('.bubble-group')
        .data(dataToShow)
        .enter().append('g')
        .attr('class', 'bubble-group');
    
    // Add outer circles (agency color)
    bubbleGroups.append('circle')
        .attr('class', 'bubble bubble-outer')
        .attr('cx', d => d.x)
        .attr('cy', d => d.y)
        .attr('r', d => sizeScale(d.budgetAuthority || d.budgetAuthorityValue || 0))
        .attr('fill', d => {
            if (aggregationLevel === 'agency') {
                return AGENCY_COLORS[d.name] || '#999999';
            } else if (aggregationLevel === 'bureau') {
                return AGENCY_COLORS[d.agency] || '#999999';
            } else {
                return AGENCY_COLORS[d.Agency] || '#999999';
            }
        })
        .style('stroke', '#333')
        .style('stroke-width', 1);
    
    // Add pattern overlay for accessibility
    bubbleGroups.append('circle')
        .attr('class', 'bubble-pattern')
        .attr('cx', d => d.x)
        .attr('cy', d => d.y)
        .attr('r', d => sizeScale(d.budgetAuthority || d.budgetAuthorityValue || 0))
        .attr('fill', d => {
            let agencyName;
            if (aggregationLevel === 'agency') {
                agencyName = d.name;
            } else if (aggregationLevel === 'bureau') {
                agencyName = d.agency;
            } else {
                agencyName = d.Agency;
            }
            const color = AGENCY_COLORS[agencyName] || '#999999';
            const patternId = COLOR_TO_PATTERN[color];
            return patternId ? `url(#pattern-${patternId})` : 'none';
        })
        .style('pointer-events', 'all');
    
    
    // Add hover handlers to bubble groups
    bubbleGroups
        .on('mouseover', function(event, d) {
            tooltip.transition()
                .duration(200)
                .style('opacity', .9);
            
            // Different tooltips based on aggregation level
            if (aggregationLevel === 'agency') {
                // Agency-level data
                tooltip.html(`
                    <strong>${d.name}</strong><br/>
                    Budget Authority: ${formatCurrency(d.budgetAuthority)}<br/>
                    Obligated: ${formatCurrency(d.budgetAuthority - d.unobligated)}<br/>
                    Unobligated: ${formatCurrency(d.unobligated)}<br/>
                    % Unobligated: ${d.percentageUnobligated.toFixed(1)}%<br/>
                    Bureaus: ${d.bureauCount}<br/>
                    Accounts: ${d.accountCount}<br/>
                    Period: ${d.period}<br/>
                    Expires: ${d.expiration}
                `);
            } else if (aggregationLevel === 'bureau') {
                // Bureau-level data
                tooltip.html(`
                    <strong>${d.name}</strong><br/>
                    Agency: ${d.agency}<br/>
                    Budget Authority: ${formatCurrency(d.budgetAuthority)}<br/>
                    Obligated: ${formatCurrency(d.budgetAuthority - d.unobligated)}<br/>
                    Unobligated: ${formatCurrency(d.unobligated)}<br/>
                    % Unobligated: ${d.percentageUnobligated.toFixed(1)}%<br/>
                    Accounts: ${d.accountCount}<br/>
                    Period: ${d.period}<br/>
                    Expires: ${d.expiration}
                `);
            } else {
                // Account-level tooltip
                const budget = d.budgetAuthorityValue || 0;
                const unobligated = d.unobligatedValue || 0;
                tooltip.html(`
                    <strong>${bubbleLabel(d)}</strong><br/>
                    Agency: ${d.Agency || 'Unknown'}<br/>
                    Bureau: ${d.Bureau || 'Unknown'}<br/>
                    Budget Authority: ${formatCurrency(budget)}<br/>
                    Obligated: ${formatCurrency(budget - unobligated)}<br/>
                    Unobligated: ${formatCurrency(unobligated)}<br/>
                    % Unobligated: ${(d.percentageValue || 0).toFixed(1)}%<br/>
                    Period: ${d.Period_of_Performance || 'Unknown'}<br/>
                    ${d.Expiration_Year ? `Expires: ${d.Expiration_Year}` : ''}
                `);
            }
            tooltip.style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY - 28) + 'px');
        })
        .on('mouseout', function() {
            tooltip.transition()
                .duration(500)
                .style('opacity', 0);
        });
    
    // Add reference lines at 50% and 75%
    g.append('line')
        .attr('x1', xScale(50))
        .attr('x2', xScale(50))
        .attr('y1', 0)
        .attr('y2', height)
        .attr('stroke', '#ff9800')
        .attr('stroke-dasharray', '3,3')
        .attr('opacity', 0.5);
    
    g.append('line')
        .attr('x1', xScale(75))
        .attr('x2', xScale(75))
        .attr('y1', 0)
        .attr('y2', height)
        .attr('stroke', '#f44336')
        .attr('stroke-dasharray', '3,3')
        .attr('opacity', 0.5);
    
    // Add reference line labels
    g.append('text')
        .attr('x', xScale(50))
        .attr('y', 10)
        .attr('text-anchor', 'middle')
        .attr('font-size', '12px')
        .attr('fill', '#ff9800')
        .text('50%');
    
    g.append('text')
        .attr('x', xScale(75))
        .attr('y', 10)
        .attr('text-anchor', 'middle')
        .attr('font-size', '12px')
        .attr('fill', '#f44336')
        .text('75%');
    
    // Add size legend
    const sizeLegend = g.append('g')
        .attr('transform', `translate(${width - 100}, 20)`);
    
    sizeLegend.append('text')
        .attr('x', 0)
        .attr('y', -5)
        .attr('font-size', '11px')
        .attr('fill', '#666')
        .text('Budget Authority');
    
    const legendSizes = [10, 100, 1000];
    legendSizes.forEach((size, i) => {
        const r = sizeScale(size);
        const y = 20 + i * 35;
        
        sizeLegend.append('circle')
            .attr('cx', 0)
            .attr('cy', y)
            .attr('r', r)
            .attr('fill', 'none')
            .attr('stroke', '#999')
            .attr('stroke-dasharray', '2,2');
        
        sizeLegend.append('text')
            .attr('x', 20)
            .attr('y', y + 4)
            .attr('font-size', '10px')
            .attr('fill', '#666')
            .text('$' + size + 'M');
    });
}

// Get filtered account data
function getFilteredAccountData(forBubbleChart = false) {
    // Filter the raw account data based on current filters
    const filteredData = obligationData.filter(row => {
        // Check Agency filter
        if (columnFilters.Agency && 
            columnFilters.Agency.length > 0 &&
            !columnFilters.Agency.includes(row.Agency)) {
            return false;
        }
        
        // Check Bureau filter
        if (columnFilters.Bureau && 
            columnFilters.Bureau.length > 0 &&
            !columnFilters.Bureau.includes(row.Bureau)) {
            return false;
        }
        
        // Check Period filter
        if (columnFilters.Period_of_Performance && 
            columnFilters.Period_of_Performance.length > 0 &&
            !columnFilters.Period_of_Performance.includes(row.Period_of_Performance)) {
            return false;
        }
        
        // Check Expiration Year filter
        if (columnFilters.Expiration_Year && 
            columnFilters.Expiration_Year.length > 0 &&
            !columnFilters.Expiration_Year.includes(row.Expiration_Year)) {
            return false;
        }
        
        // Check percentage range filter
        if (columnFilters.Percentage_Range) {
            const percentage = row.percentageValue;
            const [min, max] = columnFilters.Percentage_Range.split('-').map(v => parseFloat(v));
            
            if (!(percentage >= min && percentage <= max)) {
                return false;
            }
        }
        
        return true;
    });
    
    // For bubble chart, aggregate accounts by agency/bureau/account (no period/expiration)
    if (forBubbleChart) {
        const accountMap = new Map();
        
        filteredData.forEach(row => {
            const key = `${row.Agency}|${row.Bureau}|${row.Account}`;
            
            if (!accountMap.has(key)) {
                accountMap.set(key, {
                    Agency: row.Agency,
                    Bureau: row.Bureau,
                    Account: row.Account,
                    Account_Number: row.Account_Number,
                    Period_of_Performance: 'All',
                    Expiration_Year: 'All',
                    TAFS: row.TAFS,
                    budgetAuthorityValue: 0,
                    unobligatedValue: 0,
                    'Unobligated Balance (Line 2490)': '',
                    'Budget Authority (Line 2500)': '',
                    'Percentage Unobligated': '',
                    percentageValue: 0
                });
            }
            
            const account = accountMap.get(key);
            account.budgetAuthorityValue += row.budgetAuthorityValue;
            account.unobligatedValue += row.unobligatedValue;
        });
        
        // Calculate percentages and format values
        return Array.from(accountMap.values()).map(account => {
            account.percentageValue = account.budgetAuthorityValue > 0 ? 
                (account.unobligatedValue / account.budgetAuthorityValue * 100) : 0;
            account['Unobligated Balance (Line 2490)'] = formatCurrency(account.unobligatedValue);
            account['Budget Authority (Line 2500)'] = formatCurrency(account.budgetAuthorityValue);
            account['Percentage Unobligated'] = account.percentageValue.toFixed(1) + '%';
            return account;
        });
    }
    
    return filteredData;
}

// Get filtered agency data based on current filters
function getFilteredAgencyData(forBubbleChart = false) {
    // Filter the raw data first
    const filteredAccounts = obligationData.filter(row => {
        // Check Agency filter
        if (columnFilters.Agency && 
            columnFilters.Agency.length > 0 &&
            !columnFilters.Agency.includes(row.Agency)) {
            return false;
        }
        
        // Check Bureau filter
        if (columnFilters.Bureau && 
            columnFilters.Bureau.length > 0 &&
            !columnFilters.Bureau.includes(row.Bureau)) {
            return false;
        }
        
        // Check Period filter
        if (columnFilters.Period_of_Performance && 
            columnFilters.Period_of_Performance.length > 0 &&
            !columnFilters.Period_of_Performance.includes(row.Period_of_Performance)) {
            return false;
        }
        
        // Check Expiration Year filter
        if (columnFilters.Expiration_Year && 
            columnFilters.Expiration_Year.length > 0 &&
            !columnFilters.Expiration_Year.includes(row.Expiration_Year)) {
            return false;
        }
        
        // Check percentage range filter
        if (columnFilters.Percentage_Range) {
            const percentage = row.percentageValue;
            const [min, max] = columnFilters.Percentage_Range.split('-').map(v => parseFloat(v));
            
            if (!(percentage >= min && percentage <= max)) {
                return false;
            }
        }
        
        return true;
    });
    
    // Re-aggregate by agency (without period/expiration for bubble chart)
    const aggregateMap = new Map();
    
    filteredAccounts.forEach(row => {
        const agency = row.Agency || 'Other';
        const period = row.Period_of_Performance || 'Unknown';
        const expiration = row.Expiration_Year || 'Unknown';
        
        // For bubble chart, aggregate only by agency. For table, include period/expiration
        const key = forBubbleChart ? agency : `${agency}|${period}|${expiration}`;
        
        if (!aggregateMap.has(key)) {
            // Check if filters are applied
            const periodFilter = columnFilters.Period_of_Performance;
            const yearFilter = columnFilters.Expiration_Year;
            
            aggregateMap.set(key, {
                name: agency,
                period: forBubbleChart ? (periodFilter ? periodFilter.join(', ') : 'All') : period,
                expiration: forBubbleChart ? (yearFilter ? yearFilter.join(', ') : 'All') : expiration,
                budgetAuthority: 0,
                unobligated: 0,
                accountCount: 0,
                bureauCount: new Set()
            });
        }
        
        const aggregateInfo = aggregateMap.get(key);
        aggregateInfo.budgetAuthority += row.budgetAuthorityValue;
        aggregateInfo.unobligated += row.unobligatedValue;
        aggregateInfo.accountCount += 1;
        if (row.Bureau) {
            aggregateInfo.bureauCount.add(row.Bureau);
        }
    });
    
    // Convert to array and calculate percentages
    return Array.from(aggregateMap.values()).map(aggregate => ({
        ...aggregate,
        bureauCount: aggregate.bureauCount.size,
        percentageUnobligated: aggregate.budgetAuthority > 0 ? 
            (aggregate.unobligated / aggregate.budgetAuthority * 100) : 0
    }));
}

// Get filtered bureau data based on current filters
function getFilteredBureauData(forBubbleChart = false) {
    // Filter the raw data first
    const filteredAccounts = obligationData.filter(row => {
        // Check Agency filter
        if (columnFilters.Agency && 
            columnFilters.Agency.length > 0 &&
            !columnFilters.Agency.includes(row.Agency)) {
            return false;
        }
        
        // Check Bureau filter
        if (columnFilters.Bureau && 
            columnFilters.Bureau.length > 0 &&
            !columnFilters.Bureau.includes(row.Bureau)) {
            return false;
        }
        
        // Check Period filter
        if (columnFilters.Period_of_Performance && 
            columnFilters.Period_of_Performance.length > 0 &&
            !columnFilters.Period_of_Performance.includes(row.Period_of_Performance)) {
            return false;
        }
        
        // Check Expiration Year filter
        if (columnFilters.Expiration_Year && 
            columnFilters.Expiration_Year.length > 0 &&
            !columnFilters.Expiration_Year.includes(row.Expiration_Year)) {
            return false;
        }
        
        // Check percentage range filter
        if (columnFilters.Percentage_Range) {
            const percentage = row.percentageValue;
            const [min, max] = columnFilters.Percentage_Range.split('-').map(v => parseFloat(v));
            
            if (!(percentage >= min && percentage <= max)) {
                return false;
            }
        }
        
        return true;
    });
    
    // Re-aggregate by agency/bureau (without period/expiration for bubble chart)
    const aggregateMap = new Map();
    
    filteredAccounts.forEach(row => {
        const agency = row.Agency || 'Other';
        const bureau = row.Bureau || 'Other';
        const period = row.Period_of_Performance || 'Unknown';
        const expiration = row.Expiration_Year || 'Unknown';
        
        // For bubble chart, aggregate only by agency/bureau. For table, include period/expiration
        const key = forBubbleChart ? `${agency}|${bureau}` : `${agency}|${bureau}|${period}|${expiration}`;
        
        if (!aggregateMap.has(key)) {
            // Check if filters are applied
            const periodFilter = columnFilters.Period_of_Performance;
            const yearFilter = columnFilters.Expiration_Year;
            
            aggregateMap.set(key, {
                agency: agency,
                name: bureau,
                period: forBubbleChart ? (periodFilter ? periodFilter.join(', ') : 'All') : period,
                expiration: forBubbleChart ? (yearFilter ? yearFilter.join(', ') : 'All') : expiration,
                budgetAuthority: 0,
                unobligated: 0,
                accountCount: 0
            });
        }
        
        const aggregateInfo = aggregateMap.get(key);
        aggregateInfo.budgetAuthority += row.budgetAuthorityValue;
        aggregateInfo.unobligated += row.unobligatedValue;
        aggregateInfo.accountCount += 1;
    });
    
    // Convert to array and calculate percentages
    return Array.from(aggregateMap.values()).map(aggregate => ({
        ...aggregate,
        percentageUnobligated: aggregate.budgetAuthority > 0 ? 
            (aggregate.unobligated / aggregate.budgetAuthority * 100) : 0
    }));
}


// Show aggregated table (agency or bureau totals)
function showAggregatedTable(level) {
    let aggregatedRows;
    
    if (level === 'agency') {
        // Get filtered agency data (aggregated by agency/period/expiration)
        const filteredAgencyData = getFilteredAgencyData();
        
        // Transform agency data to match table structure
        aggregatedRows = filteredAgencyData.map(aggregate => ({
            Agency: aggregate.name,
            Bureau: `${aggregate.bureauCount} bureaus`,
            Account: `${aggregate.accountCount} accounts`,
            Account_Number: '',
            Period_of_Performance: aggregate.period,
            Expiration_Year: aggregate.expiration,
            'Unobligated Balance (Line 2490)': formatCurrency(aggregate.unobligated),
            'Budget Authority (Line 2500)': formatCurrency(aggregate.budgetAuthority),
            'Percentage Unobligated': aggregate.percentageUnobligated.toFixed(1) + '%',
            unobligatedValue: aggregate.unobligated,
            budgetAuthorityValue: aggregate.budgetAuthority,
            percentageValue: aggregate.percentageUnobligated,
            TAFS: ''
        }));
    } else {
        // Get filtered bureau data (aggregated by bureau/period/expiration)
        const filteredBureauData = getFilteredBureauData();
        
        // Transform bureau data to match table structure
        aggregatedRows = filteredBureauData.map(aggregate => ({
            Agency: aggregate.agency,
            Bureau: aggregate.name,
            Account: `${aggregate.accountCount} accounts`,
            Account_Number: '',
            Period_of_Performance: aggregate.period,
            Expiration_Year: aggregate.expiration,
            'Unobligated Balance (Line 2490)': formatCurrency(aggregate.unobligated),
            'Budget Authority (Line 2500)': formatCurrency(aggregate.budgetAuthority),
            'Percentage Unobligated': aggregate.percentageUnobligated.toFixed(1) + '%',
            unobligatedValue: aggregate.unobligated,
            budgetAuthorityValue: aggregate.budgetAuthority,
            percentageValue: aggregate.percentageUnobligated,
            TAFS: ''
        }));
    }
    
    // Clear existing data and add new data
    dataTable.clear();
    dataTable.rows.add(aggregatedRows);
    dataTable.draw();
    
    // Sort by Expiration Year (column index 5) ascending to keep year sorting
    dataTable.order([5, 'asc']).draw();
    
    // Update statistics after table is redrawn
    updateFilteredStats();
}

// Show detailed table (individual accounts)
function showDetailedTable() {
    // Get the filtered data respecting current filters
    const filteredData = getFilteredAccountData();
    
    // Clear and add filtered data
    dataTable.clear();
    dataTable.rows.add(filteredData);
    dataTable.draw();
    
    // Sort by Expiration Year (column index 5) ascending to keep year sorting
    dataTable.order([5, 'asc']).draw();
    
    // Update statistics after table is redrawn
    updateFilteredStats();
}

// Convert table data to CSV format
function tableToCSV() {
    let csvContent = [];
    
    // Get the visible data from DataTable
    const data = dataTable.rows({ search: 'applied' }).data();
    
    // Add header row based on aggregation level
    let headers;
    if (aggregationLevel === 'agency') {
        headers = [
            'Agency',
            'Bureau Count',
            'Account Count',
            'Period',
            'Expiration',
            'Unobligated (2490)',
            'Budget Authority (2500)',
            '% Unobligated'
        ];
    } else if (aggregationLevel === 'bureau') {
        headers = [
            'Agency',
            'Bureau',
            'Account Count',
            'Period',
            'Expiration',
            'Unobligated (2490)',
            'Budget Authority (2500)',
            '% Unobligated'
        ];
    } else {
        headers = [
            'Agency',
            'Bureau', 
            'Account',
            'Account Number',
            'Period',
            'Expiration',
            'Unobligated (2490)',
            'Budget Authority (2500)',
            '% Unobligated'
        ];
    }
    csvContent.push(headers.join(','));
    
    // Add data rows
    data.each(function(row) {
        let csvRow;
        if (aggregationLevel === 'agency') {
            csvRow = [
                '"' + row.Agency + '"',
                '"' + row.Bureau + '"',
                '"' + row.Account + '"',
                '"' + row.Period_of_Performance + '"',
                '"' + row.Expiration_Year + '"',
                row.unobligatedValue,
                row.budgetAuthorityValue,
                row.percentageValue.toFixed(1)
            ];
        } else if (aggregationLevel === 'bureau') {
            csvRow = [
                '"' + row.Agency + '"',
                '"' + row.Bureau + '"',
                '"' + row.Account + '"',
                '"' + row.Period_of_Performance + '"',
                '"' + row.Expiration_Year + '"',
                row.unobligatedValue,
                row.budgetAuthorityValue,
                row.percentageValue.toFixed(1)
            ];
        } else {
            csvRow = [
                '"' + row.Agency + '"',
                '"' + row.Bureau + '"',
                '"' + row.Account + '"',
                '"' + row.Account_Number + '"',
                '"' + row.Period_of_Performance + '"',
                '"' + row.Expiration_Year + '"',
                row.unobligatedValue,
                row.budgetAuthorityValue,
                row.percentageValue.toFixed(1)
            ];
        }
        csvContent.push(csvRow.join(','));
    });
    
    return csvContent.join('\n');
}

// Download CSV file
function downloadCSV() {
    const csv = tableToCSV();
    const timestamp = new Date().toISOString().split('T')[0];
    const level = aggregationLevel === 'account' ? 'accounts' : aggregationLevel;
    const filename = `obligation_data_${level}_${timestamp}.csv`;
    
    // Create blob and download link
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Load fiscal year metadata (month information)
async function loadFiscalYearMetadata() {
    try {
        const response = await fetch('data/fiscal_year_metadata.json');
        if (response.ok) {
            fiscalYearMetadata = await response.json();
            console.log('Loaded fiscal year metadata:', fiscalYearMetadata);
        } else {
            console.log('No fiscal year metadata file found, using defaults');
        }
    } catch (error) {
        console.log('Could not load fiscal year metadata:', error);
    }
}

// Initialize year selector
async function initializeYearSelector() {
    try {
        // Load metadata first
        await loadFiscalYearMetadata();
        
        // Try to detect available years by checking for year-specific files
        // Generate years from 1998 to 2030
        const testYears = Array.from({length: 2030 - 1998 + 1}, (_, i) => 1998 + i);
        const availableYearsSet = new Set();
        
        for (const year of testYears) {
            try {
                const response = await fetch(`data/all_agencies_obligation_summary_${year}.csv`, { method: 'HEAD' });
                if (response.ok) {
                    availableYearsSet.add(year);
                }
            } catch (e) {
                // File doesn't exist, skip
            }
        }
        
        availableYears = Array.from(availableYearsSet).sort((a, b) => a - b); // Sort ascending (oldest first)
        
        if (availableYears.length === 0) {
            // No year-specific files found, hide year selector
            const yearSection = document.querySelector('.year-selector-section');
            if (yearSection) {
                yearSection.style.display = 'none';
            }
            return;
        }
        
        // Create year selector buttons
        const yearSelector = document.getElementById('yearSelector');
        yearSelector.innerHTML = '';
        
        availableYears.forEach(year => {
            const button = document.createElement('button');
            button.className = 'year-btn';
            button.setAttribute('data-year', year);
            
            // Get month information for this year
            const metadata = fiscalYearMetadata[year.toString()];
            const monthText = metadata ? metadata.display_month : 'Sep'; // Default to Sep if no metadata
            
            // Create button with month above FY
            button.innerHTML = `
                <div style="font-size: 0.8em; opacity: 0.8; line-height: 1;">${monthText} ${year}</div>
                <div style="font-weight: 600;">FY ${year}</div>
            `;
            button.addEventListener('click', () => switchToYear(year));
            yearSelector.appendChild(button);
        });
        
        // Set default year (most recent)
        const defaultYear = availableYears[availableYears.length - 1]; // Last item = most recent
        currentFiscalYear = defaultYear;
        updateYearSelectorUI();
        
    } catch (error) {
        console.error('Error initializing year selector:', error);
        // Hide year selector if there's an error
        const yearSection = document.querySelector('.year-selector-section');
        if (yearSection) {
            yearSection.style.display = 'none';
        }
    }
}

// Update data update text based on current fiscal year
function updateDataUpdateText() {
    const dataUpdateElement = document.getElementById('data-update-text');
    if (dataUpdateElement && currentFiscalYear) {
        const metadata = fiscalYearMetadata[currentFiscalYear.toString()];
        const monthText = metadata ? metadata.month : 'September'; // Default to September if no metadata
        dataUpdateElement.textContent = `Latest data: ${monthText} ${currentFiscalYear}`;
    }
}

// Update year selector UI to reflect current selection
function updateYearSelectorUI() {
    const yearButtons = document.querySelectorAll('.year-btn');
    yearButtons.forEach(btn => {
        const year = parseInt(btn.getAttribute('data-year'));
        if (year === currentFiscalYear) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
        btn.classList.remove('loading'); // Remove any loading states
    });
    
    // Update the data update text
    updateDataUpdateText();
    
    // Update page subtitle if needed
    const subtitle = document.querySelector('.subtitle');
    if (subtitle && currentFiscalYear) {
        // Use more generic subtitle since month varies by year
        subtitle.textContent = `Federal Budget Execution Report - Fiscal Year ${currentFiscalYear}`;
    }
}

// Switch to a different fiscal year
async function switchToYear(year) {
    if (year === currentFiscalYear) {
        return; // Already on this year
    }
    
    // Add loading state to the clicked button
    const yearBtn = document.querySelector(`.year-btn[data-year="${year}"]`);
    if (yearBtn) {
        yearBtn.classList.add('loading');
    }
    
    // Clear existing data and properly destroy DataTable
    obligationData = [];
    if (dataTable) {
        dataTable.destroy();
        dataTable = null;
        
        // Clear the table HTML
        $('#obligationTable').empty();
    }
    
    try {
        // Load new year's data
        await loadData(year);
        
        // Update UI elements that depend on the year
        console.log(`Successfully switched to FY${year}`);
        
        // Preserve existing filter state when switching years
        preserveFiltersAcrossYears();
        
    } catch (error) {
        console.error(`Failed to switch to FY${year}:`, error);
        
        // Remove loading state from button
        if (yearBtn) {
            yearBtn.classList.remove('loading');
        }
        
        alert(`Failed to load data for FY${year}. Please check if the data file exists.`);
    }
}

// Preserve filter state when switching years
function preserveFiltersAcrossYears() {
    // Store current filter values (but NOT expiration year - that should reset to match the new fiscal year)
    const currentFilters = {
        agency: $('#mainAgencyFilter').val(),
        bureau: $('#mainBureauFilter').val(), 
        period: $('#mainPeriodFilter').val(),
        percentage: $('#mainPercentageFilter').val()
    };
    
    // Update dependent filters first to get new available options
    updateDependentFilters();
    
    // Restore filter values if they still exist in the new data
    if (currentFilters.agency && $('#mainAgencyFilter option[value="' + currentFilters.agency + '"]').length > 0) {
        $('#mainAgencyFilter').val(currentFilters.agency);
        updateDependentFilters(); // Update dependent filters after setting agency
    }
    
    if (currentFilters.bureau && $('#mainBureauFilter option[value="' + currentFilters.bureau + '"]').length > 0) {
        $('#mainBureauFilter').val(currentFilters.bureau);
    }
    
    if (currentFilters.period && $('#mainPeriodFilter option[value="' + currentFilters.period + '"]').length > 0) {
        $('#mainPeriodFilter').val(currentFilters.period);
    }
    
    // DON'T restore expiration year - let it default to the new fiscal year
    // Set expiration year to match current fiscal year
    const defaultYear = currentFiscalYear ? currentFiscalYear.toString() : '2025';
    if ($('#mainExpirationFilter option[value="' + defaultYear + '"]').length > 0) {
        $('#mainExpirationFilter').val(defaultYear);
    }
    
    if (currentFilters.percentage && $('#mainPercentageFilter option[value="' + currentFilters.percentage + '"]').length > 0) {
        $('#mainPercentageFilter').val(currentFilters.percentage);
    }
    
    // Apply filters
    updateFiltersFromUI();
    
    // Mark that we've preserved filter state
    window.filterStatePreserved = true;
}

// Initialize on page load
$(document).ready(async function() {
    // Initialize year selector first
    await initializeYearSelector();
    
    // Load initial data
    if (currentFiscalYear) {
        await loadData(currentFiscalYear);
    } else {
        await loadData(); // Load default file
    }
});