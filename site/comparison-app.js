// Multi-Year Federal Budget Comparison - JavaScript Implementation

let comparisonDataTable;
let multiYearData = [];
let availableYears = [];
let columnFilters = {};
let aggregationLevel = 'agency';
let fiscalYearMetadata = {};
let selectedMonth = null; // null means show all months
let availableMonths = [];

// Define colors for different years (long list like agency colors)
const YEAR_COLORS = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', 
    '#bcbd22', '#17becf', '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5', '#c49c94', 
    '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5', '#393b79', '#5254a3', '#6b6ecf', '#9c9ede', 
    '#637939', '#8ca252', '#b5cf6b', '#cedb9c', '#e7cb94', '#843c39', '#ad494a', '#d6616b', 
    '#e7969c', '#7b4173', '#a55194', '#ce6dbd', '#de9ed6', '#3182bd', '#6baed6', '#9ecae1', 
    '#c6dbef', '#e6550d', '#fd8d3c', '#fdae6b', '#fdd0a2', '#31a354', '#74c476', '#a1d99b', 
    '#c7e9c0', '#756bb1', '#9e9ac8', '#bcbddc', '#dadaeb', '#636363', '#969696', '#bdbdbd', 
    '#d9d9d9', '#843c39', '#ad494a', '#d6616b', '#e7969c'
];

// Define patterns for accessibility (reuse from main app)
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
    { id: 'diagonal-stripes-reverse', path: 'M 8,8 l -8,-8 M 8,0 l -8,-8 M 8,16 l -8,-8', strokeWidth: 1 }
];

// Format currency values
function formatCurrency(value) {
    return '$' + value.toFixed(1).replace(/\B(?=(\d{3})+(?!\d))/g, ',') + 'M';
}

// Format percentage
function formatPercentage(value) {
    return `${value.toFixed(1)}%`;
}

// Parse CSV line handling quoted values (needed for individual month files)
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

