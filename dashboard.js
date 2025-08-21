// DHS Budget Dashboard
// Unified view of appropriations, spending trends, and vendor data

class DashboardManager {
    constructor() {
        this.data = {
            appropriations: null,
            spending: null,
            vendors: null,
            metadata: null
        };
        this.currentFY = 2025;
        this.currentTrendView = 'component';
        this.currentMoneyView = 'vendors';
        
        this.init();
    }
    
    async init() {
        try {
            // Load configuration
            await this.loadConfig();
            
            // Set up event listeners
            this.setupEventListeners();
            
            // Load all data
            await this.loadAllData();
            
            // Render all sections
            this.renderDashboard();
            
        } catch (error) {
            console.error('Dashboard initialization error:', error);
            this.showError('Failed to load dashboard data');
        }
    }
    
    async loadConfig() {
        // Load component mappings for consistent naming
        await loadComponentMappings();
    }
    
    setupEventListeners() {
        // No event listeners needed currently
    }
    
    async loadAllData() {
        console.log('Loading dashboard data...');
        
        // Load optimized summary data for better performance
        const [appropriationsSummary, spendingSummary, vendorSummary, spendingLifecycle, monthlyTrends, metadata] = await Promise.all([
            this.loadJSON('processed_data/dashboard/appropriations_summary.json'),
            this.loadJSON('processed_data/dashboard/spending_summary.json'), 
            this.loadJSON('processed_data/dashboard/vendor_summary.json'),
            this.loadJSON('processed_data/dashboard/spending_lifecycle.json'),
            this.loadJSON('processed_data/dashboard/monthly_trends.json'),
            this.loadJSON('processed_data/appropriations/update_metadata.json')
        ]);
        
        this.data = {
            appropriationsSummary,
            spendingSummary,
            vendorSummary,
            spendingLifecycle,
            monthlyTrends,
            metadata
        };
        
        // Debug monthly trends
        if (monthlyTrends && monthlyTrends.monthly) {
            const nonZeroMonths = monthlyTrends.monthly.filter(m => 
                m.appropriations_total > 0 || m.outlays_total > 0
            );
            console.log(`Monthly trends: ${monthlyTrends.monthly.length} months, ${nonZeroMonths.length} with data`);
            console.log('First non-zero month:', nonZeroMonths[0]);
        }
        
        console.log('Data loaded:', {
            appropriationsSummary: this.data.appropriationsSummary ? 'loaded' : 'missing',
            spendingSummary: this.data.spendingSummary ? 'loaded' : 'missing',
            vendorSummary: this.data.vendorSummary ? 'loaded' : 'missing',
            spendingLifecycle: this.data.spendingLifecycle ? 'loaded' : 'missing',
            monthlyTrends: this.data.monthlyTrends ? 'loaded' : 'missing'
        });
    }
    
    async loadJSON(path) {
        try {
            // Add cache-busting parameter to force reload
            const cacheBuster = new Date().getTime();
            const url = `${path}?v=${cacheBuster}`;
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            console.log(`Loaded ${path}, size: ${JSON.stringify(data).length} bytes`);
            return data;
        } catch (error) {
            console.error(`Error loading ${path}:`, error);
            return null;
        }
    }
    
    renderDashboard() {
        this.renderRecentApportionments();
        this.renderSpendingLifecycle();
        this.renderYearOverYear();
        this.renderInteractiveVendors();
    }
    
