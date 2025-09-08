"""Модуль аутентификации и авторизации с JWT токенами"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

# Конфигурация JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Схема безопасности для FastAPI
security = HTTPBearer()


class AuthenticationError(Exception):
    """Исключение для ошибок аутентификации"""

    pass


class AuthorizationError(Exception):
    """Исключение для ошибок авторизации"""

    pass


class AuthManager:
    """Менеджер аутентификации и авторизации"""

    def __init__(self):
        self.users_db = {}  # В продакшене заменить на реальную БД
        self._init_default_users()

    def _init_default_users(self):
        """Инициализация пользователей по умолчанию"""
        default_users = [
            {
                "username": "admin",
                "email": "admin@company.com",
                "password": "admin123",
                "role": "administrator",
                "full_name": "Системный администратор",
            },
            {
                "username": "manager",
                "email": "manager@company.com",
                "password": "manager123",
                "role": "manager",
                "full_name": "Менеджер по закупкам",
            },
            {
                "username": "supervisor",
                "email": "supervisor@company.com",
                "password": "supervisor123",
                "role": "supervisor",
                "full_name": "Руководитель отдела",
            },
        ]

        for user_data in default_users:
            self.create_user(
                username=user_data["username"],
                email=user_data["email"],
                password=user_data["password"],
                role=user_data["role"],
                full_name=user_data["full_name"],
            )

    def hash_password(self, password: str) -> str:
        """Хеширование пароля"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Проверка пароля"""
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))

    def create_user(
        self, username: str, email: str, password: str, role: str, full_name: str
    ) -> dict[str, Any]:
        """Создание нового пользователя"""
        if username in self.users_db:
            raise ValueError(f"Пользователь {username} уже существует")

        user = {
            "username": username,
            "email": email,
            "password_hash": self.hash_password(password),
            "role": role,
            "full_name": full_name,
            "created_at": datetime.utcnow(),
            "is_active": True,
            "last_login": None,
        }

        self.users_db[username] = user
        logger.info(f"Создан пользователь: {username} с ролью {role}")

        # Возвращаем пользователя без пароля
        user_safe = user.copy()
        del user_safe["password_hash"]
        return user_safe

    def authenticate_user(
        self, username: str, password: str
    ) -> Optional[dict[str, Any]]:
        """Аутентификация пользователя"""
        user = self.users_db.get(username)
        if not user:
            logger.warning(f"Попытка входа несуществующего пользователя: {username}")
            return None

        if not user["is_active"]:
            logger.warning(f"Попытка входа заблокированного пользователя: {username}")
            return None

        if not self.verify_password(password, user["password_hash"]):
            logger.warning(f"Неверный пароль для пользователя: {username}")
            return None

        # Обновляем время последнего входа
        user["last_login"] = datetime.utcnow()
        logger.info(f"Успешная аутентификация пользователя: {username}")

        # Возвращаем пользователя без пароля
        user_safe = user.copy()
        del user_safe["password_hash"]
        return user_safe

    def create_access_token(self, user: dict[str, Any]) -> str:
        """Создание JWT токена"""
        payload = {
            "sub": user["username"],
            "email": user["email"],
            "role": user["role"],
            "full_name": user["full_name"],
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
            "iat": datetime.utcnow(),
        }

        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        logger.info(f"Создан JWT токен для пользователя: {user['username']}")
        return token

    def verify_token(self, token: str) -> dict[str, Any]:
        """Проверка и декодирование JWT токена"""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            username = payload.get("sub")

            if username is None:
                raise AuthenticationError("Неверный токен")

            # Проверяем, что пользователь все еще существует и активен
            user = self.users_db.get(username)
            if not user or not user["is_active"]:
                raise AuthenticationError("Пользователь не найден или заблокирован")

            return payload

        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Токен истек")
        except jwt.PyJWTError:
            raise AuthenticationError("Неверный токен")

    def get_user_by_username(self, username: str) -> Optional[dict[str, Any]]:
        """Получение пользователя по имени"""
        user = self.users_db.get(username)
        if user:
            user_safe = user.copy()
            del user_safe["password_hash"]
            return user_safe
        return None

    def update_user_role(self, username: str, new_role: str) -> bool:
        """Обновление роли пользователя"""
        if username not in self.users_db:
            return False

        old_role = self.users_db[username]["role"]
        self.users_db[username]["role"] = new_role
        logger.info(f"Роль пользователя {username} изменена с {old_role} на {new_role}")
        return True

    def deactivate_user(self, username: str) -> bool:
        """Деактивация пользователя"""
        if username not in self.users_db:
            return False

        self.users_db[username]["is_active"] = False
        logger.info(f"Пользователь {username} деактивирован")
        return True

    def get_all_users(self) -> list:
        """Получение списка всех пользователей"""
        users = []
        for user in self.users_db.values():
            user_safe = user.copy()
            del user_safe["password_hash"]
            users.append(user_safe)
        return users


