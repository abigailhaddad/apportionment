// Department of Education Obligation Summary - DataTables Implementation

let dataTable;
let obligationData = [];
let columnFilters = {};
let bureauData = [];
let bureauColorScale;
let showBureauAggregates = false;

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
        const response = await fetch('data/education_obligation_summary_enhanced.csv');
        
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
            
            // Parse time series data
            try {
                row.baTimeSeries = JSON.parse(row['BA_TimeSeries'] || '[]');
                row.unobTimeSeries = JSON.parse(row['Unob_TimeSeries'] || '[]');
            } catch (e) {
                row.baTimeSeries = [];
                row.unobTimeSeries = [];
            }
            
            obligationData.push(row);
        }
        
        // Calculate bureau-level aggregations
        aggregateBureauData();
        
        // Create bureau color scale
        const bureauNames = [...new Set(obligationData.map(d => d.Bureau))].filter(b => b).sort();
        bureauColorScale = d3.scaleOrdinal()
            .domain(bureauNames)
            .range(d3.schemeTableau10.concat(d3.schemePastel1));
        
        // Calculate summary statistics
        updateSummaryStats();
        
        // Populate chart filters
        populateChartFilters();
        
        // Set default filter to 2025 expiration BEFORE initializing
        columnFilters.Expiration_Year = ['2025'];
        
        // Initialize DataTable
        initializeDataTable();
        
        // Initialize bubble chart
        initializeBubbleChart();
        
        // Now apply the filter
        applyAllFilters();
        
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
            result.push(current.trim());
            current = '';
        } else {
            current += char;
        }
    }
    
    if (current) {
        result.push(current.trim());
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

// Aggregate data by bureau
function aggregateBureauData() {
    const bureauMap = new Map();
    
    obligationData.forEach(row => {
        const bureau = row.Bureau || 'Other';
        if (!bureauMap.has(bureau)) {
            bureauMap.set(bureau, {
                name: bureau,
                budgetAuthority: 0,
                unobligated: 0,
                accountCount: 0,
                accounts: []
            });
        }
        
        const bureauInfo = bureauMap.get(bureau);
        bureauInfo.budgetAuthority += row.budgetAuthorityValue;
        bureauInfo.unobligated += row.unobligatedValue;
        bureauInfo.accountCount += 1;
        bureauInfo.accounts.push(row);
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

// Populate chart filter dropdowns
function populateChartFilters() {
    // Get unique values
    const bureaus = [...new Set(obligationData.map(row => row.Bureau))].filter(b => b).sort();
    const periods = [...new Set(obligationData.map(row => row.Period_of_Performance))].filter(p => p).sort();
    const years = [...new Set(obligationData.map(row => row.Expiration_Year))].filter(y => y).sort();
    
    // Populate bureau filter
    const bureauSelect = $('#chartBureauFilter');
    bureaus.forEach(bureau => {
        bureauSelect.append(`<option value="${bureau}">${bureau}</option>`);
    });
    
    // Populate period filter
    const periodSelect = $('#chartPeriodFilter');
    periods.forEach(period => {
        periodSelect.append(`<option value="${period}">${period}</option>`);
    });
    
    // Populate expiration year filter
    const yearSelect = $('#chartExpirationFilter');
    years.forEach(year => {
        yearSelect.append(`<option value="${year}">${year}</option>`);
    });
    
    // Set up event handlers
    $('#chartBureauFilter, #chartPeriodFilter, #chartExpirationFilter').on('change', function() {
        // Update column filters based on dropdown selections
        const selectedBureau = $('#chartBureauFilter').val();
        const selectedPeriod = $('#chartPeriodFilter').val();
        const selectedYear = $('#chartExpirationFilter').val();
        
        // Update filters
        columnFilters.Bureau = selectedBureau ? [selectedBureau] : null;
        columnFilters.Period_of_Performance = selectedPeriod ? [selectedPeriod] : null;
        columnFilters.Expiration_Year = selectedYear ? [selectedYear] : null;
        
        // Apply all filters
        applyAllFilters();
    });
    
    // Set up aggregate toggle button
    $('#aggregateToggle').on('click', function() {
        showBureauAggregates = !showBureauAggregates;
        $(this).text(showBureauAggregates ? 'Show Individual Accounts' : 'Show Bureau Totals');
        initializeBubbleChart();
    });
}

// Initialize DataTable
function initializeDataTable() {
    dataTable = $('#obligationTable').DataTable({
        data: obligationData,
        columns: [
            { 
                data: 'Bureau',
                render: function(data, type, row) {
                    if (type === 'display' && data && bureauColorScale) {
                        const color = bureauColorScale(data);
                        return `<span style="display: inline-block; width: 12px; height: 12px; 
                                background-color: ${color}; border-radius: 50%; margin-right: 8px;"></span>${data}`;
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
                data: null,
                orderable: false,
                render: function(data, type, row) {
                    if (type === 'display') {
                        // Create container for sparklines
                        const sparklineId = `spark-${Math.random().toString(36).substr(2, 9)}`;
                        return `
                            <div style="min-width: 120px;">
                                <div id="${sparklineId}-ba" class="sparkline-ba"></div>
                                <div id="${sparklineId}-unob" class="sparkline-unob" style="margin-top: 2px;"></div>
                            </div>
                        `;
                    }
                    return '';
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
        order: [[6, 'desc']], // Sort by Budget Authority descending
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
        drawCallback: function() {
            renderSparklines();
        }
    });
    
    // Set up column click filters
    setupColumnFilters();
}

// Setup column click filters
function setupColumnFilters() {
    // Define which columns should have filters
    const filterColumns = [
        { index: 0, name: 'Bureau' },
        { index: 3, name: 'Period_of_Performance' },
        { index: 4, name: 'Expiration_Year' },
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
        
        // Check Bureau filter
        if (columnFilters.Bureau && columnFilters.Bureau.length > 0) {
            const bureauValue = data[0];
            if (!columnFilters.Bureau.includes(bureauValue)) {
                show = false;
            }
        }
        
        // Check Period filter
        if (show && columnFilters.Period_of_Performance && columnFilters.Period_of_Performance.length > 0) {
            const periodValue = data[3];
            if (!columnFilters.Period_of_Performance.includes(periodValue)) {
                show = false;
            }
        }
        
        // Check Expiration Year filter
        if (show && columnFilters.Expiration_Year && columnFilters.Expiration_Year.length > 0) {
            const yearValue = data[4];
            if (!columnFilters.Expiration_Year.includes(yearValue)) {
                show = false;
            }
        }
        
        // Check percentage range filter (now column 8 due to trends column)
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
    
    // Update dropdown selections to match filters
    $('#chartBureauFilter').val(columnFilters.Bureau && columnFilters.Bureau.length === 1 ? columnFilters.Bureau[0] : '');
    $('#chartPeriodFilter').val(columnFilters.Period_of_Performance && columnFilters.Period_of_Performance.length === 1 ? columnFilters.Period_of_Performance[0] : '');
    $('#chartExpirationFilter').val(columnFilters.Expiration_Year && columnFilters.Expiration_Year.length === 1 ? columnFilters.Expiration_Year[0] : '');
    
    // Redraw table
    dataTable.draw();
    updateFilteredStats();
    
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
    
    // Show bureau aggregates or individual accounts based on toggle
    let dataToShow, bubbleLabel;
    
    if (showBureauAggregates) {
        // Show bureau-level aggregated data
        const filteredBureauData = getFilteredBureauData();
        dataToShow = filteredBureauData.filter(d => d.budgetAuthority > 0);
        bubbleLabel = d => d.name;
    } else {
        // Show individual accounts
        dataToShow = getFilteredAccountData().filter(d => d.budgetAuthorityValue > 0);
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
    
    // Add bubbles
    const bubbles = g.selectAll('.bubble')
        .data(dataToShow)
        .enter().append('circle')
        .attr('class', 'bubble')
        .attr('cx', d => d.x)
        .attr('cy', d => d.y)
        .attr('r', d => sizeScale(d.budgetAuthority || d.budgetAuthorityValue || 0))
        .attr('fill', d => {
            if (showBureauAggregates) {
                return bureauColorScale(d.name);
            } else {
                return bureauColorScale(d.Bureau || 'Unknown');
            }
        })
        .on('mouseover', function(event, d) {
            tooltip.transition()
                .duration(200)
                .style('opacity', .9);
            
            // Different tooltips for bureau vs account level
            if (showBureauAggregates) {
                // Bureau-level data
                tooltip.html(`
                    <strong>${d.name}</strong><br/>
                    Budget Authority: ${formatCurrency(d.budgetAuthority)}<br/>
                    Obligated: ${formatCurrency(d.budgetAuthority - d.unobligated)}<br/>
                    Unobligated: ${formatCurrency(d.unobligated)}<br/>
                    % Unobligated: ${d.percentageUnobligated.toFixed(1)}%<br/>
                    Accounts: ${d.accountCount}
                `);
            } else {
                // Account-level tooltip
                const budget = d.budgetAuthorityValue || 0;
                const unobligated = d.unobligatedValue || 0;
                tooltip.html(`
                    <strong>${bubbleLabel(d)}</strong><br/>
                    Bureau: ${d.Bureau || 'Unknown'}<br/>
                    Budget Authority: ${formatCurrency(budget)}<br/>
                    Obligated: ${formatCurrency(budget - unobligated)}<br/>
                    Unobligated: ${formatCurrency(unobligated)}<br/>
                    % Unobligated: ${(d.percentageValue || 0).toFixed(1)}%<br/>
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
function getFilteredAccountData() {
    // Filter the raw account data based on current filters
    return obligationData.filter(row => {
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
}

// Get filtered bureau data based on current filters
function getFilteredBureauData() {
    // If no filters, return all bureau data
    if (!columnFilters.Period_of_Performance && 
        !columnFilters.Expiration_Year && 
        !columnFilters.Percentage_Ranges) {
        return bureauData;
    }
    
    // Filter the raw data first
    const filteredAccounts = obligationData.filter(row => {
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
    
    // Re-aggregate by bureau
    const bureauMap = new Map();
    
    filteredAccounts.forEach(row => {
        const bureau = row.Bureau || 'Other';
        if (!bureauMap.has(bureau)) {
            bureauMap.set(bureau, {
                name: bureau,
                budgetAuthority: 0,
                unobligated: 0,
                accountCount: 0
            });
        }
        
        const bureauInfo = bureauMap.get(bureau);
        bureauInfo.budgetAuthority += row.budgetAuthorityValue;
        bureauInfo.unobligated += row.unobligatedValue;
        bureauInfo.accountCount += 1;
    });
    
    // Convert to array and calculate percentages
    return Array.from(bureauMap.values()).map(bureau => ({
        ...bureau,
        percentageUnobligated: bureau.budgetAuthority > 0 ? 
            (bureau.unobligated / bureau.budgetAuthority * 100) : 0
    }));
}

// Render sparklines in visible rows
function renderSparklines() {
    // Get visible rows
    const visibleRows = dataTable.rows({ page: 'current', search: 'applied' }).data();
    
    visibleRows.each(function(row, idx) {
        const node = dataTable.row(idx, { page: 'current', search: 'applied' }).node();
        if (node) {
            const $row = $(node);
            
            // Find sparkline containers
            const $baSparkline = $row.find('.sparkline-ba');
            const $unobSparkline = $row.find('.sparkline-unob');
            
            if ($baSparkline.length && !$baSparkline.data('sparkline-rendered')) {
                // Render BA sparkline (blue)
                if (row.baTimeSeries && row.baTimeSeries.length > 0) {
                    $baSparkline.sparkline(row.baTimeSeries, {
                        type: 'line',
                        width: '100px',
                        height: '20px',
                        lineColor: '#2196F3',
                        fillColor: 'transparent',
                        spotColor: false,
                        minSpotColor: false,
                        maxSpotColor: false,
                        lineWidth: 1.5,
                        tooltipFormat: 'BA: ${{y:,.1f}}M'
                    });
                    $baSparkline.data('sparkline-rendered', true);
                }
            }
            
            if ($unobSparkline.length && !$unobSparkline.data('sparkline-rendered')) {
                // Render unobligated sparkline (orange)
                if (row.unobTimeSeries && row.unobTimeSeries.length > 0) {
                    $unobSparkline.sparkline(row.unobTimeSeries, {
                        type: 'line',
                        width: '100px', 
                        height: '20px',
                        lineColor: '#FF9800',
                        fillColor: 'transparent',
                        spotColor: false,
                        minSpotColor: false,
                        maxSpotColor: false,
                        lineWidth: 1.5,
                        tooltipFormat: 'Unob: ${{y:,.1f}}M'
                    });
                    $unobSparkline.data('sparkline-rendered', true);
                }
            }
        }
    });
}

// Initialize on page load
$(document).ready(function() {
    loadData();
});