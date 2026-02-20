# Task Breakdown: Add Real-time Zabbix Alert Notifications

**Feature**: 001-realtime-alerts  
**Created**: February 20, 2026  
**Last Updated**: February 20, 2026  
**Total Tasks**: 25  
**Phases**: 7

---

## Phase 1: Setup & Project Initialization

Foundation tasks to establish project structure and dependencies.

### Phase Goal
Set up database models, migrations, and project dependencies required for all user stories.

### Independent Test Criteria
All setup tasks must complete without errors; database schema created; all dependencies installed; APScheduler initialized and running.

- [ ] T001 Create Alert, AlertAcknowledgment, and AlertHistory database models in app/models.py
- [ ] T002 Create database migration scripts (Alembic or SQLAlchemy native) for new tables in app/migrations/
- [ ] T003 [P] Add dependencies (flask-socketio, python-socketio, APScheduler, alembic) to app/requirements.txt
- [ ] T004 Create AlertService class in app/services/alert_service.py with methods for CRUD and status transitions

---

## Phase 2: Foundational & Blocking Prerequisites

Essential infrastructure and services that all user stories depend on.

### Phase Goal
Establish Zabbix API integration, background task scheduler, and core API structure to enable real-time alert operations.

### Independent Test Criteria
ZabbixService successfully connects to Zabbix API; APScheduler task executes without errors; Alert endpoints accept requests; deduplication logic prevents duplicate alerts.

- [ ] T005 [P] Create ZabbixService class in app/services/zabbix_service.py with methods: fetch_new_alerts(), acknowledge_event(), handle_connection_failures()
- [ ] T006 [P] Implement background alert polling task in app/tasks/alert_poller.py scheduled to run every 5 seconds
- [ ] T007 Implement alert deduplication logic (by zabbix_event_id) in AlertService.store_alerts() in app/services/alert_service.py
- [ ] T008 Create Flask blueprint for alert API endpoints in app/api/alerts.py with base route /api/alerts
- [ ] T009 Initialize APScheduler in app/app.py with alert polling task on app startup
- [ ] T010 [P] Create connection state manager in app/services/alert_service.py to track Zabbix API connectivity status

---

## Phase 3: User Story 1 - View Real-time Alerts on Dashboard (Priority: P1)

Core feature: Operators see Zabbix alerts in real-time as they occur.

### Story Goal
Display Zabbix alerts on dashboard immediately upon trigger with severity color-coding, enabling rapid incident response.

### Independent Test Criteria
Can be tested by: (1) Triggering a Zabbix alert, (2) Verifying it appears on dashboard within 2 seconds, (3) Confirming severity color-coding is correct. Delivers: Immediate alert visibility without page refresh.

**Acceptance Scenarios (Automated Tests)**:

1. **Given** Zabbix alert triggered, **When** dashboard page loads, **Then** alert displays within 2 seconds
2. **Given** multiple simultaneous alerts, **When** dashboard loads, **Then** all alerts visible with correct colors
3. **Given** alert displayed, **When** operator clicks alert, **Then** details show (host, name, severity, timestamp)

- [ ] T011 [US1] Implement GET /api/alerts endpoint in app/api/alerts.py to return current alerts as JSON list
- [ ] T012 [P] [US1] Implement WebSocket broadcast in app/app.py when new alert received from Zabbix polling task
- [ ] T013 [P] [US1] Create alerts.html dashboard template in app/templates/alerts.html with alert list layout
- [ ] T014 [US1] Create alerts-dashboard.js WebSocket client in app/static/js/alerts-dashboard.js with real-time update handler
- [ ] T015 [P] [US1] Implement severity color-coding CSS in app/static/css/alerts.css (Critical=Red, High=Orange, Average=Yellow, etc.)
- [ ] T016 [US1] Add alert detail modal/expandable view to show host, name, severity, timestamp in alerts-dashboard.js
- [ ] T017 [US1] Add HTTP polling fallback in alerts-dashboard.js for clients without WebSocket support (5-second interval)

---

## Phase 4: User Story 2 - Acknowledge and Clear Alerts (Priority: P2)

Enable operators to acknowledge alerts and sync acknowledgments to Zabbix.

### Story Goal
Allow operators to mark alerts as handled, preventing duplicate responses and providing visibility into team activity.

### Independent Test Criteria
Can be tested by: (1) Clicking acknowledge on alert, (2) Observing alert status changes to "Acknowledged", (3) Verifying operator name and timestamp displayed, (4) Confirming sync to Zabbix succeeded. Delivers: Clear operational workflow and alert tracking.

