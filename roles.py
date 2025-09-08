"""Модуль управления ролями и правами доступа"""

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class UserRole(Enum):
    """Роли пользователей в системе"""

    MANAGER = "manager"  # Менеджер по закупкам
    SUPERVISOR = "supervisor"  # Руководитель отдела
    ADMINISTRATOR = "administrator"  # Системный администратор


class Permission(Enum):
    """Разрешения в системе"""

    # Документы
    VIEW_DOCUMENTS = "view_documents"
    UPLOAD_DOCUMENTS = "upload_documents"
    APPROVE_DOCUMENTS = "approve_documents"
    REJECT_DOCUMENTS = "reject_documents"
    DELETE_DOCUMENTS = "delete_documents"

    # Поставщики
    VIEW_SUPPLIERS = "view_suppliers"
    MANAGE_SUPPLIERS = "manage_suppliers"

    # Аналитика
    VIEW_ANALYTICS = "view_analytics"
    VIEW_DETAILED_ANALYTICS = "view_detailed_analytics"

    # Пользователи
    VIEW_USERS = "view_users"
    MANAGE_USERS = "manage_users"

    # Система
    VIEW_AUDIT_LOGS = "view_audit_logs"
    MANAGE_SYSTEM_SETTINGS = "manage_system_settings"

    # API
    ACCESS_API = "access_api"
    ADMIN_API = "admin_api"


class RoleManager:
    """Менеджер ролей и разрешений"""

    def __init__(self):
        self.role_permissions = self._init_role_permissions()

    def _init_role_permissions(self) -> dict[UserRole, set[Permission]]:
        """Инициализация разрешений для каждой роли"""
        return {
            UserRole.MANAGER: {
                Permission.VIEW_DOCUMENTS,
                Permission.UPLOAD_DOCUMENTS,
                Permission.VIEW_SUPPLIERS,
                Permission.VIEW_ANALYTICS,
                Permission.ACCESS_API,
            },
            UserRole.SUPERVISOR: {
                Permission.VIEW_DOCUMENTS,
                Permission.UPLOAD_DOCUMENTS,
                Permission.APPROVE_DOCUMENTS,
                Permission.REJECT_DOCUMENTS,
                Permission.VIEW_SUPPLIERS,
                Permission.MANAGE_SUPPLIERS,
                Permission.VIEW_ANALYTICS,
                Permission.VIEW_DETAILED_ANALYTICS,
                Permission.VIEW_USERS,
                Permission.ACCESS_API,
            },
            UserRole.ADMINISTRATOR: {
                # Администратор имеет все разрешения
                Permission.VIEW_DOCUMENTS,
                Permission.UPLOAD_DOCUMENTS,
                Permission.APPROVE_DOCUMENTS,
                Permission.REJECT_DOCUMENTS,
                Permission.DELETE_DOCUMENTS,
                Permission.VIEW_SUPPLIERS,
                Permission.MANAGE_SUPPLIERS,
                Permission.VIEW_ANALYTICS,
                Permission.VIEW_DETAILED_ANALYTICS,
                Permission.VIEW_USERS,
                Permission.MANAGE_USERS,
                Permission.VIEW_AUDIT_LOGS,
                Permission.MANAGE_SYSTEM_SETTINGS,
                Permission.ACCESS_API,
                Permission.ADMIN_API,
            },
        }

    def get_role_permissions(self, role: str) -> set[Permission]:
        """Получить разрешения для роли"""
        try:
            user_role = UserRole(role)
            return self.role_permissions.get(user_role, set())
        except ValueError:
            logger.warning(f"Неизвестная роль: {role}")
            return set()

    def has_permission(self, user_role: str, permission: Permission) -> bool:
        """Проверить, есть ли у роли определенное разрешение"""
        role_permissions = self.get_role_permissions(user_role)
        return permission in role_permissions

    def can_access_endpoint(
        self, user_role: str, endpoint_permissions: list[Permission]
    ) -> bool:
        """Проверить, может ли роль получить доступ к эндпоинту"""
        role_permissions = self.get_role_permissions(user_role)
        return any(perm in role_permissions for perm in endpoint_permissions)

    def get_all_roles(self) -> list[str]:
        """Получить список всех ролей"""
        return [role.value for role in UserRole]

    def get_role_hierarchy_level(self, role: str) -> int:
        """Получить уровень роли в иерархии (чем больше, тем выше)"""
        hierarchy = {
            UserRole.MANAGER.value: 1,
            UserRole.SUPERVISOR.value: 2,
            UserRole.ADMINISTRATOR.value: 3,
        }
        return hierarchy.get(role, 0)

    def can_manage_user(self, manager_role: str, target_role: str) -> bool:
        """Проверить, может ли пользователь с manager_role управлять пользователем с target_role"""
        manager_level = self.get_role_hierarchy_level(manager_role)
        target_level = self.get_role_hierarchy_level(target_role)

        # Можно управлять пользователями с более низким уровнем
        # Администратор может управлять всеми
        return (
            manager_level > target_level or manager_role == UserRole.ADMINISTRATOR.value
        )

    def get_role_description(self, role: str) -> str:
        """Получить описание роли"""
        descriptions = {
            UserRole.MANAGER.value: "Менеджер по закупкам - может просматривать документы, загружать новые, работать с поставщиками и просматривать базовую аналитику",
            UserRole.SUPERVISOR.value: "Руководитель отдела - может одобрять/отклонять документы, управлять поставщиками, просматривать детальную аналитику и управлять менеджерами",
            UserRole.ADMINISTRATOR.value: "Системный администратор - полный доступ ко всем функциям системы, включая управление пользователями и системными настройками",
        }
        return descriptions.get(role, "Неизвестная роль")

    def get_permissions_description(self, role: str) -> list[str]:
        """Получить описание разрешений для роли"""
        permissions = self.get_role_permissions(role)
        descriptions = {
            Permission.VIEW_DOCUMENTS: "Просмотр документов",
            Permission.UPLOAD_DOCUMENTS: "Загрузка документов",
            Permission.APPROVE_DOCUMENTS: "Одобрение документов",
            Permission.REJECT_DOCUMENTS: "Отклонение документов",
            Permission.DELETE_DOCUMENTS: "Удаление документов",
            Permission.VIEW_SUPPLIERS: "Просмотр поставщиков",
            Permission.MANAGE_SUPPLIERS: "Управление поставщиками",
            Permission.VIEW_ANALYTICS: "Просмотр аналитики",
            Permission.VIEW_DETAILED_ANALYTICS: "Просмотр детальной аналитики",
            Permission.VIEW_USERS: "Просмотр пользователей",
            Permission.MANAGE_USERS: "Управление пользователями",
            Permission.VIEW_AUDIT_LOGS: "Просмотр журналов аудита",
            Permission.MANAGE_SYSTEM_SETTINGS: "Управление системными настройками",
            Permission.ACCESS_API: "Доступ к API",
            Permission.ADMIN_API: "Доступ к административному API",
        }

        return [descriptions.get(perm, str(perm)) for perm in permissions]