    // Recent Apportionments Section
    renderRecentApportionments() {
        const container = document.getElementById('recentApportionments');
        
        if (!this.data.appropriationsSummary || !this.data.appropriationsSummary.recent_apportionments) {
            container.innerHTML = '<h2>Recent Apportionments</h2><div class="error">Failed to load recent apportionments</div>';
            return;
        }
        
        const recentActions = this.data.appropriationsSummary.recent_apportionments;
        
        let html = `
            <h2>Recent Apportionment Actions</h2>
            <div class="alert">
                Latest ${recentActions.length} apportionment actions from OMB
            </div>
            
            <div class="apportionment-list">
        `;
        
        recentActions.forEach((action, index) => {
            const date = new Date(action.approval_date);
            const formattedDate = date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
            });
            
            html += `
                <div class="apportionment-card" id="apportionment-${index}" onclick="dashboard.toggleApportionment(${index})">
                    <div class="apportionment-header">
                        <span class="apportionment-date">${formattedDate}</span>
                        <span class="apportionment-amount">${formatCurrency(action.amount)}</span>
                        <span class="expand-arrow">▼</span>
                    </div>
                    <div class="apportionment-details">
                        <div class="component-name">${action.component}</div>
                        <div class="account-name">${action.account}</div>
                        <div class="funds-source">Source: ${action.funds_source}</div>
                        <div class="approver">Approved by: ${action.approver}</div>
                    </div>
                    <div class="apportionment-full-details">
                        ${this.renderApportionmentFullDetails(action)}
                    </div>
                </div>
            `;
        });
        
        html += `
            </div>
            <div class="data-note">
                <a href="appropriations_detail.html">View all apportionment details →</a>
            </div>
        `;
        
        container.innerHTML = html;
    }
    
    renderApportionmentFullDetails(action) {
        // Get additional fields from the detail data if available
        const details = [
            { label: 'File ID', value: action.file_id },
            { label: 'TAS', value: action.tas },
            { label: 'Availability Period', value: action.availability_period },
            { label: 'Line Number', value: action.line_number },
            { label: 'Line Description', value: action.line_description },
            { label: 'Iteration', value: action.iteration },
            { label: 'Created At', value: action.created_at ? new Date(action.created_at).toLocaleDateString() : null },
            { label: 'Modified At', value: action.modified_at ? new Date(action.modified_at).toLocaleDateString() : null },
            { label: 'Excel URL', value: action.excel_url ? `<a href="${action.excel_url}" target="_blank">Download Excel</a>` : null },
            { label: 'Source URL', value: action.source_url ? `<a href="${action.source_url}" target="_blank">View Source</a>` : null }
        ];
        
        let html = '';
        details.forEach(detail => {
            if (detail.value && detail.value !== 'null' && detail.value !== 'undefined') {
                html += `
                    <div class="detail-row">
                        <span class="detail-label">${detail.label}:</span>
                        <span class="detail-value">${detail.value}</span>
                    </div>
                `;
            }
        });
        
        return html || '<div class="detail-row">No additional details available</div>';
    }
    
    toggleApportionment(index) {
        const card = document.getElementById(`apportionment-${index}`);
        if (card) {
            card.classList.toggle('expanded');
        }
    }
    
    toggleDropdown(dropdownId) {
        const dropdown = document.getElementById(dropdownId);
        const content = dropdown.querySelector('.filter-dropdown-content');
        
        // Close all other dropdowns
        document.querySelectorAll('.filter-dropdown-content.show').forEach(d => {
            if (d !== content) d.classList.remove('show');
        });
        
        content.classList.toggle('show');
        
        // Add click outside handler
        if (content.classList.contains('show')) {
            setTimeout(() => {
                document.addEventListener('click', this.closeDropdownsHandler);
            }, 0);
        }
    }
    
    closeDropdownsHandler = (e) => {
        if (!e.target.closest('.filter-dropdown')) {
            document.querySelectorAll('.filter-dropdown-content.show').forEach(d => {
                d.classList.remove('show');
            });
            document.removeEventListener('click', this.closeDropdownsHandler);
        }
    }
    
    // Spending Lifecycle Section
    renderSpendingLifecycle() {
        const container = document.getElementById('spendingLifecycle');
        
        if (!this.data.spendingLifecycle) {
            container.innerHTML = '<h2>Spending Lifecycle</h2><div class="error">Failed to load spending lifecycle data</div>';
            return;
        }
        
        // Handle both old (array) and new (object with aggregated/detailed) formats
        let aggregatedData, detailedData;
        if (Array.isArray(this.data.spendingLifecycle)) {
            // Old format - use as aggregated data
            aggregatedData = this.data.spendingLifecycle;
            detailedData = [];
        } else {
            // New format with both views
            aggregatedData = this.data.spendingLifecycle.aggregated || [];
            detailedData = this.data.spendingLifecycle.detailed || [];
        }
        
        // Store both views for easy access
        this.lifecycleAggregated = aggregatedData;
        this.lifecycleDetailed = detailedData;
        
        // Get unique components and fiscal years from aggregated data
        const components = [...new Set(aggregatedData.map(d => d.component))].sort();
        const fiscalYears = [...new Set(aggregatedData.map(d => d.fiscal_year))].sort((a, b) => b - a);
        
        // Get data currency info
        const apportionmentDate = this.data.metadata?.max_approval_date ? 
            new Date(this.data.metadata.max_approval_date).toLocaleDateString('en-US', {
                month: 'long',
                day: 'numeric',
                year: 'numeric'
            }) : 'current';
        
        container.innerHTML = `
            <h2>Spending Lifecycle: Appropriations → Obligations → Outlays</h2>
            
            <div class="controls" style="margin-bottom: 20px;">
                <div class="control-group">
                    <label for="lifecycleComponentFilter">Component:</label>
                    <select id="lifecycleComponentFilter" style="min-width: 300px;">
                        <option value="">All Components</option>
                        ${components.map(c => `<option value="${c}">${getComponentName(c, 'label')}</option>`).join('')}
                    </select>
                </div>
                
                <div class="control-group">
                    <label for="lifecycleFYFilter">Fiscal Year:</label>
                    <select id="lifecycleFYFilter">
                        <option value="">All Years</option>
                        ${fiscalYears.map(fy => `<option value="${fy}">FY ${fy}</option>`).join('')}
                    </select>
                </div>
                
                ${detailedData.length > 0 ? `
                <div class="control-group">
                    <label>View:</label>
                    <div style="display: flex; gap: 10px;">
                        <label style="font-weight: normal;">
                            <input type="radio" name="lifecycleView" value="aggregated" checked> 
                            Aggregated by Component
                        </label>
                        <label style="font-weight: normal;">
                            <input type="radio" name="lifecycleView" value="detailed"> 
                            Detailed by Availability Period
                        </label>
                    </div>
                </div>
                ` : ''}
            </div>
            
            <div class="table-container">
                <table id="lifecycleTable" class="display" style="width:100%">
                    <thead>
                        <tr id="lifecycleTableHeader">
                            <th>Component</th>
                            <th>Fiscal Year</th>
                            <th>Appropriations</th>
                            <th>Obligations</th>
                            <th>Outlays</th>
                            <th>Obligation Rate</th>
                            <th>Outlay Rate</th>
                        </tr>
                    </thead>
                    <tbody>
                    </tbody>
                </table>
            </div>
            
            <div class="legend" style="margin-top: 15px;">
                <div class="legend-item">
                    <span style="font-weight: bold;">Color Scale:</span>
                    <span>Darker blue = higher dollar amount (scaled to maximum across all values)</span>
                </div>
            </div>
            <div class="alert" style="margin-top: 15px;">
                <strong>Data Currency:</strong><br>
                • Appropriations data: Current through ${apportionmentDate}<br>
                • Obligations & Outlays: FY2025 through June (Q3), FY2022-2024 complete
            </div>
            <div class="data-note">
                <strong>Note:</strong> Appropriations shown are ${detailedData.length > 0 ? 'based on selected view' : 'aggregated by fiscal year'}. 
                Multi-year and no-year funds may have obligations and outlays in subsequent years.
                ⚠️ indicates obligations or outlays exceeding appropriations, which may occur with multi-year funds.
            </div>
        `;
        
        // Initialize the table
        this.initializeLifecycleTable();
        
        // Set up event listeners for filters
        document.getElementById('lifecycleComponentFilter').addEventListener('change', () => {
            this.updateLifecycleTable();
        });
        
        document.getElementById('lifecycleFYFilter').addEventListener('change', () => {
            this.updateLifecycleTable();
        });
        
        // Add listener for view toggle if detailed data exists
        if (detailedData.length > 0) {
            document.querySelectorAll('input[name="lifecycleView"]').forEach(radio => {
                radio.addEventListener('change', () => {
                    this.updateLifecycleTable();
                });
            });
        }
    }
    
    initializeLifecycleTable() {
        // Initialize table with aggregated view
        this.createLifecycleTable('aggregated');
    }
    
    createLifecycleTable(viewType) {
        // Destroy existing table if it exists
        if (this.lifecycleTable) {
            this.lifecycleTable.destroy();
            $('#lifecycleTable').empty();
        }
        
        // Get filtered data
        const filteredData = this.getFilteredLifecycleData();
        
        // Find max value for color scale
        const maxValue = Math.max(
            ...filteredData.map(d => Math.max(d.appropriations || 0, d.obligations || 0, d.outlays || 0))
        );
        
        // Create color scale function
        const getColor = (value) => {
            if (!value || value === 0) return 'rgb(255, 255, 255)';
            const intensity = value / maxValue;
            const blue = Math.round(255 - (intensity * 200)); // From light to dark blue
            return `rgb(${blue}, ${blue}, 255)`;
        };
        
        // Create text color function
        const getTextColor = (value) => {
            if (!value) return 'black';
            const intensity = value / maxValue;
            return intensity > 0.5 ? 'white' : 'black';
        };
        
        // Define columns based on view type
        let columns;
        if (viewType === 'detailed') {
            columns = [
                { 
                    data: 'component',
                    title: 'Component',
                    render: function(data) {
                        return getComponentName(data, 'label');
                    }
                },
                { 
                    data: 'account_name',
                    title: 'Account',
                    render: function(data) {
                        return data || '';
                    }
                },
                { 
                    data: 'period_label',
                    title: 'Period',
                    render: function(data) {
                        return data || '';
                    }
                },
                { 
                    data: 'availability_type',
                    title: 'Type',
                    render: function(data) {
                        return data || '';
                    }
                },
                { 
                    data: 'appropriations',
                    title: 'Appropriations',
                    render: function(data, type) {
                        if (type === 'display') {
                            const color = getColor(data);
                            const textColor = getTextColor(data);
                            return `<div style="background-color: ${color}; color: ${textColor}; padding: 8px; text-align: right; font-weight: 500;">
                                ${formatCurrency(data || 0)}
                            </div>`;
                        }
                        return data || 0;
                    }
                },
                { 
                    data: 'obligations',
                    title: 'Obligations',
                    render: function(data, type, row) {
                        if (type === 'display') {
                            const color = getColor(data);
                            const textColor = getTextColor(data);
                            const percentage = row.appropriations > 0 ? (data / row.appropriations * 100).toFixed(1) : 0;
                            const warningIcon = data > row.appropriations ? ' ⚠️' : '';
                            return `<div style="background-color: ${color}; color: ${textColor}; padding: 8px; text-align: right; font-weight: 500;" 
                                    title="${percentage}% of appropriations${warningIcon}">
                                ${formatCurrency(data || 0)}${warningIcon}
                            </div>`;
                        }
                        return data || 0;
                    }
                },
                { 
                    data: 'outlays',
                    title: 'Outlays',
                    render: function(data, type, row) {
                        if (type === 'display') {
                            const color = getColor(data);
                            const textColor = getTextColor(data);
                            const percentage = row.appropriations > 0 ? (data / row.appropriations * 100).toFixed(1) : 0;
                            const warningIcon = data > row.appropriations ? ' ⚠️' : '';
                            return `<div style="background-color: ${color}; color: ${textColor}; padding: 8px; text-align: right; font-weight: 500;"
                                    title="${percentage}% of appropriations${warningIcon}">
                                ${formatCurrency(data || 0)}${warningIcon}
                            </div>`;
                        }
                        return data || 0;
                    }
                }
            ];
        } else {
            // Aggregated view columns
            columns = [
                { 
                    data: 'component',
                    title: 'Component',
                    render: function(data) {
                        return getComponentName(data, 'label');
                    }
                },
                { 
                    data: 'fiscal_year',
                    title: 'Fiscal Year',
                    render: function(data) {
                        return `FY ${data}`;
                    }
                },
                { 
                    data: 'appropriations',
                    title: 'Appropriations',
                    render: function(data, type) {
                        if (type === 'display') {
                            const color = getColor(data);
                            const textColor = getTextColor(data);
                            return `<div style="background-color: ${color}; color: ${textColor}; padding: 8px; text-align: right; font-weight: 500;">
                                ${formatCurrency(data || 0)}
                            </div>`;
                        }
                        return data || 0;
                    }
                },
                { 
                    data: 'obligations',
                    title: 'Obligations',
                    render: function(data, type, row) {
                        if (type === 'display') {
                            const color = getColor(data);
                            const textColor = getTextColor(data);
                            const percentage = row.appropriations > 0 ? (data / row.appropriations * 100).toFixed(1) : 0;
                            const warningIcon = data > row.appropriations ? ' ⚠️' : '';
                            return `<div style="background-color: ${color}; color: ${textColor}; padding: 8px; text-align: right; font-weight: 500;" 
                                    title="${percentage}% of appropriations${warningIcon}">
                                ${formatCurrency(data || 0)}${warningIcon}
                            </div>`;
                        }
                        return data || 0;
                    }
                },
                { 
                    data: 'outlays',
                    title: 'Outlays',
                    render: function(data, type, row) {
                        if (type === 'display') {
                            const color = getColor(data);
                            const textColor = getTextColor(data);
                            const percentage = row.appropriations > 0 ? (data / row.appropriations * 100).toFixed(1) : 0;
                            const warningIcon = data > row.appropriations ? ' ⚠️' : '';
                            return `<div style="background-color: ${color}; color: ${textColor}; padding: 8px; text-align: right; font-weight: 500;"
                                    title="${percentage}% of appropriations${warningIcon}">
                                ${formatCurrency(data || 0)}${warningIcon}
                            </div>`;
                        }
                        return data || 0;
                    }
                },
                { 
                    data: null,
                    title: 'Obligation Rate',
                    render: function(data, type, row) {
                        const rate = row.appropriations > 0 ? (row.obligations / row.appropriations * 100) : 0;
                        if (type === 'display') {
                            const warningStyle = rate > 100 ? 'color: red; font-weight: bold;' : '';
                            return `<div style="text-align: right; ${warningStyle}">${rate.toFixed(1)}%</div>`;
                        }
                        return rate;
                    }
                },
                { 
                    data: null,
                    title: 'Outlay Rate',
                    render: function(data, type, row) {
                        const rate = row.appropriations > 0 ? (row.outlays / row.appropriations * 100) : 0;
                        if (type === 'display') {
                            const warningStyle = rate > 100 ? 'color: red; font-weight: bold;' : '';
                            return `<div style="text-align: right; ${warningStyle}">${rate.toFixed(1)}%</div>`;
                        }
                        return rate;
                    }
                }
            ];
        }
        
        // Initialize DataTable
        this.lifecycleTable = $('#lifecycleTable').DataTable({
            data: filteredData,
            columns: columns,
            pageLength: 25,
            order: [[viewType === 'detailed' ? 4 : 2, 'desc']], // Sort by appropriations descending
            dom: 'lrtip' // Remove search box and buttons
        });
    }
    
    getFilteredLifecycleData() {
        const componentFilter = document.getElementById('lifecycleComponentFilter')?.value || '';
        const fyFilter = document.getElementById('lifecycleFYFilter')?.value || '';
        const viewType = document.querySelector('input[name="lifecycleView"]:checked')?.value || 'aggregated';
        
        // Choose the appropriate data based on view type
        let filteredData = viewType === 'detailed' ? this.lifecycleDetailed : this.lifecycleAggregated;
        
        // Apply component filter
        if (componentFilter) {
            filteredData = filteredData.filter(d => d.component === componentFilter);
        }
        
        // Apply fiscal year filter
        if (fyFilter) {
            filteredData = filteredData.filter(d => d.fiscal_year == fyFilter);
        }
        
        // Sort by appropriations descending
        return filteredData.sort((a, b) => (b.appropriations || 0) - (a.appropriations || 0));
    }
    
    updateLifecycleTable() {
        const viewType = document.querySelector('input[name="lifecycleView"]:checked')?.value || 'aggregated';
        
        // If view type changed, we need to recreate the table with different columns
        if (this.currentLifecycleView !== viewType) {
            this.currentLifecycleView = viewType;
            this.createLifecycleTable(viewType);
        } else if (this.lifecycleTable) {
            // Otherwise just update the data
            const filteredData = this.getFilteredLifecycleData();
            this.lifecycleTable.clear();
            this.lifecycleTable.rows.add(filteredData);
            this.lifecycleTable.draw();
        }
    }
    
    
    // Old Spending Trends Section (to be replaced)
    renderSpendingTrends() {
        const container = document.getElementById('trendsChart');
        container.innerHTML = ''; // Clear existing
        
        if (!this.data.spendingSummary) {
            container.innerHTML = '<div class="error">Failed to load spending data</div>';
            return;
        }
        
        // Use pre-aggregated data based on current view
        let dataArray;
        if (this.currentTrendView === 'component') {
            // Filter by fiscal year from pre-aggregated component data
            dataArray = this.data.spendingSummary.by_component
                .filter(d => d.fiscal_year == this.currentFY)
                .map(d => ({
                    name: d.component,
                    obligations: d.obligations || 0,
                    outlays: d.outlays || 0
                }))
                .sort((a, b) => b.obligations - a.obligations)
                .slice(0, 10);
        } else {
            // Filter by fiscal year from pre-aggregated category data
            dataArray = this.data.spendingSummary.by_category
                .filter(d => d.fiscal_year == this.currentFY)
                .map(d => ({
                    name: d.category,
                    obligations: d.obligations || 0,
                    outlays: d.outlays || 0
                }))
                .sort((a, b) => b.obligations - a.obligations)
                .slice(0, 10);
        }
        
        // Create chart
        this.createBarChart(container, dataArray);
    }
    
    createBarChart(container, data) {
        const margin = { top: 20, right: 120, bottom: 60, left: 200 };
        const width = container.clientWidth - margin.left - margin.right;
        const height = 400 - margin.top - margin.bottom;
        
        const svg = d3.select(container)
            .append('svg')
            .attr('width', width + margin.left + margin.right)
            .attr('height', height + margin.top + margin.bottom);
        
        const g = svg.append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);
        
        // Scales
        const x = d3.scaleLinear()
            .domain([0, d3.max(data, d => Math.max(d.obligations, d.outlays))])
            .range([0, width]);
        
        const y = d3.scaleBand()
            .domain(data.map(d => d.name))
            .range([0, height])
            .padding(0.3);
        
        // Create bars for obligations
        g.selectAll('.bar-obligations')
            .data(data)
            .enter().append('rect')
            .attr('class', 'bar bar-obligations')
            .attr('x', 0)
            .attr('y', d => y(d.name))
            .attr('width', d => x(d.obligations))
            .attr('height', y.bandwidth() / 2)
            .attr('fill', '#007bff');
        
        // Create bars for outlays
        g.selectAll('.bar-outlays')
            .data(data)
            .enter().append('rect')
            .attr('class', 'bar bar-outlays')
            .attr('x', 0)
            .attr('y', d => y(d.name) + y.bandwidth() / 2)
            .attr('width', d => x(d.outlays))
            .attr('height', y.bandwidth() / 2)
            .attr('fill', '#28a745');
        
        // Add value labels
        g.selectAll('.label-obligations')
            .data(data)
            .enter().append('text')
            .attr('x', d => x(d.obligations) + 5)
            .attr('y', d => y(d.name) + y.bandwidth() / 4)
            .attr('dy', '.35em')
            .text(d => formatCurrency(d.obligations))
            .style('font-size', '12px');
        
        g.selectAll('.label-outlays')
            .data(data)
            .enter().append('text')
            .attr('x', d => x(d.outlays) + 5)
            .attr('y', d => y(d.name) + 3 * y.bandwidth() / 4)
            .attr('dy', '.35em')
            .text(d => formatCurrency(d.outlays))
            .style('font-size', '12px')
            .style('fill', '#28a745');
        
        // Add axes
        g.append('g')
            .attr('class', 'axis')
            .call(d3.axisLeft(y).tickFormat(d => {
                if (this.currentTrendView === 'component') {
                    return getComponentName(d, 'label');
                }
                return d;
            }));
        
        g.append('g')
            .attr('class', 'axis')
            .attr('transform', `translate(0,${height})`)
            .call(d3.axisBottom(x).tickFormat(d => formatCurrency(d, true)));
        
        // Add legend
        const legend = svg.append('g')
            .attr('transform', `translate(${width + margin.left + 10}, 20)`);
        
        legend.append('rect')
            .attr('width', 15)
            .attr('height', 15)
            .attr('fill', '#007bff');
        
        legend.append('text')
            .attr('x', 20)
            .attr('y', 12)
            .text('Obligations')
            .style('font-size', '14px');
        
        legend.append('rect')
            .attr('y', 20)
            .attr('width', 15)
            .attr('height', 15)
            .attr('fill', '#28a745');
        
        legend.append('text')
            .attr('x', 20)
            .attr('y', 32)
            .text('Outlays')
            .style('font-size', '14px');
    }
    
    // Year-over-Year Comparison
    renderYearOverYear() {
        const container = document.getElementById('yearOverYear');
        container.innerHTML = `
            <h2>Year-over-Year Spending Trends</h2>
            <div id="yearOverYearControls" style="margin-bottom: 20px; display: flex; gap: 20px; align-items: center;">
                <div class="filter-dropdown" id="componentFilterDropdown">
                    <div class="filter-dropdown-button" onclick="dashboard.toggleDropdown('componentFilterDropdown')">
                        <span id="componentFilterLabel">All Components</span>
                    </div>
                    <div class="filter-dropdown-content" id="componentFilterContent">
                        <div id="componentFilters">
                            <!-- Component checkboxes will be added here -->
                        </div>
                        <div class="filter-dropdown-actions">
                            <button onclick="dashboard.selectAllComponents()">Select All</button>
                            <button onclick="dashboard.clearAllComponents()">Clear All</button>
                        </div>
                    </div>
                </div>
                
                <div class="filter-dropdown" id="spendingTypeFilterDropdown">
                    <div class="filter-dropdown-button" onclick="dashboard.toggleDropdown('spendingTypeFilterDropdown')">
                        <span id="spendingTypeFilterLabel">Spending Types</span>
                    </div>
                    <div class="filter-dropdown-content" id="spendingTypeFilterContent">
                        <div id="spendingTypeFilters">
                            <!-- Spending type checkboxes will be added here -->
                        </div>
                        <div class="filter-dropdown-actions">
                            <button onclick="dashboard.selectAllSpendingTypes()">Select All</button>
                            <button onclick="dashboard.clearAllSpendingTypes()">Clear All</button>
                        </div>
                    </div>
                </div>
            </div>
            <div id="yearOverYearChart"></div>
            <div style="margin-top: 20px;">
                <button onclick="
                    const totals = dashboard.data.monthlyTrends.monthly.reduce((acc, m) => {
                        acc.appr += m.appropriations_total;
                        acc.obligations += m.obligations_total;
                        return acc;
                    }, {appr: 0, obligations: 0});
                    console.log('Total appropriations:', totals.appr, 'Total obligations:', totals.obligations);
                    console.log('Monthly data:', dashboard.data.monthlyTrends); 
                    alert('Total appropriations: $' + totals.appr.toLocaleString() + ', Total obligations: $' + totals.obligations.toLocaleString() + ' - Check console for details');
                ">
                    Debug: Check Data Totals
                </button>
            </div>
        `;
        
        // Initialize filters
        this.selectedComponents = new Set();
        this.selectedSpendingTypes = new Set();
        
        if (!this.data.monthlyTrends) {
            container.innerHTML += '<div class="error">Monthly trends data not available</div>';
            return;
        }
        
        // Create component filters
        const componentFilters = document.getElementById('componentFilters');
        if (this.data.monthlyTrends.components) {
            this.data.monthlyTrends.components.forEach(component => {
                const checkbox = document.createElement('div');
                checkbox.innerHTML = `
                    <label style="display: block; padding: 2px 0; cursor: pointer;">
                        <input type="checkbox" value="${component}" onchange="dashboard.updateYearOverYear()" 
                               style="margin-right: 5px;" checked>
                        ${getComponentName(component, 'label')}
                    </label>
                `;
                componentFilters.appendChild(checkbox);
                this.selectedComponents.add(component);
            });
        }
        
        // Create spending type filters  
        const spendingTypeFilters = document.getElementById('spendingTypeFilters');
        if (this.data.monthlyTrends.spending_types) {
            this.data.monthlyTrends.spending_types.forEach(type => {
                const checkbox = document.createElement('div');
                checkbox.style.display = 'inline-block';
                checkbox.style.marginRight = '15px';
                checkbox.innerHTML = `
                    <label style="cursor: pointer;">
                        <input type="checkbox" value="${type}" onchange="dashboard.updateYearOverYear()" 
                               style="margin-right: 5px;" disabled>
                        ${type}
                    </label>
                `;
                spendingTypeFilters.appendChild(checkbox);
            });
        }
        
        // Note about spending type data
        const note = document.createElement('div');
        note.style.marginTop = '5px';
        note.style.fontSize = '0.9em';
        note.style.color = '#666';
        note.innerHTML = '<em>Note: Spending type breakdown not yet available in monthly data</em>';
        spendingTypeFilters.appendChild(note);
        
        this.updateYearOverYear();
    }
    
    selectAllComponents() {
        document.querySelectorAll('#componentFilters input[type="checkbox"]').forEach(cb => {
            cb.checked = true;
            this.selectedComponents.add(cb.value);
        });
        this.updateYearOverYear();
        this.updateComponentFilterLabel();
    }
    
    clearAllComponents() {
        document.querySelectorAll('#componentFilters input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });
        this.selectedComponents.clear();
        this.updateYearOverYear();
        this.updateComponentFilterLabel();
    }
    
    selectAllSpendingTypes() {
        document.querySelectorAll('#spendingTypeFilters input[type="checkbox"]:not(:disabled)').forEach(cb => {
            cb.checked = true;
            this.selectedSpendingTypes.add(cb.value);
        });
        this.updateYearOverYear();
    }
    
    clearAllSpendingTypes() {
        document.querySelectorAll('#spendingTypeFilters input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });
        this.selectedSpendingTypes.clear();
        this.updateYearOverYear();
        this.updateComponentFilterLabel();
    }
    
    updateComponentFilterLabel() {
        const label = document.getElementById('componentFilterLabel');
        const selected = this.selectedComponents.size;
        const total = this.data.monthlyTrends?.components?.length || 0;
        
        if (selected === 0) {
            label.textContent = 'No Components Selected';
        } else if (selected === total) {
            label.textContent = 'All Components';
        } else {
            label.textContent = `${selected} of ${total} Components`;
        }
    }
    
    updateYearOverYear() {
        // Update selected components
        this.selectedComponents.clear();
        document.querySelectorAll('#componentFilters input[type="checkbox"]:checked').forEach(cb => {
            this.selectedComponents.add(cb.value);
        });
        
        // Update selected spending types
        this.selectedSpendingTypes.clear();
        document.querySelectorAll('#spendingTypeFilters input[type="checkbox"]:checked').forEach(cb => {
            this.selectedSpendingTypes.add(cb.value);
        });
        
        this.renderYearOverYearChart();
        this.updateComponentFilterLabel();
    }
    
    renderYearOverYearChart() {
        const container = document.getElementById('yearOverYearChart');
        container.innerHTML = '';
        
        if (!this.data.monthlyTrends || !this.data.monthlyTrends.monthly) {
            container.innerHTML = '<div class="error">No monthly data available</div>';
            return;
        }
        
        // Filter and aggregate data based on selected components
        console.log('Selected components:', this.selectedComponents.size, 'of', this.data.monthlyTrends.components?.length);
        console.log('Monthly trends data:', this.data.monthlyTrends);
        console.log('First month data:', this.data.monthlyTrends.monthly?.[0]);
        console.log('Sample months with data:', this.data.monthlyTrends.monthly?.filter(m => m.appropriations_total > 0 || m.obligations_total > 0).slice(0, 5));
        
        // Log what we're looking for
        console.log('Sample month structure:', this.data.monthlyTrends.monthly?.[10]);
        console.log('Selected components:', Array.from(this.selectedComponents));
        
        const monthlyData = this.data.monthlyTrends.monthly.map(month => {
            let appropriations = 0;
            let obligations = 0;
            
            // If no components selected, show all
            if (this.selectedComponents.size === 0) {
                // Sum all components
                Object.values(month.appropriations_by_component || {}).forEach(value => {
                    appropriations += value || 0;
                });
                Object.values(month.obligations_by_component || {}).forEach(value => {
                    obligations += value || 0;
                });
            } else {
                // Sum only selected components
                this.selectedComponents.forEach(component => {
                    const apprValue = month.appropriations_by_component[component] || 0;
                    const obligValue = month.obligations_by_component[component] || 0;
                    if (apprValue > 0 || obligValue > 0) {
                        console.log(`Month ${month.date}, Component ${component}: appr=${apprValue}, oblig=${obligValue}`);
                    }
                    appropriations += apprValue;
                    obligations += obligValue;
                });
            }
            
            return {
                date: new Date(month.date + '-01'),
                appropriations,
                obligations
            };
        });
        
        this.createMonthlyTrendChart(container, monthlyData);
    }
    
    createMonthlyTrendChart(container, monthlyData) {
        // Check if we have valid data
        if (!monthlyData || monthlyData.length === 0) {
            container.innerHTML = '<div class="error">No data available for selected filters</div>';
            return;
        }
        
        const margin = { top: 20, right: 150, bottom: 60, left: 100 };
        const width = 900 - margin.left - margin.right;
        const height = 400 - margin.top - margin.bottom;
        
        const svg = d3.select(container)
            .append('svg')
            .attr('width', width + margin.left + margin.right)
            .attr('height', height + margin.top + margin.bottom);
        
        const g = svg.append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);
        
        // Scales
        const dateExtent = d3.extent(monthlyData, d => d.date);
        if (!dateExtent[0] || !dateExtent[1]) {
            console.error('Invalid date extent:', dateExtent);
            container.innerHTML = '<div class="error">Invalid date data</div>';
            return;
        }
        
        const x = d3.scaleTime()
            .domain(dateExtent)
            .range([0, width]);
            
        // Ensure we have a valid Y domain
        const maxY = d3.max(monthlyData, d => Math.max(d.appropriations, d.obligations)) || 1000000;
        const y = d3.scaleLinear()
            .domain([0, maxY])
            .range([height, 0]);
        
        // Line generators
        const lineAppr = d3.line()
            .x(d => x(d.date))
            .y(d => y(d.appropriations))
            .curve(d3.curveMonotoneX);
            
        const lineObligations = d3.line()
            .x(d => x(d.date))
            .y(d => y(d.obligations))
            .curve(d3.curveMonotoneX);
        
        // Add axes
        g.append('g')
            .attr('transform', `translate(0,${height})`)
            .call(d3.axisBottom(x)
                .tickFormat(d3.timeFormat('%b %Y'))
                .ticks(d3.timeMonth.every(3)))
            .selectAll('text')
            .style('text-anchor', 'end')
            .attr('dx', '-.8em')
            .attr('dy', '.15em')
            .attr('transform', 'rotate(-45)');
            
        g.append('g')
            .call(d3.axisLeft(y).tickFormat(d => formatCurrency(d, true)));
        
        // Add grid lines
        g.append('g')
            .attr('class', 'grid')
            .attr('transform', `translate(0,${height})`)
            .call(d3.axisBottom(x)
                .tickSize(-height)
                .tickFormat(''))
            .style('stroke-dasharray', '3,3')
            .style('opacity', 0.3);
            
        g.append('g')
            .attr('class', 'grid')
            .call(d3.axisLeft(y)
                .tickSize(-width)
                .tickFormat(''))
            .style('stroke-dasharray', '3,3')
            .style('opacity', 0.3);
        
        // Add lines
        const lines = [
            {name: 'Appropriations', line: lineAppr, color: '#1f77b4', data: monthlyData},
            {name: 'Obligations', line: lineObligations, color: '#ff7f0e', data: monthlyData}
        ];
        
        lines.forEach(series => {
            // Add line
            g.append('path')
                .datum(series.data)
                .attr('fill', 'none')
                .attr('stroke', series.color)
                .attr('stroke-width', 2)
                .attr('d', series.line);
        });
        
        // Add legend
        const legend = svg.append('g')
            .attr('transform', `translate(${width + margin.left + 10}, 20)`);
        
        lines.forEach((series, i) => {
            const legendRow = legend.append('g')
                .attr('transform', `translate(0, ${i * 20})`);
            
            legendRow.append('rect')
                .attr('width', 15)
                .attr('height', 3)
                .attr('fill', series.color);
            
            legendRow.append('text')
                .attr('x', 20)
                .attr('y', 3)
                .attr('dy', '.15em')
                .text(series.name)
                .style('font-size', '12px');
        });
        
        // Add hover interactions
        // Remove any existing tooltips first
        d3.select('body').selectAll('.year-over-year-tooltip').remove();
        
        const tooltip = d3.select('body').append('div')
            .attr('class', 'tooltip year-over-year-tooltip')
            .style('opacity', 0)
            .style('position', 'absolute')
            .style('background', 'rgba(0,0,0,0.8)')
            .style('color', 'white')
            .style('padding', '10px')
            .style('border-radius', '5px')
            .style('pointer-events', 'none');
            
        // Add invisible rect for mouse tracking
        g.append('rect')
            .attr('width', width)
            .attr('height', height)
            .style('fill', 'none')
            .style('pointer-events', 'all')
            .on('mousemove', function(event) {
                const x0 = x.invert(d3.pointer(event)[0]);
                const i = d3.bisectLeft(monthlyData.map(d => d.date), x0, 1);
                const d0 = monthlyData[i - 1];
                const d1 = monthlyData[i];
                const d = d1 && (x0 - d0.date > d1.date - x0) ? d1 : d0;
                
                if (d) {
                    tooltip.transition().duration(200).style('opacity', .9);
                    tooltip.html(`
                        <strong>${d3.timeFormat('%B %Y')(d.date)}</strong><br>
                        Appropriations: ${formatCurrency(d.appropriations)}<br>
                        Obligations: ${formatCurrency(d.obligations)}
                    `)
                    .style('left', (event.pageX + 10) + 'px')
                    .style('top', (event.pageY - 28) + 'px');
                }
            })
            .on('mouseout', function() {
                tooltip.transition().duration(500).style('opacity', 0);
            });
        
        // Add note about data currency
        container.innerHTML += `
            <div class="data-note" style="margin-top: 15px;">
                <strong>Note:</strong> Appropriations show actual apportionment approval dates (causing spikes when bills pass). 
                Obligations are cumulative totals distributed evenly across fiscal year months.
                Due to data limitations, the scale may appear mismatched - see the Spending Lifecycle table for accurate fiscal year comparisons.
            </div>
        `;
    }
    
    createYearOverYearChart(container, data) {
        // Keep the old function for compatibility
        this.createMonthlyTrendChart(container, data);
    }
    
    createYearOverYearTable(data) {
        let html = `
            <table style="margin-top: 20px;">
                <thead>
                    <tr>
                        <th>Fiscal Year</th>
                        <th class="amount">Appropriations</th>
                        <th class="amount">Obligations</th>
                        <th class="amount">Outlays</th>
                        <th class="percent">Obligation Rate</th>
                        <th class="percent">Outlay Rate</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        data.forEach(d => {
            const obligationRate = d.appropriations > 0 ? (d.obligations / d.appropriations * 100) : 0;
            const outlayRate = d.appropriations > 0 ? (d.outlays / d.appropriations * 100) : 0;
            
            html += `
                <tr>
                    <td>FY ${d.year}</td>
                    <td class="amount">${formatCurrency(d.appropriations)}</td>
                    <td class="amount">${formatCurrency(d.obligations)}</td>
                    <td class="amount">${formatCurrency(d.outlays)}</td>
                    <td class="percent">${obligationRate.toFixed(1)}%</td>
                    <td class="percent">${outlayRate.toFixed(1)}%</td>
                </tr>
            `;
        });
        
        html += `
                </tbody>
            </table>
        `;
        
        return html;
    }
    
    // Where Money Goes Section
    renderWhereMoneyGoes() {
        const content = document.getElementById('moneyContent');
        
        switch (this.currentMoneyView) {
            case 'vendors':
                this.renderTopVendors(content);
                break;
            case 'categories':
                this.renderSpendingCategories(content);
                break;
            case 'changes':
                this.renderNotableChanges(content);
                break;
        }
    }
    
    // Interactive Vendor Analysis
    renderInteractiveVendors() {
        const container = document.getElementById('vendorAnalysis');
        
        if (!this.data.vendorSummary || !this.data.vendorSummary.top_vendors) {
            container.innerHTML = '<h2>Vendor Analysis</h2><div class="error">Failed to load vendor data</div>';
            return;
        }
        
        // Get vendor data for current year
        const currentYearVendors = this.data.vendorSummary.top_vendors
            .filter(d => d.fiscal_year == this.currentFY);
        
        // Aggregate by vendor
        const vendorTotals = d3.rollup(
            currentYearVendors,
            v => d3.sum(v, d => d.obligations),
            d => d.vendor_name
        );
        
        const topVendors = Array.from(vendorTotals, ([vendor, amount]) => ({ vendor, amount }))
            .sort((a, b) => b.amount - a.amount)
            .slice(0, 20);
        
        container.innerHTML = `
            <h2>Top Vendors for FY ${this.currentFY}</h2>
            <div class="vendor-grid">
                ${topVendors.map((v, i) => `
                    <div class="vendor-card" data-vendor="${v.vendor}">
                        <div class="vendor-rank">#${i + 1}</div>
                        <div class="vendor-name">${v.vendor}</div>
                        <div class="vendor-amount">${formatCurrency(v.amount)}</div>
                        <div class="vendor-action">Click for details →</div>
                    </div>
                `).join('')}
            </div>
            <div id="vendorDetails" style="display: none;">
                <h3 id="vendorDetailsTitle"></h3>
                <div id="vendorDetailsContent"></div>
            </div>
        `;
        
        // Add click handlers
        container.querySelectorAll('.vendor-card').forEach(card => {
            card.addEventListener('click', () => this.showVendorDetails(card.dataset.vendor));
        });
    }
    
    showVendorDetails(vendorName) {
        const detailsDiv = document.getElementById('vendorDetails');
        const titleDiv = document.getElementById('vendorDetailsTitle');
        const contentDiv = document.getElementById('vendorDetailsContent');
        
        // Get all data for this vendor
        const vendorData = this.data.vendorSummary.top_vendors
            .filter(d => d.vendor_name === vendorName);
        
        // Group by year
        const byYear = d3.rollup(
            vendorData,
            v => d3.sum(v, d => d.obligations),
            d => d.fiscal_year
        );
        
        // Get component breakdown if available
        const vendorComponents = this.data.vendorSummary.vendor_components
            ?.filter(d => d.vendor_name === vendorName && d.fiscal_year == this.currentFY);
        
        titleDiv.textContent = vendorName;
        
        let html = `
            <div class="vendor-detail-grid">
                <div class="vendor-trend">
                    <h4>Trend Over Years</h4>
                    <table>
                        <thead>
                            <tr>
                                <th>Fiscal Year</th>
                                <th class="amount">Obligations</th>
                            </tr>
                        </thead>
                        <tbody>
        `;
        
        Array.from(byYear, ([year, amount]) => ({ year, amount }))
            .sort((a, b) => b.year - a.year)
            .forEach(d => {
                html += `
                    <tr>
                        <td>FY ${d.year}</td>
                        <td class="amount">${formatCurrency(d.amount)}</td>
                    </tr>
                `;
            });
        
        html += `
                        </tbody>
                    </table>
                </div>
        `;
        
        if (vendorComponents && vendorComponents.length > 0) {
            html += `
                <div class="vendor-components">
                    <h4>FY ${this.currentFY} by Component</h4>
                    <table>
                        <thead>
                            <tr>
                                <th>Component</th>
                                <th class="amount">Amount</th>
                            </tr>
                        </thead>
                        <tbody>
            `;
            
            vendorComponents
                .sort((a, b) => b.obligations - a.obligations)
                .forEach(d => {
                    html += `
                        <tr>
                            <td>${d.component}</td>
                            <td class="amount">${formatCurrency(d.obligations)}</td>
                        </tr>
                    `;
                });
            
            html += `
                        </tbody>
                    </table>
                </div>
            `;
        }
        
        html += `
            </div>
            <div class="vendor-links">
                <a href="https://www.usaspending.gov/search?hash=advanced-search&filters=%7B%22recipientName%22%3A%5B%22${encodeURIComponent(vendorName)}%22%5D%7D" 
                   target="_blank" rel="noopener noreferrer">
                   View on USAspending.gov →
                </a>
            </div>
        `;
        
        contentDiv.innerHTML = html;
        detailsDiv.style.display = 'block';
        detailsDiv.scrollIntoView({ behavior: 'smooth' });
    }
    
    renderTopVendors(container) {
        if (!this.data.vendorSummary || !this.data.vendorSummary.top_vendors) {
            container.innerHTML = '<div class="error">Failed to load vendor data</div>';
            return;
        }
        
        // Filter pre-aggregated top vendors data by current fiscal year
        const topVendorsForYear = this.data.vendorSummary.top_vendors
            .filter(d => d.fiscal_year == this.currentFY);
        
        // Aggregate by vendor for the selected year
        const vendorTotals = new Map();
        topVendorsForYear.forEach(d => {
            const current = vendorTotals.get(d.vendor_name) || 0;
            vendorTotals.set(d.vendor_name, current + (d.obligations || 0));
        });
        
        // Sort and get top 20
        const topVendors = Array.from(vendorTotals, ([vendor, amount]) => ({ vendor, amount }))
            .sort((a, b) => b.amount - a.amount)
            .slice(0, 20);
        
        let html = `
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Vendor</th>
                            <th class="amount">FY ${this.currentFY} Awards</th>
                            <th class="percent">% of Total</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        const totalVendorAmount = d3.sum(topVendors, d => d.amount);
        
        topVendors.forEach((vendor, i) => {
            const percent = (vendor.amount / totalVendorAmount * 100).toFixed(1);
            html += `
                        <tr>
                            <td>${i + 1}</td>
                            <td>${vendor.vendor}</td>
                            <td class="amount">${formatCurrency(vendor.amount)}</td>
                            <td class="percent">${percent}%</td>
                        </tr>
            `;
        });
        
        html += `
                    </tbody>
                </table>
            </div>
            <div class="data-note">
                Showing top 20 vendors by total award amount in FY ${this.currentFY}.
                <a href="vendor_analysis.html">View full vendor analysis →</a>
            </div>
        `;
        
        container.innerHTML = html;
    }
    
    renderSpendingCategories(container) {
        if (!this.data.spendingSummary || !this.data.spendingSummary.by_category) {
            container.innerHTML = '<div class="error">Failed to load spending data</div>';
            return;
        }
        
        // Use pre-aggregated category data for current FY
        const categories = this.data.spendingSummary.by_category
            .filter(d => d.fiscal_year == this.currentFY)
            .map(d => ({
                category: d.category,
                obligations: d.obligations || 0,
                outlays: d.outlays || 0,
                ratio: d.outlays > 0 && d.obligations > 0 ? (d.outlays / d.obligations * 100) : 0
            }))
            .sort((a, b) => b.obligations - a.obligations);
        
        let html = `
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Category</th>
                            <th class="amount">Obligations</th>
                            <th class="amount">Outlays</th>
                            <th class="percent">Outlay Rate</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        categories.forEach(cat => {
            html += `
                        <tr>
                            <td>${cat.category}</td>
                            <td class="amount">${formatCurrency(cat.obligations)}</td>
                            <td class="amount">${formatCurrency(cat.outlays)}</td>
                            <td class="percent">${cat.ratio.toFixed(1)}%</td>
                        </tr>
            `;
        });
        
        html += `
                    </tbody>
                </table>
            </div>
        `;
        
        container.innerHTML = html;
    }
    
    renderNotableChanges(container) {
        if (!this.data.vendorSummary || !this.compareFY) {
            container.innerHTML = '<div class="alert">Select a comparison year to see vendor changes</div>';
            return;
        }
        
        // Use the pre-generated new vendors data if available
        if (this.data.vendorSummary.new_vendors_by_year && 
            this.data.vendorSummary.new_vendors_by_year[this.currentFY]) {
            
            const newVendorsList = this.data.vendorSummary.new_vendors_by_year[this.currentFY]
                .map(v => ({ vendor: v.vendor, amount: v.amount }));
            
            // Also calculate vendors that disappeared
            const currentYearVendors = new Set(
                this.data.vendorSummary.top_vendors
                    .filter(d => d.fiscal_year == this.currentFY)
                    .map(d => d.vendor_name)
            );
            
            const compareYearVendors = new Set(
                this.data.vendorSummary.top_vendors
                    .filter(d => d.fiscal_year == this.compareFY)
                    .map(d => d.vendor_name)
            );
            
            // Get vendors that were in compare year but not current
            const lostVendors = [];
            this.data.vendorSummary.top_vendors
                .filter(d => d.fiscal_year == this.compareFY)
                .forEach(d => {
                    if (!currentYearVendors.has(d.vendor_name) && d.obligations > 1000000) {
                        lostVendors.push({ vendor: d.vendor_name, amount: d.obligations });
                    }
                });
            
            // Remove duplicates and sort
            const uniqueLostVendors = Array.from(
                new Map(lostVendors.map(v => [v.vendor, v])).values()
            ).sort((a, b) => b.amount - a.amount);
            
            this.renderVendorChangesTable(container, newVendorsList, uniqueLostVendors);
            return;
        }
        
        // Fallback: calculate from top vendors data
        const currentVendors = new Map();
        const compareVendors = new Map();
        
        this.data.vendorSummary.top_vendors
            .filter(d => d.fiscal_year == this.currentFY)
            .forEach(d => {
                const current = currentVendors.get(d.vendor_name) || 0;
                currentVendors.set(d.vendor_name, current + d.obligations);
            });
        
        this.data.vendorSummary.top_vendors
            .filter(d => d.fiscal_year == this.compareFY)
            .forEach(d => {
                const current = compareVendors.get(d.vendor_name) || 0;
                compareVendors.set(d.vendor_name, current + d.obligations);
            });
        
        // Find new vendors (in current but not compare)
        const newVendors = [];
        currentVendors.forEach((amount, vendor) => {
            if (!compareVendors.has(vendor) && amount > 1000000) {
                newVendors.push({ vendor, amount });
            }
        });
        newVendors.sort((a, b) => b.amount - a.amount);
        
        // Find lost vendors (in compare but not current)
        const lostVendors = [];
        compareVendors.forEach((amount, vendor) => {
            if (!currentVendors.has(vendor) && amount > 1000000) {
                lostVendors.push({ vendor, amount });
            }
        });
        lostVendors.sort((a, b) => b.amount - a.amount);
        
        // Find biggest changes
        const changes = [];
        currentVendors.forEach((currentAmount, vendor) => {
            const compareAmount = compareVendors.get(vendor) || 0;
            if (compareAmount > 0) {
                const change = currentAmount - compareAmount;
                const changePercent = (change / compareAmount) * 100;
                if (Math.abs(changePercent) > 50 && Math.abs(change) > 1000000) {
                    changes.push({
                        vendor,
                        currentAmount,
                        compareAmount,
                        change,
                        changePercent
                    });
                }
            }
        });
        changes.sort((a, b) => Math.abs(b.changePercent) - Math.abs(a.changePercent));
        
        this.renderVendorChangesTable(container, newVendors, lostVendors, changes);
    }
    
    renderVendorChangesTable(container, newVendors, lostVendors, changes = []) {
        let html = `
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <h3>New Vendors (FY ${this.currentFY})</h3>
                    <table style="width: 100%;">
                        <thead>
                            <tr>
                                <th>Vendor</th>
                                <th class="amount">Amount</th>
                            </tr>
                        </thead>
                        <tbody>
        `;
        
        newVendors.slice(0, 10).forEach(v => {
            html += `
                            <tr>
                                <td>${v.vendor}</td>
                                <td class="amount">${formatCurrency(v.amount)}</td>
                            </tr>
            `;
        });
        
        html += `
                        </tbody>
                    </table>
                </div>
                
                <div>
                    <h3>Lost Vendors (from FY ${this.compareFY})</h3>
                    <table style="width: 100%;">
                        <thead>
                            <tr>
                                <th>Vendor</th>
                                <th class="amount">Amount</th>
                            </tr>
                        </thead>
                        <tbody>
        `;
        
        lostVendors.slice(0, 10).forEach(v => {
            html += `
                            <tr>
                                <td>${v.vendor}</td>
                                <td class="amount">${formatCurrency(v.amount)}</td>
                            </tr>
            `;
        });
        
        html += `
                        </tbody>
                    </table>
                </div>
            </div>
            
            <h3 style="margin-top: 30px;">Biggest Changes</h3>
            <table>
                <thead>
                    <tr>
                        <th>Vendor</th>
                        <th class="amount">FY ${this.compareFY}</th>
                        <th class="amount">FY ${this.currentFY}</th>
                        <th class="amount">Change</th>
                        <th class="percent">% Change</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        changes.slice(0, 15).forEach(v => {
            const changeClass = v.change > 0 ? 'positive' : 'negative';
            html += `
                    <tr>
                        <td>${v.vendor}</td>
                        <td class="amount">${formatCurrency(v.compareAmount)}</td>
                        <td class="amount">${formatCurrency(v.currentAmount)}</td>
                        <td class="amount ${changeClass}">${v.change > 0 ? '+' : ''}${formatCurrency(v.change)}</td>
                        <td class="percent ${changeClass}">${v.changePercent > 0 ? '+' : ''}${v.changePercent.toFixed(1)}%</td>
                    </tr>
            `;
        });
        
        html += `
                </tbody>
            </table>
        `;
        
        container.innerHTML = html;
    }
    
    showError(message) {
        console.error(message);
        // Could show user-friendly error in UI
    }
}