**Acceptance Scenarios (Automated Tests)**:

1. **Given** new alert displayed, **When** operator clicks "Acknowledge", **Then** status changes to Acknowledged with visual update
2. **Given** alert acknowledged in app, **When** checking Zabbix, **Then** event is marked acknowledged
3. **Given** operator acknowledges, **When** other operators view, **Then** acknowledgment visible with operator name and timestamp

- [ ] T018 [US2] Implement POST /api/alerts/{alert_id}/acknowledge endpoint in app/api/alerts.py
- [ ] T019 [P] [US2] Create AlertAcknowledgment record creation logic in AlertService.acknowledge_alert() in app/services/alert_service.py
- [ ] T020 [P] [US2] Implement Zabbix sync in ZabbixService.acknowledge_event() in app/services/zabbix_service.py to send acknowledgment back
- [ ] T021 [US2] Update alert model status to "Acknowledged" and record acknowledgment timestamp in app/models.py
- [ ] T022 [US2] Add acknowledge button and status styling to alerts-dashboard.js (grayed out or strikethrough for acknowledged)
- [ ] T023 [P] [US2] Add operator name capture to acknowledge request (from session or auth header) in app/api/alerts.py
- [ ] T024 [US2] Create AlertHistory record for acknowledgment status change in AlertService in app/services/alert_service.py

---

## Phase 5: User Story 3 - Filter and Search Alerts (Priority: P3)

Allow operators to narrow down alerts in high-volume environments.

### Story Goal
Enable filtering by status, severity, and hostname search for operational efficiency in large deployments.

### Independent Test Criteria
Can be tested by: (1) Filtering by severity "Critical Only", (2) Verifying only Critical alerts shown, (3) Searching by hostname, (4) Confirming results match filter. Delivers: Reduced alert noise and faster incident identification.

**Acceptance Scenarios (Automated Tests)**:

1. **Given** multiple alerts with different severities, **When** filter by "High" severity, **Then** only High+ severity alerts shown
2. **Given** alerts from multiple hosts, **When** search hostname, **Then** only matching host alerts visible
3. **Given** mix of statuses, **When** filter "New Alerts Only", **Then** acknowledged and resolved hidden

- [ ] T025 [P] [US3] Add query parameter support to GET /api/alerts in app/api/alerts.py (status, severity, host, search)
- [ ] T026 [P] [US3] Implement filtering logic in AlertService.get_alerts_filtered() in app/services/alert_service.py
- [ ] T027 [US3] Add filter UI controls to alerts.html with dropdown and search input
- [ ] T028 [US3] Implement filter change handler in alerts-dashboard.js to call filtered API and update display
- [ ] T029 [P] [US3] Add database indexes on Alert.status and Alert.severity in app/models.py for performance

---

## Phase 6: User Story 4 - View Alert History (Priority: P4)

Provide historical records for troubleshooting and compliance.

### Story Goal
Enable operators to review past alerts, state transitions, and operator actions for post-incident analysis and audit trail.

### Independent Test Criteria
Can be tested by: (1) Selecting past date range, (2) Viewing historical alerts from that period, (3) Confirming timestamps and state transitions recorded. Delivers: Audit trail and pattern analysis capability.

**Acceptance Scenarios (Automated Tests)**:

1. **Given** "Alert History" page opened, **When** select date range, **Then** all alerts from that period displayed with status at time
2. **Given** historical alert, **When** expand, **Then** lifecycle visible (created, acknowledged, resolved with timestamps and operators)
3. **Given** 1000+ historical alerts, **When** query date range, **Then** results load within 3 seconds

- [ ] T030 [P] [US4] Implement GET /api/alerts/history endpoint in app/api/alerts.py with date_from and date_to parameters
- [ ] T031 [P] [US4] Create history query logic in AlertService.get_alert_history() in app/services/alert_service.py with date range filtering
- [ ] T032 [US4] Create alerts-history.html template with date range picker and history table/timeline view
- [ ] T033 [US4] Implement history UI in alerts-dashboard.js with date picker, API call, and timeline/table rendering
- [ ] T034 [P] [US4] Create database migration to add index on AlertHistory.alert_id and changed_at for performance
- [ ] T035 [US4] Add alert lifecycle visualization (created → acknowledged → resolved) to history view in alerts-dashboard.js

---

## Phase 7: Polish & Cross-Cutting Concerns

