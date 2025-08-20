// Global variables
let appropriationsData = [];
let dataTable = null;
// dataConfig is already declared globally in config_loader.js

// Initialize configuration
async function initializeConfig() {
    try {
        // dataConfig is already instantiated in config_loader.js
        if (!dataConfig.loaded) {
            await dataConfig.load();
        }
        // Also load component mappings for common utils
        await loadComponentMappings();
        console.log('Configuration loaded successfully');
    } catch (error) {
        console.error('Failed to load configuration:', error);
        // Configuration loading failed, but we can continue with defaults
    }
}

// Format date
function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// Load data
async function loadData() {
    try {
        // First load config
        await initializeConfig();
        
        const response = await fetch('processed_data/appropriations/dhs_tas_aggregated_detail.csv');
        const csvText = await response.text();
        
        // Parse CSV
        const lines = csvText.split('\n');
        const headers = lines[0].split(',').map(h => h.trim());
        
        appropriationsData = [];
        let errorCount = 0;
        for (let i = 1; i < lines.length; i++) {
            if (lines[i].trim() === '') continue;
            
            try {
                const values = parseCSVLine(lines[i]);
                const row = {};
                headers.forEach((header, index) => {
                    row[header] = values[index] || '';
                });
                
                // Map bureau to component for consistency
                row.component = row.bureau || row.component;
                
                // Convert amount to number
                row.amount = parseFloat(row.amount) || 0;
                
                // Add computed fields
                row.has_footnote = row.footnote_number ? 'Yes' : 'No';
                
                // Skip rows with missing critical data
                if (!row.component && !row.bureau) {
                    console.warn(`Row ${i} missing component/bureau:`, row);
                    errorCount++;
                    continue;
                }
                
                appropriationsData.push(row);
            } catch (error) {
                console.error(`Error parsing row ${i}:`, error);
                errorCount++;
            }
        }
        
        if (errorCount > 0) {
            console.warn(`Skipped ${errorCount} rows due to parsing errors`);
        }
        
        console.log(`Loaded ${appropriationsData.length} rows`);
        
        // Debug: Check sample row for available fields
        if (appropriationsData.length > 0) {
            const availableFields = Object.keys(appropriationsData[0]);
            console.log('Available fields in CSV:', availableFields);
            console.log('Sample row data:', appropriationsData[0]);
            
            // Store available fields globally for column initialization
            window.availableDataFields = availableFields;
        }
        
        // Initialize filters first
        populateFilters();
        
        // Show loading indicator
        document.querySelector('.loading').textContent = 'Initializing table...';
        
        // Defer table initialization for better performance
        setTimeout(() => {
            initializeDataTable();
            
            // Apply default FY 2025 filter
            applyFilters();
            updateStats();
        }, 100);
        
    } catch (error) {
        console.error('Error loading data:', error);
        document.querySelector('.loading').textContent = 'Error loading data. Please try again later.';
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
    
    result.push(current.trim());
    return result;
}

// Populate filter dropdowns
function populateFilters() {
    // Get unique values for filters, filtering out null/undefined
    const components = [...new Set(appropriationsData.map(d => d.component).filter(c => c))].sort();
    const accounts = [...new Set(appropriationsData.map(d => d.account).filter(a => a))].sort();
    
    // Populate component filter
    const componentSelect = document.getElementById('componentFilter');
    
    // Debug: Log unusual components
    const unusualComponents = components.filter(c => {
        if (!c || typeof c !== 'string') return false;
        return c.length > 50 || c.includes('000') || c.includes('--');
    });
    if (unusualComponents.length > 0) {
        console.log('Unusual components found:', unusualComponents);
    }
    
    components.forEach(component => {
        if (!component) return;
        const option = document.createElement('option');
        option.value = component;
        // Use full name in filters (not abbreviations)
        option.textContent = component;
        componentSelect.appendChild(option);
    });
    
    // Populate account filter
    const accountSelect = document.getElementById('accountFilter');
    accounts.forEach(account => {
        if (!account) return;
        const option = document.createElement('option');
        option.value = account;
        option.textContent = account;
        accountSelect.appendChild(option);
    });
    
    
    // Update account filter when component changes
    componentSelect.addEventListener('change', () => {
        const selectedComponent = componentSelect.value;
        accountSelect.innerHTML = '<option value="">All Accounts</option>';
        
        if (selectedComponent) {
            const filteredAccounts = [...new Set(
                appropriationsData
                    .filter(d => d.component === selectedComponent)
                    .map(d => d.account)
            )].sort();
            
            filteredAccounts.forEach(account => {
                const option = document.createElement('option');
                option.value = account;
                option.textContent = account;
                accountSelect.appendChild(option);
            });
        } else {
            accounts.forEach(account => {
                const option = document.createElement('option');
                option.value = account;
                option.textContent = account;
                accountSelect.appendChild(option);
            });
        }
        
        applyFilters();
    });
}


// Build table headers dynamically
function buildTableHeaders() {
    const headerRow = document.getElementById('tableHeaders');
    if (!headerRow) return;
    
    const headerMap = {
        'fiscal_year': 'FY',
        'component': 'Component',
        'account': 'Account',
        'tas': 'TAS',
        'availability_period': 'Availability',
        'line_number': 'Line #',
        'line_split': 'Split',
        'line_description': 'Description',
        'amount': 'Amount',
        'footnote_number': 'Footnote',
        'footnote_text': 'Footnote Text',
        'approval_date': 'Approval Date',
        'approver_title': 'Approver',
        'file_name': 'File'
    };
    
    const expectedColumns = [
        'fiscal_year', 'component', 'account', 'tas', 'availability_period',
        'line_number', 'line_split', 'line_description', 'amount',
        'footnote_number', 'footnote_text', 'approval_date', 'approver_title', 'file_name'
    ];
    
    const availableFields = window.availableDataFields || [];
    
    // Clear existing headers
    headerRow.innerHTML = '';
    
    // Add headers for columns that exist in data
    expectedColumns.forEach(col => {
        if (col === 'component' || availableFields.includes(col)) {
            const th = document.createElement('th');
            th.textContent = headerMap[col] || col;
            headerRow.appendChild(th);
        }
    });
}

// Initialize DataTable
function initializeDataTable() {
    // First build the headers
    buildTableHeaders();
    // Define column configurations
    const columnConfig = {
        fiscal_year: { className: 'text-center' },
        component: {
            render: function(data) {
                const displayName = getComponentName(data, 'table');
                return '<div class="truncate" title="' + data + '">' + displayName + '</div>';
            }
        },
        account: {
            render: function(data) {
                return '<div class="truncate" title="' + data + '">' + data + '</div>';
            }
        },
        tas: { className: 'text-center' },
        availability_period: {
            className: 'text-center',
            render: function(data) {
                if (data === 'X') {
                    return getStandardizedValue('availability_type', 'no-year') || 'No-Year';
                }
                return data;
            }
        },
        line_number: { className: 'line-number text-center' },
        line_split: { className: 'text-center' },
        line_description: {
            render: function(data) {
                return '<div class="truncate" title="' + data + '">' + data + '</div>';
            }
        },
        amount: {
            className: 'amount',
            render: function(data) {
                return formatCurrency(data, false);
            }
        },
        footnote_number: { className: 'text-center' },
        footnote_text: {
            visible: false,
            render: function(data) {
                return data || '';
            }
        },
        approval_date: {
            render: function(data) {
                return formatDate(data);
            }
        },
        approver_title: {
            render: function(data) {
                return '<div class="truncate" title="' + data + '">' + data + '</div>';
            }
        },
        file_name: {
            render: function(data, type, row) {
                if (row.excel_url) {
                    return '<a href="' + row.excel_url + '" target="_blank" title="' + data + '">📄</a>';
                }
                return '<span title="' + data + '">📄</span>';
            }
        }
    };
    
    // Build columns array based on what columns we expect
    const expectedColumns = [
        'fiscal_year', 'component', 'account', 'tas', 'availability_period',
        'line_number', 'line_split', 'line_description', 'amount',
        'footnote_number', 'footnote_text', 'approval_date', 'approver_title', 'file_name'
    ];
    
    // Only include columns that actually exist in the data
    const availableFields = window.availableDataFields || [];
    const columns = expectedColumns
        .filter(col => {
            // Always include component even if data has bureau
            if (col === 'component') return true;
            // Check if column exists in data
            return availableFields.includes(col);
        })
        .map(col => {
            const config = columnConfig[col] || {};
            return { data: col, ...config };
        });
    
    console.log('Configured columns:', columns.map(c => c.data));
    
    dataTable = $('#appropriationsTable').DataTable({
        data: appropriationsData,
        columns: columns,
        pageLength: 25,
        lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "All"]],
        dom: 'Bfrtip',
        buttons: [
            {
                extend: 'csv',
                text: 'Download CSV',
                className: 'dt-button',
                filename: 'dhs_appropriations_detail',
                exportOptions: {
                    columns: ':visible'
                }
            }
        ],
        order: [[0, 'desc'], [1, 'asc'], [2, 'asc'], [5, 'asc']],
        responsive: true
    });
}

