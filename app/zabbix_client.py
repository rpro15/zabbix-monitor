#!/usr/bin/env python3
"""
zabbix_client.py

Небольшой, надёжный клиент к Zabbix API.
* Автоматические попытки подключения (retry + delay)
* «Мягкое» поведение – при отсутствии Zabbix клиент остаётся в состоянии
  `self._zapi is None`, а вызовы методов просто логируют ошибку.
* Обработчик дублирующего хоста.
* Поддержка контекст‑менеджера (with … as client:).
"""

from __future__ import annotations

import logging
import time
from typing import Any, Mapping, List, Dict, Optional

from pyzabbix import ZabbixAPI, ZabbixAPIException

# ----------------------------------------------------------------------
# Базовое конфигурирование логирования (если приложение уже его задало,
# эта строка ничего не меняет)
# ----------------------------------------------------------------------
_logger = logging.getLogger(__name__)
if not _logger.handlers:          # добавить базовый handler только один раз
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s – %(message)s",
    )
logger = _logger


class ZabbixClient:
    """
    Мини‑клиент Zabbix API.

    Parameters
    ----------
    url : str
        Полный URL к JSON‑RPC‑конечному пункту Zabbix,
        например ``http://zabbix-web:8080/api_jsonrpc.php``.
    username : str
        Логин пользователя.
    password : str
        Пароль пользователя.
    retries : int, optional
        Число попыток подключения (по‑умолчанию 5).
    delay : int, optional
        Пауза, сек., между попытками (по‑умолчанию 5 сек.).
    """
    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        retries: int = 5,
        delay: int = 5,
    ) -> None:
        self.url = url
        self.username = username
        self.password = password
        self._zapi: Optional[ZabbixAPI] = None
        self._connect_with_retry(retries=retries, delay=delay)

    # ------------------------------------------------------------------
    # Приватный метод подключения с повторными попытками
    # ------------------------------------------------------------------
    def _connect_with_retry(self, retries: int = 5, delay: int = 5) -> None:
        """Попытаться выполнить login к Zabbix ``retries`` раз."""
        for attempt in range(1, retries + 1):
            try:
                api = ZabbixAPI(self.url)
                api.login(self.username, self.password)   # официальное API‑login
                self._zapi = api
                logger.info("Connected to Zabbix API v%s", api.api_version())
                return
            except Exception as exc:                         # pylint: disable=broad-except
                logger.warning(
                    "Connection attempt %d/%d failed: %s",
                    attempt,
                    retries,
                    exc,
                )
                if attempt < retries:
                    time.sleep(delay)

        logger.error("Unable to connect to Zabbix after %d attempts", retries)
        self._zapi = None

    # ------------------------------------------------------------------
    # Свойство – наружный код может проверить, есть ли живой объект API
    # ------------------------------------------------------------------
    @property
    def zapi(self) -> Optional[ZabbixAPI]:
        """Возвращает внутренний объект ZabbixAPI (может быть None)."""
        return self._zapi

    # ------------------------------------------------------------------
    # Публичные методы
    # ------------------------------------------------------------------
    def create_host(self, host_data: Mapping[str, Any]) -> Optional[str]:
        """
        Создать хост в Zabbix.

        Parameters
        ----------
        host_data : Mapping[str, Any]
            Параметры, которые принимает ``ZabbixAPI.host.create``:
            ``host``, ``interfaces``, ``groups`` и т.д.

        Returns
        -------
        Optional[str]
            Идентификатор созданного хоста, либо ``None`` в случае ошибки.
            Если хост уже существует, возвращаем его ``hostid`` (удобно
            для идемпотентных скриптов).
        """
        if not self._zapi:
            logger.error("Zabbix client not connected – cannot create host")
            return None

        # 1️⃣ Проверим, есть ли уже хост с таким именем
        try:
            existing = self._zapi.host.get(filter={"host": host_data.get("host")})
            if existing:
                host_id = existing[0]["hostid"]
                logger.info(
                    "Host %s already exists (id=%s) – returning existing id",
                    host_data.get("host"),
                    host_id,
                )
                return host_id
        except Exception as exc:               # pragma: no cover
            logger.warning("Failed to pre‑check host existence: %s", exc)

        # 2️⃣ Пытаемся создать
        try:
            result = self._zapi.host.create(**host_data)
            hostids = result.get("hostids")
            if not hostids:
                logger.error("Zabbix returned no hostids: %s", result)
                return None
            host_id = str(hostids[0])
            logger.info(
                "Created host %s with id %s",
                host_data.get("host"),
                host_id,
            )
            return host_id
        except ZabbixAPIException as exc:
            # Если Zabbix вернул «Host with the same name … already exists»
            # (code -32602), попытаемся вытащить уже существующий id.
            if getattr(exc, "code", None) == -32602 and "already exists" in str(exc):
                logger.info(
                    "Host %s already exists – trying to fetch its id",
                    host_data.get("host"),
                )
                try:
                    existing = self._zapi.host.get(filter={"host": host_data.get("host")})
                    if existing:
                        host_id = existing[0]["hostid"]
                        logger.info("Found existing host id=%s", host_id)
                        return host_id
                except Exception as inner_exc:   # pragma: no cover
                    logger.error("Failed to fetch existing host id: %s", inner_exc)
            logger.error("Failed to create host: %s", exc)
            return None
        except Exception as exc:               # pragma: no cover
            logger.error("Unexpected error while creating host: %s", exc)
            return None

    def get_host_problems(self, host_id: str) -> List[Dict[str, Any]]:
        """
        Получить активные триггеры (value = 1) для хоста.

        Parameters
        ----------
        host_id : str
            Идентификатор хоста в Zabbix.

        Returns
        -------
        List[dict]
            Список словарей‑триггеров. Пустой список – ошибок нет
            или клиент не подключён.
        """
        if not self._zapi:
            logger.error("Zabbix client not connected – cannot fetch problems")
            return []

        try:
            problems = self._zapi.trigger.get(
                filter={"value": 1},
                hostids=host_id,
                selectHosts=["host"],
                output=[
                    "triggerid",
                    "description",
                    "priority",
                    "lastchange",
                ],
            )
            return problems
        except ZabbixAPIException as exc:
            logger.error("Zabbix API error while fetching problems: %s", exc)
            return []
        except Exception as exc:               # pragma: no cover
            logger.error("Unexpected error while fetching problems: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Очистка сессии (необязательно, но удобно)
    # ------------------------------------------------------------------
    def logout(self) -> None:
        """Явно завершить сессию в Zabbix (если была открыта)."""
        if self._zapi:
            try:
                self._zapi.logout()
                logger.info("Logged out from Zabbix")
            except Exception:                     # pylint: disable=broad-except
                pass
            finally:
                self._zapi = None

    # ------------------------------------------------------------------
    # Поддержка контекст‑менеджера
    # ------------------------------------------------------------------
    def __enter__(self) -> "ZabbixClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.logout()

    # ------------------------------------------------------------------
    # Краткое строковое представление (debug)
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        state = "connected" if self._zapi else "disconnected"
        return f"<ZabbixClient url={self.url!r} status={state}>"
