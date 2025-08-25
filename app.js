// Department of Education Obligation Summary - DataTables Implementation

let dataTable;
let obligationData = [];

// Format currency values
function formatCurrency(value) {
    return '$' + value.toFixed(1) + 'M';
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
        const response = await fetch('data/education_obligation_summary_july.csv');
        const csvText = await response.text();
        
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
        
        // Populate filters
        populateFilters();
        
        // Calculate summary statistics
        updateSummaryStats();
        
        // Initialize DataTable
        initializeDataTable();
        
    } catch (error) {
        console.error('Error loading data:', error);
        alert('Error loading data. Please ensure the CSV file is in the correct location.');
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

// Populate filter dropdowns
function populateFilters() {
    // Get unique bureaus
    const bureaus = [...new Set(obligationData.map(row => row.Bureau))].sort();
    const bureauSelect = $('#bureauFilter');
    bureaus.forEach(bureau => {
        if (bureau && bureau !== '') {
            bureauSelect.append(`<option value="${bureau}">${bureau}</option>`);
        }
    });
    
    // Get unique expiration years
    const years = [...new Set(obligationData.map(row => row.Expiration_Year))].sort();
    const yearSelect = $('#expirationFilter');
    years.forEach(year => {
        if (year && year !== '') {
            yearSelect.append(`<option value="${year}">${year}</option>`);
        }
    });
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
                className: 'text-end'
            },
            { 
                data: 'Budget Authority (Line 2500)',
                className: 'text-end'
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
    
    // Set up custom filters
    setupFilters();
}

// Setup custom filter functionality
function setupFilters() {
    // Bureau filter
    $('#bureauFilter').on('change', function() {
        const value = $(this).val();
        if (value === '') {
            dataTable.column(0).search('').draw();
        } else {
            dataTable.column(0).search('^' + $.fn.dataTable.util.escapeRegex(value) + '$', true, false).draw();
        }
        updateFilteredStats();
    });
    
    // Expiration year filter
    $('#expirationFilter').on('change', function() {
        const value = $(this).val();
        if (value === '') {
            dataTable.column(4).search('').draw();
        } else {
            dataTable.column(4).search('^' + $.fn.dataTable.util.escapeRegex(value) + '$', true, false).draw();
        }
        updateFilteredStats();
    });
    
    // Percentage range filter
    $('#percentageFilter').on('change', function() {
        const value = $(this).val();
        
        // Remove any existing search function
        $.fn.dataTable.ext.search.pop();
        
        if (value !== '') {
            const ranges = value.split('-').map(v => parseFloat(v));
            
            $.fn.dataTable.ext.search.push(function(settings, data, dataIndex) {
                const percentage = parseFloat(data[7].replace(/<[^>]*>/g, '').replace('%', ''));
                return percentage >= ranges[0] && percentage <= ranges[1];
            });
        }
        
        dataTable.draw();
        updateFilteredStats();
    });
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

// Initialize on page load
$(document).ready(function() {
    loadData();
});