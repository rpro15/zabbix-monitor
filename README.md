# Zabbix Monitor - Real-time Alerts

Real-time monitoring dashboard for Zabbix alerts with acknowledgments, filtering, and history.

## Features
- Real-time alerts via polling + WebSocket broadcast
- Acknowledge alerts with operator tracking and optional reason
- Filter by status, severity, host, and name
- History view with lifecycle timeline

## Prerequisites
- Docker and Docker Compose
- Ports available: 5000 (web), 5432 (Postgres), 8080 (Zabbix web), 10051 (Zabbix server)

## Run with Docker Compose

```bash
cd c:\Users\rpro1\my_projects\zabbix-monitor

docker compose up --build
```

Open:
- Dashboard: http://localhost:5000/alerts
- History: http://localhost:5000/alerts/history
- Zabbix Web UI: http://localhost:8080

## Environment Variables
The compose file provides defaults. Override if needed:
- DATABASE_URL
- ZABBIX_URL
- ZABBIX_USER
- ZABBIX_PASSWORD

## API Quick Test

```bash
# List alerts (filtered)
curl "http://localhost:5000/api/alerts?status=new&severity=4&limit=10"

# Acknowledge an alert
curl -X POST "http://localhost:5000/api/alerts/<alert_id>/acknowledge" \
  -H "Content-Type: application/json" \
  -d "{\"operator_name\":\"Operator\",\"reason\":\"Investigating\"}"

# History by date range
curl "http://localhost:5000/api/alerts/history?date_from=2026-02-20T00:00:00&date_to=2026-02-20T23:59:59"
```

## Notes
- The app polls Zabbix every few seconds and broadcasts updates via WebSocket.
- If Zabbix is unreachable, the dashboard shows a disconnected status and continues polling.

## Verification
Run the full build verification suite:

```bash
cd c:\Users\rpro1\my_projects\zabbix-monitor\app

python test_build.py
python test_build_phase2.py
python test_build_phase3.py
python test_build_phase4.py
python test_build_phase5.py
python test_build_phase6.py
python test_build_phase7.py
```
