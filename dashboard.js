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
        const [appropriations, appropriationsSummary, spendingSummary, vendorSummary, metadata] = await Promise.all([
            this.loadJSON('processed_data/appropriations/dhs_budget_flat.json'),
            this.loadJSON('processed_data/dashboard/appropriations_summary.json'),
            this.loadJSON('processed_data/dashboard/spending_summary.json'), 
            this.loadJSON('processed_data/dashboard/vendor_summary.json'),
            this.loadJSON('processed_data/appropriations/update_metadata.json')
        ]);
        
        this.data = {
            appropriations: appropriations.data || appropriations,
            appropriationsSummary,
            spendingSummary,
            vendorSummary,
            metadata
        };
        
        console.log('Data loaded:', {
            appropriations: this.data.appropriations.length,
            appropriationsSummary: this.data.appropriationsSummary ? 'loaded' : 'missing',
            spendingSummary: this.data.spendingSummary ? 'loaded' : 'missing',
            vendorSummary: this.data.vendorSummary ? 'loaded' : 'missing'
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
        this.renderSpendingTrends();
        this.renderWhereMoneyGoes();
    }
    
    // Recent Apportionments Section
    renderRecentApportionments() {
        const container = document.getElementById('recentApportionments');
        const content = container.querySelector('.loading') || container;
        
        if (!this.data.appropriations) {
            content.innerHTML = '<div class="error">Failed to load appropriations data</div>';
            return;
        }
        
        // Filter to current FY
        const currentData = this.data.appropriations.filter(d => d.fiscal_year == this.currentFY);
        
        // Group by component and sum
        const byComponent = d3.rollup(
            currentData,
            v => d3.sum(v, d => d.amount),
            d => d.component
        );
        
        // Sort by amount
        const sortedComponents = Array.from(byComponent, ([component, amount]) => ({ component, amount }))
            .sort((a, b) => b.amount - a.amount);
        
        // Calculate totals
        const totalAmount = d3.sum(sortedComponents, d => d.amount);
        
        // Get latest approval date from metadata
        const latestDate = this.data.metadata?.max_approval_date ? 
            new Date(this.data.metadata.max_approval_date).toLocaleDateString('en-US', {
                month: 'long',
                day: 'numeric',
                year: 'numeric'
            }) : 'Unknown';
        
        let html = `
            <div class="alert">
                Latest apportionment data as of ${latestDate}
            </div>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">${formatCurrency(totalAmount)}</div>
                    <div class="metric-label">Total FY ${this.currentFY} Appropriations</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${sortedComponents.length}</div>
                    <div class="metric-label">Components Funded</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${formatCurrency(sortedComponents[0]?.amount || 0)}</div>
                    <div class="metric-label">Largest Component (${getComponentName(sortedComponents[0]?.component, 'label')})</div>
                </div>
            </div>
            
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Component</th>
                            <th class="amount">FY ${this.currentFY} Amount</th>
                            <th class="percent">% of Total</th>
        `;
        
        // Add comparison column if selected
        if (this.compareFY) {
            html += `
                            <th class="amount">FY ${this.compareFY} Amount</th>
                            <th class="percent">Change</th>
            `;
        }
        
        html += `
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        // Add rows for each component
        sortedComponents.slice(0, 15).forEach(({ component, amount }) => {
            const percent = (amount / totalAmount * 100).toFixed(1);
            
            html += `
                        <tr>
                            <td class="component-name">${component}</td>
                            <td class="amount">${formatCurrency(amount)}</td>
                            <td class="percent">${percent}%</td>
            `;
            
            if (this.compareFY) {
                const compareData = this.data.appropriations.filter(
                    d => d.fiscal_year == this.compareFY && d.component === component
                );
                const compareAmount = d3.sum(compareData, d => d.amount);
                const change = compareAmount > 0 ? ((amount - compareAmount) / compareAmount * 100) : 0;
                const changeClass = change > 0 ? 'positive' : change < 0 ? 'negative' : '';
                
                html += `
                            <td class="amount">${formatCurrency(compareAmount)}</td>
                            <td class="percent ${changeClass}">${change > 0 ? '+' : ''}${change.toFixed(1)}%</td>
                `;
            }
            
            html += `
                        </tr>
            `;
        });
        
        html += `
                    </tbody>
                </table>
            </div>
            
            <div class="data-note">
                Showing top 15 components by appropriation amount. 
                <a href="appropriations_detail.html">View full detail →</a>
            </div>
        `;
        
        container.innerHTML = `<h2>Recent Apportionments</h2>` + html;
    }
    
    // Spending Trends Section
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

// Global functions for button clicks
function switchTrendView(view) {
    document.querySelectorAll('#spendingTrends .tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event.target.classList.add('active');
    
    dashboard.currentTrendView = view;
    dashboard.renderSpendingTrends();
}

function switchMoneyView(view) {
    document.querySelectorAll('#whereMoneyGoes .tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event.target.classList.add('active');
    
    dashboard.currentMoneyView = view;
    dashboard.renderWhereMoneyGoes();
}

function downloadData() {
    // Create a combined dataset for download
    const data = [];
    
    // Add appropriations data
    if (dashboard.data.appropriations) {
        dashboard.data.appropriations
            .filter(d => d.fiscal_year == dashboard.currentFY)
            .forEach(row => {
                data.push({
                    type: 'Appropriation',
                    fiscal_year: row.fiscal_year,
                    component: row.component,
                    account: row.account || '',
                    category: row.availability_type || '',
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