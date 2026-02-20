# Implementation Plan: Add Real-time Zabbix Alert Notifications

**Feature Branch**: `001-realtime-alerts`  
**Created**: February 20, 2026  
**Status**: Ready for Implementation

## Technology Stack & Architecture

### Existing Stack
- **Backend**: Flask 2.3.3 (Python web framework)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Zabbix Integration**: py-zabbix 1.1.7 (Zabbix API client)
- **Server**: Gunicorn WSGI
- **Deployment**: Docker Compose

### New Components Required
- **Real-time Communication**: Flask-SocketIO (WebSocket with fallback polling)
- **Background Tasks**: APScheduler (for periodic Zabbix polling) OR Celery (for distributed task queue)
- **Frontend**: Vanilla JavaScript + WebSockets (extend existing dashboard)
- **Database Migrations**: Alembic or SQLAlchemy native migrations

### Recommended Architecture Decision
**Polling-based approach** (initially simpler than streaming):
- APScheduler runs background task every 1-5 seconds
- Polls Zabbix API for new/changed alerts (events)
- Stores in local database
- WebSocket broadcasts changes to connected clients in real-time
- Fallback: HTTP polling for non-WebSocket browsers

## Project Structure

```
app/
├── models.py                      # NEW: Alert, AlertAcknowledgment, AlertHistory models
├── services/
│   ├── __init__.py
│   ├── alert_service.py           # NEW: Alert domain logic, deduplication, sync
│   └── zabbix_service.py          # NEW: Zabbix API integration, polling
├── api/
│   ├── __init__.py
│   ├── alerts.py                  # NEW: Flask blueprint for alert endpoints
│   └── health.py                  # EXISTING: Health check endpoints
├── tasks/
│   ├── __init__.py
│   └── alert_poller.py            # NEW: Background task to poll Zabbix
├── static/
│   └── js/
│       └── alerts-dashboard.js    # NEW: Frontend alert UI and WebSocket client
├── templates/
│   └── alerts.html                # NEW: Alert dashboard HTML
├── app.py                         # MODIFY: Add alert endpoints, WebSocket, scheduler
├── requirements.txt               # MODIFY: Add flask-socketio, python-socketio, APScheduler
└── zabbix_client.py               # EXISTING: Zabbix API wrapper (may enhance)
```

## Database Schema

### New Tables

**Alert**
- `id` (UUID, Primary Key)
- `zabbix_event_id` (String, Unique) - Zabbix event ID for deduplication
- `zabbix_problem_id` (String) - Zabbix problem ID
- `host` (String) - Affected host name
- `alert_name` (String) - Alert/trigger name
- `severity` (Enum: Information, Warning, Average, High, Critical, Disaster)
- `status` (Enum: New, Acknowledged, Resolved)
- `created_at` (DateTime)
- `resolved_at` (DateTime, nullable)
- `last_updated_at` (DateTime)
- `raw_zabbix_data` (JSON) - Full Zabbix event data for extensibility

**AlertAcknowledgment**
- `id` (UUID, Primary Key)
- `alert_id` (FK to Alert)
- `operator_name` (String)
- `acknowledged_at` (DateTime)
- `reason` (Text, nullable)
- `synced_to_zabbix` (Boolean) - Track if acknowledgment was sent back to Zabbix

**AlertHistory**
- `id` (UUID, Primary Key)
- `alert_id` (FK to Alert)
- `status_change_from` (Enum)
- `status_change_to` (Enum)
- `changed_at` (DateTime)
- `changed_by` (String, nullable)
- `reason` (Text, nullable)

### Indexes
- `Alert.zabbix_event_id` - Fast deduplication
- `Alert.created_at` - History queries by date range
- `Alert.status` - Filtering by status
- `AlertHistory.alert_id, changed_at` - Timeline queries

## Integration Points with Zabbix

### Zabbix API Methods Used
- `problem.get()` - Fetch current unresolved problems
- `event.get()` - Fetch historical events
- `event.acknowledge()` - Acknowledge events in Zabbix (sync back)

### Key Assumptions
- Zabbix API v4.0+ with event.acknowledge support
- Zabbix authentication token or user/password stored securely
- Zabbix events include event_id and problem_id fields

## Implementation Phases

### Phase 1: Setup & Infrastructure
- Create database models (Alert, AlertAcknowledgment, AlertHistory)
- Create database schema with migrations
- Set up background scheduler (APScheduler)
- Add dependencies to requirements.txt

### Phase 2: Foundational & Blocking Prerequisites
- Implement ZabbixService with Zabbix API integration and polling (1-2 second interval)
- Background task to poll Zabbix and store alerts with deduplication by event_id
- Initialize APScheduler and connection state manager
- Create Flask blueprint and alert API infrastructure

### Phase 3: User Story 1 - View Real-time Alerts on Dashboard (P1)
- Implement GET /api/alerts endpoint to retrieve current alerts
- WebSocket broadcast infrastructure for real-time updates
- Alert dashboard UI (alerts.html template)
- Frontend WebSocket client and real-time rendering
- Severity color-coding and alert detail modal
- HTTP polling fallback for non-WebSocket clients

