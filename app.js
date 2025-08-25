// Department of Education Obligation Summary - DataTables Implementation

let dataTable;
let obligationData = [];
let columnFilters = {};
let bureauData = [];

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
        const response = await fetch('data/education_obligation_summary_july.csv');
        
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
        
        // Calculate bureau-level aggregations
        aggregateBureauData();
        
        // Calculate summary statistics
        updateSummaryStats();
        
        // Initialize visualizations
        initializeTreemap();
        
        // Initialize DataTable
        initializeDataTable();
        
    } catch (error) {
        console.error('Error loading data:', error);
        console.error('Failed to load: data/education_obligation_summary_july.csv');
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

// Initialize DataTable
function initializeDataTable() {
    dataTable = $('#obligationTable').DataTable({
        data: obligationData,
        columns: [
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
        }
    });
    
    // Set up column click filters
    setupColumnFilters();
    
    // Set up percentage dropdown filter
    setupPercentageFilter();
}

// Setup column click filters
function setupColumnFilters() {
    // Define which columns should have filters
    const filterColumns = [
        { index: 0, name: 'Bureau' },
        { index: 3, name: 'Period_of_Performance' },
        { index: 4, name: 'Expiration_Year' },
        { index: 7, name: 'Percentage_Unobligated' }
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
        
        // Check percentage range filter
        if (show && columnFilters.Percentage_Ranges && columnFilters.Percentage_Ranges.length > 0) {
            const percentage = parseFloat(data[7].replace(/<[^>]*>/g, '').replace('%', ''));
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
    
    // Redraw table
    dataTable.draw();
    updateFilteredStats();
    
    // Update treemap
    initializeTreemap();
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

// Initialize treemap
function initializeTreemap() {
    const container = d3.select('#treemap');
    container.selectAll('*').remove();
    
    // Get dimensions
    const width = container.node().getBoundingClientRect().width;
    const height = 400;
    
    // Create color scale based on percentage unobligated
    const colorScale = d3.scaleSequential()
        .domain([0, 100])
        .interpolator(d3.interpolateRdYlGn);
    
    // Filter bureau data based on current filters
    const filteredBureauData = getFilteredBureauData();
    
    // Create hierarchy
    const root = d3.hierarchy({children: filteredBureauData})
        .sum(d => d.budgetAuthority)
        .sort((a, b) => b.value - a.value);
    
    // Create treemap layout
    d3.treemap()
        .size([width, height])
        .padding(2)
        (root);
    
    // Create SVG
    const svg = container
        .append('svg')
        .attr('width', width)
        .attr('height', height);
    
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
    
    // Create cells
    const cell = svg.selectAll('g')
        .data(root.leaves())
        .enter().append('g')
        .attr('transform', d => `translate(${d.x0},${d.y0})`);
    
    // Add rectangles
    cell.append('rect')
        .attr('class', 'treemap-rect')
        .attr('width', d => d.x1 - d.x0)
        .attr('height', d => d.y1 - d.y0)
        .attr('fill', d => colorScale(100 - d.data.percentageUnobligated))
        .on('mouseover', function(event, d) {
            tooltip.transition()
                .duration(200)
                .style('opacity', .9);
            tooltip.html(`
                <strong>${d.data.name}</strong><br/>
                Budget Authority: ${formatCurrency(d.data.budgetAuthority)}<br/>
                Unobligated: ${formatCurrency(d.data.unobligated)}<br/>
                % Unobligated: ${d.data.percentageUnobligated.toFixed(1)}%<br/>
                Accounts: ${d.data.accountCount}
            `)
                .style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY - 28) + 'px');
        })
        .on('mouseout', function() {
            tooltip.transition()
                .duration(500)
                .style('opacity', 0);
        })
        .on('click', function(event, d) {
            const rect = d3.select(this);
            const bureauName = d.data.name;
            
            // Toggle selection
            if (rect.classed('selected')) {
                rect.classed('selected', false);
                // Clear bureau filter
                columnFilters.Bureau = null;
            } else {
                svg.selectAll('.treemap-rect').classed('selected', false);
                rect.classed('selected', true);
                // Set bureau filter
                columnFilters.Bureau = [bureauName];
            }
            
            // Apply filters
            applyAllFilters();
        });
    
    // Add text labels
    cell.append('text')
        .attr('class', 'treemap-text')
        .attr('x', d => (d.x1 - d.x0) / 2)
        .attr('y', d => (d.y1 - d.y0) / 2 - 10)
        .text(d => {
            const width = d.x1 - d.x0;
            const name = d.data.name;
            if (width > 150) return name;
            if (width > 100) return name.substring(0, 15) + '...';
            if (width > 50) return name.substring(0, 8) + '...';
            return '';
        })
        .style('font-size', d => {
            const width = d.x1 - d.x0;
            if (width > 150) return '14px';
            if (width > 100) return '12px';
            return '10px';
        });
    
    // Add value labels
    cell.append('text')
        .attr('class', 'treemap-value')
        .attr('x', d => (d.x1 - d.x0) / 2)
        .attr('y', d => (d.y1 - d.y0) / 2 + 10)
        .text(d => {
            const width = d.x1 - d.x0;
            if (width > 80) return formatCurrency(d.data.budgetAuthority);
            return '';
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

// Initialize on page load
$(document).ready(function() {
    loadData();
});