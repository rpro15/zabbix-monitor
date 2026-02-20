# Research Notes: Add Real-time Zabbix Alert Notifications

## Decision: Polling-based ingestion with APScheduler
- Rationale: Zabbix API is naturally queried; polling every 1-5 seconds matches latency goals and simplifies operations.
- Alternatives considered: Streaming/webhook from Zabbix (requires additional Zabbix configuration and infrastructure).

## Decision: Flask-SocketIO for real-time updates
- Rationale: Fits existing Flask stack, supports WebSocket + polling fallback for broad client compatibility.
- Alternatives considered: Server-Sent Events (SSE) or custom WebSocket server (extra complexity).

## Decision: PostgreSQL with SQLAlchemy ORM
- Rationale: Existing docker-compose provides Postgres; SQLAlchemy is already used in the app.
- Alternatives considered: SQLite for local dev only (not suitable for production load).

## Decision: Docker Compose deployment
- Rationale: Repo already includes compose services for Zabbix + Postgres + web app; easy local bootstrap.
- Alternatives considered: Manual local installs (higher setup burden).