### Phase 4: User Story 2 - Acknowledge and Clear Alerts (P2)
- Implement POST /api/alerts/{id}/acknowledge endpoint
- AlertAcknowledgment record creation and storage
- Zabbix sync logic to acknowledge events back to Zabbix
- Operator name capture from session/auth context
- Alert status updates and UI styling for acknowledged state
- AlertHistory records for all status transitions

### Phase 5: User Story 3 - Filter and Search Alerts (P3)
- Enhance GET /api/alerts with query parameters (status, severity, host, search)
- Filtering logic in AlertService for accurate subset retrieval
- Frontend filter UI controls and search input
- Database indexes on Alert.status and Alert.severity for performance

### Phase 6: User Story 4 - View Alert History (P4)
- Implement GET /api/alerts/history endpoint with date range parameters
- History query logic and database indexes for performance
- Alert history template with date range picker
- Timeline/table view with alert lifecycle visualization

### Phase 7: Polish & Cross-Cutting Concerns
- Connection status indicator and automatic reconnect logic
- Alert queuing/buffering during API downtime
- Error handling and user notifications
- Performance optimization (pagination, virtual scrolling for 1000+ alerts)
- Comprehensive testing (unit, integration, performance)
- Logging and monitoring infrastructure

## Database Schema Field Population Mapping

The following tasks populate specific database schema fields:

| Field | Table | Populated By Tasks | Description |
|-------|-------|-------------------|-------------|
| `id`, `created_at` | Alert | T006, T007, T009 | Task polling creates alert records on initial entry |
| `zabbix_event_id`, `zabbix_problem_id` | Alert | T005, T006 | ZabbixService extracts from Zabbix API response |
| `host`, `alert_name`, `severity` | Alert | T006, T007 | Data parsed from Zabbix event in polling task |
| `status` (New/Acknowledged/Resolved) | Alert | T006, T021, T009 | Initial set to New by polling, updated by T021 on acknowledge, T009 on resolution |
| `last_updated_at` | Alert | T012, T024 | Updated when alert broadcast to clients (T012) or status changes (T024) |
| `resolved_at` | Alert | T009 | Set when alert status transitions to Resolved |
| `raw_zabbix_data` | Alert | T006 | Full JSON from Zabbix API stored for extensibility |
| All fields | AlertAcknowledgment | T019, T023 | Created when operator acknowledges via T019, operator_name from T023 |
| All fields | AlertHistory | T024, T035 | Created on every status change: T024 for acknowledge transitions, T035 for lifecycle tracking |

## Key Implementation Details

### Polling Strategy
- **Interval**: 1-2 seconds (configured via environment variable, default 2s)
- **Rationale**: Balances 2-second end-to-end latency requirement with Zabbix API load
- **Correlation ID**: Each polling cycle gets unique ID for tracing and deduplication
- **Incremental Fetch**: Query only events changed since last poll (use lastEventTime)

### Operator Name Extraction
- **Source**: Flask session or request auth header (X-Operator-Name or similar)
- **Fallback**: Anonymous if not available in development/testing
- **Storage**: Captured in AlertAcknowledgment.operator_name and AlertHistory.changed_by

### Data Retention
- **Historical Data**: Rolling 30-day window (alerts older than 30 days can be archived/deleted)
- **Archive Strategy**: Post-MVP feature (not in Phase 6) - store in separate table or file storage
- **Cleanup Job**: Scheduled task to run daily to remove alerts older than 30 days

## Success Metrics (Implementation Checklist)

- [ ] Alert polling latency < 2 seconds (end-to-end Zabbix trigger to dashboard display)
- [ ] 99.9% alert delivery reliability achieved (less than 1 alert lost per 1000)
- [ ] Dashboard handles 1000+ concurrent alerts without UI lag or degradation
- [ ] 100% acknowledgment sync to Zabbix (all app acknowledgments synced)
- [ ] All FR-001 through FR-010 functional requirements implemented
- [ ] All acceptance scenarios passing (36 scenarios across 4 user stories)
- [ ] All success criteria SC-001 through SC-008 achieved
- [ ] Zero data loss under 100 concurrent alert streams

## Open Questions & Risks

### Questions to Address During Development
1. **Polling Frequency**: What interval for Zabbix polling (1s, 5s, 10s)? Trade-off between latency and API load
2. **Data Retention**: How to archive/delete old alerts? (30-day retention mentioned)
3. **Operator Identification**: How to get operator name? (Session, LDAP, header, manual entry)
4. **Zabbix Acknowledgment**: Should ALL acknowledgments sync back to Zabbix, or only some?

### Risks & Mitigation
| Risk | Impact | Mitigation |
|------|--------|-----------|
| Zabbix API downtime | Lost alerts during outage | Queue alerts in memory, store when reconnected |
| High alert volume (1000+/min) | Database write bottleneck | Batch inserts, async database writes, consider time-series DB |
| WebSocket connection drops | Clients miss alerts | Automatic fallback to HTTP polling, client reconnect logic |
| Alert deduplication failure | Duplicate displays | Unique constraint on (zabbix_event_id, created_at) |
| Performance with 1000+ alerts | UI freezing | Implement pagination, virtual scrolling, aggregate old alerts |

