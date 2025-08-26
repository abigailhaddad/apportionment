// Federal Agency Obligation Summary - DataTables Implementation

let dataTable;
let obligationData = [];
let columnFilters = {};
let agencyData = [];
let bureauData = [];
let agencyColorScale;
let showBureauAggregates = false;
let aggregationLevel = 'individual'; // 'individual', 'bureau', or 'agency'
let bureauColorMap = new Map(); // Store consistent bureau colors
let bureauColorIndex = 0;

// Tableau 20 colors for consistent bureau coloring
const tableau20 = [
    '#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c',
    '#98df8a', '#d62728', '#ff9896', '#9467bd', '#c5b0d5',
    '#8c564b', '#c49c94', '#e377c2', '#f7b6d2', '#7f7f7f',
    '#c7c7c7', '#bcbd22', '#dbdb8d', '#17becf', '#9edae5'
];

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

// Get color for bureau based on parent agency
function getBureauColor(bureau, agency) {
    const baseColor = AGENCY_COLORS[agency] || '#999999';
    const color = d3.color(baseColor);
    
    // Create more distinct variations using both saturation and lightness
    const bureauHash = bureau.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    
    // Create 7 distinct variations
    const variationIndex = bureauHash % 7;
    
    switch(variationIndex) {
        case 0: // Original color
            return baseColor;
        case 1: // Lighter
            return color.brighter(0.6).toString();
        case 2: // Darker
            return color.darker(0.6).toString();
        case 3: // More saturated
            if (color.s) {
                const hsl = d3.hsl(color);
                hsl.s = Math.min(1, hsl.s * 1.3);
                return hsl.toString();
            }
            return color.brighter(0.3).toString();
        case 4: // Less saturated
            if (color.s) {
                const hsl = d3.hsl(color);
                hsl.s = hsl.s * 0.7;
                return hsl.toString();
            }
            return color.darker(0.3).toString();
        case 5: // Lighter + more saturated
            if (color.s) {
                const hsl = d3.hsl(color);
                hsl.s = Math.min(1, hsl.s * 1.2);
                hsl.l = Math.min(0.9, hsl.l * 1.2);
                return hsl.toString();
            }
            return color.brighter(0.8).toString();
        case 6: // Darker + less saturated
            if (color.s) {
                const hsl = d3.hsl(color);
                hsl.s = hsl.s * 0.8;
                hsl.l = hsl.l * 0.8;
                return hsl.toString();
            }
            return color.darker(0.5).toString();
    }
}

// Get consistent bureau color
function getConsistentBureauColor(bureau) {
    // If we haven't assigned a color to this bureau yet, assign one
    if (!bureauColorMap.has(bureau)) {
        bureauColorMap.set(bureau, tableau20[bureauColorIndex % tableau20.length]);
        bureauColorIndex++;
    }
    return bureauColorMap.get(bureau);
}

// Format currency values
function formatCurrency(value) {
    return '$' + value.toFixed(1).replace(/\B(?=(\d{3})+(?!\d))/g, ',') + 'M';
}

// Format percentage with color coding
function formatPercentage(value) {
    const className = value >= 75 ? 'high-percentage' : 
                     value >= 50 ? 'medium-percentage' : 'low-percentage';
    return `<span class="percentage-cell ${className}">${value.toFixed(1)}%</span>`;
}

