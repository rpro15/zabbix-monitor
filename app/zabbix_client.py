from pyzabbix import ZabbixAPI
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class ZabbixClient:
    def __init__(self, url: str, username: str, password: str):
        # py-zabbix appends /api_jsonrpc.php automatically; avoid double path
        if url.endswith('/api_jsonrpc.php'):
            url = url[: -len('/api_jsonrpc.php')]
        self.url = url
        self.username = username
        self.password = password
        self.zapi = None
        self.connect()

    def connect(self):
        try:
            self.zapi = ZabbixAPI(self.url)
            # Выполняем логин через do_request
            response = self.zapi.do_request('user.login', {
                'user': self.username,
                'password': self.password
            })
            self.zapi.auth = response['result']
            logger.info(f"Connected to Zabbix API v{self.zapi.api_version()}")
        except Exception as e:
            logger.error(f"Failed to connect to Zabbix: {e}")
            raise

    def create_host(self, host_data: dict) -> Optional[str]:
        try:
            result = self.zapi.host.create(**host_data)
            host_id = result['hostids'][0]
            logger.info(f"Created host {host_data.get('host')} with id {host_id}")
            return host_id
        except Exception as e:
            logger.error(f"Failed to create host: {e}")
            return None

    def get_host_problems(self, host_id: str):
        problems = self.zapi.trigger.get(
            filter={'value': 1},
            hostids=host_id,
            selectHosts=['host'],
            output=['triggerid', 'description', 'priority', 'lastchange']
        )
        return problems
