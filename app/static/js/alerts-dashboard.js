/**
 * Real-time Alert Dashboard - JavaScript
 * T014: WebSocket client for real-time updates
 * T016: Alert detail modal functionality
 * T017: HTTP polling fallback for non-WebSocket browsers
 */

class AlertDashboard {
    constructor() {
        this.alerts = [];
        this.currentPage = 0;
        this.pageSize = 50;
        this.totalAlerts = 0;
        this.socket = null;
        this.useWebSocket = true;
        this.pollingInterval = 5000; // Fallback polling interval (ms)
        this.pollingTimer = null;
        this.filters = {
            status: null,
            severity: null,
            host: null,
            search: null
        };
        this.selectedAlert = null;
        this.pollCount = 0;

        this.initializeUI();
        this.initializeWebSocket();
        this.loadAlerts();
    }

    /**
     * Initialize UI event listeners
     */
    initializeUI() {
        // Filter buttons
        document.getElementById('filter-btn').addEventListener('click', () => {
            this.applyFilters();
        });

        document.getElementById('clear-filters-btn').addEventListener('click', () => {
            this.clearFilters();
        });

        // Filter inputs (Enter key)
        document.getElementById('filter-status').addEventListener('change', () => this.applyFilters());
        document.getElementById('filter-severity').addEventListener('change', () => this.applyFilters());
        document.getElementById('filter-host').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.applyFilters();
        });
        document.getElementById('filter-search').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.applyFilters();
        });

        // Pagination
        document.getElementById('prev-page-btn').addEventListener('click', () => {
            if (this.currentPage > 0) {
                this.currentPage--;
                this.renderAlerts();
            }
        });

        document.getElementById('next-page-btn').addEventListener('click', () => {
            if ((this.currentPage + 1) * this.pageSize < this.totalAlerts) {
                this.currentPage++;
                this.renderAlerts();
            }
        });

        // Modal
        const modal = document.getElementById('alert-modal');
        document.querySelector('.close-btn').addEventListener('click', () => this.closeModal());
        document.getElementById('close-modal-btn').addEventListener('click', () => this.closeModal());
        document.getElementById('acknowledge-btn').addEventListener('click', () => this.acknowledgeAlert());

        // Close modal when clicking outside
        window.addEventListener('click', (event) => {
            if (event.target === modal) {
                this.closeModal();
            }
        });
    }

    /**
     * Initialize WebSocket connection (T014: WebSocket client)
     */
    initializeWebSocket() {
        try {
            // Connect to WebSocket server
            this.socket = io(window.location.origin, {
                reconnection: true,
                reconnectionDelay: 1000,
                reconnectionDelayMax: 5000,
                reconnectionAttempts: 5
            });

            // WebSocket Event Handlers
            this.socket.on('connect', () => {
                console.log('WebSocket connected');
                this.useWebSocket = true;
                this.updateConnectionStatus(true);
                if (this.pollingTimer) clearInterval(this.pollingTimer);
            });

            this.socket.on('disconnect', () => {
                console.log('WebSocket disconnected, falling back to HTTP polling');
                this.useWebSocket = false;
                this.updateConnectionStatus(false);
                this.startHTTPPolling();
            });

            // Listen for new alerts from server
            this.socket.on('new_alerts_batch', (data) => {
                console.log(`Received ${data.created} new alerts via WebSocket`);
                // Refresh alert list when new alerts arrive
                if (data.created > 0) {
                    this.loadAlerts();
                }
            });

            // Listen for connection status updates
            this.socket.on('connection_status', (status) => {
                console.log('Connection status update:', status);
                this.updateConnectionStatus(status.is_connected);
            });

            // Listen for connection errors
            this.socket.on('connection_error', (data) => {
                console.error('Zabbix connection error:', data.error);
                // Could show toast notification here
            });

            // Listen for alert acknowledgments from other operators
            this.socket.on('alert_acknowledged', (data) => {
                console.log(`Alert ${data.alert_id} acknowledged by ${data.operator_name}`);
                // Refresh alert list to reflect new acknowledgment
                this.loadAlerts();
            });

        } catch (error) {
            console.error('Failed to initialize WebSocket:', error);
            this.useWebSocket = false;
            this.startHTTPPolling();
        }
    }

    /**
     * T017: HTTP Polling Fallback for non-WebSocket browsers
     */
    startHTTPPolling() {
        if (this.pollingTimer) return;

        console.log('Starting HTTP polling fallback');
        this.pollingTimer = setInterval(() => {
            this.loadAlerts();
        }, this.pollingInterval);
    }

    /**
     * Apply filters to alert list
     */
    applyFilters() {
        this.filters.status = document.getElementById('filter-status').value || null;
        this.filters.severity = document.getElementById('filter-severity').value || null;
        this.filters.host = document.getElementById('filter-host').value || null;
        this.filters.search = document.getElementById('filter-search').value || null;
        
        this.currentPage = 0; // Reset to first page
        this.loadAlerts();
    }

    /**
     * Clear all filters
     */
    clearFilters() {
        this.filters = { status: null, severity: null, host: null, search: null };
        document.getElementById('filter-status').value = '';
        document.getElementById('filter-severity').value = '';
        document.getElementById('filter-host').value = '';
        document.getElementById('filter-search').value = '';
        
        this.currentPage = 0; // Reset to first page
        this.loadAlerts();
    }

    /**
     * Load alerts from API with current filters
     */
    loadAlerts() {
        const params = new URLSearchParams({
            skip: this.currentPage * this.pageSize,
            limit: this.pageSize
        });

        if (this.filters.status) params.append('status', this.filters.status);
        if (this.filters.severity) params.append('severity', this.filters.severity);
        if (this.filters.host) params.append('host', this.filters.host);
        if (this.filters.search) params.append('search', this.filters.search);

        fetch(`/api/alerts?${params}`)
            .then(response => {
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    this.alerts = data.data;
                    this.totalAlerts = data.pagination.total;
                    this.pollCount++;
                    this.renderAlerts();
                    this.updateStats();
                }
            })
            .catch(error => console.error('Error loading alerts:', error));
    }

    /**
     * Render alerts to the DOM
     */
    renderAlerts() {
        const alertsList = document.getElementById('alerts-list');
        const loadingMsg = document.getElementById('loading-indicator');
        const emptyMsg = document.getElementById('no-alerts-message');
        const pageInfo = document.getElementById('page-info');
        const prevBtn = document.getElementById('prev-page-btn');
        const nextBtn = document.getElementById('next-page-btn');

        loadingMsg.style.display = 'none';
        emptyMsg.style.display = 'none';

        if (this.alerts.length === 0) {
            alertsList.innerHTML = '';
            emptyMsg.style.display = 'block';
        } else {
            alertsList.innerHTML = this.alerts.map(alert => this.createAlertElement(alert)).join('');

            // Add click handlers for modal
            document.querySelectorAll('.alert-item').forEach(elem => {
                elem.addEventListener('click', () => {
                    const alertId = elem.dataset.alertId;
                    const alert = this.alerts.find(a => a.id === alertId);
                    if (alert) this.showAlertModal(alert);
                });
            });
        }

        // Update pagination
        pageInfo.textContent = `Page ${this.currentPage + 1} of ${Math.ceil(this.totalAlerts / this.pageSize) || 1}`;
        prevBtn.disabled = this.currentPage === 0;
        nextBtn.disabled = (this.currentPage + 1) * this.pageSize >= this.totalAlerts;
    }

    /**
     * Create HTML element for single alert
     */
    createAlertElement(alert) {
        const severityClass = `severity-${alert.severity}`;
        const severityText = this.getSeverityText(alert.severity);
        const statusClass = `status-badge ${alert.status}`;
        const alertTimestamp = new Date(alert.created_at).toLocaleString();

        return `
            <div class="alert-item ${severityClass}" data-alert-id="${alert.id}">
                <div>
                    <span class="severity-badge ${severityText.class}">${severityText.text}</span>
                </div>
                <div class="alert-info">
                    <div class="alert-title">${this.escapeHtml(alert.alert_name)}</div>
                    <div class="alert-host"><strong>Host:</strong> ${this.escapeHtml(alert.host)}</div>
                    <div class="alert-time">${alertTimestamp}</div>
                </div>
                <span class="${statusClass}">${alert.status}</span>
                <span class="status-badge" style="cursor: pointer; background-color: #e0e0e0; color: #333;">
                    → View Details
                </span>
            </div>
        `;
    }

    /**
     * Get severity level text and CSS class
     */
    getSeverityText(severity) {
        const levels = {
            0: { text: 'Not Classified', class: 'not-classified' },
            1: { text: 'Information', class: 'information' },
            2: { text: 'Warning', class: 'warning' },
            3: { text: 'Average', class: 'average' },
            4: { text: 'High', class: 'high' },
            5: { text: 'Critical', class: 'critical' }
        };
        return levels[severity] || levels[0];
    }

    /**
     * T016: Show alert detail modal
     */
    showAlertModal(alert) {
        this.selectedAlert = alert;
        const modalBody = document.getElementById('modal-body');
        const severityText = this.getSeverityText(alert.severity);

        // Fetch alert history for timeline
        this.fetchAlertHistory(alert.id).then(history => {
            const timelineHtml = history.map(item => `
                <div class="timeline-item">
                    <div class="timeline-dot"></div>
                    <div>
                        <strong>${item.status_change_to}</strong> by ${item.changed_by}
                        <br><small>${new Date(item.changed_at).toLocaleString()}</small>
                    </div>
                </div>
            `).join('');

            modalBody.innerHTML = `
                <h2>${this.escapeHtml(alert.alert_name)}</h2>
                <div class="detail-row">
                    <div class="detail-label">Severity:</div>
                    <div class="detail-value">
                        <span class="severity-badge ${severityText.class}">${severityText.text}</span>
                    </div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Status:</div>
                    <div class="detail-value">${alert.status}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Host:</div>
                    <div class="detail-value">${this.escapeHtml(alert.host)}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Created:</div>
                    <div class="detail-value">${new Date(alert.created_at).toLocaleString()}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Event ID:</div>
                    <div class="detail-value">${alert.zabbix_event_id}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Problem ID:</div>
                    <div class="detail-value">${alert.zabbix_problem_id || 'N/A'}</div>
                </div>
                ${history.length > 0 ? `
                    <div class="alert-timeline">
                        <h3>Timeline:</h3>
                        ${timelineHtml}
                    </div>
                ` : ''}
            `;
        });

        // Update acknowledge button based on status
        const ackBtn = document.getElementById('acknowledge-btn');
        ackBtn.disabled = alert.status === 'acknowledged' || alert.status === 'resolved';
        ackBtn.textContent = alert.status === 'acknowledged' ? 'Already Acknowledged' : 'Acknowledge';

        // Show modal
        document.getElementById('alert-modal').classList.add('active');
    }

    /**
     * Fetch alert history (for timeline in modal)
     */
    fetchAlertHistory(alertId) {
        return fetch(`/api/alerts/${alertId}/history`)
            .then(response => response.json())
            .then(data => data.success ? data.data : [])
            .catch(error => {
                console.error('Error fetching alert history:', error);
                return [];
            });
    }

    /**
     * Close alert detail modal
     */
    closeModal() {
        document.getElementById('alert-modal').classList.remove('active');
        this.selectedAlert = null;
    }

    /**
     * Acknowledge alert
     */
    acknowledgeAlert() {
        if (!this.selectedAlert) return;

        // Already acknowledged
        if (this.selectedAlert.status === 'acknowledged' || this.selectedAlert.status === 'resolved') {
            alert('Alert is already ' + this.selectedAlert.status);
            return;
        }

        const reason = prompt('Enter acknowledgment reason (optional):');
        if (reason === null) return; // User cancelled

        const ackBtn = document.getElementById('acknowledge-btn');
        ackBtn.disabled = true;
        ackBtn.textContent = 'Acknowledging...';

        fetch(`/api/alerts/${this.selectedAlert.id}/acknowledge`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                operator_name: 'Web User', // TODO: get from session/auth
                reason: reason || ''
            })
        })
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            if (data.success) {
                console.log('Alert acknowledged successfully');
                // Update the selected alert with new status
                this.selectedAlert.status = 'acknowledged';
                
                // Show success message
                const successMsg = document.createElement('div');
                successMsg.style.cssText = `
                    position: fixed; top: 20px; right: 20px;
                    background: #4caf50; color: white;
                    padding: 15px 20px; border-radius: 4px;
                    font-weight: 500; z-index: 2000;
                    animation: slideInRight 0.3s ease;
                `;
                successMsg.textContent = 'Alert acknowledged successfully!';
                document.body.appendChild(successMsg);
                
                // Auto-remove message
                setTimeout(() => {
                    successMsg.remove();
                    this.closeModal();
                    this.loadAlerts(); // Refresh list
                }, 2000);
            } else {
                throw new Error(data.error || 'Failed to acknowledge alert');
            }
        })
        .catch(error => {
            console.error('Error acknowledging alert:', error);
            alert('Failed to acknowledge alert: ' + error.message);
            ackBtn.disabled = false;
            ackBtn.textContent = 'Acknowledge';
        });
    }

    /**
     * Update connection status indicator
     */
    updateConnectionStatus(connected) {
        const statusDot = document.getElementById('connection-status');
        const statusText = document.getElementById('connection-text');

        if (connected) {
            statusDot.classList.remove('disconnected');
            statusDot.classList.add('connected');
            statusText.textContent = 'Connected';
        } else {
            statusDot.classList.remove('connected');
            statusDot.classList.add('disconnected');
            statusText.textContent = 'Disconnected (Polling)';
        }
    }

    /**
     * Update dashboard statistics
     */
    updateStats() {
        document.getElementById('alert-count').textContent = `${this.totalAlerts} alerts`;
        document.getElementById('poll-count').textContent = `${this.pollCount} polls`;
    }

    /**
     * Escape HTML special characters
     */
    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const dashboard = new AlertDashboard();
    // Make dashboard globally accessible for debugging
    window.alertDashboard = dashboard;
});