// Load CSV data
async function loadData() {
    try {
        console.log('Starting to load CSV data...');
        const response = await fetch('data/all_agencies_obligation_summary.csv');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
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
        
        // Set default filter to Department of Education and 2025 expiration
        $('#mainAgencyFilter').val('Department of Education');
        $('#mainExpirationFilter').val('2025').trigger('change');
        
    } catch (error) {
        console.error('Error loading data:', error);
        console.error('Failed to load: data/education_obligation_summary_enhanced.csv');
        console.error('Make sure you are running the server with ./serve.py or python3 serve.py');
        alert('Error loading data. Please ensure you are running the server with ./serve.py and not just opening the HTML file directly.');
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

// Create column filter HTML
function createColumnFilter(columnName, values) {
    const filterId = `filter-${columnName.replace(/\s+/g, '-')}`;
    let html = `<div class="column-filter-container" id="${filterId}">`;
    html += `<input type="text" class="filter-search" placeholder="Search...">`;
    html += `<div class="filter-values">`;
    
    values.forEach((value, index) => {
        const checkId = `${filterId}-${index}`;
        html += `<label><input type="checkbox" value="${value}" checked> ${value || '(empty)'}</label>`;
    });
    
    html += `</div>`;
    html += `<div class="filter-buttons">`;
    html += `<button class="clear-all">Clear</button>`;
    html += `<button class="select-all">Select All</button>`;
    html += `<button class="apply">Apply</button>`;
    html += `</div>`;
    html += `</div>`;
    
    return html;
}

// Create percentage range filter HTML
function createPercentageRangeFilter() {
    const filterId = 'filter-percentage-range';
    let html = `<div class="column-filter-container" id="${filterId}">`;
    html += `<div class="filter-values">`;
    html += `<label><input type="checkbox" value="0-25" checked> 0-25%</label>`;
    html += `<label><input type="checkbox" value="25-50" checked> 25-50%</label>`;
    html += `<label><input type="checkbox" value="50-75" checked> 50-75%</label>`;
    html += `<label><input type="checkbox" value="75-100" checked> 75-100%</label>`;
    html += `</div>`;
    html += `<div class="filter-buttons">`;
    html += `<button class="clear-all">Clear</button>`;
    html += `<button class="select-all">Select All</button>`;
    html += `<button class="apply">Apply</button>`;
    html += `</div>`;
    html += `</div>`;
    
    return html;
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

// Populate main filter dropdowns
function populateMainFilters() {
    // Get unique values
    const agencies = [...new Set(obligationData.map(row => row.Agency))].filter(a => a).sort();
    const bureaus = [...new Set(obligationData.map(row => row.Bureau))].filter(b => b).sort();
    const periods = [...new Set(obligationData.map(row => row.Period_of_Performance))].filter(p => p).sort();
    const years = [...new Set(obligationData.map(row => row.Expiration_Year))].filter(y => y).sort();
    
    // Populate agency filter
    const agencySelect = $('#mainAgencyFilter');
    agencies.forEach(agency => {
        agencySelect.append(`<option value="${agency}">${agency}</option>`);
    });
    
    // Populate bureau filter
    const bureauSelect = $('#mainBureauFilter');
    bureaus.forEach(bureau => {
        bureauSelect.append(`<option value="${bureau}">${bureau}</option>`);
    });
    
    // Populate period filter
    const periodSelect = $('#mainPeriodFilter');
    periods.forEach(period => {
        periodSelect.append(`<option value="${period}">${period}</option>`);
    });
    
    // Populate expiration year filter
    const yearSelect = $('#mainExpirationFilter');
    years.forEach(year => {
        yearSelect.append(`<option value="${year}">${year}</option>`);
    });
    
    // Set up event handlers for all main filters
    $('#mainAgencyFilter, #mainBureauFilter, #mainPeriodFilter, #mainExpirationFilter, #mainPercentageFilter').on('change', function() {
        updateFiltersFromUI();
    });
    
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
        // Stats are now updated within showAggregatedTable and showDetailedTable
    });
}

// Update filters from UI and display active filter badges
function updateFiltersFromUI() {
    const agency = $('#mainAgencyFilter').val();
    const bureau = $('#mainBureauFilter').val();
    const period = $('#mainPeriodFilter').val();
    const year = $('#mainExpirationFilter').val();
    const percentage = $('#mainPercentageFilter').val();
    
    // Update column filters
    columnFilters.Agency = agency ? [agency] : null;
    columnFilters.Bureau = bureau ? [bureau] : null;
    columnFilters.Period_of_Performance = period ? [period] : null;
    columnFilters.Expiration_Year = year ? [year] : null;
    columnFilters.Percentage_Ranges = percentage ? [percentage] : null;
    
    // Helper function to get filtered data based on all current filters
    const getFilteredData = (includeAgency, includeBureau, includePeriod, includeYear) => {
        let filtered = obligationData;
        
        if (includeAgency && agency) {
            filtered = filtered.filter(row => row.Agency === agency);
        }
        if (includeBureau && bureau) {
            filtered = filtered.filter(row => row.Bureau === bureau);
        }
        if (includePeriod && period) {
            filtered = filtered.filter(row => row.Period_of_Performance === period);
        }
        if (includeYear && year) {
            filtered = filtered.filter(row => row.Expiration_Year === year);
        }
        if (percentage) {
            const [min, max] = percentage.split('-').map(v => parseFloat(v));
            filtered = filtered.filter(row => row.percentageValue >= min && row.percentageValue <= max);
        }
        
        return filtered;
    };
    
    // Update bureau options - filter by agency and other active filters
    const bureauSelect = $('#mainBureauFilter');
    const currentBureau = bureauSelect.val();
    const bureauFiltered = getFilteredData(true, false, true, true); // Include agency, period, year filters
    const availableBureaus = [...new Set(bureauFiltered.map(row => row.Bureau).filter(b => b))].sort();
    bureauSelect.empty();
    bureauSelect.append('<option value="">All Bureaus</option>');
    availableBureaus.forEach(b => {
        bureauSelect.append(`<option value="${b}">${b}</option>`);
    });
    if (availableBureaus.includes(currentBureau)) {
        bureauSelect.val(currentBureau);
    }
    
    // Update period options - filter by agency, bureau, and year
    const periodSelect = $('#mainPeriodFilter');
    const currentPeriod = periodSelect.val();
    const periodFiltered = getFilteredData(true, true, false, true); // Include agency, bureau, year filters
    const availablePeriods = [...new Set(periodFiltered.map(row => row.Period_of_Performance).filter(p => p))].sort();
    periodSelect.empty();
    periodSelect.append('<option value="">All Periods</option>');
    availablePeriods.forEach(p => {
        periodSelect.append(`<option value="${p}">${p}</option>`);
    });
    if (availablePeriods.includes(currentPeriod)) {
        periodSelect.val(currentPeriod);
    }
    
    // Update expiration year options - filter by agency, bureau, and period
    const yearSelect = $('#mainExpirationFilter');
    const currentYear = yearSelect.val();
    const yearFiltered = getFilteredData(true, true, true, false); // Include agency, bureau, period filters
    const availableYears = [...new Set(yearFiltered.map(row => row.Expiration_Year).filter(y => y))].sort();
    yearSelect.empty();
    yearSelect.append('<option value="">All Years</option>');
    availableYears.forEach(y => {
        yearSelect.append(`<option value="${y}">${y}</option>`);
    });
    if (availableYears.includes(currentYear)) {
        yearSelect.val(currentYear);
    }
    
    // Update active filter badges
    updateActiveFilterBadges();
    
    // Apply all filters
    applyAllFilters();
}

// Update active filter badges display
function updateActiveFilterBadges() {
    const $activeFilters = $('#activeFilters');
    $activeFilters.empty();
    
    const filters = [];
    
    if ($('#mainAgencyFilter').val()) {
        filters.push({
            type: 'Agency',
            value: $('#mainAgencyFilter').val(),
            id: 'mainAgencyFilter'
        });
    }
    
    if ($('#mainBureauFilter').val()) {
        filters.push({
            type: 'Bureau',
            value: $('#mainBureauFilter').val(),
            id: 'mainBureauFilter'
        });
    }
    
    if ($('#mainPeriodFilter').val()) {
        filters.push({
            type: 'Period',
            value: $('#mainPeriodFilter').val(),
            id: 'mainPeriodFilter'
        });
    }
    
    if ($('#mainExpirationFilter').val()) {
        filters.push({
            type: 'Expiration Year',
            value: $('#mainExpirationFilter').val(),
            id: 'mainExpirationFilter'
        });
    }
    
    if ($('#mainPercentageFilter').val()) {
        const range = $('#mainPercentageFilter').val();
        filters.push({
            type: 'Unobligated %',
            value: range.replace('-', '-') + '%',
            id: 'mainPercentageFilter'
        });
    }
    
    if (filters.length === 0) {
        $activeFilters.html('<span style="color: #999;">No filters active</span>');
    } else {
        filters.forEach(filter => {
            const $badge = $(`<span class="filter-badge">
                ${filter.type}: ${filter.value}
                <span class="remove-filter" data-filter-id="${filter.id}">×</span>
            </span>`);
            $activeFilters.append($badge);
        });
        
        // Set up remove filter handlers
        $('.remove-filter').on('click', function() {
            const filterId = $(this).data('filter-id');
            $(`#${filterId}`).val('').trigger('change');
        });
    }
}

// Initialize DataTable
function initializeDataTable() {
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
                render: function(data, type, row) {
                    if (type === 'display' && data) {
                        const color = getConsistentBureauColor(data);
                        return `<span style="display: inline-block; width: 10px; height: 10px; 
                                background-color: ${color}; border-radius: 50%; margin-right: 6px;"></span>${data}`;
                    }
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
                render: function(data) {
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
    
    // Set up column click filters
    setupColumnFilters();
}

// Setup column click filters
function setupColumnFilters() {
    // Define which columns should have filters
    const filterColumns = [
        { index: 0, name: 'Agency' },
        { index: 1, name: 'Bureau' },
        { index: 4, name: 'Period_of_Performance' },
        { index: 5, name: 'Expiration_Year' },
        { index: 8, name: 'Percentage_Unobligated' }
    ];
    
    // Add click handlers to specific column headers
    filterColumns.forEach(col => {
        const th = $(`#obligationTable thead th:eq(${col.index})`);
        th.addClass('has-filter');
        
        th.on('click', function(e) {
            e.stopPropagation();
            
            // Close any open filters
            $('.column-filter-container').remove();
            $('.filtering').removeClass('filtering');
            
            // Special handling for percentage column
            let filterHtml;
            if (col.name === 'Percentage_Unobligated') {
                // Create percentage range filter
                filterHtml = createPercentageRangeFilter();
                const $filter = $(filterHtml);
                
                // Position the filter
                const offset = $(this).offset();
                $filter.css({
                    top: offset.top + $(this).outerHeight(),
                    left: offset.left
                });
                
                $('body').append($filter);
                $(this).addClass('filtering');
                
                // Initialize percentage filter behavior
                initializePercentageFilterBehavior($filter);
            } else {
                // Get unique values for this column
                const columnData = dataTable.column(col.index).data().unique().sort();
                const uniqueValues = Array.from(columnData).filter(v => v !== null && v !== undefined);
                
                // Create and show filter
                filterHtml = createColumnFilter(col.name, uniqueValues);
                const $filter = $(filterHtml);
                
                // Position the filter
                const offset = $(this).offset();
                $filter.css({
                    top: offset.top + $(this).outerHeight(),
                    left: offset.left
                });
                
                $('body').append($filter);
                $(this).addClass('filtering');
                
                // Initialize filter behavior
                initializeFilterBehavior($filter, col.index, col.name);
            }
        });
    });
    
    // Close filter when clicking outside
    $(document).on('click', function(e) {
        if (!$(e.target).closest('.column-filter-container, .has-filter').length) {
            $('.column-filter-container').remove();
            $('.filtering').removeClass('filtering');
        }
    });
}

// Initialize filter behavior
function initializeFilterBehavior($filter, columnIndex, columnName) {
    const $searchInput = $filter.find('.filter-search');
    const $checkboxes = $filter.find('input[type="checkbox"]');
    
    // Search functionality
    $searchInput.on('input', function() {
        const searchTerm = $(this).val().toLowerCase();
        $filter.find('label').each(function() {
            const text = $(this).text().toLowerCase();
            $(this).toggle(text.includes(searchTerm));
        });
    });
    
    // Select all button
    $filter.find('.select-all').on('click', function() {
        $checkboxes.prop('checked', true);
    });
    
    // Clear all button
    $filter.find('.clear-all').on('click', function() {
        $checkboxes.prop('checked', false);
    });
    
    // Apply button
    $filter.find('.apply').on('click', function() {
        const selectedValues = [];
        $checkboxes.filter(':checked').each(function() {
            selectedValues.push($(this).val());
        });
        
        // Store filter state
        columnFilters[columnName] = selectedValues;
        
        // Apply all filters (column + percentage)
        applyAllFilters();
        
        // Close filter
        $filter.remove();
        $('.filtering').removeClass('filtering');
    });
}

// Initialize percentage filter behavior
function initializePercentageFilterBehavior($filter) {
    const $checkboxes = $filter.find('input[type="checkbox"]');
    
    // Select all button
    $filter.find('.select-all').on('click', function() {
        $checkboxes.prop('checked', true);
    });
    
    // Clear all button
    $filter.find('.clear-all').on('click', function() {
        $checkboxes.prop('checked', false);
    });
    
    // Apply button
    $filter.find('.apply').on('click', function() {
        const selectedRanges = [];
        $checkboxes.filter(':checked').each(function() {
            selectedRanges.push($(this).val());
        });
        
        // Store filter state
        columnFilters.Percentage_Ranges = selectedRanges;
        
        // Apply all filters
        applyAllFilters();
        
        // Close filter
        $filter.remove();
        $('.filtering').removeClass('filtering');
    });
}

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
        if (show && columnFilters.Percentage_Ranges && columnFilters.Percentage_Ranges.length > 0) {
            const percentage = parseFloat(data[8].replace(/<[^>]*>/g, '').replace('%', ''));
            let inRange = false;
            
            for (const range of columnFilters.Percentage_Ranges) {
                const [min, max] = range.split('-').map(v => parseFloat(v));
                if (percentage >= min && percentage <= max) {
                    inRange = true;
                    break;
                }
            }
            
            if (!inRange) {
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
        // Individual accounts - apply the filter and draw
        dataTable.draw();
        updateFilteredStats();
    }
    
    // Update bubble chart
    initializeBubbleChart();
}

// Update statistics based on filtered data
function updateFilteredStats() {
    const filteredData = dataTable.rows({ filter: 'applied' }).data();
    let totalBudget = 0;
    let totalUnobligated = 0;
    let count = 0;
    
    filteredData.each(function(row) {
        totalBudget += row.budgetAuthorityValue;
        totalUnobligated += row.unobligatedValue;
        count++;
    });
    
    const overallPercentage = totalBudget > 0 ? (totalUnobligated / totalBudget * 100) : 0;
    
    // Update display
    $('#totalBudget').text(formatCurrency(totalBudget));
    $('#totalUnobligated').text(formatCurrency(totalUnobligated));
    $('#overallPercentage').text(overallPercentage.toFixed(1) + '%');
    $('#accountCount').text(count);
}

// Initialize bubble chart
function initializeBubbleChart() {
    const container = d3.select('#bubble-chart');
    container.selectAll('*').remove();
    
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
        });
    
    // Add inner circles (variation color) for bureau and account views
    if (aggregationLevel !== 'agency') {
        bubbleGroups.append('circle')
            .attr('class', 'bubble bubble-inner')
            .attr('cx', d => d.x)
            .attr('cy', d => d.y)
            .attr('r', d => sizeScale(d.budgetAuthority || d.budgetAuthorityValue || 0) * 0.7) // 70% of outer radius
            .attr('fill', d => {
                if (aggregationLevel === 'bureau') {
                    // Use consistent bureau colors
                    return getConsistentBureauColor(d.name);
                } else {
                    // For accounts, use the same color as their bureau
                    return getConsistentBureauColor(d.Bureau || 'Unknown');
                }
            });
    }
    
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
        if (columnFilters.Percentage_Ranges && columnFilters.Percentage_Ranges.length > 0) {
            const percentage = row.percentageValue;
            let inRange = false;
            
            for (const range of columnFilters.Percentage_Ranges) {
                const [min, max] = range.split('-').map(v => parseFloat(v));
                if (percentage >= min && percentage <= max) {
                    inRange = true;
                    break;
                }
            }
            
            if (!inRange) return false;
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
        if (columnFilters.Percentage_Ranges && columnFilters.Percentage_Ranges.length > 0) {
            const percentage = row.percentageValue;
            let inRange = false;
            
            for (const range of columnFilters.Percentage_Ranges) {
                const [min, max] = range.split('-').map(v => parseFloat(v));
                if (percentage >= min && percentage <= max) {
                    inRange = true;
                    break;
                }
            }
            
            if (!inRange) return false;
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
            aggregateMap.set(key, {
                name: agency,
                period: forBubbleChart ? 'All' : period,
                expiration: forBubbleChart ? 'All' : expiration,
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
        if (columnFilters.Percentage_Ranges && columnFilters.Percentage_Ranges.length > 0) {
            const percentage = row.percentageValue;
            let inRange = false;
            
            for (const range of columnFilters.Percentage_Ranges) {
                const [min, max] = range.split('-').map(v => parseFloat(v));
                if (percentage >= min && percentage <= max) {
                    inRange = true;
                    break;
                }
            }
            
            if (!inRange) return false;
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
            aggregateMap.set(key, {
                agency: agency,
                name: bureau,
                period: forBubbleChart ? 'All' : period,
                expiration: forBubbleChart ? 'All' : expiration,
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
    
    // Update statistics after table is redrawn
    updateFilteredStats();
}

// Initialize on page load
$(document).ready(function() {
    loadData();
});