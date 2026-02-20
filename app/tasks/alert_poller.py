"""Alert polling task - background job to fetch alerts from Zabbix"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Polling metrics tracker for monitoring
polling_metrics = {
    'total_polls': 0,
    'successful_polls': 0,
    'failed_polls': 0,
    'total_alerts_created': 0,
    'total_alerts_updated': 0,
    'last_poll_duration': 0,
    'last_poll_time': None,
    'consecutive_failures': 0
}


def poll_alerts_task(zabbix_service, alert_service, connection_state, socketio=None, telegram_service=None):
    """
    Background task to poll Zabbix API for new/updated alerts.
    
    Called every 1-5 seconds by APScheduler.
    Broadcasts new alerts to WebSocket clients in real-time.
    Tracks connection state and polling metrics.
    
    Args:
        zabbix_service: ZabbixService instance
        alert_service: AlertService instance
        connection_state: ConnectionStateManager instance
        socketio: Flask-SocketIO instance (optional, for WebSocket broadcast)
        telegram_service: TelegramService instance (optional, for notifications)
    
    Returns:
        Dictionary with poll results or None on failure
    """
    start_time = datetime.utcnow()
    polling_metrics['total_polls'] += 1
    
    try:
        logger.debug(f"[POLL #{polling_metrics['total_polls']}] Starting alert polling...")
        
        # Fetch new alerts from Zabbix
        alerts_data = zabbix_service.fetch_new_alerts()
        
        if alerts_data is not None:
            # Successfully connected to Zabbix
            connection_state.mark_connected()
            
            # Store alerts in database (with deduplication)
            result = alert_service.store_alerts(alerts_data)
            
            # Broadcast newly created/updated alerts to WebSocket clients
            if result['created'] > 0 and socketio:
                try:
                    # Note: alerts_data is from Zabbix, need to fetch from DB to get our IDs
                    # For now, broadcast the raw data with a marker that it's new
                    socketio.emit(
                        'new_alerts_batch',
                        {
                            'created': result['created'],
                            'updated': result['updated'],
                            'timestamp': start_time.isoformat()
                        },
                        namespace='/'
                    )
                    logger.debug(f"Broadcasted {result['created']} new alerts to WebSocket clients")
                except Exception as e:
                    logger.error(f"Error broadcasting alerts via WebSocket: {str(e)}")

            # Notify Telegram for newly created alerts
            if telegram_service and result['created'] > 0:
                try:
                    created_alerts = alert_service.get_alerts_by_ids(result.get('created_ids', []))
                    for alert in created_alerts:
                        telegram_service.notify_new_alert(alert)
                except Exception as e:
                    logger.error(f"Error sending Telegram notifications: {str(e)}")
            
            # Update polling metrics
            polling_metrics['successful_polls'] += 1
            polling_metrics['total_alerts_created'] += result['created']
            polling_metrics['total_alerts_updated'] += result['updated']
            polling_metrics['consecutive_failures'] = 0
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            polling_metrics['last_poll_duration'] = duration
            polling_metrics['last_poll_time'] = start_time.isoformat()
            
            if result['created'] > 0 or result['updated'] > 0:
                logger.info(
                    f"[POLL OK] Created: {result['created']}, Updated: {result['updated']}, "
                    f"Duration: {duration:.3f}s, Success: {(polling_metrics['successful_polls']/max(polling_metrics['total_polls'],1)*100):.1f}%"
                )
            
            return result
        else:
            raise Exception("Zabbix API returned None response")
            
    except Exception as e:
        polling_metrics['failed_polls'] += 1
        polling_metrics['consecutive_failures'] += 1
        
        error_str = str(e)
        logger.error(
            f"[POLL FAIL #{polling_metrics['failed_polls']}] Error: {error_str} "
            f"(consecutive: {polling_metrics['consecutive_failures']})",
            exc_info=False
        )
        
        # Broadcast connection error to clients
        if socketio:
            try:
                socketio.emit(
                    'connection_error',
                    {
                        'error': error_str,
                        'timestamp': start_time.isoformat()
                    },
                    namespace='/'
                )
            except Exception as broadcast_err:
                logger.error(f"Error broadcasting connection error: {str(broadcast_err)}")
        
        # Mark disconnected
        connection_state.mark_disconnected(error_str)
        
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


def get_polling_metrics() -> Dict[str, Any]:
    """
    Get current polling metrics for monitoring/debugging.
    
    Returns:
        Dictionary with polling statistics
    """
    return polling_metrics.copy()
