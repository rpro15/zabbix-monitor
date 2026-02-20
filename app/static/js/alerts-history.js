/**
 * Alert History View Controller
 * T032: Date range based alert history browser
 * T033: History UI with timeline and state visualization
 * T035: Alert lifecycle visualization
 */

class AlertHistoryView {
    constructor() {
        this.currentPage = 0;
        this.pageSize = 50;
        this.totalAlerts = 0;
        this.selectedAlert = null;
        
        this.initializeDateInputs();
        this.initializeEventListeners();
    }

    /**
     * Initialize date inputs with defaults
     */
    initializeDateInputs() {
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        
        // Default to today
        const fromInput = document.getElementById('history-date-from');
        const toInput = document.getElementById('history-date-to');
        
        fromInput.value = this.formatDateTimeLocal(today);
        toInput.value = this.formatDateTimeLocal(new Date(today.getTime() + 24 * 60 * 60 * 1000));
    }

    /**
     * Format date for datetime-local input
     */
    formatDateTimeLocal(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        
        return `${year}-${month}-${day}T${hours}:${minutes}`;
    }

    /**
     * Initialize event listeners
     */
    initializeEventListeners() {
        // Search button
        document.getElementById('history-filter-btn').addEventListener('click', () => {
            this.currentPage = 0;
            this.loadHistory();
        });

        // Quick filter buttons
        document.getElementById('history-today-btn').addEventListener('click', () => {
            this.applyDateRange('today');
        });

        document.getElementById('history-week-btn').addEventListener('click', () => {
            this.applyDateRange('week');
        });

        document.getElementById('history-month-btn').addEventListener('click', () => {
            this.applyDateRange('month');
        });

        // Pagination
        document.getElementById('history-prev-page-btn').addEventListener('click', () => {
            if (this.currentPage > 0) {
                this.currentPage--;
                this.loadHistory();
            }
        });

        document.getElementById('history-next-page-btn').addEventListener('click', () => {
            if ((this.currentPage + 1) * this.pageSize < this.totalAlerts) {
                this.currentPage++;
                this.loadHistory();
            }
        });

        // Modal
        const modal = document.getElementById('alert-modal');
        document.querySelector('.close-btn').addEventListener('click', () => this.closeModal());
        document.getElementById('close-modal-btn').addEventListener('click', () => this.closeModal());
        document.getElementById('acknowledge-btn').addEventListener('click', () => this.acknowledgeAlert());

        window.addEventListener('click', (event) => {
            if (event.target === modal) {
                this.closeModal();
            }
        });

        // Enter key on date inputs
        document.getElementById('history-date-from').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.loadHistory();
        });
        document.getElementById('history-date-to').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.loadHistory();
        });
    }

    /**
     * Apply quick date range filters
     */
    applyDateRange(range) {
        const now = new Date();
        let from, to;

        if (range === 'today') {
            from = new Date(now.getFullYear(), now.getMonth(), now.getDate());
            to = new Date(from.getTime() + 24 * 60 * 60 * 1000);
        } else if (range === 'week') {
            to = new Date();
            from = new Date(to.getTime() - 7 * 24 * 60 * 60 * 1000);
        } else if (range === 'month') {
            to = new Date();
            from = new Date(to.getTime() - 30 * 24 * 60 * 60 * 1000);
        }

        document.getElementById('history-date-from').value = this.formatDateTimeLocal(from);
        document.getElementById('history-date-to').value = this.formatDateTimeLocal(to);

        this.currentPage = 0;
        this.loadHistory();
    }

    /**
     * Load historical alerts from API
     */
    async loadHistory() {
        const dateFrom = document.getElementById('history-date-from').value;
        const dateTo = document.getElementById('history-date-to').value;

        if (!dateFrom || !dateTo) {
            alert('Please select both date range fields');
            return;
        }

        // Convert to ISO format for API
        const fromIso = new Date(dateFrom).toISOString();
        const toIso = new Date(dateTo).toISOString();

        const skip = this.currentPage * this.pageSize;

        try {
            document.getElementById('history-loading').style.display = 'block';
            document.getElementById('history-list').style.display = 'none';
            document.getElementById('history-no-results').style.display = 'none';
            document.getElementById('history-stats').style.display = 'none';

            const response = await fetch(
                `/api/alerts/history?date_from=${encodeURIComponent(fromIso)}&date_to=${encodeURIComponent(toIso)}&skip=${skip}&limit=${this.pageSize}`
            );

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to load history');
            }

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error || 'Failed to load history');
            }

            this.totalAlerts = result.pagination.total;
            const alerts = result.data;

            if (alerts.length === 0) {
                document.getElementById('history-no-results').style.display = 'block';
            } else {
                this.renderHistoryList(alerts);
                this.updateStats(alerts);
                document.getElementById('history-list').style.display = 'block';
                document.getElementById('history-stats').style.display = 'flex';
            }

            this.updatePagination();
        } catch (error) {
            console.error('Error loading history:', error);
            alert('Error loading alert history: ' + error.message);
        } finally {
            document.getElementById('history-loading').style.display = 'none';
        }
    }

    /**
     * Calculate and display statistics
     */
    updateStats(alerts) {
        let total = this.totalAlerts;
        let critical = 0;
        let high = 0;
        let acknowledged = 0;

        for (const alert of alerts) {
            if (alert.severity === 5 || alert.severity === 4) {
                if (alert.severity === 5) critical++;
                if (alert.severity === 4) high++;
            }
            if (alert.status === 'acknowledged') acknowledged++;
        }

        document.getElementById('history-total').textContent = total;
        document.getElementById('history-critical').textContent = critical;
        document.getElementById('history-high').textContent = high;
        document.getElementById('history-acknowledged').textContent = acknowledged;
    }

    /**
     * Render list of historical alerts
     */
    renderHistoryList(alerts) {
        const listContainer = document.getElementById('history-list');
        
        const html = alerts.map(alert => {
            const severityText = this.getSeverityText(alert.severity);
            const dateTime = new Date(alert.created_at).toLocaleString();
            
            return `
                <div class="history-item alert-item severity-${severityText.class}" data-alert-id="${alert.id}" role="button" tabindex="0">
                    <div class="alert-header">
                        <h4 class="alert-title">${this.escapeHtml(alert.alert_name)}</h4>
                        <span class="severity-badge ${severityText.class}">${severityText.text}</span>
                    </div>
                    <div class="alert-details">
                        <div class="detail-item">
                            <span class="detail-label">Host:</span>
                            <span class="detail-value">${this.escapeHtml(alert.host)}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Status:</span>
                            <span class="detail-value status-${alert.status}">${alert.status.charAt(0).toUpperCase() + alert.status.slice(1)}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Created:</span>
                            <span class="detail-value">${dateTime}</span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        listContainer.innerHTML = html;

        // Add click handlers
        document.querySelectorAll('.history-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const alertId = item.getAttribute('data-alert-id');
                const alert = alerts.find(a => a.id === alertId);
                if (alert) this.showAlertModal(alert);
            });
        });
    }

    /**
     * Show alert detail modal with timeline (T016, T035: Lifecycle visualization)
     */
    async showAlertModal(alert) {
        this.selectedAlert = alert;
        const modalBody = document.getElementById('modal-body');
        const severityText = this.getSeverityText(alert.severity);

        // Fetch alert history for lifecycle timeline (T035)
        const history = await this.fetchAlertHistory(alert.id);
        
        const lifecycle = this.buildLifecycle(alert, history);
        const timelineHtml = lifecycle.map((item, idx) => `
            <div class="timeline-item">
                <div class="timeline-dot status-${item.status}"></div>
                <div class="timeline-content">
                    <strong>${item.status.charAt(0).toUpperCase() + item.status.slice(1)}</strong>
                    ${item.operator ? ` by ${this.escapeHtml(item.operator)}` : ' (System)'}
                    <br>
                    <small>${new Date(item.timestamp).toLocaleString()}</small>
                    ${item.reason ? `<br><em>${this.escapeHtml(item.reason)}</em>` : ''}
                </div>
            </div>
        `).join('');

        const resolvedText = alert.resolved_at 
            ? `<div class="detail-row"><div class="detail-label">Resolved:</div><div class="detail-value">${new Date(alert.resolved_at).toLocaleString()}</div></div>`
            : '';

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
                <div class="detail-value status-${alert.status}">${alert.status.charAt(0).toUpperCase() + alert.status.slice(1)}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Host:</div>
                <div class="detail-value">${this.escapeHtml(alert.host)}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Created:</div>
                <div class="detail-value">${new Date(alert.created_at).toLocaleString()}</div>
            </div>
            ${resolvedText}
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
                    <h3>State Changes Timeline (T035 - Lifecycle Visualization):</h3>
                    <div class="timeline">
                        ${timelineHtml}
                    </div>
                </div>
            ` : ''}
        `;

        // Update acknowledge button
        const ackBtn = document.getElementById('acknowledge-btn');
        ackBtn.disabled = alert.status === 'acknowledged' || alert.status === 'resolved';
        ackBtn.textContent = alert.status === 'acknowledged' ? 'Already Acknowledged' : 'Acknowledge';

        document.getElementById('alert-modal').classList.add('active');
    }

    /**
     * Build lifecycle timeline from alert and history
     * T035: Shows alert lifecycle from creation through acknowledgment and resolution
     */
    buildLifecycle(alert, history) {
        const lifecycle = [];

        // Add creation event
        lifecycle.push({
            status: 'created',
            timestamp: alert.created_at,
            operator: null,
            reason: 'Alert triggered in Zabbix'
        });

        // Add state changes from history
        for (const item of history) {
            lifecycle.push({
                status: item.status_change_to,
                timestamp: item.changed_at,
                operator: item.changed_by,
                reason: item.reason
            });
        }

        // Add resolution if applicable
        if (alert.resolved_at && !history.some(h => h.status_change_to === 'resolved')) {
            lifecycle.push({
                status: 'resolved',
                timestamp: alert.resolved_at,
                operator: null,
                reason: 'Alert resolved in Zabbix'
            });
        }

        return lifecycle.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    }

    /**
     * Fetch timeline history for a specific alert
     */
    async fetchAlertHistory(alertId) {
        try {
            const response = await fetch(`/api/alerts/${alertId}/history`);
            const data = await response.json();
            return data.success ? data.data : [];
        } catch (error) {
            console.error('Error fetching alert history:', error);
            return [];
        }
    }

    /**
     * Acknowledge alert (same as dashboard)
     */
    async acknowledgeAlert() {
        if (!this.selectedAlert) return;

        const reason = prompt('Enter acknowledgment reason (optional):');
        if (reason === null) return;

        const btn = document.getElementById('acknowledge-btn');
        btn.disabled = true;
        btn.textContent = 'Acknowledging...';

        try {
            const response = await fetch(
                `/api/alerts/${this.selectedAlert.id}/acknowledge`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        operator_name: 'Operator',
                        reason: reason || ''
                    })
                }
            );

            if (response.ok) {
                this.showToast('Alert acknowledged successfully', 'success');
                setTimeout(() => {
                    this.closeModal();
                    this.loadHistory();
                }, 2000);
            } else {
                const error = await response.json();
                this.showToast(error.error || 'Failed to acknowledge alert', 'error');
                btn.disabled = false;
                btn.textContent = 'Acknowledge';
            }
        } catch (error) {
            console.error('Error acknowledging alert:', error);
            this.showToast('Error acknowledging alert', 'error');
            btn.disabled = false;
            btn.textContent = 'Acknowledge';
        }
    }

    /**
     * Show toast notification
     */
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideOutRight 0.3s ease forwards';
            setTimeout(() => toast.remove(), 300);
        }, 2000);
    }

    /**
     * Close modal
     */
    closeModal() {
        document.getElementById('alert-modal').classList.remove('active');
        this.selectedAlert = null;
    }

    /**
     * Update pagination controls
     */
    updatePagination() {
        const prevBtn = document.getElementById('history-prev-page-btn');
        const nextBtn = document.getElementById('history-next-page-btn');
        const pageInfo = document.getElementById('history-page-info');

        prevBtn.disabled = this.currentPage === 0;
        nextBtn.disabled = (this.currentPage + 1) * this.pageSize >= this.totalAlerts;

        const fromRecord = this.currentPage * this.pageSize + 1;
        const toRecord = Math.min((this.currentPage + 1) * this.pageSize, this.totalAlerts);
        pageInfo.textContent = `Records ${fromRecord}-${toRecord} of ${this.totalAlerts}`;
    }

    /**
     * Get severity text and class
     */
    getSeverityText(severity) {
        const severityMap = {
            0: { text: 'Not classified', class: 'not-classified' },
            1: { text: 'Information', class: 'information' },
            2: { text: 'Warning', class: 'warning' },
            3: { text: 'Average', class: 'average' },
            4: { text: 'High', class: 'high' },
            5: { text: 'Critical', class: 'critical' }
        };
        return severityMap[severity] || { text: 'Unknown', class: 'unknown' };
    }

    /**
     * Escape HTML special characters
     */
    escapeHtml(text) {
        if (!text) return '';
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

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    window.historyView = new AlertHistoryView();
    window.historyView.loadHistory();
});