Quality, reliability, and user experience enhancements.

### Phase Goal
Implement connection resilience, error handling, performance optimization, and user-facing features for production readiness.

### Independent Test Criteria
Connection failures detected and recovered; UI remains responsive with 1000+ alerts; error messages clear; all performance targets met.

- [ ] T036 [P] Implement connection status indicator in alerts.html showing Zabbix API connectivity (connected/disconnected)
- [ ] T037 [P] Add automatic reconnection logic with exponential backoff in ZabbixService in app/services/zabbix_service.py
- [ ] T038 [P] Implement alert queuing/buffering during Zabbix API downtime in AlertService in app/services/alert_service.py
- [ ] T039 Implement error boundary and error toast/notification UI in alerts-dashboard.js for API failures
- [ ] T040 [P] Add pagination/virtual scrolling for 1000+ alerts in alerts-dashboard.js (load 50 at a time, lazy load on scroll)
- [ ] T041 [P] Create comprehensive error handling for edge cases: duplicate alerts, state conflicts, null fields
- [ ] T042 Add logging and monitoring: all API call, database operation, and error logs to structured logger
- [ ] T043 Create unit tests for AlertService deduplication, status transitions, and filtering logic
- [ ] T044 Create integration tests for Zabbix polling, acknowledgment sync, and WebSocket updates
- [ ] T045 [P] Performance testing: verify <2s end-to-end latency, 99.9% delivery rate, handle 100 concurrent streams

---

## Dependencies & Sequencing

### Critical Path (Must Complete in Order)
1. **Setup Phase (T001-T004)**: All dependent on these
2. **Foundational Phase (T005-T010)**: Required before any user story work
3. **US1 (T011-T017)**: Can start in parallel with Foundational completion
4. **US2 (T018-T024)**: Depends on US1 backend (T011, T012) but UI can start after T013
5. **US3 (T025-T029)**: Can start as T024 completes
6. **US4 (T030-T035)**: Can start in parallel with US3
7. **Polish (T036-T045)**: Can start after T017 (first frontend), refinement throughout

### Parallel Execution Opportunities

**After Phase 1 Complete**: T005, T006, T008, T009, T010 can run in parallel

**After Phase 2 Complete**: 
- T011-T017 (US1 backend + UI)
- T018-T024 (US2, but T019-T020 can wait for T011-T012)
- T025-T029 (US3, but T026 waits for T011)

**Final Polish**: T036-T045 can largely run in parallel, with T043-T044 (testing) depending on implementation completion

### MVP Release Scope
**Recommended**: Phase 1 + Phase 2 + Phase 3 (P1)
- Provides core value: Real-time alert visibility
- Unblocks operationss with immediate incident alerts
- Estimated effort: 3-4 weeks

**Phase 2 Release**: Add Phase 4 (P2 - Acknowledgment)
- Complete operational workflow
- Estimated effort: +2 weeks

**Phase 3 Release**: Add Phase 5 (P3 - Filtering)
- Handle high-volume production environments
- Estimated effort: +1 week

**Post-1.0**: Add Phase 6 (P4 - History) and Phase 7 (Polish)
- Audit trail and analytics
- Performance hardening

---

## Testing Strategy

### Unit Tests (Per Task)
- T007: Deduplication logic (same event_id should not create duplicate)
- T019: AlertService acknowledgment creates correct record
- T026: Filter logic returns correct subset of alerts

### Integration Tests (Phase Level)
- Phase 2: Zabbix API connection and polling
- Phase 3: End-to-end alert ingestion and WebSocket broadcast
- Phase 4: Acknowledgment flow (app → Zabbix sync)
- Phase 5: Filtering and search accuracy

### End-to-End Tests (User Story)
- US1: Trigger Zabbix alert → appears on dashboard within 2s
- US2: Acknowledge alert → status changes → reflected in Zabbix
- US3: Filter by severity → correct subset displayed
- US4: Query history by date → correct alerts returned with state transitions

### Performance Tests
- 1000 concurrent alerts: UI remains responsive
- 100 alerts/second ingestion: No drops or delays
- 2-second latency: Zabbix trigger → dashboard display

---

## Success Metrics

- **Code Coverage**: Minimum 80% for services, 60% for API endpoints
- **All Acceptance Scenarios**: 100% passing
- **All Success Criteria**: 100% met (latency, reliability, performance)
- **Zero Data Loss**: No alerts lost under normal operation or recovery scenarios
- **User Feedback**: 95% of test operators find feature valuable

