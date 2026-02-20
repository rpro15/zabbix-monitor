"""Alert polling task - background job to fetch alerts from Zabbix"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def poll_alerts_task(zabbix_service, alert_service, connection_state):
    """
    Background task to poll Zabbix API for new/updated alerts.
    
    Called every 1-2 seconds by APScheduler.
    
    Args:
        zabbix_service: ZabbixService instance
        alert_service: AlertService instance
        connection_state: ConnectionStateManager instance
    """
    try:
        logger.debug("Starting alert polling task...")
        
        # Fetch new alerts from Zabbix
        alerts_data = zabbix_service.fetch_new_alerts()
        
        if alerts_data is not None:
            # Successfully connected to Zabbix
            connection_state.mark_connected()
            
            # Store alerts in database (with deduplication)
            result = alert_service.store_alerts(alerts_data)
            
            logger.info(
                f"Poll completed - Created: {result['created']}, "
                f"Updated: {result['updated']}, Skipped: {result['skipped']}"
            )
            
            return result
        else:
            # Failed to connect to Zabbix
            connection_state.mark_disconnected("Failed to fetch alerts from Zabbix API")
            return None
            
    except Exception as e:
        logger.error(f"Error in alert polling task: {str(e)}", exc_info=True)
        connection_state.mark_disconnected(str(e))
        return None


def cleanup_old_alerts_task(alert_service, retention_days=30):
    """
    Background task to clean up old alerts (data retention).
    
    Runs daily at configured time.
    
    Args:
        alert_service: AlertService instance
        retention_days: Number of days to retain alerts (default 30)
    """
    try:
        logger.info(f"Starting cleanup of alerts older than {retention_days} days...")
        
        deleted_count = alert_service.clear_old_alerts(days=retention_days)
        
        logger.info(f"Cleanup completed - Deleted {deleted_count} old alerts")
        
        return deleted_count
    except Exception as e:
        logger.error(f"Error in cleanup task: {str(e)}", exc_info=True)
        return None