# Глобальный экземпляр менеджера ролей
role_manager = RoleManager()


def check_permission(user_role: str, required_permission: Permission) -> bool:
    """Проверить разрешение пользователя"""
    return role_manager.has_permission(user_role, required_permission)


def check_endpoint_access(
    user_role: str, endpoint_permissions: list[Permission]
) -> bool:
    """Проверить доступ к эндпоинту"""
    return role_manager.can_access_endpoint(user_role, endpoint_permissions)


def get_user_permissions(user_role: str) -> list[str]:
    """Получить список разрешений пользователя"""
    permissions = role_manager.get_role_permissions(user_role)
    return [perm.value for perm in permissions]


def validate_role(role: str) -> bool:
    """Проверить, является ли роль валидной"""
    return role in role_manager.get_all_roles()


def get_role_info(role: str) -> dict[str, any]:
    """Получить полную информацию о роли"""
    if not validate_role(role):
        return {"error": "Неизвестная роль"}

    return {
        "role": role,
        "description": role_manager.get_role_description(role),
        "hierarchy_level": role_manager.get_role_hierarchy_level(role),
        "permissions": get_user_permissions(role),
        "permissions_descriptions": role_manager.get_permissions_description(role),
    }


def can_user_manage_target(manager_role: str, target_role: str) -> bool:
    """Проверить, может ли пользователь управлять другим пользователем"""
    return role_manager.can_manage_user(manager_role, target_role)


# Константы для быстрого доступа к разрешениям
class EndpointPermissions:
    """Разрешения для различных эндпоинтов"""

    # Документы
    UPLOAD_DOCUMENT = [Permission.UPLOAD_DOCUMENTS]
    VIEW_DOCUMENT = [Permission.VIEW_DOCUMENTS]
    APPROVE_DOCUMENT = [Permission.APPROVE_DOCUMENTS]
    REJECT_DOCUMENT = [Permission.REJECT_DOCUMENTS]
    DELETE_DOCUMENT = [Permission.DELETE_DOCUMENTS]

    # Поставщики
    VIEW_SUPPLIERS = [Permission.VIEW_SUPPLIERS]
    MANAGE_SUPPLIERS = [Permission.MANAGE_SUPPLIERS]

    # Аналитика
    BASIC_ANALYTICS = [Permission.VIEW_ANALYTICS]
    DETAILED_ANALYTICS = [Permission.VIEW_DETAILED_ANALYTICS]

    # Пользователи
    VIEW_USERS = [Permission.VIEW_USERS]
    MANAGE_USERS = [Permission.MANAGE_USERS]

    # Система
    AUDIT_LOGS = [Permission.VIEW_AUDIT_LOGS]
    SYSTEM_SETTINGS = [Permission.MANAGE_SYSTEM_SETTINGS]

    # API
    API_ACCESS = [Permission.ACCESS_API]
    ADMIN_API = [Permission.ADMIN_API]
