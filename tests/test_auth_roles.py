"""
Тесты для проверки ролей и доступа к маршрутам
Тестирует модуль roles.py и систему авторизации
"""

import os
import sys

import pytest

# Добавляем путь к корневой директории проекта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from roles import (
    Permission,
    RoleManager,
    UserRole,
    can_user_manage_target,
    check_endpoint_access,
    check_permission,
    get_role_info,
    get_user_permissions,
    role_manager,
    validate_role,
)


class TestUserRole:
    """Тесты для перечисления UserRole"""

    def test_user_role_values(self):
        """Проверка корректности значений ролей"""
        assert UserRole.MANAGER.value == "manager"
        assert UserRole.SUPERVISOR.value == "supervisor"
        assert UserRole.ADMINISTRATOR.value == "administrator"

    def test_user_role_enum_members(self):
        """Проверка всех членов перечисления"""
        roles = list(UserRole)
        assert len(roles) == 3
        assert UserRole.MANAGER in roles
        assert UserRole.SUPERVISOR in roles
        assert UserRole.ADMINISTRATOR in roles


class TestPermission:
    """Тесты для перечисления Permission"""

    def test_permission_values(self):
        """Проверка корректности значений разрешений"""
        assert Permission.VIEW_DOCUMENTS.value == "view_documents"
        assert Permission.UPLOAD_DOCUMENTS.value == "upload_documents"
        assert Permission.APPROVE_DOCUMENTS.value == "approve_documents"
        assert Permission.ADMIN_API.value == "admin_api"

    def test_all_permissions_exist(self):
        """Проверка наличия всех ожидаемых разрешений"""
        permissions = list(Permission)
        expected_permissions = [
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
        ]

        for perm in expected_permissions:
            assert perm in permissions


class TestRoleManager:
    """Тесты для класса RoleManager"""

    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.role_manager = RoleManager()

    def test_init_role_permissions(self):
        """Проверка инициализации разрешений для ролей"""
        role_permissions = self.role_manager._init_role_permissions()

        # Проверка наличия всех ролей
        assert UserRole.MANAGER in role_permissions
        assert UserRole.SUPERVISOR in role_permissions
        assert UserRole.ADMINISTRATOR in role_permissions

        # Проверка разрешений для менеджера
        manager_perms = role_permissions[UserRole.MANAGER]
        expected_manager_perms = {
            Permission.VIEW_DOCUMENTS,
            Permission.UPLOAD_DOCUMENTS,
            Permission.VIEW_SUPPLIERS,
            Permission.VIEW_ANALYTICS,
            Permission.ACCESS_API,
        }
        assert manager_perms == expected_manager_perms

        # Проверка разрешений для супервайзера
        supervisor_perms = role_permissions[UserRole.SUPERVISOR]
        assert Permission.APPROVE_DOCUMENTS in supervisor_perms
        assert Permission.REJECT_DOCUMENTS in supervisor_perms
        assert Permission.MANAGE_SUPPLIERS in supervisor_perms
        assert Permission.VIEW_DETAILED_ANALYTICS in supervisor_perms

        # Проверка разрешений для администратора
        admin_perms = role_permissions[UserRole.ADMINISTRATOR]
        assert len(admin_perms) == len(list(Permission))  # Все разрешения

    def test_get_role_permissions_valid_role(self):
        """Получение разрешений для валидной роли"""
        manager_perms = self.role_manager.get_role_permissions("manager")
        assert isinstance(manager_perms, set)
        assert len(manager_perms) > 0
        assert Permission.VIEW_DOCUMENTS in manager_perms

    def test_get_role_permissions_invalid_role(self):
        """Получение разрешений для невалидной роли"""
        perms = self.role_manager.get_role_permissions("invalid_role")
        assert perms == set()

    def test_has_permission_true(self):
        """Проверка наличия разрешения (положительный случай)"""
        assert self.role_manager.has_permission("manager", Permission.VIEW_DOCUMENTS)
        assert self.role_manager.has_permission(
            "administrator", Permission.DELETE_DOCUMENTS
        )

    def test_has_permission_false(self):
        """Проверка отсутствия разрешения (отрицательный случай)"""
        assert not self.role_manager.has_permission(
            "manager", Permission.DELETE_DOCUMENTS
        )
        assert not self.role_manager.has_permission("manager", Permission.ADMIN_API)

    def test_can_access_endpoint_single_permission(self):
        """Проверка доступа к эндпоинту с одним разрешением"""
        assert self.role_manager.can_access_endpoint(
            "manager", [Permission.VIEW_DOCUMENTS]
        )

    def test_can_access_endpoint_multiple_permissions(self):
        """Проверка доступа к эндпоинту с несколькими разрешениями"""
        # Менеджер имеет VIEW_DOCUMENTS, но не имеет DELETE_DOCUMENTS
        assert self.role_manager.can_access_endpoint(
            "manager", [Permission.VIEW_DOCUMENTS, Permission.DELETE_DOCUMENTS]
        )

    def test_cannot_access_endpoint(self):
        """Проверка отсутствия доступа к эндпоинту"""
        assert not self.role_manager.can_access_endpoint(
            "manager", [Permission.DELETE_DOCUMENTS, Permission.ADMIN_API]
        )

    def test_get_all_roles(self):
        """Получение списка всех ролей"""
        roles = self.role_manager.get_all_roles()
        assert len(roles) == 3
        assert "manager" in roles
        assert "supervisor" in roles
        assert "administrator" in roles

    def test_get_role_hierarchy_level(self):
        """Проверка уровней иерархии ролей"""
        assert self.role_manager.get_role_hierarchy_level("manager") == 1
        assert self.role_manager.get_role_hierarchy_level("supervisor") == 2
        assert self.role_manager.get_role_hierarchy_level("administrator") == 3
        assert self.role_manager.get_role_hierarchy_level("unknown") == 0

    def test_can_manage_user_hierarchy(self):
        """Проверка возможности управления пользователями по иерархии"""
        # Супервайзер может управлять менеджерами
        assert self.role_manager.can_manage_user("supervisor", "manager")
        # Администратор может управлять всеми
        assert self.role_manager.can_manage_user("administrator", "manager")
        assert self.role_manager.can_manage_user("administrator", "supervisor")
        # Менеджер не может управлять супервайзером
        assert not self.role_manager.can_manage_user("manager", "supervisor")
        # Роль не может управлять самой собой
        assert not self.role_manager.can_manage_user("manager", "manager")

    def test_get_role_description(self):
        """Получение описания роли"""
        manager_desc = self.role_manager.get_role_description("manager")
        assert "Менеджер по закупкам" in manager_desc

        supervisor_desc = self.role_manager.get_role_description("supervisor")
        assert "Руководитель отдела" in supervisor_desc

    def test_get_permissions_description(self):
        """Получение описаний разрешений для роли"""
        descriptions = self.role_manager.get_permissions_description("manager")
        assert isinstance(descriptions, list)
        assert len(descriptions) > 0
        assert "Просмотр документов" in descriptions


