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

### Phase 2: Core Alert Retrieval (P1 - US1)
- Implement ZabbixService.fetch_new_alerts() method
- Background task to poll Zabbix every N seconds
- Store alerts in local database with deduplication by event_id
- Implement alert status transitions (New → Resolved)
- Create /api/alerts GET endpoint to retrieve current alerts
- WebSocket event broadcast when new alert arrives

### Phase 3: Alert Acknowledgment (P2 - US2)
- Create AlertAcknowledgment model and database table
- Implement POST /api/alerts/{id}/acknowledge endpoint
- Logic to sync acknowledgment back to Zabbix via event.acknowledge()
- Update alert status in dashboard when acknowledged
- Capture operator name (from HTTP header, session, or request body)

### Phase 4: Filtering & Search (P3 - US3)
- Enhance GET /api/alerts with query parameters:
  - `status` filter (new, acknowledged, resolved)
  - `severity` filter (Critical, High, Average, etc.)
  - `host` search/filter
  - `name` search
- Frontend UI filters that call enhanced API

### Phase 5: Alert History (P4 - US4)
- Create AlertHistory model for all status changes
- Implement GET /api/alerts/history endpoint with date range
- Track all state transitions with operator info
- Frontend history timeline/table view

### Phase 6: Frontend & Polish
- Create alerts.html dashboard view
- Build real-time alert UI with WebSocket integration
- Severity color-coding and visual styling
- Connection status indicator
- Error handling and graceful degradation
- Performance optimization (pagination, virtualization for 1000+ alerts)

## Success Metrics (Implementation Checklist)

- [ ] Alert polling latency < 2 seconds (end-to-end)
- [ ] 99.9% alert delivery reliability achieved
- [ ] Dashboard handles 1000+ alerts without UI lag
- [ ] 100% acknowledgment sync to Zabbix
- [ ] All FR-001 through FR-010 functional requirements implemented
- [ ] All acceptance scenarios passing
- [ ] All success criteria SC-001 through SC-008 met
- [ ] No data loss under 100 concurrent alert streams

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

