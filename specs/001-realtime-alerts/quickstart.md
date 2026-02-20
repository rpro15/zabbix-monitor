# Quickstart: Real-time Zabbix Alerts

## Prerequisites
- Docker + Docker Compose
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
  -d '{"operator_name":"Operator","reason":"Investigating"}'

# History by date range
curl "http://localhost:5000/api/alerts/history?date_from=2026-02-20T00:00:00&date_to=2026-02-20T23:59:59"
```

## Notes
- The app uses polling (APScheduler) to ingest Zabbix alerts and broadcasts updates via WebSocket.
- If Zabbix is unreachable, the dashboard will show a disconnected status and continue polling.