// Load data for a single fiscal year and specific month (lazy loading)
async function loadYearData(fiscalYear, month = null) {
    try {
        let dataFile;
        if (month && month !== 'all') {
            // Load specific month file
            dataFile = `data/all_agencies_monthly_summary_${fiscalYear}_${month}.csv`;
        } else {
            // Load most recent month (use JSON for performance)
            dataFile = `data/all_agencies_summary_${fiscalYear}.json`;
        }
        
        const response = await fetch(dataFile);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status} for ${dataFile}`);
        }
        
        let yearData;
        if (dataFile.endsWith('.json')) {
            yearData = await response.json();
        } else {
            // Parse CSV for specific month
            const csvText = await response.text();
            const lines = csvText.split('\n');
            const headers = lines[0].split(',');
            
            yearData = [];
            for (let i = 1; i < lines.length; i++) {
                if (lines[i].trim() === '') continue;
                
                const values = parseCSVLine(lines[i]);
                if (values.length !== headers.length) continue;
                
                const row = {};
                headers.forEach((header, index) => {
                    row[header.trim()] = values[index];
                });
                yearData.push(row);
            }
        }
        
        // Convert to format expected by the comparison app
        const processedData = yearData.map(row => {
            // Convert numeric values (handle both JSON and CSV formats)
            if (row.Unobligated_Balance_M !== undefined) {
                row.unobligatedValue = row.Unobligated_Balance_M;
            } else {
                row.unobligatedValue = parseFloat(row['Unobligated Balance (Line 2490)'].replace(/[$,M]/g, ''));
            }
            
            if (row.Budget_Authority_M !== undefined) {
                row.budgetAuthorityValue = row.Budget_Authority_M;
            } else {
                row.budgetAuthorityValue = parseFloat(row['Budget Authority (Line 2500)'].replace(/[$,M]/g, ''));
            }
            
            if (row.Percentage_Unobligated !== undefined) {
                row.percentageValue = row.Percentage_Unobligated;
            } else {
                row.percentageValue = parseFloat(row['Percentage Unobligated'].replace('%', ''));
            }
            
            // Set fiscal year and month
            row.fiscalYear = parseInt(row.Fiscal_Year || fiscalYear);
            
            // For CSV files, extract month from the data; for JSON, it's the most recent month
            if (dataFile.endsWith('.csv') && row.Month) {
                row.month = row.Month;
            } else if (dataFile.endsWith('.json')) {
                row.month = 'Most Recent';
            }
            
            return row;
        });
        
        console.log(`Loaded ${processedData.length} records for FY${fiscalYear} (${month || 'most recent month'})`);
        return processedData;
    } catch (error) {
        console.error(`Error loading data for FY${fiscalYear}:`, error);
        throw error;
    }
}

// Load fiscal year metadata (month information)
async function loadFiscalYearMetadata() {
    try {
        const response = await fetch('data/fiscal_year_metadata.json');
        if (response.ok) {
            fiscalYearMetadata = await response.json();
            console.log('Loaded fiscal year metadata:', fiscalYearMetadata);
            
            // Extract all available months from the metadata
            const monthsSet = new Set();
            Object.values(fiscalYearMetadata).forEach(yearMeta => {
                if (yearMeta.display_month) {
                    monthsSet.add(yearMeta.display_month);
                }
            });
            availableMonths = Array.from(monthsSet).sort((a, b) => {
                // Sort months in fiscal year order: Oct, Nov, Dec, Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep
                const fiscalOrder = ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep'];
                return fiscalOrder.indexOf(a) - fiscalOrder.indexOf(b);
            });
            console.log('Available months:', availableMonths);
        } else {
            console.log('No fiscal year metadata file found, using defaults');
            // Will be populated from actual data if metadata fails
        }
    } catch (error) {
        console.log('Could not load fiscal year metadata:', error);
        // Will be populated from actual data if metadata fails
    }
}

// Detect available months by checking file existence
async function detectAvailableMonths() {
    const testMonths = ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep'];
    const monthsSet = new Set();
    
    // Check each year to see what months have files
    for (const year of availableYears) {
        for (const month of testMonths) {
            try {
                const response = await fetch(`data/all_agencies_monthly_summary_${year}_${month}.csv`, { method: 'HEAD' });
                if (response.ok) {
                    monthsSet.add(month);
                }
            } catch (e) {
                // File doesn't exist, skip
            }
        }
    }
    
    // Sort months in fiscal year order
    availableMonths = Array.from(monthsSet).sort((a, b) => {
        const fiscalOrder = ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep'];
        return fiscalOrder.indexOf(a) - fiscalOrder.indexOf(b);
    });
    
    console.log('Detected available months from files:', availableMonths);
    
    // Fallback to metadata if no months detected
    if (availableMonths.length === 0 && fiscalYearMetadata) {
        const monthsSet = new Set();
        availableYears.forEach(year => {
            const metadata = fiscalYearMetadata[year.toString()];
            const monthText = metadata ? metadata.display_month : 'Sep';
            monthsSet.add(monthText);
        });
        availableMonths = Array.from(monthsSet).sort((a, b) => {
            const fiscalOrder = ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep'];
            return fiscalOrder.indexOf(a) - fiscalOrder.indexOf(b);
        });
        console.log('Using metadata fallback for available months:', availableMonths);
    }
}

// Load data for multiple years (all available years)
async function loadAllYearsData() {
    try {
        console.log(`Loading data for all years: ${availableYears.join(', ')} (month: ${selectedMonth || 'most recent'})`);
        
        // Load metadata first
        await loadFiscalYearMetadata();
        
        const promises = availableYears.map(year => loadYearData(year, selectedMonth));
        const yearDataArrays = await Promise.all(promises);
        
        // Combine all data
        multiYearData = yearDataArrays.flat();
        
        console.log(`Loaded data for ${availableYears.length} years, total records: ${multiYearData.length}`);
        
        // For lazy loading, we need to detect available months from file existence
        // instead of relying on loaded data (which might only be "Most Recent")
        await detectAvailableMonths();
        
        // Initial setup of filter options
        updateFilterOptions();
        
        // Set default agency filter to Department of Defense (it's usually large and interesting)
        const defaultAgency = 'Department of Defense-Military';
        if ($('#mainAgencyFilter option[value="' + defaultAgency + '"]').length > 0) {
            $('#mainAgencyFilter').val(defaultAgency);
            columnFilters.Agency = [defaultAgency];
            // Update dependent filters after setting default agency
            updateFilterOptions();
        }
        
        updateSummaryStats();
        createMonthSelector();
        initializeBubbleChart();
        initializeDataTable();
        
        // Update active filters display
        updateFilters();
        
    } catch (error) {
        console.error('Error loading multi-year data:', error);
        alert('Failed to load data for one or more years.');
    }
}

// Update filter options based on loaded multi-year data and current selections (cascading filters)
function updateFilterOptions() {
    const selectedAgency = $('#mainAgencyFilter').val();
    const selectedBureau = $('#mainBureauFilter').val();
    const selectedPeriod = $('#mainPeriodFilter').val();
    
    // Start with all data and progressively filter for each dropdown
    let filteredForBureaus = multiYearData;
    let filteredForPeriods = multiYearData;
    let filteredForYears = multiYearData;
    
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
    
    // Get unique values for each dropdown based on filtered data
    const agencies = [...new Set(multiYearData.map(row => row.Agency))].filter(a => a).sort();
    const bureaus = [...new Set(filteredForBureaus.map(row => row.Bureau))].filter(b => b).sort();
    const periods = [...new Set(filteredForPeriods.map(row => row.Period_of_Performance))].filter(p => p).sort();
    const expirationYears = [...new Set(filteredForYears.map(row => row.Expiration_Year))].filter(y => y).sort();
    
    // Update Agency dropdown (always shows all agencies)
    const $agencyFilter = $('#mainAgencyFilter');
    const currentAgency = $agencyFilter.val();
    $agencyFilter.empty().append('<option value="">All Agencies</option>');
    agencies.forEach(agency => {
        $agencyFilter.append(`<option value="${agency}">${agency}</option>`);
    });
    if (agencies.includes(currentAgency)) {
        $agencyFilter.val(currentAgency);
    }
    
    // Update Bureau dropdown (cascaded from Agency)
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
    
    // Update Expiration Year dropdown (cascaded from Agency + Bureau + Period)
    const $expirationFilter = $('#mainExpirationFilter');
    const currentExpiration = $expirationFilter.val();
    $expirationFilter.empty().append('<option value="">Expiring That Year (Default)</option>');
    $expirationFilter.append('<option value="ALL_YEARS">All Years</option>');
    expirationYears.forEach(year => {
        $expirationFilter.append(`<option value="${year}">${year}</option>`);
    });
    
    // Preserve current selection if it exists in the new list, otherwise clear it
    if (currentExpiration && (currentExpiration === 'ALL_YEARS' || expirationYears.includes(currentExpiration))) {
        $expirationFilter.val(currentExpiration);
    } else if (currentExpiration && !expirationYears.includes(currentExpiration) && currentExpiration !== '' && currentExpiration !== 'ALL_YEARS') {
        // Clear selection if it's no longer available
        $expirationFilter.val('');
    }
    
    // Update filter hint
    if (selectedAgency || selectedBureau || selectedPeriod) {
        $('#yearFilterHint').text(`(${expirationYears.length} available)`);
    } else {
        $('#yearFilterHint').text('');
    }
}

// Create month selector buttons
function createMonthSelector() {
    const monthSelector = document.getElementById('monthSelector');
    if (!monthSelector) return;
    
    monthSelector.innerHTML = '';
    
    // Add "Most Recent" button
    const allButton = document.createElement('button');
    allButton.className = 'year-btn';
    allButton.setAttribute('data-month', 'all');
    allButton.innerHTML = `
        <div style="font-weight: 600;">Most Recent</div>
        <div style="font-size: 0.8rem; color: #666; margin-top: 2px;">All Years</div>
    `;
    allButton.addEventListener('click', () => switchToMonth(null));
    monthSelector.appendChild(allButton);
    
    // Add buttons for each available month
    availableMonths.forEach(month => {
        const button = document.createElement('button');
        button.className = 'year-btn';
        button.setAttribute('data-month', month);
        button.innerHTML = `
            <div style="font-weight: 600;">${month}</div>
            <div style="font-size: 0.8rem; color: #666; margin-top: 2px;">Month</div>
        `;
        button.addEventListener('click', () => switchToMonth(month));
        monthSelector.appendChild(button);
    });
    
    // Set initial state (all months selected)
    updateMonthSelectorUI();
}

// Loading state management
function showLoadingState() {
    // Add loading class to main containers
    const containers = document.querySelectorAll('.summary-stats, .table-container, .treemap-container');
    containers.forEach(container => {
        container.style.opacity = '0.5';
        container.style.pointerEvents = 'none';
    });
    
    // Show loading text in summary stats
    const summaryStats = document.querySelector('.summary-stats');
    if (summaryStats && !summaryStats.querySelector('.loading-overlay')) {
        const loadingOverlay = document.createElement('div');
        loadingOverlay.className = 'loading-overlay';
        loadingOverlay.style.cssText = `
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(255,255,255,0.9);
            padding: 10px 20px;
            border-radius: 4px;
            font-weight: 600;
            color: #003366;
        `;
        loadingOverlay.textContent = 'Loading month data...';
        summaryStats.style.position = 'relative';
        summaryStats.appendChild(loadingOverlay);
    }
}

function hideLoadingState() {
    // Remove loading state
    const containers = document.querySelectorAll('.summary-stats, .table-container, .treemap-container');
    containers.forEach(container => {
        container.style.opacity = '1';
        container.style.pointerEvents = 'auto';
    });
    
    // Remove loading overlay
    const loadingOverlay = document.querySelector('.loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.remove();
    }
}

// Switch to a specific month filter
async function switchToMonth(month) {
    if (selectedMonth === month) {
        return; // Already on this month
    }
    
    selectedMonth = month;
    console.log('Switched to month:', month || 'Most Recent');
    
    // Show loading state
    showLoadingState();
    
    try {
        // Reload data for the new month
        await loadAllYearsData();
        
        // Update data display
        updateSummaryStats();
        initializeBubbleChart();
        initializeDataTable();
        updateFilters(); // Update active filters display
        
        hideLoadingState();
    } catch (error) {
        console.error('Error switching month:', error);
        hideLoadingState();
    }
    
    // Update month selector UI
    updateMonthSelectorUI();
}

// Update month selector UI to reflect current selection
function updateMonthSelectorUI() {
    const monthButtons = document.querySelectorAll('#monthSelector .year-btn');
    monthButtons.forEach(btn => {
        const month = btn.getAttribute('data-month');
        if ((selectedMonth === null && month === 'all') || month === selectedMonth) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

// Aggregate data based on current aggregation level and filters
function getAggregatedData() {
    // First handle month filtering
    let filteredData;
    if (selectedMonth === null) {
        // "Most Recent" - show only the most recent month for each fiscal year
        const mostRecentByYear = new Map();
        
        // Define fiscal year month order (Oct = 1, Nov = 2, ..., Sep = 12)
        const fiscalMonthOrder = {
            'Oct': 1, 'Nov': 2, 'Dec': 3,
            'Jan': 4, 'Feb': 5, 'Mar': 6,
            'Apr': 7, 'May': 8, 'Jun': 9,
            'Jul': 10, 'Aug': 11, 'Sep': 12
        };
        
        // Find the most recent month for each fiscal year
        multiYearData.forEach(row => {
            const year = row.fiscalYear;
            const currentMonthOrder = fiscalMonthOrder[row.month] || 0;
            const existingMonthOrder = mostRecentByYear.has(year) ? fiscalMonthOrder[mostRecentByYear.get(year)] || 0 : 0;
            
            if (!mostRecentByYear.has(year) || currentMonthOrder > existingMonthOrder) {
                mostRecentByYear.set(year, row.month);
            }
        });
        
        // Filter to only include the most recent month for each year
        filteredData = multiYearData.filter(row => {
            return row.month === mostRecentByYear.get(row.fiscalYear);
        });
    } else {
        // Specific month selected - filter to only that month
        filteredData = multiYearData.filter(row => {
            return row.month === selectedMonth;
        });
    }
    
    // Now apply other filters to the month-filtered data
    filteredData = filteredData.filter(row => {
        // Handle expiration year filtering
        if (!columnFilters.Expiration_Year) {
            // Default behavior: only show money expiring in the same year as the fiscal year
            if (row.Expiration_Year !== row.fiscalYear.toString()) return false;
        } else if (columnFilters.Expiration_Year[0] === 'ALL_YEARS') {
            // Show all expiration years
            // No filter applied
        } else {
            // Specific expiration year(s) selected
            if (!columnFilters.Expiration_Year.includes(row.Expiration_Year)) return false;
        }
        
        if (columnFilters.Agency && !columnFilters.Agency.includes(row.Agency)) return false;
        if (columnFilters.Bureau && !columnFilters.Bureau.includes(row.Bureau)) return false;
        if (columnFilters.Period_of_Performance && !columnFilters.Period_of_Performance.includes(row.Period_of_Performance)) return false;
        if (columnFilters.Percentage_Range) {
            const [min, max] = columnFilters.Percentage_Range.split('-').map(v => parseFloat(v));
            if (!(row.percentageValue >= min && row.percentageValue <= max)) return false;
        }
        return true;
    });
    
    // Group data by account and month, then aggregate
    const accountMap = new Map();
    
    filteredData.forEach(row => {
        let baseKey;
        if (aggregationLevel === 'agency') {
            baseKey = `${row.fiscalYear}|${row.month}|${row.Agency}`;
        } else if (aggregationLevel === 'bureau') {
            baseKey = `${row.fiscalYear}|${row.month}|${row.Agency}|${row.Bureau}`;
        } else {
            baseKey = `${row.fiscalYear}|${row.month}|${row.Agency}|${row.Bureau}|${row.Account}`;
        }
        
        if (!accountMap.has(baseKey)) {
            let displayData;
            if (aggregationLevel === 'agency') {
                displayData = {
                    Agency: row.Agency,
                    Bureau: '', // Will be filled with count later
                    Account: '', 
                    Period_of_Performance: 'All'
                };
            } else if (aggregationLevel === 'bureau') {
                displayData = {
                    Agency: row.Agency,
                    Bureau: row.Bureau,
                    Account: '', // Will be filled with count later
                    Period_of_Performance: 'All'
                };
            } else {
                displayData = {
                    Agency: row.Agency,
                    Bureau: row.Bureau,
                    Account: row.Account,
                    Period_of_Performance: row.Period_of_Performance || 'All'
                };
            }
            
            accountMap.set(baseKey, {
                fiscalYear: row.fiscalYear,
                month: row.month,
                ...displayData,
                budgetAuthorityValue: 0,
                unobligatedValue: 0,
                accountCount: 0,
                uniqueAccounts: new Set(),
                uniqueBureaus: new Set()
            });
        }
        
        const aggregate = accountMap.get(baseKey);
        
        // Add values from the monthly summary (already aggregated)
        aggregate.budgetAuthorityValue += row.budgetAuthorityValue || 0;
        aggregate.unobligatedValue += row.unobligatedValue || 0;
        aggregate.accountCount += 1;
        
        // Track unique items for display
        if (row.Account) aggregate.uniqueAccounts.add(row.Account);
        if (row.Bureau) aggregate.uniqueBureaus.add(row.Bureau);
    });
    
    // Calculate percentages and format display fields
    return Array.from(accountMap.values()).map(item => {
        // Update display fields based on aggregation level
        if (aggregationLevel === 'agency') {
            item.Bureau = `${item.uniqueBureaus.size} bureaus`;
            item.Account = `${item.accountCount} accounts`;
        } else if (aggregationLevel === 'bureau') {
            item.Account = `${item.accountCount} accounts`;
        }
        
        // Clean up the sets (not needed in final data)
        delete item.uniqueAccounts;
        delete item.uniqueBureaus;
        
        return {
            ...item,
            monthText: item.month || 'Unknown',
            percentageValue: item.budgetAuthorityValue > 0 ? 
                (item.unobligatedValue / item.budgetAuthorityValue * 100) : 0
        };
    });
}

// Update summary statistics
function updateSummaryStats() {
    const aggregatedData = getAggregatedData();
    
    const totalBudget = aggregatedData.reduce((sum, row) => sum + row.budgetAuthorityValue, 0);
    const totalUnobligated = aggregatedData.reduce((sum, row) => sum + row.unobligatedValue, 0);
    const overallPercentage = totalBudget > 0 ? (totalUnobligated / totalBudget * 100) : 0;
    
    $('#totalBudget').text(formatCurrency(totalBudget));
    $('#totalUnobligated').text(formatCurrency(totalUnobligated));
    $('#overallPercentage').text(formatPercentage(overallPercentage));
    $('#yearsCount').text(availableYears.length);
}

// Get color for a fiscal year
function getYearColor(fiscalYear) {
    const yearIndex = availableYears.indexOf(fiscalYear);
    return yearIndex >= 0 ? YEAR_COLORS[yearIndex % YEAR_COLORS.length] : '#999999';
}

// Get pattern for a fiscal year
function getYearPattern(fiscalYear) {
    const yearIndex = availableYears.indexOf(fiscalYear);
    return yearIndex >= 0 && yearIndex < PATTERN_DEFINITIONS.length ? 
           PATTERN_DEFINITIONS[yearIndex].id : 'dots';
}

// Initialize bubble chart
function initializeBubbleChart() {
    const container = d3.select('#bubble-chart');
    container.selectAll('*').remove();
    
    const aggregatedData = getAggregatedData();
    const dataToShow = aggregatedData.filter(d => d.budgetAuthorityValue > 0);
    
    if (dataToShow.length === 0) {
        container.append('div')
            .style('text-align', 'center')
            .style('padding', '100px')
            .style('color', '#666')
            .text('No data to display. Please select different filters.');
        return;
    }
    
    // Get dimensions
    const margin = {top: 20, right: 40, bottom: 60, left: 40};
    const width = container.node().getBoundingClientRect().width - margin.left - margin.right;
    const height = 400 - margin.top - margin.bottom;
    
    // Create scales
    const xScale = d3.scaleLinear()
        .domain([0, 100])
        .range([0, width]);
    
    const maxBudget = d3.max(dataToShow, d => d.budgetAuthorityValue);
    const sizeScale = d3.scaleSqrt()
        .domain([0, maxBudget])
        .range([3, 25]);
    
    // Create force simulation
    const simulation = d3.forceSimulation(dataToShow)
        .force('x', d3.forceX(d => xScale(d.percentageValue)).strength(1))
        .force('y', d3.forceY(height / 2).strength(0.1))
        .force('collide', d3.forceCollide(d => sizeScale(d.budgetAuthorityValue) + 1))
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
    
    // Create year-based patterns 
    availableYears.forEach((year, index) => {
        const patternDef = PATTERN_DEFINITIONS[index % PATTERN_DEFINITIONS.length];
        const color = getYearColor(year);
        
        const pattern = defs.append('pattern')
            .attr('id', `year-pattern-${year}`)
            .attr('patternUnits', 'userSpaceOnUse')
            .attr('width', 8)
            .attr('height', 8);
        
        if (patternDef.fill) {
            pattern.append('circle')
                .attr('cx', 4)
                .attr('cy', 4)
                .attr('r', 2)
                .attr('fill', color)
                .attr('opacity', 0.6);
        } else {
            pattern.append('path')
                .attr('d', patternDef.path)
                .attr('stroke', color)
                .attr('stroke-width', patternDef.strokeWidth)
                .attr('fill', 'none')
                .attr('opacity', 0.6);
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
    
    // Add x-axis
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
    
    // Create tooltip
    d3.selectAll('.tooltip').remove();
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
    
    // Add bubble groups
    const bubbleGroups = g.selectAll('.bubble-group')
        .data(dataToShow)
        .enter().append('g')
        .attr('class', 'bubble-group');
    
    // Add solid color circles
    bubbleGroups.append('circle')
        .attr('class', 'bubble bubble-solid')
        .attr('cx', d => d.x)
        .attr('cy', d => d.y)
        .attr('r', d => sizeScale(d.budgetAuthorityValue))
        .attr('fill', d => getYearColor(d.fiscalYear))
        .attr('opacity', 0.8)
        .style('stroke', '#333')
        .style('stroke-width', 1);
    
    // Add pattern overlay
    bubbleGroups.append('circle')
        .attr('class', 'bubble-pattern')
        .attr('cx', d => d.x)
        .attr('cy', d => d.y)
        .attr('r', d => sizeScale(d.budgetAuthorityValue))
        .attr('fill', d => `url(#year-pattern-${d.fiscalYear})`)
        .style('pointer-events', 'all');
    
    // Add hover handlers
    bubbleGroups
        .on('mouseover', function(event, d) {
            tooltip.transition()
                .duration(200)
                .style('opacity', .9);
            
            let label;
            if (aggregationLevel === 'agency') {
                label = d.Agency || 'Unknown Agency';
            } else if (aggregationLevel === 'bureau') {
                label = d.Bureau || 'Unknown Bureau';
            } else {
                label = d.Account || 'Unknown Account';
            }
            
            tooltip.html(`
                <strong>${label}</strong><br/>
                <strong>Year:</strong> FY${d.fiscalYear} (${d.monthText || 'Sep'})<br/>
                ${aggregationLevel !== 'agency' ? `<strong>Agency:</strong> ${d.Agency}<br/>` : ''}
                ${aggregationLevel === 'individual' ? `<strong>Bureau:</strong> ${d.Bureau}<br/>` : ''}
                <strong>Budget Authority:</strong> ${formatCurrency(d.budgetAuthorityValue)}<br/>
                <strong>Unobligated:</strong> ${formatCurrency(d.unobligatedValue)}<br/>
                <strong>% Unobligated:</strong> ${formatPercentage(d.percentageValue)}<br/>
                ${aggregationLevel !== 'individual' ? `<strong>Account Count:</strong> ${d.accountCount}` : ''}
            `);
            
            tooltip.style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY - 28) + 'px');
        })
        .on('mouseout', function() {
            tooltip.transition()
                .duration(500)
                .style('opacity', 0);
        });
    
    // Add reference lines
    [50, 75].forEach(percent => {
        g.append('line')
            .attr('x1', xScale(percent))
            .attr('x2', xScale(percent))
            .attr('y1', 0)
            .attr('y2', height)
            .attr('stroke', percent === 50 ? '#ff9800' : '#f44336')
            .attr('stroke-dasharray', '3,3')
            .attr('opacity', 0.5);
        
        g.append('text')
            .attr('x', xScale(percent))
            .attr('y', 10)
            .attr('text-anchor', 'middle')
            .attr('font-size', '12px')
            .attr('fill', percent === 50 ? '#ff9800' : '#f44336')
            .text(percent + '%');
    });
}