// Global functions for dashboard

function downloadData() {
    // Create a combined dataset for download
    const data = [];
    
    // Add appropriations data from summary
    if (dashboard.data.appropriationsSummary && dashboard.data.appropriationsSummary.by_component) {
        dashboard.data.appropriationsSummary.by_component
            .filter(d => d.fiscal_year == dashboard.currentFY)
            .forEach(row => {
                data.push({
                    type: 'Appropriation',
                    fiscal_year: row.fiscal_year,
                    component: row.component,
                    account: '',
                    category: '',
                    amount: row.amount,
                    vendor: '',
                    notes: ''
                });
            });
    }
    
    // Add spending data from summary
    if (dashboard.data.spendingSummary && dashboard.data.spendingSummary.by_component) {
        dashboard.data.spendingSummary.by_component
            .filter(d => d.fiscal_year == dashboard.currentFY)
            .forEach(row => {
                data.push({
                    type: 'Spending',
                    fiscal_year: row.fiscal_year,
                    component: row.component,
                    account: '',
                    category: '',
                    amount: row.obligations || 0,
                    vendor: '',
                    notes: 'Obligations'
                });
            });
    }
    
    // Convert to CSV
    const headers = ['Type', 'Fiscal Year', 'Component', 'Account', 'Category', 'Amount', 'Vendor', 'Notes'];
    let csv = headers.join(',') + '\n';
    
    data.forEach(row => {
        const values = headers.map(header => {
            const value = row[header.toLowerCase().replace(' ', '_')];
            // Escape quotes and wrap in quotes if contains comma
            const escaped = String(value).replace(/"/g, '""');
            return escaped.includes(',') ? `"${escaped}"` : escaped;
        });
        csv += values.join(',') + '\n';
    });
    
    // Download
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `dhs_budget_dashboard_FY${dashboard.currentFY}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Initialize dashboard when page loads
let dashboard;
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new DashboardManager();
});