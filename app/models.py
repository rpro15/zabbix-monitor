from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from enum import Enum
import uuid

db = SQLAlchemy()


class AlertSeverity(Enum):
    """Alert severity levels matching Zabbix severity"""
    INFORMATION = 0
    WARNING = 1
    AVERAGE = 2
    HIGH = 3
    CRITICAL = 4
    DISASTER = 5


class AlertStatus(Enum):
    """Alert lifecycle status"""
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"

class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    zabbix_host_id = db.Column(db.String(50), nullable=True)


class Alert(db.Model):
    """Represents a Zabbix event/problem - real-time alert"""
    __tablename__ = 'alerts'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    zabbix_event_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    zabbix_problem_id = db.Column(db.String(50), nullable=True)
    host = db.Column(db.String(255), nullable=False, index=True)
    alert_name = db.Column(db.String(500), nullable=False)
    severity = db.Column(db.Integer, nullable=False)  # 0-5, maps to AlertSeverity
    status = db.Column(db.String(20), nullable=False, default=AlertStatus.NEW.value, index=True)
    timestamp = db.Column(db.DateTime, nullable=False)  # When alert triggered in Zabbix
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    last_updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    raw_zabbix_data = db.Column(db.JSON, nullable=True)  # Full Zabbix event data

    # Relationships
    acknowledgments = db.relationship('AlertAcknowledgment', backref='alert', lazy=True, cascade='all, delete-orphan')
    history = db.relationship('AlertHistory', backref='alert', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        """Convert alert to dictionary for JSON response"""
        return {
            'id': self.id,
            'zabbix_event_id': self.zabbix_event_id,
            'zabbix_problem_id': self.zabbix_problem_id,
            'host': self.host,
            'alert_name': self.alert_name,
            'severity': self.severity,
            'status': self.status,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'created_at': self.created_at.isoformat(),
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'last_updated_at': self.last_updated_at.isoformat()
        }


class AlertAcknowledgment(db.Model):
    """Represents acknowledgment action on an alert"""
    __tablename__ = 'alert_acknowledgments'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id = db.Column(db.String(36), db.ForeignKey('alerts.id'), nullable=False, index=True)
    operator_name = db.Column(db.String(255), nullable=False)
    acknowledged_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    reason = db.Column(db.Text, nullable=True)
    synced_to_zabbix = db.Column(db.Boolean, default=False)

    def to_dict(self):
        """Convert to dictionary for JSON response"""
        return {
            'id': self.id,
            'alert_id': self.alert_id,
            'operator_name': self.operator_name,
            'acknowledged_at': self.acknowledged_at.isoformat(),
            'reason': self.reason,
            'synced_to_zabbix': self.synced_to_zabbix
        }


class AlertHistory(db.Model):
    """Audit log of all alert status changes"""
    __tablename__ = 'alert_history'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id = db.Column(db.String(36), db.ForeignKey('alerts.id'), nullable=False, index=True)
    status_change_from = db.Column(db.String(20), nullable=True)
    status_change_to = db.Column(db.String(20), nullable=False)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    changed_by = db.Column(db.String(255), nullable=True)  # Operator name or system
    reason = db.Column(db.Text, nullable=True)

    def to_dict(self):
        """Convert to dictionary for JSON response"""
        return {
            'id': self.id,
            'alert_id': self.alert_id,
            'status_change_from': self.status_change_from,
            'status_change_to': self.status_change_to,
            'changed_at': self.changed_at.isoformat(),
            'changed_by': self.changed_by,
            'reason': self.reason
        }