// Initialize DataTable
function initializeDataTable() {
    // Destroy existing table if exists
    if ($.fn.DataTable.isDataTable('#comparisonTable')) {
        $('#comparisonTable').DataTable().destroy();
    }
    
    const aggregatedData = getAggregatedData();
    
    // Transform data for table
    const tableData = aggregatedData.map(row => ({
        ...row,
        'Unobligated Balance (Line 2490)': formatCurrency(row.unobligatedValue),
        'Budget Authority (Line 2500)': formatCurrency(row.budgetAuthorityValue),
        'Percentage Unobligated': formatPercentage(row.percentageValue)
    }));
    
    comparisonDataTable = $('#comparisonTable').DataTable({
        data: tableData,
        columns: [
            { 
                data: 'monthText',
                render: function(data) {
                    return data || 'Sep';
                }
            },
            { 
                data: 'fiscalYear',
                type: 'num',
                render: function(data) {
                    const color = getYearColor(data);
                    return `<span style="display: inline-block; width: 12px; height: 12px; 
                            background-color: ${color}; border-radius: 50%; margin-right: 8px;"></span>FY${data}`;
                }
            },
            { 
                data: 'Agency',
                render: function(data, type, row) {
                    if (type === 'display' && data) {
                        const color = getYearColor(row.fiscalYear);
                        return `<span style="display: inline-block; width: 12px; height: 12px; 
                                background-color: ${color}; border-radius: 50%; margin-right: 8px;"></span>${data}`;
                    }
                    return data || '';
                }
            },
            { data: 'Bureau' },
            { data: 'Account' },
            { data: 'Period_of_Performance' },
            { data: 'Unobligated Balance (Line 2490)', className: 'text-end' },
            { data: 'Budget Authority (Line 2500)', className: 'text-end' },
            { data: 'Percentage Unobligated', className: 'text-center' }
        ],
        pageLength: 25,
        order: [[1, 'asc']], // Sort by Year ascending
        language: {
            info: "Showing _START_ to _END_ of _TOTAL_ entries across selected years",
        }
    });
}

