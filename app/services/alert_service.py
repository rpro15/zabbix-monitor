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
        Store alerts from Zabbix API response, with advanced deduplication by zabbix_event_id.
        
        Deduplication strategy:
        1. Primary key: zabbix_event_id (UNIQUE constraint)
        2. For updates: Compare severity, name, host to detect if alert changed
        3. Track duplicate attempts to prevent double-processing
        
        Args:
            alerts_data: List of alert dictionaries from Zabbix API
            
        Returns:
            Dictionary with counts: {'created': int, 'updated': int, 'skipped': int, 'duplicates': int}
        """
        counts = {'created': 0, 'updated': 0, 'skipped': 0, 'duplicates': 0}
        
        if not alerts_data:
            logger.debug("No alerts to process")
            return counts
        
        # Build a map of event_ids in this batch to detect batch duplicates
        event_ids_in_batch = {}
        for alert_data in alerts_data:
            event_id = alert_data.get('eventid')
            if event_id in event_ids_in_batch:
                counts['duplicates'] += 1
                logger.warning(
                    f"Duplicate event in batch: eventid={event_id} appeared multiple times"
                )
            event_ids_in_batch[event_id] = alert_data
        
        try:
            for event_id, alert_data in event_ids_in_batch.items():
                if not event_id:
                    counts['skipped'] += 1
                    logger.warning("Alert missing eventid field, skipping")
                    continue
                
                # Check for existing alert (deduplication by event_id)
                existing = Alert.query.filter_by(zabbix_event_id=event_id).first()
                
                if existing:
                    # Check if alert content actually changed
                    severity = int(alert_data.get('severity', existing.severity))
                    name = alert_data.get('name', existing.alert_name)
                    host = alert_data.get('host', existing.host)
                    problem_id = alert_data.get('problemid', existing.zabbix_problem_id)
                    
                    # Update last_updated_at and raw data always
                    existing.last_updated_at = datetime.utcnow()
                    existing.raw_zabbix_data = alert_data
                    
                    # Check if payload changed (severity, name, or host)
                    changed = (
                        existing.severity != severity or
                        existing.alert_name != name or
                        existing.host != host or
                        existing.zabbix_problem_id != problem_id
                    )
                    
                    if changed:
                        existing.severity = severity
                        existing.alert_name = name
                        existing.host = host
                        existing.zabbix_problem_id = problem_id
                        logger.debug(
                            f"Alert updated: eventid={event_id}, "
                            f"host={host}, severity={severity}"
                        )
                    else:
                        logger.debug(
                            f"Alert unchanged: eventid={event_id} (re-received with same data)"
                        )
                    
                    counts['updated'] += 1
                else:
                    # Create new alert
                    try:
                        alert = Alert(
                            zabbix_event_id=event_id,
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
                        logger.info(
                            f"Alert created: eventid={event_id}, "
                            f"host={alert.host}, severity={alert.severity}"
                        )
                    except ValueError as e:
                        counts['skipped'] += 1
                        logger.error(
                            f"Failed to parse alert data for eventid={event_id}: {str(e)}"
                        )
                        continue
            
            db.session.commit()
            logger.info(
                f"Batch processed: Created={counts['created']}, Updated={counts['updated']}, "
                f"Skipped={counts['skipped']}, Duplicates in batch={counts['duplicates']}"
            )
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error storing alerts: {str(e)}", exc_info=True)
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
    """Manager for tracking Zabbix API connection state with exponential backoff reconnection strategy"""
    
    def __init__(self, initial_backoff_seconds: int = 1, max_backoff_seconds: int = 300):
        """
        Initialize connection state manager.
        
        Args:
            initial_backoff_seconds: Initial backoff delay (default 1s)
            max_backoff_seconds: Maximum backoff delay (default 300s = 5min)
        """
        self.is_connected = False
        self.last_check = None
        self.error_count = 0
        self.last_error = None
        self.consecutive_failures = 0
        self.last_successful_poll = None
        
        # Exponential backoff parameters
        self.initial_backoff = initial_backoff_seconds
        self.max_backoff = max_backoff_seconds
        self.current_backoff = initial_backoff_seconds
        self.next_reconnect_attempt = None
        
        logger.info(
            f"ConnectionStateManager initialized: backoff {initial_backoff_seconds}s-{max_backoff_seconds}s"
        )
    
    def mark_connected(self):
        """Mark API as connected and reset backoff"""
        self.is_connected = True
        self.error_count = 0
        self.consecutive_failures = 0
        self.current_backoff = self.initial_backoff
        self.last_check = datetime.utcnow()
        self.last_successful_poll = datetime.utcnow()
        self.next_reconnect_attempt = None
        logger.info("✓ Zabbix API connection established (backoff reset)")
    
    def mark_disconnected(self, error: str):
        """
        Mark API as disconnected with error message.
        
        Increments failure counter and calculates next backoff.
        
        Args:
            error: Error message
        """
        self.is_connected = False
        self.error_count += 1
        self.consecutive_failures += 1
        self.last_error = error
        self.last_check = datetime.utcnow()
        logger.warning(f"✗ Zabbix API disconnected (error #{self.error_count}): {error}")
    
    def attempt_reconnect(self) -> bool:
        """
        Check if reconnection should be attempted based on exponential backoff.
        
        Returns:
            True if reconnection should be attempted, False if still in backoff period
        """
        now = datetime.utcnow()
        
        # If not yet scheduled or time has arrived
        if self.next_reconnect_attempt is None:
            self.next_reconnect_attempt = now
            logger.info(f"⏱️  Next reconnect attempt scheduled immediately")
            return True
        
        # Check if backoff period has elapsed
        if now >= self.next_reconnect_attempt:
            # Calculate next backoff (exponential: 1s, 2s, 4s, 8s, ..., capped at 5min)
            next_backoff = min(self.current_backoff * 2, self.max_backoff)
            self.next_reconnect_attempt = now + __import__('datetime').timedelta(seconds=self.current_backoff)
            
            logger.info(
                f"⏱️  Reconnect attempt #{self.consecutive_failures}: backoff was {self.current_backoff}s, "
                f"next attempt in {self.current_backoff}s (max will be {next_backoff}s)"
            )
            
            self.current_backoff = next_backoff
            return True
        else:
            # Still in backoff period
            wait_time = (self.next_reconnect_attempt - now).total_seconds()
            logger.debug(f"⏱️  Still in backoff: wait {wait_time:.1f}s until next reconnect attempt")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current connection status.
        
        Returns:
            Dictionary with detailed connection state
        """
        return {
            'is_connected': self.is_connected,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'last_successful_poll': self.last_successful_poll.isoformat() if self.last_successful_poll else None,
            'error_count': self.error_count,
            'consecutive_failures': self.consecutive_failures,
            'last_error': self.last_error,
            'current_backoff_seconds': self.current_backoff,
            'next_reconnect_attempt': self.next_reconnect_attempt.isoformat() if self.next_reconnect_attempt else None
        }
