"""Модуль аудита для отслеживания действий пользователей и изменений в системе."""

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from audit_logger import (
    AuditEventType,
    AuditSeverity,
    audit_logger,
)
from src.models import User


@dataclass
class AuditTrail:
    """Модель для аудиторского следа."""

    id: Optional[int] = None
    timestamp: datetime = None
    event_type: str = ""
    user_id: Optional[str] = None
    username: Optional[str] = None
    user_role: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: str = ""
    old_values: Optional[dict[str, Any]] = None
    new_values: Optional[dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    additional_context: Optional[dict[str, Any]] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class SystemChange:
    """Модель для отслеживания системных изменений."""

    change_id: str
    timestamp: datetime
    change_type: str  # config, schema, permission, etc.
    component: str
    description: str
    changed_by: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    impact_level: str = "low"  # low, medium, high, critical
    rollback_info: Optional[dict[str, Any]] = None


class AuditManager:
    """Менеджер для управления аудитом и отслеживанием изменений."""

    def __init__(self, db_path: str = "audit.db"):
        self.db_path = db_path
        self.audit_logger = audit_logger
        self._init_audit_tables()

    def _init_audit_tables(self):
        """Инициализация дополнительных таблиц для аудита."""
        with sqlite3.connect(self.db_path) as conn:
            # Таблица для детального отслеживания изменений
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_trail (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    user_id TEXT,
                    username TEXT,
                    user_role TEXT,
                    resource_type TEXT,
                    resource_id TEXT,
                    action TEXT NOT NULL,
                    old_values TEXT,
                    new_values TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    session_id TEXT,
                    additional_context TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Таблица для системных изменений
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS system_changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    change_id TEXT UNIQUE NOT NULL,
                    timestamp TEXT NOT NULL,
                    change_type TEXT NOT NULL,
                    component TEXT NOT NULL,
                    description TEXT NOT NULL,
                    changed_by TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    impact_level TEXT DEFAULT 'low',
                    rollback_info TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Таблица для сессий пользователей
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    user_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    last_activity TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Создаем индексы
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_trail_timestamp ON audit_trail(timestamp)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_trail_user ON audit_trail(user_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_trail_resource ON audit_trail(resource_type, resource_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_system_changes_timestamp ON system_changes(timestamp)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id)"
            )

            conn.commit()

    def record_change(
        self,
        event_type: str,
        action: str,
        user: Optional[User] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        old_values: Optional[dict[str, Any]] = None,
        new_values: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        additional_context: Optional[dict[str, Any]] = None,
    ) -> AuditTrail:
        """Записать изменение в аудиторский след."""

        audit_trail = AuditTrail(
            timestamp=datetime.now(),
            event_type=event_type,
            user_id=user.user_id if user else None,
            username=user.username if user else None,
            user_role=user.role if user else None,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            additional_context=additional_context,
        )

        # Сохраняем в базу данных
        self._save_audit_trail(audit_trail)

        # Логируем через audit_logger
        severity = self._determine_severity(event_type, action)
        self.audit_logger.log_event(
            event_type=self._map_to_audit_event_type(event_type),
            severity=severity,
            user_id=audit_trail.user_id,
            username=audit_trail.username,
            user_role=audit_trail.user_role,
            resource_type=resource_type,
            resource_id=resource_id,
            action_details=action,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            additional_data=additional_context,
        )

        return audit_trail

    def _save_audit_trail(self, trail: AuditTrail):
        """Сохранить аудиторский след в базу данных."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO audit_trail (
                    timestamp, event_type, user_id, username, user_role,
                    resource_type, resource_id, action, old_values, new_values,
                    ip_address, user_agent, session_id, additional_context
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    trail.timestamp.isoformat(),
                    trail.event_type,
                    trail.user_id,
                    trail.username,
                    trail.user_role,
                    trail.resource_type,
                    trail.resource_id,
                    trail.action,
                    json.dumps(trail.old_values) if trail.old_values else None,
                    json.dumps(trail.new_values) if trail.new_values else None,
                    trail.ip_address,
                    trail.user_agent,
                    trail.session_id,
                    json.dumps(trail.additional_context)
                    if trail.additional_context
                    else None,
                ),
            )
            conn.commit()

    def _determine_severity(self, event_type: str, action: str) -> AuditSeverity:
        """Определить уровень важности события."""
        critical_events = [
            "user_deleted",
            "role_changed",
            "permission_denied",
            "security_breach",
        ]
        warning_events = ["login_failed", "unauthorized_access", "data_export"]

        if any(
            critical in event_type.lower() or critical in action.lower()
            for critical in critical_events
        ):
            return AuditSeverity.CRITICAL
        elif any(
            warning in event_type.lower() or warning in action.lower()
            for warning in warning_events
        ):
            return AuditSeverity.WARNING
        else:
            return AuditSeverity.INFO

    def _map_to_audit_event_type(self, event_type: str) -> AuditEventType:
        """Маппинг типа события к AuditEventType."""
        mapping = {
            "authentication": AuditEventType.LOGIN_SUCCESS,
            "user_management": AuditEventType.USER_CREATED,
            "document_processing": AuditEventType.DOCUMENT_CHECKED,
            "analytics_access": AuditEventType.ANALYTICS_VIEWED,
            "api_access": AuditEventType.API_ACCESS,
            "permission_check": AuditEventType.PERMISSION_DENIED,
        }
        return mapping.get(event_type, AuditEventType.API_ACCESS)

    def record_system_change(
        self,
        change_id: str,
        change_type: str,
        component: str,
        description: str,
        changed_by: str,
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        impact_level: str = "low",
        rollback_info: Optional[dict[str, Any]] = None,
    ) -> SystemChange:
        """Записать системное изменение."""

        system_change = SystemChange(
            change_id=change_id,
            timestamp=datetime.now(),
            change_type=change_type,
            component=component,
            description=description,
            changed_by=changed_by,
            old_value=old_value,
            new_value=new_value,
            impact_level=impact_level,
            rollback_info=rollback_info,
        )

        # Сохраняем в базу данных
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO system_changes (
                    change_id, timestamp, change_type, component, description,
                    changed_by, old_value, new_value, impact_level, rollback_info
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    system_change.change_id,
                    system_change.timestamp.isoformat(),
                    system_change.change_type,
                    system_change.component,
                    system_change.description,
                    system_change.changed_by,
                    json.dumps(system_change.old_value)
                    if system_change.old_value
                    else None,
                    json.dumps(system_change.new_value)
                    if system_change.new_value
                    else None,
                    system_change.impact_level,
                    json.dumps(system_change.rollback_info)
                    if system_change.rollback_info
                    else None,
                ),
            )
            conn.commit()

        # Логируем критические изменения
        if impact_level in ["high", "critical"]:
            self.audit_logger.log_event(
                event_type=AuditEventType.SYSTEM_CONFIG_CHANGED,
                severity=AuditSeverity.CRITICAL
                if impact_level == "critical"
                else AuditSeverity.WARNING,
                username=changed_by,
                action_details=f"Системное изменение: {description}",
                additional_data={
                    "change_id": change_id,
                    "component": component,
                    "impact_level": impact_level,
                },
            )

        return system_change

    def start_user_session(
        self,
        session_id: str,
        user_id: str,
        username: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Начать пользовательскую сессию."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO user_sessions (
                    session_id, user_id, username, start_time, ip_address,
                    user_agent, is_active, last_activity
                ) VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """,
                (
                    session_id,
                    user_id,
                    username,
                    datetime.now().isoformat(),
                    ip_address,
                    user_agent,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

    def end_user_session(self, session_id: str):
        """Завершить пользовательскую сессию."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE user_sessions
                SET end_time = ?, is_active = 0
                WHERE session_id = ?
            """,
                (datetime.now().isoformat(), session_id),
            )
            conn.commit()

    def update_session_activity(self, session_id: str):
        """Обновить время последней активности сессии."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE user_sessions
                SET last_activity = ?
                WHERE session_id = ? AND is_active = 1
            """,
                (datetime.now().isoformat(), session_id),
            )
            conn.commit()

    def get_user_audit_trail(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        resource_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Получить аудиторский след пользователя."""
        query = "SELECT * FROM audit_trail WHERE user_id = ?"
        params = [user_id]

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.isoformat())

        if resource_type:
            query += " AND resource_type = ?"
            params.append(resource_type)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_resource_audit_trail(
        self,
        resource_type: str,
        resource_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Получить аудиторский след ресурса."""
        query = "SELECT * FROM audit_trail WHERE resource_type = ? AND resource_id = ?"
        params = [resource_type, resource_id]

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.isoformat())

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_system_changes(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        change_type: Optional[str] = None,
        component: Optional[str] = None,
        impact_level: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Получить системные изменения."""
        query = "SELECT * FROM system_changes WHERE 1=1"
        params = []

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.isoformat())

        if change_type:
            query += " AND change_type = ?"
            params.append(change_type)

        if component:
            query += " AND component = ?"
            params.append(component)

        if impact_level:
            query += " AND impact_level = ?"
            params.append(impact_level)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_active_sessions(self) -> list[dict[str, Any]]:
        """Получить активные пользовательские сессии."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM user_sessions
                WHERE is_active = 1
                ORDER BY last_activity DESC
            """
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_user_sessions(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Получить сессии пользователя."""
        query = "SELECT * FROM user_sessions WHERE user_id = ?"
        params = [user_id]

        if start_date:
            query += " AND start_time >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query += " AND start_time <= ?"
            params.append(end_date.isoformat())

        query += " ORDER BY start_time DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def generate_audit_report(
        self,
        start_date: datetime,
        end_date: datetime,
        include_user_actions: bool = True,
        include_system_changes: bool = True,
        include_sessions: bool = True,
    ) -> dict[str, Any]:
        """Сгенерировать отчет по аудиту."""
        report = {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "generated_at": datetime.now().isoformat(),
        }

        if include_user_actions:
            # Получаем статистику по действиям пользователей
            user_actions = self.audit_logger.get_audit_statistics(start_date, end_date)
            report["user_actions"] = user_actions

        if include_system_changes:
            # Получаем системные изменения
            system_changes = self.get_system_changes(start_date, end_date)
            report["system_changes"] = {
                "total_changes": len(system_changes),
                "changes_by_impact": self._group_changes_by_impact(system_changes),
                "changes_by_component": self._group_changes_by_component(
                    system_changes
                ),
                "recent_changes": system_changes[:10],  # Последние 10 изменений
            }

        if include_sessions:
            # Получаем статистику по сессиям
            sessions_stats = self._get_sessions_statistics(start_date, end_date)
            report["sessions"] = sessions_stats

        return report

    def _group_changes_by_impact(self, changes: list[dict[str, Any]]) -> dict[str, int]:
        """Группировка изменений по уровню воздействия."""
        impact_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for change in changes:
            impact_level = change.get("impact_level", "low")
            impact_counts[impact_level] = impact_counts.get(impact_level, 0) + 1
        return impact_counts

    def _group_changes_by_component(
        self, changes: list[dict[str, Any]]
    ) -> dict[str, int]:
        """Группировка изменений по компонентам."""
        component_counts = {}
        for change in changes:
            component = change.get("component", "unknown")
            component_counts[component] = component_counts.get(component, 0) + 1
        return component_counts

    def _get_sessions_statistics(
        self, start_date: datetime, end_date: datetime
    ) -> dict[str, Any]:
        """Получить статистику по сессиям."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Общее количество сессий
            cursor = conn.execute(
                """
                SELECT COUNT(*) as total_sessions
                FROM user_sessions
                WHERE start_time >= ? AND start_time <= ?
            """,
                (start_date.isoformat(), end_date.isoformat()),
            )
            total_sessions = cursor.fetchone()["total_sessions"]

            # Уникальные пользователи
            cursor = conn.execute(
                """
                SELECT COUNT(DISTINCT user_id) as unique_users
                FROM user_sessions
                WHERE start_time >= ? AND start_time <= ?
            """,
                (start_date.isoformat(), end_date.isoformat()),
            )
            unique_users = cursor.fetchone()["unique_users"]

            # Активные сессии
            cursor = conn.execute(
                """
                SELECT COUNT(*) as active_sessions
                FROM user_sessions
                WHERE is_active = 1
            """
            )
            active_sessions = cursor.fetchone()["active_sessions"]

            return {
                "total_sessions": total_sessions,
                "unique_users": unique_users,
                "active_sessions": active_sessions,
            }


# Глобальный экземпляр менеджера аудита
audit_manager = AuditManager()


# Декораторы для автоматического аудита
def audit_action(event_type: str, resource_type: str = None):
    """Декоратор для автоматического аудита действий."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            # Здесь можно добавить логику извлечения пользователя из контекста
            # Пока оставляем заглушку
            result = func(*args, **kwargs)

            # Записываем действие в аудит
            audit_manager.record_change(
                event_type=event_type,
                action=func.__name__,
                resource_type=resource_type,
                additional_context={"function": func.__name__, "args_count": len(args)},
            )

            return result

        return wrapper

    return decorator


# Функции для интеграции с существующими модулями
def audit_user_action(
    user,
    action: str,
    resource_type: str = None,
    resource_id: str = None,
    details: dict[str, Any] = None,
):
    """Аудит действия пользователя.

    Args:
        user: Объект User или словарь с данными пользователя
    """
    # Проверяем, является ли user словарем
    if isinstance(user, dict):
        # Если это словарь, создаем временный объект с нужными атрибутами
        from types import SimpleNamespace

        user_obj = SimpleNamespace(
            user_id=user.get("user_id"),
            username=user.get("username"),
            role=user.get("role"),
        )
        user = user_obj

    audit_manager.record_change(
        event_type="user_action",
        action=action,
        user=user,
        resource_type=resource_type,
        resource_id=resource_id,
        additional_context=details,
    )


def audit_document_processing(
    user: User,
    document_name: str,
    action: str,
    processing_time: float = None,
    result: dict[str, Any] = None,
):
    """Аудит обработки документов."""
    audit_manager.record_change(
        event_type="document_processing",
        action=action,
        user=user,
        resource_type="document",
        resource_id=document_name,
        additional_context={
            "processing_time_ms": processing_time,
            "result_summary": result,
        },
    )


def audit_analytics_access(
    user: User, analytics_type: str, filters: dict[str, Any] = None
):
    """Аудит доступа к аналитике."""
    audit_manager.record_change(
        event_type="analytics_access",
        action=f"access_{analytics_type}",
        user=user,
        resource_type="analytics",
        resource_id=analytics_type,
        additional_context={"filters": filters},
    )
