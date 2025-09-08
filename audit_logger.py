"""Расширенная система логирования для аудита действий пользователей."""

import json
import sqlite3
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from loguru import logger


class AuditEventType(Enum):
    """Типы событий для аудита."""

    # Аутентификация
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"

    # Управление пользователями
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DEACTIVATED = "user_deactivated"
    ROLE_CHANGED = "role_changed"

    # Проверка документов
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_CHECKED = "document_checked"
    DOCUMENT_DOWNLOADED = "document_downloaded"
    TASK_CREATED = "task_created"

    # Аналитика
    ANALYTICS_VIEWED = "analytics_viewed"
    REPORT_GENERATED = "report_generated"
    DASHBOARD_ACCESSED = "dashboard_accessed"

    # Поставщики
    SUPPLIER_VIEWED = "supplier_viewed"
    SUPPLIER_HISTORY_ACCESSED = "supplier_history_accessed"
    PROPOSAL_CHECKED = "proposal_checked"

    # Системные события
    API_ACCESS = "api_access"
    PERMISSION_DENIED = "permission_denied"
    ERROR_OCCURRED = "error_occurred"
    SYSTEM_CONFIG_CHANGED = "system_config_changed"


class AuditSeverity(Enum):
    """Уровни важности событий аудита."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditLogger:
    """Класс для детального логирования действий пользователей."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or "audit.db"
        self._init_database()

        # Настройка специального логгера для аудита
        self._setup_audit_logger()

    def _init_database(self):
        """Инициализация базы данных для аудита."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    user_id TEXT,
                    username TEXT,
                    user_role TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    endpoint TEXT,
                    method TEXT,
                    resource_id TEXT,
                    resource_type TEXT,
                    action_details TEXT,
                    request_data TEXT,
                    response_status INTEGER,
                    processing_time_ms REAL,
                    session_id TEXT,
                    additional_data TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Создаем индексы для быстрого поиска
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_log(timestamp)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON audit_log(user_id)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_event_type ON audit_log(event_type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_severity ON audit_log(severity)"
            )

            conn.commit()

    def _setup_audit_logger(self):
        """Настройка специального логгера для аудита."""
        audit_log_path = Path("logs/audit.log")
        audit_log_path.parent.mkdir(parents=True, exist_ok=True)

        # Добавляем специальный обработчик для аудита
        logger.add(
            audit_log_path,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | AUDIT | {message}",
            level="INFO",
            rotation="50 MB",
            retention="6 months",
            compression="zip",
            filter=lambda record: record.get("audit", False),
        )

    def log_event(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity = AuditSeverity.INFO,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        user_role: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        action_details: Optional[str] = None,
        request_data: Optional[dict[str, Any]] = None,
        response_status: Optional[int] = None,
        processing_time_ms: Optional[float] = None,
        session_id: Optional[str] = None,
        additional_data: Optional[dict[str, Any]] = None,
    ):
        """Логирование события аудита."""
        timestamp = datetime.now().isoformat()

        # Подготавливаем данные для записи в БД
        audit_record = {
            "timestamp": timestamp,
            "event_type": event_type.value,
            "severity": severity.value,
            "user_id": user_id,
            "username": username,
            "user_role": user_role,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "endpoint": endpoint,
            "method": method,
            "resource_id": resource_id,
            "resource_type": resource_type,
            "action_details": action_details,
            "request_data": json.dumps(request_data) if request_data else None,
            "response_status": response_status,
            "processing_time_ms": processing_time_ms,
            "session_id": session_id,
            "additional_data": json.dumps(additional_data) if additional_data else None,
        }

        # Записываем в базу данных
        self._save_to_database(audit_record)

        # Записываем в файловый лог
        log_message = self._format_log_message(audit_record)
        logger.bind(audit=True).info(log_message)

        # Для критических событий также логируем в основной лог
        if severity in [AuditSeverity.ERROR, AuditSeverity.CRITICAL]:
            logger.error(f"AUDIT ALERT: {log_message}")

    def _save_to_database(self, record: dict[str, Any]):
        """Сохранение записи аудита в базу данных."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                placeholders = ", ".join(["?" for _ in record.keys()])
                columns = ", ".join(record.keys())

                conn.execute(
                    f"INSERT INTO audit_log ({columns}) VALUES ({placeholders})",
                    list(record.values()),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Ошибка при сохранении записи аудита: {e}")

    def _format_log_message(self, record: dict[str, Any]) -> str:
        """Форматирование сообщения для лога."""
        parts = [f"Event: {record['event_type']}", f"Severity: {record['severity']}"]

        if record.get("username"):
            parts.append(
                f"User: {record['username']} ({record.get('user_role', 'unknown')})"
            )

        if record.get("endpoint"):
            parts.append(f"Endpoint: {record['method']} {record['endpoint']}")

        if record.get("resource_type") and record.get("resource_id"):
            parts.append(f"Resource: {record['resource_type']}#{record['resource_id']}")

        if record.get("action_details"):
            parts.append(f"Details: {record['action_details']}")

        if record.get("response_status"):
            parts.append(f"Status: {record['response_status']}")

        if record.get("processing_time_ms"):
            parts.append(f"Time: {record['processing_time_ms']}ms")

        return " | ".join(parts)

    def get_user_actions(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_types: Optional[list[AuditEventType]] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Получение действий пользователя."""
        query = "SELECT * FROM audit_log WHERE user_id = ?"
        params = [user_id]

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.isoformat())

        if event_types:
            event_type_values = [et.value for et in event_types]
            placeholders = ", ".join(["?" for _ in event_type_values])
            query += f" AND event_type IN ({placeholders})"
            params.extend(event_type_values)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_audit_logs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        severity: Optional[AuditSeverity] = None,
        event_types: Optional[list[AuditEventType]] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Получение логов аудита с фильтрацией."""
        query = "SELECT * FROM audit_log WHERE 1=1"
        count_query = "SELECT COUNT(*) as total FROM audit_log WHERE 1=1"
        params = []

        # Добавляем фильтры
        if start_date:
            filter_clause = " AND timestamp >= ?"
            query += filter_clause
            count_query += filter_clause
            params.append(start_date.isoformat())

        if end_date:
            filter_clause = " AND timestamp <= ?"
            query += filter_clause
            count_query += filter_clause
            params.append(end_date.isoformat())

        if severity:
            filter_clause = " AND severity = ?"
            query += filter_clause
            count_query += filter_clause
            params.append(severity.value)

        if event_types:
            event_type_values = [et.value for et in event_types]
            placeholders = ", ".join(["?" for _ in event_type_values])
            filter_clause = f" AND event_type IN ({placeholders})"
            query += filter_clause
            count_query += filter_clause
            params.extend(event_type_values)

        if user_id:
            filter_clause = " AND user_id = ?"
            query += filter_clause
            count_query += filter_clause
            params.append(user_id)

        # Добавляем сортировку и лимиты
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Получаем общее количество записей
            cursor = conn.execute(count_query, params)
            total = cursor.fetchone()["total"]

            # Получаем записи с пагинацией
            cursor = conn.execute(query, params + [limit, offset])
            logs = [dict(row) for row in cursor.fetchall()]

            return {
                "logs": logs,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total,
            }

    def get_audit_statistics(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> dict[str, Any]:
        """Получение статистики аудита."""
        query_base = "SELECT * FROM audit_log WHERE 1=1"
        params = []

        if start_date:
            query_base += " AND timestamp >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query_base += " AND timestamp <= ?"
            params.append(end_date.isoformat())

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Общее количество событий
            cursor = conn.execute(
                f"SELECT COUNT(*) as total FROM ({query_base})", params
            )
            total_events = cursor.fetchone()["total"]

            # События по типам
            cursor = conn.execute(
                f"""
                SELECT event_type, COUNT(*) as count
                FROM ({query_base})
                GROUP BY event_type
                ORDER BY count DESC
            """,
                params,
            )
            events_by_type = {
                row["event_type"]: row["count"] for row in cursor.fetchall()
            }

            # События по уровням важности
            cursor = conn.execute(
                f"""
                SELECT severity, COUNT(*) as count
                FROM ({query_base})
                GROUP BY severity
            """,
                params,
            )
            events_by_severity = {
                row["severity"]: row["count"] for row in cursor.fetchall()
            }

            # Активные пользователи
            cursor = conn.execute(
                f"""
                SELECT COUNT(DISTINCT user_id) as active_users
                FROM ({query_base})
                WHERE user_id IS NOT NULL
            """,
                params,
            )
            active_users = cursor.fetchone()["active_users"]

            # Топ пользователей по активности
            cursor = conn.execute(
                f"""
                SELECT username, user_role, COUNT(*) as activity_count
                FROM ({query_base})
                WHERE username IS NOT NULL
                GROUP BY username, user_role
                ORDER BY activity_count DESC
                LIMIT 10
            """,
                params,
            )
            top_users = [
                {
                    "username": row["username"],
                    "user_role": row["user_role"],
                    "activity_count": row["activity_count"],
                }
                for row in cursor.fetchall()
            ]

            return {
                "total_events": total_events,
                "events_by_type": events_by_type,
                "events_by_severity": events_by_severity,
                "active_users": active_users,
                "top_users": top_users,
            }


# Глобальный экземпляр аудит-логгера
audit_logger = AuditLogger()


# Удобные функции для логирования различных типов событий
def log_authentication(
    username: str, success: bool, ip_address: str = None, user_agent: str = None
):
    """Логирование событий аутентификации."""
    event_type = (
        AuditEventType.LOGIN_SUCCESS if success else AuditEventType.LOGIN_FAILED
    )
    severity = AuditSeverity.INFO if success else AuditSeverity.WARNING

    audit_logger.log_event(
        event_type=event_type,
        severity=severity,
        username=username,
        ip_address=ip_address,
        user_agent=user_agent,
        action_details=f"Попытка входа {'успешна' if success else 'неуспешна'}",
    )


def log_document_action(
    user_id: str,
    username: str,
    action: str,
    document_name: str,
    endpoint: str = None,
    processing_time: float = None,
):
    """Логирование действий с документами."""
    event_type_map = {
        "upload": AuditEventType.DOCUMENT_UPLOADED,
        "check": AuditEventType.DOCUMENT_CHECKED,
        "download": AuditEventType.DOCUMENT_DOWNLOADED,
    }

    audit_logger.log_event(
        event_type=event_type_map.get(action, AuditEventType.API_ACCESS),
        user_id=user_id,
        username=username,
        endpoint=endpoint,
        resource_type="document",
        resource_id=document_name,
        action_details=f"Действие с документом: {action}",
        processing_time_ms=processing_time,
    )


def log_user_management(
    admin_user: str, target_user: str, action: str, details: str = None
):
    """Логирование действий по управлению пользователями."""
    event_type_map = {
        "create": AuditEventType.USER_CREATED,
        "update": AuditEventType.USER_UPDATED,
        "deactivate": AuditEventType.USER_DEACTIVATED,
        "role_change": AuditEventType.ROLE_CHANGED,
    }

    audit_logger.log_event(
        event_type=event_type_map.get(action, AuditEventType.USER_UPDATED),
        username=admin_user,
        resource_type="user",
        resource_id=target_user,
        action_details=details or f"Управление пользователем: {action}",
        severity=AuditSeverity.INFO,
    )


def log_api_access(
    user_id: str,
    username: str,
    endpoint: str,
    method: str,
    status_code: int,
    processing_time: float = None,
    ip_address: str = None,
):
    """Логирование доступа к API."""
    severity = AuditSeverity.INFO
    if status_code >= 400:
        severity = AuditSeverity.WARNING if status_code < 500 else AuditSeverity.ERROR

    audit_logger.log_event(
        event_type=AuditEventType.API_ACCESS,
        severity=severity,
        user_id=user_id,
        username=username,
        endpoint=endpoint,
        method=method,
        response_status=status_code,
        processing_time_ms=processing_time,
        ip_address=ip_address,
    )


def log_permission_denied(
    user_id: str, username: str, endpoint: str, required_permission: str
):
    """Логирование отказа в доступе."""
    audit_logger.log_event(
        event_type=AuditEventType.PERMISSION_DENIED,
        severity=AuditSeverity.WARNING,
        user_id=user_id,
        username=username,
        endpoint=endpoint,
        action_details=f"Отказ в доступе. Требуется разрешение: {required_permission}",
    )