// Initialize available years and load all data
async function initializeAndLoadData() {
    try {
        // Try to detect available years (only check reasonable range)
        const testYears = Array.from({length: 2030 - 2015 + 1}, (_, i) => 2015 + i);
        const availableYearsSet = new Set();
        
        for (const year of testYears) {
            try {
                // Check if JSON summary file exists (for most recent month)
                const response = await fetch(`data/all_agencies_summary_${year}.json`, { method: 'HEAD' });
                if (response.ok) {
                    availableYearsSet.add(year);
                }
            } catch (e) {
                // File doesn't exist, skip
            }
        }
        
        availableYears = Array.from(availableYearsSet).sort((a, b) => a - b); // Sort ascending (oldest first for consistent colors)
        
        console.log('Available years:', availableYears);
        
        // Automatically load data for all available years
        if (availableYears.length > 0) {
            await loadAllYearsData();
        } else {
            console.error('No data files found');
            alert('No data files found. Please ensure CSV files are available in the data/ directory.');
        }
        
    } catch (error) {
        console.error('Error initializing data:', error);
    }
}

// Set up filter change handlers
function setupFilterHandlers() {
    // Separate handlers for filters that affect other dropdowns vs those that don't
    $('#mainAgencyFilter').on('change', function() {
        updateFilterOptions(); // Update dependent dropdowns first (cascading)
        updateFilters();       // Then update the data display
    });
    
    $('#mainBureauFilter').on('change', function() {
        updateFilterOptions(); // Update dependent dropdowns first (cascading)
        updateFilters();       // Then update the data display
    });
    
    $('#mainPeriodFilter').on('change', function() {
        updateFilterOptions(); // Update dependent dropdowns first (cascading)
        updateFilters();       // Then update the data display
    });
    
    // These filters don't affect other dropdowns, so just update data
    $('#mainExpirationFilter, #mainPercentageFilter').on('change', function() {
        updateFilters();       // Just update the data display
    });
    
    $('#aggregationLevel').on('change', function() {
        aggregationLevel = $(this).val();
        if (multiYearData.length > 0) {
            updateSummaryStats();
            initializeBubbleChart();
            initializeDataTable();
        }
    });
}

