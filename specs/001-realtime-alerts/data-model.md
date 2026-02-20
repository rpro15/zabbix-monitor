# Data Model: Real-time Zabbix Alerts

## Entities

### Alert
Represents a Zabbix event/problem.

Fields:
- id (UUID string, primary key)
- zabbix_event_id (string, unique, indexed)
- zabbix_problem_id (string, nullable)
- host (string, indexed)
- alert_name (string)
- severity (int 0-5, indexed)
- status (string: new/acknowledged/resolved, indexed)
- timestamp (datetime, when triggered in Zabbix)
- created_at (datetime, indexed)
- resolved_at (datetime, nullable)
- last_updated_at (datetime)
- raw_zabbix_data (JSON, nullable)

Relationships:
- acknowledgments: one-to-many -> AlertAcknowledgment
- history: one-to-many -> AlertHistory

Validation rules:
- zabbix_event_id required and unique
- severity must be 0-5
- status must be one of new/acknowledged/resolved

State transitions:
- new -> acknowledged
- new -> resolved
- acknowledged -> resolved

### AlertAcknowledgment
Captures operator acknowledgment.

Fields:
- id (UUID string, primary key)
- alert_id (FK to Alert, indexed)
- operator_name (string)
- acknowledged_at (datetime)
- reason (text, nullable)
- synced_to_zabbix (boolean)

Validation rules:
- operator_name required

### AlertHistory
Audit trail of alert status changes.

Fields:
- id (UUID string, primary key)
- alert_id (FK to Alert, indexed)
- status_change_from (string, nullable)
- status_change_to (string)
- changed_at (datetime, indexed)
- changed_by (string, nullable)
- reason (text, nullable)

Validation rules:
- status_change_to required

### Project
Optional mapping of monitored projects to Zabbix hosts.

Fields:
- id (int, primary key)
- name (string)
- url (string)
- created_at (datetime)
- is_active (boolean)
- zabbix_host_id (string, nullable)