# Глобальный экземпляр менеджера аутентификации
auth_manager = AuthManager()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict[str, Any]:
    """Dependency для получения текущего пользователя из JWT токена"""
    try:
        token = credentials.credentials
        payload = auth_manager.verify_token(token)
        return payload
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role(allowed_roles: list[str]):
    """Зависимость FastAPI для проверки роли пользователя"""

    def check_role(current_user: User = Depends(get_current_user)) -> User:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Требуется аутентификация",
            )

        user_role = (
            current_user.get("role")
            if isinstance(current_user, dict)
            else current_user.role
        )

        # Проверяем, есть ли роль пользователя в списке разрешенных
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Недостаточно прав. Требуется одна из ролей: {', '.join(allowed_roles)}",
            )

        return current_user

    return check_role


def create_admin_user(
    username: str, email: str, password: str, full_name: str
) -> dict[str, Any]:
    """Создание администратора (для инициализации системы)"""
    return auth_manager.create_user(
        username=username,
        email=email,
        password=password,
        role="administrator",
        full_name=full_name,
    )


def login_user(username: str, password: str) -> dict[str, Any]:
    """Вход пользователя в систему"""
    user = auth_manager.authenticate_user(username, password)
    if not user:
        raise AuthenticationError("Неверное имя пользователя или пароль")

    access_token = auth_manager.create_access_token(user)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": JWT_EXPIRATION_HOURS * 3600,  # в секундах
        "user": user,
    }


def get_user_info(username: str) -> Optional[dict[str, Any]]:
    """Получение информации о пользователе"""
    return auth_manager.get_user_by_username(username)


def change_user_password(username: str, old_password: str, new_password: str) -> bool:
    """Смена пароля пользователя"""
    user = auth_manager.users_db.get(username)
    if not user:
        return False

    if not auth_manager.verify_password(old_password, user["password_hash"]):
        return False

    user["password_hash"] = auth_manager.hash_password(new_password)
    logger.info(f"Пароль пользователя {username} изменен")
    return True


# Функции-обертки для совместимости с main.py
def create_access_token(user: dict[str, Any]) -> str:
    """Создание JWT токена доступа"""
    return auth_manager.create_access_token(user)


def authenticate_user(username: str, password: str) -> Optional[dict[str, Any]]:
    """Аутентификация пользователя"""
    return auth_manager.authenticate_user(username, password)


def create_user(
    username: str, email: str, password: str, role: str, full_name: str
) -> dict[str, Any]:
    """Создание нового пользователя"""
    return auth_manager.create_user(username, email, password, role, full_name)


def update_user_role(username: str, new_role: str) -> bool:
    """Обновление роли пользователя"""
    return auth_manager.update_user_role(username, new_role)


def deactivate_user(username: str) -> bool:
    """Деактивация пользователя"""
    return auth_manager.deactivate_user(username)


def get_user_by_username(username: str) -> Optional[dict[str, Any]]:
    """Получение пользователя по имени"""
    return auth_manager.get_user_by_username(username)


# Псевдоним для совместимости
User = dict[str, Any]