// Update filters
function updateFilters() {
    const agencyVal = $('#mainAgencyFilter').val();
    const bureauVal = $('#mainBureauFilter').val();
    const periodVal = $('#mainPeriodFilter').val();
    const expirationVal = $('#mainExpirationFilter').val();
    const percentVal = $('#mainPercentageFilter').val();
    
    columnFilters.Agency = agencyVal ? [agencyVal] : null;
    columnFilters.Bureau = bureauVal ? [bureauVal] : null;
    columnFilters.Period_of_Performance = periodVal ? [periodVal] : null;
    columnFilters.Expiration_Year = expirationVal ? [expirationVal] : null;
    columnFilters.Percentage_Range = percentVal || null;
    
    if (multiYearData.length > 0) {
        updateSummaryStats();
        initializeBubbleChart();
        initializeDataTable();
    }
    
    // Update active filters display
    const filterTexts = [];
    if (selectedMonth) filterTexts.push(`Month: ${selectedMonth}`);
    if (agencyVal) filterTexts.push(agencyVal);
    if (bureauVal) filterTexts.push(bureauVal);
    if (periodVal) filterTexts.push(periodVal);
    if (expirationVal === 'ALL_YEARS') filterTexts.push('All Expiration Years');
    else if (expirationVal) filterTexts.push(`Expires: ${expirationVal}`);
    else filterTexts.push('Expiring That Year');
    if (percentVal) filterTexts.push($('#mainPercentageFilter option:selected').text());
    
    $('#activeFiltersDisplay').text(filterTexts.length > 0 ? filterTexts.join(' • ') : '');
}

