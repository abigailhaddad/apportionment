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
        this.currentFY = '2025';
        this.compareFY = null;
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
        document.getElementById('fiscalYear').addEventListener('change', (e) => {
            this.currentFY = e.target.value;
            this.renderDashboard();
        });
        
        document.getElementById('compareYear').addEventListener('change', (e) => {
            this.compareFY = e.target.value || null;
            this.renderDashboard();
        });
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
            const response = await fetch(path);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
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
        
        recentActions.forEach(action => {
            const date = new Date(action.approval_date);
            const formattedDate = date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
            });
            
            html += `
                <div class="apportionment-card">
                    <div class="apportionment-header">
                        <span class="apportionment-date">${formattedDate}</span>
                        <span class="apportionment-amount">${formatCurrency(action.amount)}</span>
                    </div>
                    <div class="apportionment-details">
                        <div class="component-name">${action.component}</div>
                        <div class="account-name">${action.account}</div>
                        <div class="funds-source">Source: ${action.funds_source}</div>
                        <div class="approver">Approved by: ${action.approver}</div>
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
    
    // Spending Lifecycle Section
    renderSpendingLifecycle() {
        const container = document.getElementById('spendingLifecycle');
        
        if (!this.data.spendingLifecycle) {
            container.innerHTML = '<h2>Spending Lifecycle</h2><div class="error">Failed to load spending lifecycle data</div>';
            return;
        }
        
        // Filter by current FY and sort by appropriations
        const lifecycleData = this.data.spendingLifecycle
            .filter(d => d.fiscal_year == this.currentFY)
            .sort((a, b) => b.appropriations - a.appropriations)
            .slice(0, 10); // Top 10 components
        
        // Clear and set up
        container.innerHTML = '<h2>Spending Lifecycle: Appropriations → Obligations → Outlays</h2>';
        
        const chartContainer = document.createElement('div');
        chartContainer.className = 'chart-container';
        chartContainer.id = 'lifecycleChart';
        container.appendChild(chartContainer);
        
        this.createLifecycleChart(chartContainer, lifecycleData);
        
        // Get data currency info
        const apportionmentDate = this.data.metadata?.max_approval_date ? 
            new Date(this.data.metadata.max_approval_date).toLocaleDateString('en-US', {
                month: 'long',
                day: 'numeric',
                year: 'numeric'
            }) : 'current';
            
        // Add legend and notes
        container.innerHTML += `
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background: #28a745;"></div>
                    <span>Outlays (Paid)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #ffc107;"></div>
                    <span>Obligated (Committed)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #6c757d;"></div>
                    <span>Unobligated (Available)</span>
                </div>
            </div>
            <div class="alert" style="margin-top: 15px;">
                <strong>Data Currency:</strong><br>
                • Appropriations data: Current through ${apportionmentDate}<br>
                • Obligations & Outlays: FY2025 through June (Q3), FY2022-2024 complete
            </div>
            <div class="data-note">
                Bar height shows total appropriation amount. Segments show spending status.
            </div>
        `;
    }
    
    createLifecycleChart(container, data) {
        const margin = { top: 20, right: 20, bottom: 120, left: 200 };
        const width = container.clientWidth - margin.left - margin.right;
        const height = 500 - margin.top - margin.bottom;
        
        const svg = d3.select(container)
            .append('svg')
            .attr('width', width + margin.left + margin.right)
            .attr('height', height + margin.top + margin.bottom);
        
        const g = svg.append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);
        
        // Calculate percentages and prepare data
        data.forEach(d => {
            d.outlayPercent = d.appropriations > 0 ? (d.outlays / d.appropriations) * 100 : 0;
            d.obligatedPercent = d.appropriations > 0 ? ((d.obligations - d.outlays) / d.appropriations) * 100 : 0;
            d.unobligatedPercent = d.appropriations > 0 ? 
                ((d.appropriations - d.obligations) / d.appropriations) * 100 : 0;
        });
        
        // Scales
        const y = d3.scaleBand()
            .domain(data.map(d => d.component))
            .range([0, height])
            .padding(0.2);
        
        const x = d3.scaleLinear()
            .domain([0, 100])
            .range([0, width]);
        
        const heightScale = d3.scaleLinear()
            .domain([0, d3.max(data, d => d.appropriations)])
            .range([5, y.bandwidth()]); // Min 5px height for visibility
        
        // Create bars
        const bars = g.selectAll('.component-bar')
            .data(data)
            .enter().append('g')
            .attr('class', 'component-bar')
            .attr('transform', d => `translate(0, ${y(d.component) + (y.bandwidth() - heightScale(d.appropriations)) / 2})`);
        
        // Outlays (green)
        bars.append('rect')
            .attr('class', 'outlay-bar')
            .attr('x', 0)
            .attr('y', 0)
            .attr('width', d => x(d.outlayPercent))
            .attr('height', d => heightScale(d.appropriations))
            .attr('fill', '#28a745');
        
        // Obligated but not outlayed (yellow)
        bars.append('rect')
            .attr('class', 'obligated-bar')
            .attr('x', d => x(d.outlayPercent))
            .attr('y', 0)
            .attr('width', d => x(d.obligatedPercent))
            .attr('height', d => heightScale(d.appropriations))
            .attr('fill', '#ffc107');
        
        // Unobligated (gray)
        bars.append('rect')
            .attr('class', 'unobligated-bar')
            .attr('x', d => x(d.outlayPercent + d.obligatedPercent))
            .attr('y', 0)
            .attr('width', d => x(d.unobligatedPercent))
            .attr('height', d => heightScale(d.appropriations))
            .attr('fill', '#6c757d');
        
        // Add percentage labels
        bars.each(function(d) {
            const bar = d3.select(this);
            
            // Only show labels if segment is wide enough
            if (d.outlayPercent > 5) {
                bar.append('text')
                    .attr('x', x(d.outlayPercent / 2))
                    .attr('y', heightScale(d.appropriations) / 2)
                    .attr('dy', '.35em')
                    .attr('text-anchor', 'middle')
                    .text(`${d.outlayPercent.toFixed(0)}%`)
                    .style('fill', 'white')
                    .style('font-size', '12px');
            }
            
            if (d.obligatedPercent > 5) {
                bar.append('text')
                    .attr('x', x(d.outlayPercent + d.obligatedPercent / 2))
                    .attr('y', heightScale(d.appropriations) / 2)
                    .attr('dy', '.35em')
                    .attr('text-anchor', 'middle')
                    .text(`${d.obligatedPercent.toFixed(0)}%`)
                    .style('fill', 'black')
                    .style('font-size', '12px');
            }
        });
        
        // Add axes
        g.append('g')
            .attr('class', 'axis')
            .call(d3.axisLeft(y).tickFormat(d => getComponentName(d, 'label')));
        
        g.append('g')
            .attr('class', 'axis')
            .attr('transform', `translate(0,${height})`)
            .call(d3.axisBottom(x).tickFormat(d => d + '%'));
        
        // Add amount labels on the right
        g.selectAll('.amount-label')
            .data(data)
            .enter().append('text')
            .attr('x', width + 5)
            .attr('y', d => y(d.component) + y.bandwidth() / 2)
            .attr('dy', '.35em')
            .text(d => formatCurrency(d.appropriations, true))
            .style('font-size', '12px')
            .style('fill', '#666');
        
        // Add tooltips
        const tooltip = d3.select('body').append('div')
            .attr('class', 'tooltip')
            .style('opacity', 0);
        
        bars.on('mouseover', function(event, d) {
            tooltip.transition().duration(200).style('opacity', .9);
            tooltip.html(`
                <strong>${d.component}</strong><br>
                Appropriations: ${formatCurrency(d.appropriations)}<br>
                Obligations: ${formatCurrency(d.obligations)} (${d.outlayPercent.toFixed(1) + d.obligatedPercent.toFixed(1)}%)<br>
                Outlays: ${formatCurrency(d.outlays)} (${d.outlayPercent.toFixed(1)}%)<br>
                Unobligated: ${formatCurrency(d.appropriations - d.obligations)} (${d.unobligatedPercent.toFixed(1)}%)
            `)
            .style('left', (event.pageX + 10) + 'px')
            .style('top', (event.pageY - 28) + 'px');
        })
        .on('mouseout', function(d) {
            tooltip.transition().duration(500).style('opacity', 0);
        });
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
            <div id="yearOverYearControls" style="margin-bottom: 20px;">
                <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                    <div style="flex: 1; min-width: 300px;">
                        <label style="display: block; font-weight: bold; margin-bottom: 5px;">Components:</label>
                        <div id="componentFilters" style="max-height: 200px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; border-radius: 4px;">
                            <!-- Component checkboxes will be added here -->
                        </div>
                        <div style="margin-top: 5px;">
                            <button onclick="dashboard.selectAllComponents()">Select All</button>
                            <button onclick="dashboard.clearAllComponents()">Clear All</button>
                        </div>
                    </div>
                    <div style="flex: 1; min-width: 300px;">
                        <label style="display: block; font-weight: bold; margin-bottom: 5px;">Spending Types:</label>
                        <div id="spendingTypeFilters" style="border: 1px solid #ddd; padding: 10px; border-radius: 4px;">
                            <!-- Spending type checkboxes will be added here -->
                        </div>
                        <div style="margin-top: 5px;">
                            <button onclick="dashboard.selectAllSpendingTypes()">Select All</button>
                            <button onclick="dashboard.clearAllSpendingTypes()">Clear All</button>
                        </div>
                    </div>
                </div>
            </div>
            <div id="yearOverYearChart"></div>
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
        this.data.monthlyTrends.components.forEach(component => {
            const checkbox = document.createElement('div');
            checkbox.innerHTML = `
                <label style="display: block; padding: 2px 0; cursor: pointer;">
                    <input type="checkbox" value="${component}" onchange="dashboard.updateYearOverYear()" 
                           style="margin-right: 5px;" checked>
                    ${component}
                </label>
            `;
            componentFilters.appendChild(checkbox);
            this.selectedComponents.add(component);
        });
        
        // Create spending type filters  
        const spendingTypeFilters = document.getElementById('spendingTypeFilters');
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
    }
    
    clearAllComponents() {
        document.querySelectorAll('#componentFilters input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });
        this.selectedComponents.clear();
        this.updateYearOverYear();
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
    }
    
    renderYearOverYearChart() {
        const container = document.getElementById('yearOverYearChart');
        container.innerHTML = '';
        
        if (!this.data.monthlyTrends || !this.data.monthlyTrends.monthly) {
            container.innerHTML = '<div class="error">No monthly data available</div>';
            return;
        }
        
        // Filter and aggregate data based on selected components
        const monthlyData = this.data.monthlyTrends.monthly.map(month => {
            let appropriations = 0;
            let outlays = 0;
            
            // Sum only selected components
            this.selectedComponents.forEach(component => {
                appropriations += month.appropriations_by_component[component] || 0;
                outlays += month.outlays_by_component[component] || 0;
            });
            
            return {
                date: new Date(month.date + '-01'),
                appropriations,
                outlays
            };
        });
        
        this.createMonthlyTrendChart(container, monthlyData);
    }
    
    createMonthlyTrendChart(container, monthlyData) {
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
        const x = d3.scaleTime()
            .domain(d3.extent(monthlyData, d => d.date))
            .range([0, width]);
            
        const y = d3.scaleLinear()
            .domain([0, d3.max(monthlyData, d => Math.max(d.appropriations, d.outlays))])
            .range([height, 0]);
        
        // Line generators
        const lineAppr = d3.line()
            .x(d => x(d.date))
            .y(d => y(d.appropriations))
            .curve(d3.curveMonotoneX);
            
        const lineOutlay = d3.line()
            .x(d => x(d.date))
            .y(d => y(d.outlays))
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
            {name: 'Outlays', line: lineOutlay, color: '#2ca02c', data: monthlyData}
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
        const tooltip = d3.select('body').append('div')
            .attr('class', 'tooltip')
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
                        Outlays: ${formatCurrency(d.outlays)}
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
                <strong>Note:</strong> Appropriations show actual apportionment dates. 
                Outlays are distributed evenly across fiscal year months (actual monthly data not available).
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