class TestGlobalFunctions:
    """Тесты для глобальных функций модуля"""

    def test_check_permission(self):
        """Проверка функции check_permission"""
        assert check_permission("manager", Permission.VIEW_DOCUMENTS)
        assert not check_permission("manager", Permission.DELETE_DOCUMENTS)

    def test_check_endpoint_access(self):
        """Проверка функции check_endpoint_access"""
        assert check_endpoint_access("manager", [Permission.VIEW_DOCUMENTS])
        assert not check_endpoint_access("manager", [Permission.ADMIN_API])

    def test_get_user_permissions(self):
        """Проверка функции get_user_permissions"""
        perms = get_user_permissions("manager")
        assert isinstance(perms, list)
        assert "view_documents" in perms
        assert "upload_documents" in perms

    def test_validate_role(self):
        """Проверка функции validate_role"""
        assert validate_role("manager")
        assert validate_role("supervisor")
        assert validate_role("administrator")
        assert not validate_role("invalid_role")

    def test_get_role_info_valid(self):
        """Получение информации о валидной роли"""
        info = get_role_info("manager")
        assert "error" not in info
        assert info["role"] == "manager"
        assert "description" in info
        assert "permissions" in info
        assert isinstance(info["permissions"], list)

    def test_get_role_info_invalid(self):
        """Получение информации о невалидной роли"""
        info = get_role_info("invalid_role")
        assert "error" in info

    def test_can_user_manage_target(self):
        """Проверка функции can_user_manage_target"""
        assert can_user_manage_target("supervisor", "manager")
        assert not can_user_manage_target("manager", "supervisor")