// Apply filters
function applyFilters() {
    // Get filter values
    const fy = document.getElementById('fyFilter').value;
    const component = document.getElementById('componentFilter').value;
    const account = document.getElementById('accountFilter').value;
    const lineRange = document.getElementById('lineFilter').value;
    
    // Build search function
    $.fn.dataTable.ext.search.pop(); // Remove previous filter
    
    $.fn.dataTable.ext.search.push(function(settings, data, dataIndex) {
        const row = appropriationsData[dataIndex];
        
        // FY filter
        if (fy && row.fiscal_year !== fy) return false;
        
        // Component filter
        if (component && row.component !== component) return false;
        
        // Account filter
        if (account && row.account !== account) return false;
        
        // Line number range filter
        if (lineRange) {
            const lineNum = parseInt(row.line_number);
            const [min, max] = lineRange.split('-').map(n => parseInt(n));
            if (lineNum < min || lineNum > max) return false;
        }
        
        return true;
    });
    
    dataTable.draw();
    updateStats();
}

// Update statistics
function updateStats() {
    const filteredData = dataTable.rows({ search: 'applied' }).data().toArray();
    
    const totalAmount = filteredData.reduce((sum, row) => sum + row.amount, 0);
    const uniqueFiles = [...new Set(filteredData.map(row => row.file_id))].length;
    const uniqueTAS = [...new Set(filteredData.map(row => row.tas))].length;
    
    document.getElementById('totalAmount').textContent = formatCurrency(totalAmount);
    document.getElementById('lineCount').textContent = formatNumber(filteredData.length);
    document.getElementById('fileCount').textContent = formatNumber(uniqueFiles);
    document.getElementById('tasCount').textContent = formatNumber(uniqueTAS);
}

// Initialize event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Load data
    loadData();
    
    // Filter change handlers
    document.getElementById('fyFilter').addEventListener('change', applyFilters);
    document.getElementById('componentFilter').addEventListener('change', applyFilters);
    document.getElementById('accountFilter').addEventListener('change', applyFilters);
    document.getElementById('lineFilter').addEventListener('change', applyFilters);
    
});