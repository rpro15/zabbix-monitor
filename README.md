# Zabbix Monitor - Real-time Alerts

Real-time monitoring dashboard for Zabbix alerts with acknowledgments, filtering, history, and Telegram notifications.

---

## English

### What this service does
- Shows Zabbix problems in real time (polling + WebSocket)
- Lets operators acknowledge alerts (syncs back to Zabbix)
- Provides filtering by status, severity, host, and name
- Keeps history with lifecycle timeline
- Sends Telegram notifications for new/ack/resolved events

### Prerequisites
- Docker and Docker Compose
- Ports available: 5000 (web), 5432 (Postgres), 8080 (Zabbix web), 10051 (Zabbix server)

### Run with Docker Compose

```bash
cd c:\Users\rpro1\my_projects\zabbix-monitor

docker compose up --build
```

Open:
- Dashboard: http://localhost:5000/alerts
- History: http://localhost:5000/alerts/history
- Zabbix Web UI: http://localhost:8080

### Environment variables
The compose file provides defaults. Override if needed:
- DATABASE_URL
- ZABBIX_URL
- ZABBIX_USER
- ZABBIX_PASSWORD

Telegram notifications (optional):
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_IDS (comma-separated: "123, -100987654321")
- TELEGRAM_MESSAGE_FORMAT (short|detailed, default short)
- APP_BASE_URL (optional, used for dashboard link in detailed messages)

### API quick test

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

### Notes
- The app polls Zabbix every few seconds and broadcasts updates via WebSocket.
- If Zabbix is unreachable, the dashboard shows a disconnected status and continues polling.

### Verification
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

---

## Русский

### Для чего нужен сервис
- Показывает проблемы Zabbix в реальном времени (polling + WebSocket)
- Позволяет подтверждать алерты (синхронизация обратно в Zabbix)
- Есть фильтры по статусу, критичности, хосту и названию
- Хранит историю с таймлайном изменений
- Отправляет уведомления в Telegram (новые/ack/решённые)

### Требования
- Docker и Docker Compose
- Свободные порты: 5000 (web), 5432 (Postgres), 8080 (Zabbix web), 10051 (Zabbix server)

### Запуск через Docker Compose

```bash
cd c:\Users\rpro1\my_projects\zabbix-monitor

docker compose up --build
```

Открыть:
- Дашборд: http://localhost:5000/alerts
- История: http://localhost:5000/alerts/history
- Zabbix UI: http://localhost:8080

### Переменные окружения
В compose уже есть значения по умолчанию. При необходимости можно переопределить:
- DATABASE_URL
- ZABBIX_URL
- ZABBIX_USER
- ZABBIX_PASSWORD

Telegram (опционально):
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_IDS (через запятую: "123, -100987654321")
- TELEGRAM_MESSAGE_FORMAT (short|detailed, по умолчанию short)
- APP_BASE_URL (необязательно, ссылка на дашборд для подробных сообщений)

### Быстрый тест API

```bash
# Список алертов (с фильтрами)
curl "http://localhost:5000/api/alerts?status=new&severity=4&limit=10"

# Подтверждение алерта
curl -X POST "http://localhost:5000/api/alerts/<alert_id>/acknowledge" \
  -H "Content-Type: application/json" \
  -d "{\"operator_name\":\"Operator\",\"reason\":\"Investigating\"}"

# История по диапазону дат
curl "http://localhost:5000/api/alerts/history?date_from=2026-02-20T00:00:00&date_to=2026-02-20T23:59:59"
```

### Примечания
- Приложение опрашивает Zabbix каждые несколько секунд и пушит обновления через WebSocket.
- Если Zabbix недоступен, в интерфейсе будет статус Disconnected, но опрос продолжится.

### Проверка
Запуск полного набора проверок:

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