class TestRoleBasedRouteAccess:
    """Тесты для проверки доступа к маршрутам на основе ролей"""

    def test_document_routes_access(self):
        """Проверка доступа к маршрутам документов"""
        # Менеджер может просматривать и загружать документы
        assert check_endpoint_access("manager", [Permission.VIEW_DOCUMENTS])
        assert check_endpoint_access("manager", [Permission.UPLOAD_DOCUMENTS])

        # Менеджер не может одобрять документы
        assert not check_endpoint_access("manager", [Permission.APPROVE_DOCUMENTS])

        # Супервайзер может одобрять и отклонять документы
        assert check_endpoint_access("supervisor", [Permission.APPROVE_DOCUMENTS])
        assert check_endpoint_access("supervisor", [Permission.REJECT_DOCUMENTS])

        # Администратор может удалять документы
        assert check_endpoint_access("administrator", [Permission.DELETE_DOCUMENTS])

    def test_supplier_routes_access(self):
        """Проверка доступа к маршрутам поставщиков"""
        # Менеджер может только просматривать поставщиков
        assert check_endpoint_access("manager", [Permission.VIEW_SUPPLIERS])
        assert not check_endpoint_access("manager", [Permission.MANAGE_SUPPLIERS])

        # Супервайзер может управлять поставщиками
        assert check_endpoint_access("supervisor", [Permission.MANAGE_SUPPLIERS])

    def test_analytics_routes_access(self):
        """Проверка доступа к маршрутам аналитики"""
        # Менеджер имеет базовый доступ к аналитике
        assert check_endpoint_access("manager", [Permission.VIEW_ANALYTICS])
        assert not check_endpoint_access(
            "manager", [Permission.VIEW_DETAILED_ANALYTICS]
        )

        # Супервайзер имеет доступ к детальной аналитике
        assert check_endpoint_access("supervisor", [Permission.VIEW_DETAILED_ANALYTICS])

    def test_user_management_routes_access(self):
        """Проверка доступа к маршрутам управления пользователями"""
        # Только супервайзер и администратор могут просматривать пользователей
        assert not check_endpoint_access("manager", [Permission.VIEW_USERS])
        assert check_endpoint_access("supervisor", [Permission.VIEW_USERS])

        # Только администратор может управлять пользователями
        assert not check_endpoint_access("supervisor", [Permission.MANAGE_USERS])
        assert check_endpoint_access("administrator", [Permission.MANAGE_USERS])

    def test_system_routes_access(self):
        """Проверка доступа к системным маршрутам"""
        # Только администратор имеет доступ к системным настройкам
        assert not check_endpoint_access("manager", [Permission.MANAGE_SYSTEM_SETTINGS])
        assert not check_endpoint_access(
            "supervisor", [Permission.MANAGE_SYSTEM_SETTINGS]
        )
        assert check_endpoint_access(
            "administrator", [Permission.MANAGE_SYSTEM_SETTINGS]
        )

        # Только администратор имеет доступ к журналам аудита
        assert not check_endpoint_access("supervisor", [Permission.VIEW_AUDIT_LOGS])
        assert check_endpoint_access("administrator", [Permission.VIEW_AUDIT_LOGS])

    def test_api_routes_access(self):
        """Проверка доступа к API маршрутам"""
        # Все роли имеют базовый доступ к API
        assert check_endpoint_access("manager", [Permission.ACCESS_API])
        assert check_endpoint_access("supervisor", [Permission.ACCESS_API])
        assert check_endpoint_access("administrator", [Permission.ACCESS_API])

        # Только администратор имеет доступ к административному API
        assert not check_endpoint_access("manager", [Permission.ADMIN_API])
        assert not check_endpoint_access("supervisor", [Permission.ADMIN_API])
        assert check_endpoint_access("administrator", [Permission.ADMIN_API])


class TestRoleHierarchy:
    """Тесты для проверки иерархии ролей"""

    def test_role_ordering(self):
        """Проверка правильного порядка ролей по иерархии"""
        assert role_manager.get_role_hierarchy_level(
            "manager"
        ) < role_manager.get_role_hierarchy_level("supervisor")
        assert role_manager.get_role_hierarchy_level(
            "supervisor"
        ) < role_manager.get_role_hierarchy_level("administrator")

    def test_management_hierarchy(self):
        """Проверка иерархии управления"""
        # Проверяем все возможные комбинации
        test_cases = [
            ("administrator", "manager", True),
            ("administrator", "supervisor", True),
            ("administrator", "administrator", True),
            ("supervisor", "manager", True),
            ("supervisor", "supervisor", False),
            ("supervisor", "administrator", False),
            ("manager", "manager", False),
            ("manager", "supervisor", False),
            ("manager", "administrator", False),
        ]

        for manager, target, expected in test_cases:
            result = can_user_manage_target(manager, target)
            assert (
                result == expected
            ), f"Expected {expected} for {manager} managing {target}"


class TestIntegrationScenarios:
    """Интеграционные тесты для сложных сценариев"""

    def test_complex_permission_check(self):
        """Проверка сложных сценариев с несколькими разрешениями"""
        # Сценарий: пользователь пытается получить доступ к защищенному ресурсу
        # Требуются ВСЕ разрешения (AND логика вместо OR)
        required_permissions = [
            Permission.APPROVE_DOCUMENTS,
            Permission.VIEW_DETAILED_ANALYTICS,
        ]

        # Менеджер не имеет всех необходимых разрешений
        manager_perms = role_manager.get_role_permissions("manager")
        has_all_perms = all(perm in manager_perms for perm in required_permissions)
        assert not has_all_perms

        # Супервайзер имеет все необходимые разрешения
        supervisor_perms = role_manager.get_role_permissions("supervisor")
        has_all_perms_supervisor = all(
            perm in supervisor_perms for perm in required_permissions
        )
        assert has_all_perms_supervisor

    def test_role_info_completeness(self):
        """Проверка полноты информации о роли"""
        for role in ["manager", "supervisor", "administrator"]:
            info = get_role_info(role)

            # Проверяем наличие всех необходимых полей
            assert "role" in info
            assert "description" in info
            assert "hierarchy_level" in info
            assert "permissions" in info
            assert "permissions_descriptions" in info

            # Проверяем типы данных
            assert isinstance(info["role"], str)
            assert isinstance(info["description"], str)
            assert isinstance(info["hierarchy_level"], int)
            assert isinstance(info["permissions"], list)
            assert isinstance(info["permissions_descriptions"], list)

            # Проверяем содержимое
            assert info["role"] == role
            assert len(info["permissions"]) > 0
            assert len(info["permissions_descriptions"]) == len(info["permissions"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