// Download CSV
function downloadCSV() {
    const aggregatedData = getAggregatedData();
    const csv = convertToCSV(aggregatedData);
    const timestamp = new Date().toISOString().split('T')[0];
    const filename = `multi_year_comparison_${aggregationLevel}_${timestamp}.csv`;
    
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

function convertToCSV(data) {
    const headers = ['Month', 'Fiscal Year', 'Agency', 'Bureau', 'Account', 'Period', 'Budget Authority', 'Unobligated', '% Unobligated'];
    const csvContent = [headers.join(',')];
    
    data.forEach(row => {
        const csvRow = [
            `"${row.monthText || 'Sep'}"`,
            row.fiscalYear,
            `"${row.Agency || ''}"`,
            `"${row.Bureau || ''}"`,
            `"${row.Account || ''}"`,
            `"${row.Period_of_Performance || ''}"`,
            row.budgetAuthorityValue.toFixed(1),
            row.unobligatedValue.toFixed(1),
            row.percentageValue.toFixed(1)
        ];
        csvContent.push(csvRow.join(','));
    });
    
    return csvContent.join('\n');
}

// Initialize on page load
$(document).ready(async function() {
    setupFilterHandlers();
    
    // Set up download button
    $('#downloadCSV').on('click', downloadCSV);
    
    // Initialize and load all data automatically
    await initializeAndLoadData();
});