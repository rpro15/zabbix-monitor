"""Telegram notification service."""

from typing import List, Optional
import logging
import requests

logger = logging.getLogger(__name__)


class TelegramService:
    """Send alert notifications to Telegram chats."""

    def __init__(self, token: str, chat_ids: str, message_format: str = "short", base_url: Optional[str] = None):
        self.token = token
        self.chat_ids = self._parse_chat_ids(chat_ids)
        self.message_format = (message_format or "short").lower()
        self.base_url = base_url

    def _parse_chat_ids(self, chat_ids: str) -> List[str]:
        return [chat_id.strip() for chat_id in chat_ids.split(',') if chat_id.strip()]

    def send_message(self, text: str) -> None:
        if not self.token or not self.chat_ids:
            logger.warning("Telegram token or chat IDs missing, skipping message")
            return

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        for chat_id in self.chat_ids:
            try:
                response = requests.post(
                    url,
                    json={"chat_id": chat_id, "text": text},
                    timeout=5
                )
                if response.status_code >= 400:
                    logger.error(
                        f"Telegram send failed for chat {chat_id}: {response.status_code} {response.text}"
                    )
            except Exception as e:
                logger.error(f"Telegram send error for chat {chat_id}: {str(e)}")

    def notify_new_alert(self, alert) -> None:
        self.send_message(self._format_alert("NEW", alert))

    def notify_ack(self, alert, operator_name: str, reason: Optional[str] = None) -> None:
        self.send_message(self._format_alert("ACKNOWLEDGED", alert, operator_name, reason))

    def notify_resolved(self, alert) -> None:
        self.send_message(self._format_alert("RESOLVED", alert))

    def _format_alert(
        self,
        status: str,
        alert,
        operator_name: Optional[str] = None,
        reason: Optional[str] = None
    ) -> str:
        severity_text = self._severity_text(getattr(alert, "severity", None))
        host = getattr(alert, "host", "Unknown")
        name = getattr(alert, "alert_name", "Unnamed Alert")
        created_at = getattr(alert, "created_at", None)
        created_str = created_at.isoformat() if created_at else "N/A"
        event_id = getattr(alert, "zabbix_event_id", "N/A")
        problem_id = getattr(alert, "zabbix_problem_id", "N/A")

        if self.message_format == "detailed":
            lines = [
                f"Status: {status}",
                f"Severity: {severity_text}",
                f"Host: {host}",
                f"Name: {name}",
                f"Time: {created_str}",
                f"Event ID: {event_id}",
                f"Problem ID: {problem_id}"
            ]
            if operator_name:
                lines.append(f"By: {operator_name}")
            if reason:
                lines.append(f"Reason: {reason}")
            if self.base_url:
                lines.append(f"Dashboard: {self.base_url}/alerts")
            return "\n".join(lines)

        # Short format
        parts = [f"{status} [{severity_text}]", f"Host: {host}", name]
        if operator_name:
            parts.append(f"By: {operator_name}")
        if reason:
            parts.append(f"Reason: {reason}")
        return " | ".join(parts)

    def _severity_text(self, severity: Optional[int]) -> str:
        severity_map = {
            0: "NOT CLASSIFIED",
            1: "INFORMATION",
            2: "WARNING",
            3: "AVERAGE",
            4: "HIGH",
            5: "CRITICAL"
        }
        return severity_map.get(severity, "UNKNOWN")
