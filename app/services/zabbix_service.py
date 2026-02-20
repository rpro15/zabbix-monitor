"""Zabbix API integration service"""

import logging
from typing import Optional, List, Dict, Any
from pyzabbix import ZabbixAPI
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ZabbixService:
    """Service for Zabbix API integration - fetches alerts and manages acknowledgments"""

    def __init__(self, url: str, username: str, password: str):
        """
        Initialize ZabbixService.
        
        Args:
            url: Zabbix API URL (e.g., http://zabbix-web:8080/api_jsonrpc.php)
            username: Zabbix API username
            password: Zabbix API password
        """
        # py-zabbix appends /api_jsonrpc.php automatically; avoid double path
        if url.endswith('/api_jsonrpc.php'):
            url = url[: -len('/api_jsonrpc.php')]
        self.url = url
        self.username = username
        self.password = password
        self.zabbix = None
        self._authenticated = False
        self._last_event_time = None
        
        # Try initial connection
        self._authenticate()

    def _authenticate(self) -> bool:
        """
        Authenticate with Zabbix API.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.zabbix = ZabbixAPI(url=self.url)
            response = self.zabbix.do_request('user.login', {
                'user': self.username,
                'password': self.password
            })
            self.zabbix.auth = response['result']
            self._authenticated = True
            logger.info("✓ Successfully authenticated with Zabbix API")
            return True
        except Exception as e:
            logger.error(f"Failed to authenticate with Zabbix: {str(e)}")
            self._authenticated = False
            return False

    def fetch_new_alerts(self) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch new and updated alerts from Zabbix.
        
        Uses problem.get() to fetch current problems/alerts.
        
        Returns:
            List of alert dictionaries or None if failed
        """
        try:
            if not self._authenticated:
                logger.warning("Not authenticated with Zabbix, skipping fetch")
                return None
            
            # Fetch unresolved problems from Zabbix
            # problem.get returns current problems (triggers in problem state)
            problems = self.zabbix.problem.get(
                output=['eventid', 'objectid', 'clock', 'severity', 'name'],
                selectHosts=['host', 'hostid'],
                recent=True,
                limit=1000
            )
            
            # Convert to our format
            alerts = []
            for problem in problems:
                host_info = problem.get('hosts', [{}])[0]
                
                alert_data = {
                    'eventid': problem.get('eventid'),
                    'problemid': problem.get('objectid'),
                    'host': host_info.get('host', 'Unknown'),
                    'name': problem.get('name', 'Unnamed Problem'),
                    'severity': problem.get('severity', 2),
                    'clock': problem.get('clock', int(datetime.utcnow().timestamp()))
                }
                alerts.append(alert_data)
            
            logger.debug(f"Fetched {len(alerts)} problems from Zabbix")
            return alerts
            
        except Exception as e:
            logger.error(f"Error fetching alerts from Zabbix: {str(e)}")
            return None

    def acknowledge_event(
        self,
        eventid: str,
        message: str,
        username: Optional[str] = None
    ) -> bool:
        """
        Acknowledge an event in Zabbix (sync alert acknowledgment back to Zabbix).
        
        Args:
            eventid: Zabbix event ID
            message: Acknowledgment message
            username: Optional username for the acknowledgment
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self._authenticated:
                logger.warning("Not authenticated with Zabbix, cannot acknowledge event")
                return False
            
            # Acknowledge the event in Zabbix
            result = self.zabbix.event.acknowledge(
                eventids=eventid,
                message=message
            )
            
            if result.get('eventids'):
                logger.info(f"Acknowledged event {eventid} in Zabbix")
                return True
            else:
                logger.warning(f"Failed to acknowledge event {eventid} in Zabbix")
                return False
                
        except Exception as e:
            logger.error(f"Error acknowledging event {eventid}: {str(e)}")
            return False

    def handle_connection_failures(self) -> bool:
        """
        Handle connection failures with automatic reconnection.
        
        Returns:
            True if reconnected successfully, False otherwise
        """
        logger.warning("Attempting to reconnect to Zabbix...")
        
        # Try to re-authenticate
        if self._authenticate():
            logger.info("✓ Reconnected to Zabbix API")
            return True
        else:
            logger.error("✗ Failed to reconnect to Zabbix API")
            return False

    def get_status(self) -> Dict[str, Any]:
        """
        Get Zabbix service status information.
        
        Returns:
            Dictionary with status information
        """
        try:
            if self._authenticated and self.zabbix:
                # Try to get API version to verify connection
                api_version = self.zabbix.api_version()
                return {
                    'connected': True,
                    'url': self.url,
                    'api_version': api_version,
                    'timestamp': datetime.utcnow().isoformat()
                }
            else:
                return {
                    'connected': False,
                    'url': self.url,
                    'timestamp': datetime.utcnow().isoformat()
                }
        except Exception as e:
            logger.error(f"Error getting Zabbix status: {str(e)}")
            return {
                'connected': False,
                'url': self.url,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
