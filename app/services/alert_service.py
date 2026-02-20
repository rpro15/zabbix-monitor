"""Alert service - business logic for alert management"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from models import db, Alert, AlertAcknowledgment, AlertHistory, AlertStatus, AlertSeverity
import logging

logger = logging.getLogger(__name__)


class AlertService:
    """Service for managing alerts - creation, updates, filtering, deduplication"""

    @staticmethod
    def store_alerts(alerts_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Store alerts from Zabbix API response, with deduplication by zabbix_event_id.
        
        Args:
            alerts_data: List of alert dictionaries from Zabbix API
            
        Returns:
            Dictionary with counts: {'created': int, 'updated': int, 'skipped': int}
        """
        counts = {'created': 0, 'updated': 0, 'skipped': 0}
        
        try:
            for alert_data in alerts_data:
                zabbix_event_id = alert_data.get('eventid')
                
                # Check for existing alert (deduplication by event_id)
                existing = Alert.query.filter_by(zabbix_event_id=zabbix_event_id).first()
                
                if existing:
                    # Update existing alert
                    existing.last_updated_at = datetime.utcnow()
                    existing.raw_zabbix_data = alert_data
                    counts['updated'] += 1
                else:
                    # Create new alert
                    alert = Alert(
                        zabbix_event_id=zabbix_event_id,
                        zabbix_problem_id=alert_data.get('problemid'),
                        host=alert_data.get('host', 'Unknown'),
                        alert_name=alert_data.get('name', 'Unnamed Alert'),
                        severity=int(alert_data.get('severity', 2)),
                        status=AlertStatus.NEW.value,
                        timestamp=datetime.fromtimestamp(int(alert_data.get('clock', 0))),
                        raw_zabbix_data=alert_data
                    )
                    db.session.add(alert)
                    counts['created'] += 1
            
            db.session.commit()
            logger.info(f"Alerts stored: {counts}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error storing alerts: {str(e)}")
            counts['skipped'] = len(alerts_data) - counts['created'] - counts['updated']
        
        return counts

    @staticmethod
    def get_all_alerts(status: Optional[str] = None, severity: Optional[int] = None) -> List[Alert]:
        """
        Retrieve alerts with optional filtering.
        
        Args:
            status: Filter by status (new, acknowledged, resolved)
            severity: Filter by severity level (0-5)
            
        Returns:
            List of Alert objects
        """
        query = Alert.query
        
        if status:
            query = query.filter_by(status=status)
        if severity is not None:
            query = query.filter_by(severity=severity)
        
        return query.order_by(Alert.created_at.desc()).all()

    @staticmethod
    def get_alerts_filtered(
        status: Optional[str] = None,
        severity: Optional[int] = None,
        host: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[Alert], int]:
        """
        Get filtered alerts with pagination.
        
        Args:
            status: Filter by status (new, acknowledged, resolved)
            severity: Filter by severity level (0-5)
            host: Filter by hostname (exact or partial match)
            search: Search in alert name
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            Tuple of (list of alerts, total count)
        """
        query = Alert.query
        
        if status:
            query = query.filter_by(status=status)
        if severity is not None:
            query = query.filter_by(severity=severity)
        if host:
            query = query.filter(Alert.host.ilike(f'%{host}%'))
        if search:
            query = query.filter(Alert.alert_name.ilike(f'%{search}%'))
        
        total = query.count()
        alerts = query.order_by(Alert.created_at.desc()).offset(skip).limit(limit).all()
        
        return alerts, total

    @staticmethod
    def acknowledge_alert(
        alert_id: str,
        operator_name: str,
        reason: Optional[str] = None
    ) -> Optional[AlertAcknowledgment]:
        """
        Acknowledge an alert.
        
        Args:
            alert_id: Alert ID
            operator_name: Name of operator acknowledging
            reason: Optional acknowledgment reason
            
        Returns:
            AlertAcknowledgment object or None if failed
        """
        try:
            alert = Alert.query.get(alert_id)
            if not alert:
                logger.warning(f"Alert not found: {alert_id}")
                return None
            
            # Create acknowledgment record
            ack = AlertAcknowledgment(
                alert_id=alert_id,
                operator_name=operator_name,
                reason=reason
            )
            
            # Update alert status
            alert.status = AlertStatus.ACKNOWLEDGED.value
            alert.last_updated_at = datetime.utcnow()
            
            # Record in history
            history = AlertHistory(
                alert_id=alert_id,
                status_change_from=AlertStatus.NEW.value,
                status_change_to=AlertStatus.ACKNOWLEDGED.value,
                changed_by=operator_name,
                reason=reason
            )
            
            db.session.add(ack)
            db.session.add(history)
            db.session.commit()
            
            logger.info(f"Alert {alert_id} acknowledged by {operator_name}")
            return ack
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error acknowledging alert {alert_id}: {str(e)}")
            return None

    @staticmethod
    def resolve_alert(alert_id: str) -> bool:
        """
        Mark an alert as resolved.
        
        Args:
            alert_id: Alert ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            alert = Alert.query.get(alert_id)
            if not alert:
                logger.warning(f"Alert not found: {alert_id}")
                return False
            
            old_status = alert.status
            alert.status = AlertStatus.RESOLVED.value
            alert.resolved_at = datetime.utcnow()
            alert.last_updated_at = datetime.utcnow()
            
            # Record in history
            history = AlertHistory(
                alert_id=alert_id,
                status_change_from=old_status,
                status_change_to=AlertStatus.RESOLVED.value,
                changed_by='system'
            )
            
            db.session.add(history)
            db.session.commit()
            
            logger.info(f"Alert {alert_id} resolved")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error resolving alert {alert_id}: {str(e)}")
            return False

    @staticmethod
    def get_alert_history(
        alert_id: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[AlertHistory]:
        """
        Get history records for an alert.
        
        Args:
            alert_id: Alert ID
            date_from: Filter from date
            date_to: Filter to date
            
        Returns:
            List of AlertHistory records ordered by date
        """
        query = AlertHistory.query.filter_by(alert_id=alert_id)
        
        if date_from:
            query = query.filter(AlertHistory.changed_at >= date_from)
        if date_to:
            query = query.filter(AlertHistory.changed_at <= date_to)
        
        return query.order_by(AlertHistory.changed_at.desc()).all()

    @staticmethod
    def get_alerts_by_date_range(
        date_from: datetime,
        date_to: datetime,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[Alert], int]:
        """
        Get alerts created within a date range (for history view).
        
        Args:
            date_from: Start date
            date_to: End date
            skip: Number of records to skip (pagination)
            limit: Maximum records to return
            
        Returns:
            Tuple of (list of alerts, total count)
        """
        query = Alert.query.filter(
            Alert.created_at >= date_from,
            Alert.created_at <= date_to
        )
        
        total = query.count()
        alerts = query.order_by(Alert.created_at.desc()).offset(skip).limit(limit).all()
        
        return alerts, total

    @staticmethod
    def clear_old_alerts(days: int = 30) -> int:
        """
        Delete alerts older than specified days (cleanup for data retention).
        
        Args:
            days: Number of days to retain (default 30)
            
        Returns:
            Number of alerts deleted
        """
        try:
            cutoff_date = datetime.utcnow() - __import__('datetime').timedelta(days=days)
            
            # First delete related records (history, acknowledgments)
            old_alerts = Alert.query.filter(Alert.created_at < cutoff_date).all()
            count = len(old_alerts)
            
            for alert in old_alerts:
                db.session.delete(alert)
            
            db.session.commit()
            logger.info(f"Deleted {count} alerts older than {days} days")
            return count
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error clearing old alerts: {str(e)}")
            return 0


class ConnectionStateManager:
    """Manager for tracking Zabbix API connection state"""
    
    def __init__(self):
        self.is_connected = False
        self.last_check = None
        self.error_count = 0
        self.last_error = None
    
    def mark_connected(self):
        """Mark API as connected"""
        self.is_connected = True
        self.error_count = 0
        self.last_check = datetime.utcnow()
        logger.info("Zabbix API connection established")
    
    def mark_disconnected(self, error: str):
        """Mark API as disconnected with error message"""
        self.is_connected = False
        self.error_count += 1
        self.last_error = error
        self.last_check = datetime.utcnow()
        logger.warning(f"Zabbix API connection failed: {error}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current connection status"""
        return {
            'is_connected': self.is_connected,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'error_count': self.error_count,
            'last_error': self.last_error
        }
