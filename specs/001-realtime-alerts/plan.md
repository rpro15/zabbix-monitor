# Implementation Plan: Add Real-time Zabbix Alert Notifications

**Branch**: `001-realtime-alerts` | **Date**: February 20, 2026 | **Spec**: [specs/001-realtime-alerts/spec.md](specs/001-realtime-alerts/spec.md)
**Input**: Feature specification from `/specs/001-realtime-alerts/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Deliver a real-time Zabbix alert dashboard with acknowledgments, filtering, and historical review. The solution uses polling (APScheduler) to ingest Zabbix events, stores alerts in PostgreSQL via SQLAlchemy, and pushes updates to clients over Flask-SocketIO with HTTP polling fallback. It also supports acknowledgment sync back to Zabbix and date-range history queries with lifecycle timelines.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.9  
**Primary Dependencies**: Flask 2.3.3, Flask-SocketIO 5.3.4, APScheduler 3.10.4, SQLAlchemy (flask-sqlalchemy 3.0.5), Alembic 1.12.1, py-zabbix 1.1.7, Gunicorn 21.2.0  
**Storage**: PostgreSQL (Docker Compose)  
**Testing**: Build verification scripts (test_build_phase*.py)  
**Target Platform**: Linux containers (Docker Compose)  
**Project Type**: Web application (Flask backend + HTML/JS/CSS)  
**Performance Goals**: <2s alert latency; responsive UI with 1000+ alerts; 99.9% delivery rate  
**Constraints**: Polling interval 1-5s; Zabbix API availability; UI must remain responsive under alert spikes  
**Scale/Scope**: 1000+ concurrent alerts; 100 concurrent alert streams

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution file contains placeholders only. No enforceable gates are defined, so no violations can be evaluated at this time.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
app/
├── api/
│   └── alerts.py
├── services/
│   ├── alert_service.py
│   └── zabbix_service.py
├── tasks/
│   └── alert_poller.py
├── static/
│   ├── css/
│   │   └── alerts.css
│   └── js/
│       ├── alerts-dashboard.js
│       └── alerts-history.js
├── templates/
│   ├── alerts.html
│   └── alerts-history.html
├── models.py
├── app.py
└── requirements.txt

docker-compose.yml
init-databases.sh
```

**Structure Decision**: Web application with a single Flask backend (templates + static assets). API, services, tasks, and data models live under app/.

## Complexity Tracking

No constitution-based violations to track.

## Phase 0 Output: Research

- [specs/001-realtime-alerts/research.md](specs/001-realtime-alerts/research.md)

## Phase 1 Output: Design and Contracts

- [specs/001-realtime-alerts/data-model.md](specs/001-realtime-alerts/data-model.md)
- [specs/001-realtime-alerts/contracts/openapi.yaml](specs/001-realtime-alerts/contracts/openapi.yaml)
- [specs/001-realtime-alerts/quickstart.md](specs/001-realtime-alerts/quickstart.md)

## Constitution Check (Post-Design)

No constitution gates are defined beyond placeholders. Post-design check remains non-applicable.
