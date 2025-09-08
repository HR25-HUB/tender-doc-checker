"""FastAPI приложение для проверки тендерных документов."""

import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Literal, Optional, cast

from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from analytics import AnalyticsEngine
from audit import (
    audit_analytics_access,
    audit_manager,
    audit_user_action,
)
from audit_logger import (
    audit_logger,
    log_api_access,
    log_permission_denied,
)

# Импорты для аутентификации и авторизации
from auth import (
    User,
    authenticate_user,
    create_access_token,
    create_user,
    deactivate_user,
    get_current_user,
    get_user_by_username,
    require_role,
    update_user_role,
)
from bitrix_api import create_bitrix_task
from checker import (
    check_commercial_proposal,
    check_document,
    check_product_specification,
)
from db import get_supplier_history, init_db, save_report
from extractor import extract_text_from_file
from price_analytics import PriceAnalyticsEngine
from recommendations import RecommendationEngine
from report_generator import export_audit_history, generate_pdf
from roles import (
    can_user_manage_target,
    get_role_info,
    get_user_permissions,
    validate_role,
)
from src.config import settings
from src.logger import setup_logging
from src.models import (
    CheckResult,
    CommercialProposal,
    CommercialProposalAnalysis,
    CriteriaWeights,
    ProductSpecification,
    SupplierHistory,
    UploadResponse,
)

# Настройка логирования
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Управление жизненным циклом приложения."""
    logger.info("Запуск Tender Document Checker API")
    init_db()
    logger.info("База данных инициализирована")
    yield
    logger.info("Завершение работы API")


app = FastAPI(
    title="Tender Document Checker API",
    description="API для проверки тендерной документации",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RateLimitMiddleware:
    """Middleware для rate limiting с поддержкой ролей."""

    def __init__(self, app):
        self.app = app
        self.storage = {}  # In-memory storage for rate limits

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Create a mock request for middleware
        from fastapi import Request

        async def receive_wrapper():
            return await receive()

        request = Request(scope, receive_wrapper)

        # Skip rate limiting if disabled
        if not settings.rate_limit_enabled:
            await self.app(scope, receive, send)
            return

        # Get client identifier (IP or user)
        client_id = self._get_client_id(request)

        # Check if user has bypass role
        if await self._has_bypass_role(request):
            await self.app(scope, receive, send)
            return

        # Check rate limits
        if not self._check_rate_limit(client_id):
            response = JSONResponse(
                status_code=429,
                content={"detail": "Превышен лимит запросов. Попробуйте позже."},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

    def _get_client_id(self, request: Request) -> str:
        """Получить идентификатор клиента."""
        # Use X-Forwarded-For if behind proxy
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def _has_bypass_role(self, request: Request) -> bool:
        """Проверить, имеет ли пользователь роль для обхода rate limiting."""
        try:
            from auth import get_current_user

            # Get authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return False

            token = auth_header.split(" ")[1]
            user = await get_current_user(token)

            return user["role"] in settings.rate_limit_bypass_roles
        except Exception:
            return False

    def _check_rate_limit(self, client_id: str) -> bool:
        """Проверить лимиты запросов для клиента."""
        now = time.time()

        if client_id not in self.storage:
            self.storage[client_id] = {
                "requests_per_second": [],
                "requests_per_minute": [],
                "requests_per_hour": [],
            }

        client_limits = self.storage[client_id]

        # Clean old requests
        client_limits["requests_per_second"] = [
            req_time
            for req_time in client_limits["requests_per_second"]
            if now - req_time < 1
        ]
        client_limits["requests_per_minute"] = [
            req_time
            for req_time in client_limits["requests_per_minute"]
            if now - req_time < 60
        ]
        client_limits["requests_per_hour"] = [
            req_time
            for req_time in client_limits["requests_per_hour"]
            if now - req_time < 3600
        ]

        # Check limits
        if (
            len(client_limits["requests_per_second"])
            >= settings.rate_limit_requests_per_second
        ):
            return False
        if (
            len(client_limits["requests_per_minute"])
            >= settings.rate_limit_requests_per_minute
        ):
            return False
        if (
            len(client_limits["requests_per_hour"])
            >= settings.rate_limit_requests_per_hour
        ):
            return False

        # Add current request
        client_limits["requests_per_second"].append(now)
        client_limits["requests_per_minute"].append(now)
        client_limits["requests_per_hour"].append(now)

        return True


# Rate limiting middleware
app.add_middleware(RateLimitMiddleware)


class UploadFileWrapper:
    """Обертка для UploadFile для совместимости с extractor."""

    def __init__(self, name: str, content: bytes) -> None:
        self.name = name
        self._content = content

    def read(self) -> bytes:
        return self._content


# === ЭНДПОИНТЫ АУТЕНТИФИКАЦИИ ===


@app.post("/auth/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """Аутентификация пользователя и получение токена доступа."""
    try:
        user = authenticate_user(credentials.username, credentials.password)
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Неверное имя пользователя или пароль",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = create_access_token(user)
        logger.info(f"Пользователь {credentials.username} успешно аутентифицирован")

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user={
                "username": user["username"],
                "role": user["role"],
                "is_active": user["is_active"],
                "permissions": get_user_permissions(user["role"]),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при аутентификации пользователя {username}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера при аутентификации")


@app.post("/auth/register", response_model=RegisterResponse)
async def register(
    credentials: RegisterRequest,
    current_user: User = Depends(require_role(["administrator"])),
):
    """Регистрация нового пользователя (только для администраторов)."""
    try:
        if not validate_role(credentials.role):
            raise HTTPException(status_code=400, detail="Неверная роль пользователя")

        # Проверяем, может ли текущий пользователь создавать пользователей с такой ролью
        if not can_user_manage_target(current_user["role"], credentials.role):
            raise HTTPException(
                status_code=403,
                detail="Недостаточно прав для создания пользователя с такой ролью",
            )

        existing_user = get_user_by_username(credentials.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Пользователь уже существует")

        user = create_user(credentials.username, credentials.password, credentials.role)
        logger.info(
            f"Пользователь {credentials.username} создан администратором {current_user['username']}"
        )

        return RegisterResponse(
            message="Пользователь успешно создан",
            user={
                "username": user.username,
                "role": user.role,
                "is_active": user.is_active,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при создании пользователя {username}: {e}")
        raise HTTPException(
            status_code=500, detail="Ошибка сервера при создании пользователя"
        )


@app.get("/auth/me", response_model=UserInfoResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Получить информацию о текущем пользователе."""
    return UserInfoResponse(
        username=current_user["username"],
        role=current_user["role"],
        is_active=current_user["is_active"],
        permissions=get_user_permissions(current_user["role"]),
        role_info=get_role_info(current_user["role"]),
    )


@app.put("/auth/users/{username}/role", response_model=UpdateRoleResponse)
async def update_user_role_endpoint(
    username: str,
    request: UpdateRoleRequest,
    current_user: User = Depends(require_role(["administrator", "supervisor"])),
):
    """Обновить роль пользователя (для администраторов и руководителей)."""
    try:
        if not validate_role(request.new_role):
            raise HTTPException(status_code=400, detail="Неверная роль пользователя")

        target_user = get_user_by_username(username)
        if not target_user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        # Проверяем права на изменение роли
        if not can_user_manage_target(
            current_user["role"], target_user["role"]
        ) or not can_user_manage_target(current_user["role"], request.new_role):
            raise HTTPException(
                status_code=403,
                detail="Недостаточно прав для изменения роли этого пользователя",
            )

        updated_user = update_user_role(username, request.new_role)
        logger.info(
            f"Роль пользователя {username} изменена на {request.new_role} администратором {current_user['username']}"
        )

        return UpdateRoleResponse(
            message="Роль пользователя успешно обновлена",
            user={
                "username": updated_user.username,
                "role": updated_user.role,
                "is_active": updated_user.is_active,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении роли пользователя {username}: {e}")
        raise HTTPException(
            status_code=500, detail="Ошибка сервера при обновлении роли"
        )


@app.delete("/auth/users/{username}", response_model=UserActionResponse)
async def deactivate_user_endpoint(
    username: str, current_user: User = Depends(require_role(["administrator"]))
):
    """Деактивировать пользователя (только для администраторов)."""
    try:
        target_user = get_user_by_username(username)
        if not target_user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        if target_user["username"] == current_user["username"]:
            raise HTTPException(
                status_code=400, detail="Нельзя деактивировать самого себя"
            )

        deactivated_user = deactivate_user(username)
        logger.info(
            f"Пользователь {username} деактивирован администратором {current_user['username']}"
        )

        return UserActionResponse(
            message="Пользователь успешно деактивирован",
            user={
                "username": deactivated_user.username,
                "role": deactivated_user.role,
                "is_active": deactivated_user.is_active,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при деактивации пользователя {username}: {e}")
        raise HTTPException(
            status_code=500, detail="Ошибка сервера при деактивации пользователя"
        )


# === АУДИТ ===


@app.get("/audit/logs", response_model=AuditLogsResponse)
async def get_audit_logs(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(require_role(["administrator", "supervisor"])),
):
    """Получить логи аудита."""
    logger.info(f"Пользователь {current_user['username']} запросил логи аудита")

    # Аудит доступа к логам
    log_api_access(
        user_id=current_user.get("user_id", current_user["username"]),
        username=current_user["username"],
        endpoint="/audit/logs",
        method="GET",
    )
    audit_user_action(
        current_user,
        "view_audit_logs",
        "audit",
        "logs",
        {
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
                "user_id": user_id,
                "event_type": event_type,
            }
        },
    )

    try:
        from datetime import datetime

        # Преобразуем строки дат в datetime объекты
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        # Получаем логи через audit_logger
        logs = audit_logger.get_audit_logs(
            start_date=start_dt,
            end_date=end_dt,
            user_id=user_id,
            event_type=event_type,
            limit=limit,
        )

        return AuditLogsResponse(
            status="success",
            data=AuditLogsData(
                logs=logs,
                total_count=len(logs),
                filters_applied=AuditFilters(
                    start_date=start_date,
                    end_date=end_date,
                    user_id=user_id,
                    event_type=event_type,
                    limit=limit,
                ),
            ),
        )
    except ValueError as e:
        logger.error(f"Ошибка формата даты: {e}")
        raise HTTPException(
            status_code=400,
            detail="Неверный формат даты. Используйте ISO формат (YYYY-MM-DDTHH:MM:SS)",
        )
    except Exception as e:
        logger.error(f"Ошибка получения логов аудита: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения логов аудита")


@app.get("/audit/user-actions/{user_id}", response_model=UserAuditTrailResponse)
async def get_user_audit_trail(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(require_role(["administrator", "supervisor"])),
):
    """Получить аудиторский след пользователя."""
    logger.info(
        f"Пользователь {current_user['username']} запросил аудиторский след пользователя {user_id}"
    )

    # Проверяем, что пользователь может просматривать чужие действия или свои собственные
    if (
        current_user["role"] not in ["administrator", "supervisor"]
        and current_user.get("user_id", current_user["username"]) != user_id
    ):
        log_permission_denied(
            user_id=current_user.get("user_id", current_user["username"]),
            username=current_user["username"],
            resource="user_audit_trail",
            action="view",
            reason="Недостаточно прав для просмотра чужого аудиторского следа",
        )
        raise HTTPException(
            status_code=403,
            detail="Недостаточно прав для просмотра аудиторского следа другого пользователя",
        )

    # Аудит доступа к аудиторскому следу
    log_api_access(
        user_id=current_user.get("user_id", current_user["username"]),
        username=current_user["username"],
        endpoint=f"/audit/user-actions/{user_id}",
        method="GET",
    )
    audit_user_action(
        current_user,
        "view_user_audit_trail",
        "audit",
        f"user_trail_{user_id}",
        {
            "target_user_id": user_id,
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
                "resource_type": resource_type,
            },
        },
    )

    try:
        from datetime import datetime

        # Преобразуем строки дат в datetime объекты
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        # Получаем аудиторский след пользователя
        user_trail = audit_manager.get_user_audit_trail(
            user_id=user_id,
            start_date=start_dt,
            end_date=end_dt,
            resource_type=resource_type,
            limit=limit,
        )

        # Получаем сессии пользователя
        user_sessions = audit_manager.get_user_sessions(
            user_id=user_id, start_date=start_dt, end_date=end_dt, limit=20
        )

        return UserAuditTrailResponse(
            status="success",
            data=UserAuditTrailData(
                user_id=user_id,
                audit_trail=user_trail,
                sessions=user_sessions,
                total_actions=len(user_trail),
                total_sessions=len(user_sessions),
                filters_applied=UserAuditFilters(
                    start_date=start_date,
                    end_date=end_date,
                    resource_type=resource_type,
                    limit=limit,
                ),
            ),
        )
    except ValueError as e:
        logger.error(f"Ошибка формата даты: {e}")
        raise HTTPException(
            status_code=400,
            detail="Неверный формат даты. Используйте ISO формат (YYYY-MM-DDTHH:MM:SS)",
        )
    except Exception as e:
        logger.error(f"Ошибка получения аудиторского следа пользователя {user_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Ошибка получения аудиторского следа пользователя"
        )


@app.get("/audit/export", response_model=AuditExportResponse)
async def export_audit_history_endpoint(
    export_format: str = "json",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    doc_type: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 10000,
    offset: int = 0,
    current_user: User = Depends(require_role(["administrator", "supervisor"])),
):
    """Экспорт истории отчетов (аудит) в формат txt или json."""
    username = current_user.get("sub", current_user.get("username", "unknown"))
    logger.info(
        f"Пользователь {username} запрашивает экспорт истории аудита в формате {export_format}"
    )

    # Аудит доступа к экспорту
    log_api_access(
        user_id=current_user.get("user_id", username),
        username=username,
        endpoint="/audit/export",
        method="GET",
        status_code=200,
    )
    # Создаем объект User из словаря current_user для audit_user_action
    # Создаем словарь с данными пользователя вместо объекта User
    user_dict = {
        "username": username,
        "user_id": current_user.get(
            "sub", username
        ),  # Добавляем user_id как отдельное поле
        "role": current_user.get("role", "user"),
        "email": current_user.get("email", ""),
    }

    audit_user_action(
        user_dict,
        "export_audit_history",
        "audit",
        "history_export",
        {
            "export_format": export_format,
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
                "doc_type": doc_type,
                "user_id": user_id,
                "limit": limit,
                "offset": offset,
            },
        },
    )

    try:
        filters = {
            "start_date": start_date,
            "end_date": end_date,
            "doc_type": doc_type,
            "user_id": user_id,
            "limit": limit,
            "offset": offset,
        }
        file_path = export_audit_history(export_format, filters)
        return AuditExportResponse(
            status="success",
            data=AuditExportData(
                file_path=file_path,
                format=export_format,
                filters_applied=AuditExportFilters(
                    start_date=start_date,
                    end_date=end_date,
                    doc_type=doc_type,
                    user_id=user_id,
                    limit=limit,
                    offset=offset,
                ),
            ),
        )
    except ValueError as e:
        logger.error(f"Ошибка параметров экспорта: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка экспорта истории аудита: {e}")
        raise HTTPException(status_code=500, detail="Ошибка экспорта истории аудита")


@app.get("/audit/system-changes")
async def get_system_changes(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    change_type: Optional[str] = None,
    component: Optional[str] = None,
    impact_level: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(require_role(["administrator"])),
):
    """Получить системные изменения (только для администраторов)."""
    logger.info(
        f"Администратор {current_user['username']} запросил системные изменения"
    )

    # Аудит доступа к системным изменениям
    log_api_access(
        user_id=current_user.get("user_id", current_user["username"]),
        username=current_user["username"],
        endpoint="/audit/system-changes",
        method="GET",
    )
    audit_user_action(
        current_user,
        "view_system_changes",
        "audit",
        "system_changes",
        {
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
                "change_type": change_type,
                "component": component,
                "impact_level": impact_level,
            }
        },
    )

    try:
        from datetime import datetime

        # Преобразуем строки дат в datetime объекты
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        # Получаем системные изменения
        system_changes = audit_manager.get_system_changes(
            start_date=start_dt,
            end_date=end_dt,
            change_type=change_type,
            component=component,
            impact_level=impact_level,
            limit=limit,
        )

        return {
            "status": "success",
            "data": {
                "system_changes": system_changes,
                "total_count": len(system_changes),
                "filters_applied": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "change_type": change_type,
                    "component": component,
                    "impact_level": impact_level,
                    "limit": limit,
                },
            },
        }
    except ValueError as e:
        logger.error(f"Ошибка формата даты: {e}")
        raise HTTPException(
            status_code=400,
            detail="Неверный формат даты. Используйте ISO формат (YYYY-MM-DDTHH:MM:SS)",
        )
    except Exception as e:
        logger.error(f"Ошибка получения системных изменений: {e}")
        raise HTTPException(
            status_code=500, detail="Ошибка получения системных изменений"
        )


@app.get("/audit/report")
async def generate_audit_report(
    start_date: str,
    end_date: str,
    include_user_actions: bool = True,
    include_system_changes: bool = True,
    include_sessions: bool = True,
    current_user: User = Depends(require_role(["administrator", "supervisor"])),
):
    """Сгенерировать отчет по аудиту."""
    logger.info(
        f"Пользователь {current_user['username']} запросил отчет по аудиту за период {start_date} - {end_date}"
    )

    # Аудит генерации отчета
    log_api_access(
        user_id=current_user.get("user_id", current_user["username"]),
        username=current_user["username"],
        endpoint="/audit/report",
        method="GET",
    )
    audit_user_action(
        current_user,
        "generate_audit_report",
        "audit",
        "report",
        {
            "period": f"{start_date} - {end_date}",
            "include_user_actions": include_user_actions,
            "include_system_changes": include_system_changes,
            "include_sessions": include_sessions,
        },
    )

    try:
        from datetime import datetime

        # Преобразуем строки дат в datetime объекты
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)

        # Генерируем отчет
        report = audit_manager.generate_audit_report(
            start_date=start_dt,
            end_date=end_dt,
            include_user_actions=include_user_actions,
            include_system_changes=include_system_changes,
            include_sessions=include_sessions,
        )

        return {"status": "success", "data": report}
    except ValueError as e:
        logger.error(f"Ошибка формата даты: {e}")
        raise HTTPException(
            status_code=400,
            detail="Неверный формат даты. Используйте ISO формат (YYYY-MM-DDTHH:MM:SS)",
        )
    except Exception as e:
        logger.error(f"Ошибка генерации отчета по аудиту: {e}")
        raise HTTPException(status_code=500, detail="Ошибка генерации отчета по аудиту")


@app.get("/audit/active-sessions")
async def get_active_sessions(
    current_user: User = Depends(require_role(["administrator", "supervisor"]))
):
    """Получить активные пользовательские сессии."""
    logger.info(f"Пользователь {current_user['username']} запросил активные сессии")

    # Аудит доступа к активным сессиям
    log_api_access(
        user_id=current_user.get("user_id", current_user["username"]),
        username=current_user["username"],
        endpoint="/audit/active-sessions",
        method="GET",
    )
    audit_user_action(current_user, "view_active_sessions", "audit", "active_sessions")

    try:
        active_sessions = audit_manager.get_active_sessions()

        return {
            "status": "success",
            "data": {
                "active_sessions": active_sessions,
                "total_active": len(active_sessions),
            },
        }
    except Exception as e:
        logger.error(f"Ошибка получения активных сессий: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения активных сессий")


# === СИСТЕМНЫЕ ЭНДПОИНТЫ ===


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Проверка состояния API."""
    return {"status": "healthy", "version": "0.1.0"}


@app.post("/check/", response_model=UploadResponse)
async def check_document_endpoint(
    file: UploadFile,
    current_user: User = Depends(
        require_role(["manager", "specialist", "supervisor", "administrator"])
    ),
) -> UploadResponse:
    """Проверить документ на соответствие стандартам."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Имя файла не указано")

    try:
        logger.info(
            f"Пользователь {current_user['username']} начинает проверку документа: {file.filename}"
        )

        content = await file.read()
        text = extract_text_from_file(UploadFileWrapper(file.filename, content))

        if not text.strip():
            raise HTTPException(
                status_code=400, detail="Не удалось извлечь текст из документа"
            )

        result = check_document(text)
        save_report(file.filename, result)

        # Преобразуем словари в объекты CheckResult
        check_results = [
            CheckResult(
                section=r["section"],
                match=cast(
                    Literal["да", "нет", "частично"],
                    r["match"] if r["match"] in ["да", "нет", "частично"] else "нет",
                ),
                comments=r.get("comments", ""),
                confidence=None,
            )
            for r in result
        ]

        pdf_path = settings.reports_dir / f"{file.filename}.pdf"
        generate_pdf(file.filename, result, str(pdf_path))

        logger.info(
            f"Документ {file.filename} успешно проверен пользователем {current_user['username']}"
        )

        return UploadResponse(
            filename=file.filename,
            report=check_results,
            task_id=None,
            pdf_path=str(pdf_path),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при проверке документа {file.filename}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Ошибка обработки документа: {str(e)}"
        ) from e


@app.post("/upload-and-create-task/", response_model=UploadResponse)
async def upload_create_task(
    file: UploadFile,
    current_user: User = Depends(
        require_role(["manager", "specialist", "supervisor", "administrator"])
    ),
) -> UploadResponse:
    """Проверить документ и создать задачу в Bitrix24."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Имя файла не указано")

    try:
        logger.info(
            f"Пользователь {current_user['username']} начинает проверку документа с созданием задачи: {file.filename}"
        )

        content = await file.read()
        text = extract_text_from_file(UploadFileWrapper(file.filename, content))

        if not text.strip():
            raise HTTPException(
                status_code=400, detail="Не удалось извлечь текст из документа"
            )

        result = check_document(text)

        # Создание задачи в Bitrix24
        summary = "\n".join(
            [f"{r['section']}: {r['match']} ({r['comments']})" for r in result]
        )

        task_id: int | None = None
        if settings.bitrix_webhook_url:
            try:
                task_id = create_bitrix_task(
                    title=f"Проверка: {file.filename}",
                    description=f"Результат проверки документа:\n{summary}",
                )
                logger.info(f"Создана задача в Bitrix24: {task_id}")
            except Exception as e:
                logger.warning(f"Не удалось создать задачу в Bitrix24: {e}")

        save_report(file.filename, result)

        # Преобразуем словари в объекты CheckResult
        check_results = [
            CheckResult(
                section=r["section"],
                match=cast(
                    Literal["да", "нет", "частично"],
                    r["match"] if r["match"] in ["да", "нет", "частично"] else "нет",
                ),
                comments=r.get("comments", ""),
                confidence=None,
            )
            for r in result
        ]

        pdf_path = settings.reports_dir / f"{file.filename}.pdf"
        generate_pdf(file.filename, result, str(pdf_path))

        logger.info(
            f"Документ {file.filename} успешно проверен с созданием задачи пользователем {current_user['username']}"
        )

        return UploadResponse(
            filename=file.filename,
            report=check_results,
            task_id=task_id,
            pdf_path=str(pdf_path),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при проверке документа {file.filename}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Ошибка обработки документа: {str(e)}"
        ) from e


@app.post("/check-supplier-proposal/", response_model=CommercialProposalAnalysis)
async def check_supplier_proposal(
    proposal: CommercialProposal,
    current_user: User = Depends(
        require_role(["manager", "specialist", "supervisor", "administrator"])
    ),
):
    """
    Проверяет коммерческое предложение поставщика
    """
    try:
        analysis = check_commercial_proposal(proposal)
        return analysis
    except Exception as e:
        logger.error(f"Ошибка при проверке коммерческого предложения: {e}")
        raise HTTPException(
            status_code=500, detail=f"Ошибка при проверке предложения: {str(e)}"
        )


@app.post("/check-product-specification/", response_model=list[CheckResult])
async def check_product_specification_endpoint(
    specifications: list[ProductSpecification],
    current_user: User = Depends(
        require_role(["manager", "specialist", "supervisor", "administrator"])
    ),
):
    """
    Проверяет товарные спецификации на соответствие требованиям
    """
    try:
        results = check_product_specification(specifications)
        return results
    except Exception as e:
        logger.error(f"Ошибка при проверке товарных спецификаций: {e}")
        raise HTTPException(
            status_code=500, detail=f"Ошибка при проверке спецификаций: {str(e)}"
        )


@app.get("/suppliers/{supplier_id}/history", response_model=SupplierHistory)
async def get_supplier_history_endpoint(
    supplier_id: int,
    current_user: User = Depends(
        require_role(["manager", "specialist", "supervisor", "administrator"])
    ),
):
    """
    Получает историю поставщика по его ID

    Args:
        supplier_id: ID поставщика

    Returns:
        SupplierHistory: Полная история поставщика включая транзакции и метрики
    """
    try:
        if supplier_id <= 0:
            raise HTTPException(
                status_code=400, detail="ID поставщика должен быть положительным числом"
            )

        logger.info(f"Получение истории для поставщика ID: {supplier_id}")
        history = get_supplier_history(supplier_id)
        logger.info(f"История поставщика {supplier_id} успешно получена")
        return history
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении истории поставщика {supplier_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Ошибка при получении истории поставщика: {str(e)}"
        )


# === АНАЛИТИЧЕСКИЕ ЭНДПОИНТЫ ===


@app.get("/analytics/dashboard")
async def get_analytics_dashboard(
    current_user: User = Depends(
        require_role(["manager", "supervisor", "administrator"])
    ),
):
    """
    Получить данные для аналитического дашборда с ключевыми метриками.

    Returns:
        dict: Словарь с основными метриками для дашборда
    """
    try:
        logger.info("Получение данных для аналитического дашборда")

        # Аудит доступа к аналитике
        log_api_access(
            user_id=current_user.get("user_id", current_user["username"]),
            username=current_user["username"],
            endpoint="/analytics/dashboard",
            method="GET",
        )
        audit_analytics_access(current_user, "dashboard")

        analytics_engine = AnalyticsEngine()
        price_engine = PriceAnalyticsEngine()
        recommendation_engine = RecommendationEngine()

        # Получаем основные метрики
        processing_metrics = analytics_engine.get_processing_metrics()
        approval_metrics = analytics_engine.get_approval_metrics()
        supplier_analytics = analytics_engine.get_supplier_analytics()
        document_analytics = analytics_engine.get_document_type_analytics()
        system_metrics = analytics_engine.get_system_metrics()

        # Получаем ценовую аналитику
        market_analysis = price_engine.get_market_overview()
        price_trends = price_engine.analyze_price_trends(days_back=30)

        # Получаем топ рекомендации
        top_recommendations = recommendation_engine.generate_supplier_recommendations()[
            :5
        ]
        market_opportunities = recommendation_engine.identify_market_opportunities()[:3]

        dashboard_data = {
            "processing_metrics": {
                "total_documents": processing_metrics.total_documents,
                "avg_processing_time": processing_metrics.avg_processing_time_minutes,
                "documents_today": processing_metrics.documents_processed_today,
                "processing_speed_trend": processing_metrics.processing_speed_trend,
            },
            "approval_metrics": {
                "approval_rate": approval_metrics.approval_rate,
                "avg_approval_time": approval_metrics.avg_approval_time_hours,
                "pending_approvals": approval_metrics.pending_approvals_count,
                "approval_trend": approval_metrics.approval_rate_trend,
            },
            "supplier_metrics": {
                "total_suppliers": supplier_analytics.total_suppliers,
                "active_suppliers": supplier_analytics.active_suppliers,
                "avg_supplier_rating": supplier_analytics.avg_supplier_rating,
                "top_suppliers": supplier_analytics.top_suppliers[:5],
            },
            "document_analytics": {
                "total_by_type": document_analytics.documents_by_type,
                "approval_rates_by_type": document_analytics.approval_rates_by_type,
                "avg_processing_time_by_type": document_analytics.avg_processing_time_by_type,
            },
            "market_overview": {
                "total_market_value": market_analysis.get("total_market_value", 0),
                "avg_price_change": market_analysis.get("avg_price_change_percent", 0),
                "active_categories": market_analysis.get("active_categories", 0),
                "price_volatility": market_analysis.get("price_volatility", 0),
            },
            "recent_trends": [
                {
                    "item_name": trend.item_name,
                    "supplier_name": trend.supplier_name,
                    "trend_direction": trend.trend_direction,
                    "trend_percentage": trend.trend_percentage,
                    "confidence_score": trend.confidence_score,
                }
                for trend in price_trends[:5]
            ],
            "recommendations": [
                {
                    "supplier_name": rec.supplier_name,
                    "recommendation_type": rec.recommendation_type,
                    "confidence_score": rec.confidence_score,
                    "estimated_savings": rec.estimated_savings,
                    "priority": rec.priority,
                }
                for rec in top_recommendations
            ],
            "market_opportunities": [
                {
                    "opportunity_type": opp.opportunity_type,
                    "description": opp.description,
                    "potential_savings": opp.potential_savings,
                    "time_sensitivity": opp.time_sensitivity,
                    "confidence_score": opp.confidence_score,
                }
                for opp in market_opportunities
            ],
            "system_health": {
                "uptime_hours": system_metrics.uptime_hours,
                "error_rate": system_metrics.error_rate,
                "avg_response_time": system_metrics.avg_response_time_ms,
                "active_users": system_metrics.active_users_count,
            },
            "generated_at": analytics_engine._get_current_timestamp(),
        }

        logger.info("Данные дашборда успешно сформированы")
        return dashboard_data

    except Exception as e:
        logger.error(f"Ошибка при получении данных дашборда: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении аналитических данных: {str(e)}",
        )


@app.get("/analytics/suppliers")
async def get_suppliers_analytics(
    current_user: User = Depends(
        require_role(["manager", "supervisor", "administrator"])
    ),
    supplier_id: Optional[str] = None,
    min_rating: Optional[float] = None,
    cooperation_status: Optional[str] = None,
    sort_by: Optional[str] = "rating",
    limit: Optional[int] = 50,
):
    """
    Получить аналитику по поставщикам с возможностью фильтрации.

    Args:
        supplier_id: ID конкретного поставщика (опционально)
        min_rating: Минимальный рейтинг поставщика (опционально)
        cooperation_status: Статус сотрудничества ('активный', 'потенциальный', 'приостановлен')
        sort_by: Поле для сортировки ('rating', 'total_amount', 'reliability_score')
        limit: Максимальное количество поставщиков в ответе

    Returns:
        dict: Аналитические данные по поставщикам
    """
    try:
        logger.info(
            f"Получение аналитики по поставщикам с фильтрами: supplier_id={supplier_id}, min_rating={min_rating}"
        )

        # Аудит доступа к аналитике
        log_api_access(
            user_id=current_user.get("user_id", current_user["username"]),
            username=current_user["username"],
            endpoint="/analytics/suppliers",
            method="GET",
        )
        audit_analytics_access(current_user, "suppliers")

        analytics_engine = AnalyticsEngine()
        price_engine = PriceAnalyticsEngine()
        recommendation_engine = RecommendationEngine()

        # Если запрашивается конкретный поставщик
        if supplier_id:
            # Получаем детальную информацию по поставщику
            supplier_analytics = analytics_engine.get_supplier_analytics()

            # Находим конкретного поставщика
            target_supplier = None
            for supplier in supplier_analytics.supplier_details:
                if supplier["supplier_id"] == supplier_id:
                    target_supplier = supplier
                    break

            if not target_supplier:
                raise HTTPException(
                    status_code=404, detail=f"Поставщик с ID {supplier_id} не найден"
                )

            # Получаем ценовой профиль поставщика
            try:
                price_profile = price_engine.analyze_supplier_price_profile(supplier_id)
                price_data = {
                    "avg_price_level": price_profile.avg_price_level,
                    "price_stability": price_profile.price_stability,
                    "competitive_advantage": price_profile.competitive_advantage,
                    "price_trend": price_profile.price_trend,
                }
            except:
                price_data = None

            # Получаем рекомендации по поставщику
            supplier_recommendations = (
                recommendation_engine.generate_supplier_recommendations()
            )
            supplier_rec = None
            for rec in supplier_recommendations:
                if rec.supplier_id == supplier_id:
                    supplier_rec = {
                        "recommendation_type": rec.recommendation_type,
                        "confidence_score": rec.confidence_score,
                        "reasons": rec.reasons,
                        "advantages": rec.advantages,
                        "risk_factors": rec.risk_factors,
                        "suggested_actions": rec.suggested_actions,
                        "estimated_savings": rec.estimated_savings,
                        "priority": rec.priority,
                    }
                    break

            return {
                "supplier_details": target_supplier,
                "price_analysis": price_data,
                "recommendation": supplier_rec,
                "generated_at": analytics_engine._get_current_timestamp(),
            }

        # Получаем общую аналитику по поставщикам
        supplier_analytics = analytics_engine.get_supplier_analytics()

        # Применяем фильтры
        filtered_suppliers = supplier_analytics.supplier_details

        if min_rating is not None:
            filtered_suppliers = [
                s
                for s in filtered_suppliers
                if s.get("overall_rating", 0) >= min_rating
            ]

        if cooperation_status:
            filtered_suppliers = [
                s
                for s in filtered_suppliers
                if s.get("cooperation_status", "").lower() == cooperation_status.lower()
            ]

        # Сортировка
        sort_key_map = {
            "rating": "overall_rating",
            "total_amount": "total_amount",
            "reliability_score": "reliability_score",
        }

        sort_key = sort_key_map.get(sort_by, "overall_rating")
        filtered_suppliers.sort(key=lambda x: x.get(sort_key, 0), reverse=True)

        # Ограничиваем количество
        if limit:
            filtered_suppliers = filtered_suppliers[:limit]

        # Получаем рекомендации для отфильтрованных поставщиков
        all_recommendations = recommendation_engine.generate_supplier_recommendations()
        recommendations_map = {rec.supplier_id: rec for rec in all_recommendations}

        # Обогащаем данные поставщиков рекомендациями
        enriched_suppliers = []
        for supplier in filtered_suppliers:
            supplier_id = supplier["supplier_id"]
            rec = recommendations_map.get(supplier_id)

            enriched_supplier = supplier.copy()
            if rec:
                enriched_supplier["recommendation"] = {
                    "type": rec.recommendation_type,
                    "confidence_score": rec.confidence_score,
                    "estimated_savings": rec.estimated_savings,
                    "priority": rec.priority,
                }

            enriched_suppliers.append(enriched_supplier)

        # Статистика по категориям
        category_stats = {
            "preferred": len(
                [
                    s
                    for s in enriched_suppliers
                    if s.get("recommendation", {}).get("type") == "preferred"
                ]
            ),
            "alternative": len(
                [
                    s
                    for s in enriched_suppliers
                    if s.get("recommendation", {}).get("type") == "alternative"
                ]
            ),
            "new_opportunity": len(
                [
                    s
                    for s in enriched_suppliers
                    if s.get("recommendation", {}).get("type") == "new_opportunity"
                ]
            ),
            "avoid": len(
                [
                    s
                    for s in enriched_suppliers
                    if s.get("recommendation", {}).get("type") == "avoid"
                ]
            ),
        }

        # Топ поставщики по различным метрикам
        top_by_rating = sorted(
            enriched_suppliers, key=lambda x: x.get("overall_rating", 0), reverse=True
        )[:5]
        top_by_amount = sorted(
            enriched_suppliers, key=lambda x: x.get("total_amount", 0), reverse=True
        )[:5]
        top_by_reliability = sorted(
            enriched_suppliers,
            key=lambda x: x.get("reliability_score", 0),
            reverse=True,
        )[:5]

        result = {
            "summary": {
                "total_suppliers": len(enriched_suppliers),
                "avg_rating": sum(
                    s.get("overall_rating", 0) for s in enriched_suppliers
                )
                / len(enriched_suppliers)
                if enriched_suppliers
                else 0,
                "total_transaction_amount": sum(
                    s.get("total_amount", 0) for s in enriched_suppliers
                ),
                "category_distribution": category_stats,
            },
            "suppliers": enriched_suppliers,
            "top_performers": {
                "by_rating": [
                    {
                        "supplier_id": s["supplier_id"],
                        "name": s["name"],
                        "overall_rating": s.get("overall_rating", 0),
                    }
                    for s in top_by_rating
                ],
                "by_transaction_volume": [
                    {
                        "supplier_id": s["supplier_id"],
                        "name": s["name"],
                        "total_amount": s.get("total_amount", 0),
                    }
                    for s in top_by_amount
                ],
                "by_reliability": [
                    {
                        "supplier_id": s["supplier_id"],
                        "name": s["name"],
                        "reliability_score": s.get("reliability_score", 0),
                    }
                    for s in top_by_reliability
                ],
            },
            "filters_applied": {
                "min_rating": min_rating,
                "cooperation_status": cooperation_status,
                "sort_by": sort_by,
                "limit": limit,
            },
            "generated_at": analytics_engine._get_current_timestamp(),
        }

        logger.info(
            f"Аналитика по поставщикам успешно сформирована: {len(enriched_suppliers)} поставщиков"
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении аналитики по поставщикам: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении аналитики по поставщикам: {str(e)}",
        )


@app.get("/analytics/reports/{period}")
async def get_periodic_report(
    period: str,
    current_user: User = Depends(require_role(["supervisor", "administrator"])),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    include_charts: Optional[bool] = True,
    format: Optional[str] = "json",
):
    """
    Получить периодический отчет за указанный период.

    Args:
        period: Период отчета ('day', 'week', 'month', 'quarter', 'year', 'custom')
        start_date: Начальная дата для custom периода (YYYY-MM-DD)
        end_date: Конечная дата для custom периода (YYYY-MM-DD)
        include_charts: Включать ли данные для графиков
        format: Формат ответа ('json', 'summary')

    Returns:
        dict: Периодический отчет с аналитическими данными
    """
    try:
        logger.info(f"Генерация периодического отчета за период: {period}")

        # Аудит доступа к аналитике
        log_api_access(
            user_id=current_user.get("user_id", current_user["username"]),
            username=current_user["username"],
            endpoint=f"/analytics/reports/{period}",
            method="GET",
        )
        audit_analytics_access(current_user, "reports", {"period": period})

        # Валидация периода
        valid_periods = ["day", "week", "month", "quarter", "year", "custom"]
        if period not in valid_periods:
            raise HTTPException(
                status_code=400,
                detail=f"Неверный период. Доступные периоды: {', '.join(valid_periods)}",
            )

        # Валидация дат для custom периода
        if period == "custom":
            if not start_date or not end_date:
                raise HTTPException(
                    status_code=400,
                    detail="Для периода 'custom' необходимо указать start_date и end_date",
                )

            try:
                from datetime import datetime

                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")

                if start_dt >= end_dt:
                    raise HTTPException(
                        status_code=400,
                        detail="Начальная дата должна быть раньше конечной даты",
                    )
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Неверный формат даты. Используйте YYYY-MM-DD",
                )

        analytics_engine = AnalyticsEngine()
        price_engine = PriceAnalyticsEngine()
        recommendation_engine = RecommendationEngine()

        # Получаем базовые метрики
        processing_metrics = analytics_engine.get_processing_metrics()
        approval_metrics = analytics_engine.get_approval_metrics()
        supplier_analytics = analytics_engine.get_supplier_analytics()
        document_analytics = analytics_engine.get_document_type_analytics()
        system_metrics = analytics_engine.get_system_metrics()

        # Получаем ценовую аналитику
        market_analysis = price_engine.get_market_overview()
        price_trends = price_engine.analyze_price_trends()

        # Получаем рекомендации
        supplier_recommendations = (
            recommendation_engine.generate_supplier_recommendations()
        )
        procurement_recommendations = (
            recommendation_engine.generate_procurement_recommendations()
        )

        # Формируем отчет в зависимости от периода
        period_info = {
            "period_type": period,
            "start_date": start_date if period == "custom" else None,
            "end_date": end_date if period == "custom" else None,
            "generated_at": analytics_engine._get_current_timestamp(),
        }

        # Основные показатели эффективности (KPI)
        kpi_summary = {
            "processing_efficiency": {
                "avg_processing_time": processing_metrics.avg_processing_time_hours,
                "documents_processed": processing_metrics.total_documents,
                "processing_speed_trend": "улучшение"
                if processing_metrics.avg_processing_time_hours < 24
                else "требует внимания",
            },
            "approval_performance": {
                "approval_rate": approval_metrics.overall_approval_rate,
                "avg_approval_time": approval_metrics.avg_approval_time_hours,
                "approval_trend": "стабильно"
                if approval_metrics.overall_approval_rate > 0.7
                else "снижение",
            },
            "supplier_performance": {
                "total_suppliers": len(supplier_analytics.supplier_details),
                "avg_supplier_rating": supplier_analytics.avg_rating,
                "top_supplier_rating": max(
                    [
                        s.get("overall_rating", 0)
                        for s in supplier_analytics.supplier_details
                    ],
                    default=0,
                ),
            },
            "financial_metrics": {
                "total_transaction_volume": sum(
                    [
                        s.get("total_amount", 0)
                        for s in supplier_analytics.supplier_details
                    ]
                ),
                "avg_price_level": market_analysis.avg_market_price,
                "price_volatility": market_analysis.price_volatility,
                "potential_savings": sum(
                    [
                        rec.estimated_savings
                        for rec in procurement_recommendations
                        if rec.estimated_savings
                    ]
                ),
            },
        }

        # Детальная аналитика по категориям
        detailed_analysis = {
            "document_processing": {
                "by_type": {
                    doc_type: {
                        "count": stats["count"],
                        "avg_processing_time": stats["avg_processing_time"],
                        "approval_rate": stats["approval_rate"],
                    }
                    for doc_type, stats in document_analytics.type_statistics.items()
                },
                "processing_bottlenecks": processing_metrics.bottlenecks,
                "quality_metrics": {
                    "error_rate": 1
                    - (
                        processing_metrics.successful_checks
                        / max(processing_metrics.total_documents, 1)
                    ),
                    "reprocessing_rate": 0.05,  # Примерное значение
                },
            },
            "supplier_analysis": {
                "performance_distribution": {
                    "excellent": len(
                        [
                            s
                            for s in supplier_analytics.supplier_details
                            if s.get("overall_rating", 0) >= 4.5
                        ]
                    ),
                    "good": len(
                        [
                            s
                            for s in supplier_analytics.supplier_details
                            if 3.5 <= s.get("overall_rating", 0) < 4.5
                        ]
                    ),
                    "average": len(
                        [
                            s
                            for s in supplier_analytics.supplier_details
                            if 2.5 <= s.get("overall_rating", 0) < 3.5
                        ]
                    ),
                    "poor": len(
                        [
                            s
                            for s in supplier_analytics.supplier_details
                            if s.get("overall_rating", 0) < 2.5
                        ]
                    ),
                },
                "cooperation_status": {
                    status: len(
                        [
                            s
                            for s in supplier_analytics.supplier_details
                            if s.get("cooperation_status") == status
                        ]
                    )
                    for status in ["активный", "потенциальный", "приостановлен"]
                },
                "risk_assessment": {
                    "high_risk": len(
                        [
                            s
                            for s in supplier_analytics.supplier_details
                            if s.get("risk_score", 0) > 0.7
                        ]
                    ),
                    "medium_risk": len(
                        [
                            s
                            for s in supplier_analytics.supplier_details
                            if 0.3 <= s.get("risk_score", 0) <= 0.7
                        ]
                    ),
                    "low_risk": len(
                        [
                            s
                            for s in supplier_analytics.supplier_details
                            if s.get("risk_score", 0) < 0.3
                        ]
                    ),
                },
            },
            "market_insights": {
                "price_trends": {
                    "trending_up": len(
                        [trend for trend in price_trends if trend.direction == "up"]
                    ),
                    "trending_down": len(
                        [trend for trend in price_trends if trend.direction == "down"]
                    ),
                    "stable": len(
                        [trend for trend in price_trends if trend.direction == "stable"]
                    ),
                },
                "market_opportunities": {
                    "cost_reduction_potential": market_analysis.cost_reduction_opportunities,
                    "new_supplier_opportunities": len(
                        [
                            rec
                            for rec in supplier_recommendations
                            if rec.recommendation_type == "new_opportunity"
                        ]
                    ),
                    "market_volatility_level": "высокая"
                    if market_analysis.price_volatility > 0.3
                    else "умеренная"
                    if market_analysis.price_volatility > 0.1
                    else "низкая",
                },
            },
        }

        # Рекомендации и действия
        actionable_insights = {
            "priority_actions": [
                {
                    "category": "supplier_management",
                    "action": rec.suggested_actions[0]
                    if rec.suggested_actions
                    else "Оптимизировать работу с поставщиком",
                    "priority": rec.priority,
                    "estimated_impact": rec.estimated_savings,
                }
                for rec in supplier_recommendations[:5]
                if rec.priority == "high"
            ],
            "procurement_optimizations": [
                {
                    "category": rec.category,
                    "recommendation": rec.description,
                    "confidence": rec.confidence_score,
                    "potential_savings": rec.estimated_savings,
                }
                for rec in procurement_recommendations[:3]
            ],
            "risk_mitigation": [
                {
                    "risk_type": "supplier_reliability",
                    "description": "Мониторинг поставщиков с низким рейтингом",
                    "recommended_action": "Провести аудит поставщиков с рейтингом ниже 3.0",
                },
                {
                    "risk_type": "price_volatility",
                    "description": "Высокая волатильность цен на рынке",
                    "recommended_action": "Рассмотреть долгосрочные контракты с фиксированными ценами",
                },
            ],
        }

        # Данные для графиков (если запрошены)
        chart_data = None
        if include_charts:
            chart_data = {
                "processing_timeline": {
                    "labels": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
                    "datasets": [
                        {
                            "label": "Обработанные документы",
                            "data": [12, 15, 18, 14, 20, 8, 5],
                        },
                        {
                            "label": "Одобренные документы",
                            "data": [10, 12, 15, 11, 16, 6, 4],
                        },
                    ],
                },
                "supplier_ratings_distribution": {
                    "labels": ["1-2", "2-3", "3-4", "4-5"],
                    "data": [
                        len(
                            [
                                s
                                for s in supplier_analytics.supplier_details
                                if 1 <= s.get("overall_rating", 0) < 2
                            ]
                        ),
                        len(
                            [
                                s
                                for s in supplier_analytics.supplier_details
                                if 2 <= s.get("overall_rating", 0) < 3
                            ]
                        ),
                        len(
                            [
                                s
                                for s in supplier_analytics.supplier_details
                                if 3 <= s.get("overall_rating", 0) < 4
                            ]
                        ),
                        len(
                            [
                                s
                                for s in supplier_analytics.supplier_details
                                if 4 <= s.get("overall_rating", 0) <= 5
                            ]
                        ),
                    ],
                },
                "price_trend_chart": {
                    "labels": [trend.category for trend in price_trends[:10]],
                    "datasets": [
                        {
                            "label": "Изменение цены (%)",
                            "data": [
                                trend.percentage_change for trend in price_trends[:10]
                            ],
                        }
                    ],
                },
            }

        # Формируем итоговый отчет
        report = {
            "report_info": period_info,
            "executive_summary": {
                "key_metrics": kpi_summary,
                "highlights": [
                    f"Обработано {processing_metrics.total_documents} документов",
                    f"Средний процент одобрения: {approval_metrics.overall_approval_rate:.1%}",
                    f"Активных поставщиков: {len([s for s in supplier_analytics.supplier_details if s.get('cooperation_status') == 'активный'])}",
                    f"Потенциальная экономия: {sum([rec.estimated_savings for rec in procurement_recommendations if rec.estimated_savings]):,.0f} руб.",
                ],
                "concerns": [
                    concern
                    for concern in [
                        "Низкий процент одобрения документов"
                        if approval_metrics.overall_approval_rate < 0.6
                        else None,
                        "Высокое время обработки"
                        if processing_metrics.avg_processing_time_hours > 48
                        else None,
                        "Высокая волатильность цен"
                        if market_analysis.price_volatility > 0.3
                        else None,
                    ]
                    if concern
                ],
            },
            "detailed_analysis": detailed_analysis,
            "actionable_insights": actionable_insights,
        }

        # Добавляем данные графиков если запрошены
        if chart_data:
            report["chart_data"] = chart_data

        # Возвращаем краткую версию если запрошен summary формат
        if format == "summary":
            return {
                "period": period_info,
                "summary": report["executive_summary"],
                "top_recommendations": actionable_insights["priority_actions"][:3],
            }

        logger.info(f"Периодический отчет за {period} успешно сформирован")
        return report

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при генерации периодического отчета: {e}")
        raise HTTPException(
            status_code=500, detail=f"Ошибка при генерации отчета: {str(e)}"
        )


@app.post("/suppliers/compare")
async def compare_suppliers(
    suppliers_data: list[dict],
    criteria_weights: Optional[CriteriaWeights] = None,
    top_n: int = 5,
    normalize: bool = True,
):
    """
    Сравнение поставщиков по многокритериальному анализу.

    Args:
        suppliers_data: Список данных о поставщиках (цены, сроки, рейтинги)
        criteria_weights: Веса критериев (опционально, используются умолчания)
        top_n: Количество лучших поставщиков для возврата
        normalize: Нормализовать ли значения перед расчетом

    Returns:
        dict: Топ-N поставщиков с их оценками и детальной информацией
    """
    try:
        from recommendations import score_suppliers, select_top_suppliers

        # Используем веса по умолчанию если не предоставлены
        if criteria_weights is None:
            criteria_weights = CriteriaWeights()

        # Валидация входных данных
        if not suppliers_data:
            raise HTTPException(
                status_code=400, detail="Список поставщиков не может быть пустым"
            )

        if top_n <= 0:
            raise HTTPException(
                status_code=400,
                detail="Параметр top_n должен быть положительным числом",
            )

        # Преобразуем входные данные в SupplierScore объекты
        supplier_scores = []
        for idx, supplier in enumerate(suppliers_data):
            try:
                # Извлекаем основные данные с проверками
                supplier_info = {
                    "supplier_id": supplier.get("supplier_id", f"supplier_{idx}"),
                    "supplier_name": supplier.get(
                        "supplier_name", f"Поставщик {idx + 1}"
                    ),
                    "contact_info": supplier.get("contact_info", {}),
                    "certifications": supplier.get("certifications", []),
                }

                # Извлекаем критерии оценки
                price = float(supplier.get("price", 0))
                delivery_days = int(supplier.get("delivery_days", 0))
                quality_rating = float(supplier.get("quality_rating", 0))
                reliability_rating = float(supplier.get("reliability_rating", 0))
                service_rating = float(supplier.get("service_rating", 0))

                # Создаем объект оценки поставщика
                supplier_score = SupplierScore(
                    supplier_info=supplier_info,
                    criteria_weights=criteria_weights,
                    scores={
                        "price": price,
                        "delivery_days": delivery_days,
                        "quality_rating": quality_rating,
                        "reliability_rating": reliability_rating,
                        "service_rating": service_rating,
                    },
                )

                supplier_scores.append(supplier_score)

            except (ValueError, TypeError) as e:
                logger.warning(f"Ошибка при обработке данных поставщика {idx}: {e}")
                continue

        if not supplier_scores:
            raise HTTPException(
                status_code=400,
                detail="Не удалось обработать ни одного поставщика из-за ошибок в данных",
            )

        # Оцениваем поставщиков
        scored_suppliers = score_suppliers(
            suppliers=supplier_scores, normalize=normalize
        )

        # Выбираем топ-N поставщиков
        top_suppliers = select_top_suppliers(
            scored_suppliers=scored_suppliers, top_n=min(top_n, len(scored_suppliers))
        )

        # Формируем ответ
        response = {
            "comparison_summary": {
                "total_suppliers": len(suppliers_data),
                "analyzed_suppliers": len(supplier_scores),
                "top_n": len(top_suppliers),
                "criteria_weights": criteria_weights.dict(),
            },
            "top_suppliers": [
                {
                    "rank": idx + 1,
                    "supplier_id": supplier.supplier_info.get("supplier_id"),
                    "supplier_name": supplier.supplier_info.get("supplier_name"),
                    "total_score": supplier.total_score,
                    "individual_scores": supplier.scores,
                    "weighted_scores": supplier.weighted_scores,
                    "criteria_breakdown": {
                        criterion: {
                            "raw_score": supplier.scores[criterion],
                            "weight": getattr(criteria_weights, f"{criterion}_weight"),
                            "weighted_score": supplier.weighted_scores[criterion],
                        }
                        for criterion in supplier.scores.keys()
                    },
                }
                for idx, supplier in enumerate(top_suppliers)
            ],
            "analysis_metadata": {
                "normalized": normalize,
                "scoring_method": "weighted_sum",
                "timestamp": datetime.now().isoformat(),
            },
        }

        logger.info(
            f"Успешно сравнено {len(suppliers_data)} поставщиков, возвращено топ-{len(top_suppliers)}"
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при сравнении поставщиков: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при сравнении: {str(e)}")


# === ЭНДПОИНТЫ ДЛЯ СМЕНЫ СТАТУСА И ОТПРАВКИ НАПОМИНАНИЙ ===


@app.post("/tasks/{task_id}/status")
async def change_task_status(
    task_id: int,
    status_update: dict,
    current_user: User = Depends(
        require_role(["manager", "specialist", "supervisor", "administrator"])
    ),
):
    """
    Изменить статус задачи в Bitrix24

    Args:
        task_id: ID задачи в Bitrix24
        status_update: Словарь с новым статусом и комментарием

    Returns:
        dict: Результат операции обновления статуса
    """
    try:
        new_status = status_update.get("status")
        comment = status_update.get("comment", "")

        if not new_status:
            raise HTTPException(status_code=400, detail="Не указан новый статус")

        logger.info(
            f"Пользователь {current_user['username']} изменяет статус задачи {task_id} на {new_status}"
        )

        # Аудит изменения статуса
        log_api_access(
            user_id=current_user.get("user_id", current_user["username"]),
            username=current_user["username"],
            endpoint=f"/tasks/{task_id}/status",
            method="POST",
        )
        audit_user_action(
            current_user,
            "change_task_status",
            "task_management",
            "status_change",
            {"task_id": task_id, "new_status": new_status, "comment": comment},
        )

        # Обновляем статус задачи в Bitrix24
        from src.bitrix_integration import update_task_status

        success = update_task_status(task_id, new_status, comment)

        if success:
            logger.info(f"Статус задачи {task_id} успешно изменен на {new_status}")
            return {
                "status": "success",
                "message": f"Статус задачи успешно изменен на {new_status}",
                "task_id": task_id,
                "new_status": new_status,
            }
        else:
            logger.error(f"Не удалось изменить статус задачи {task_id}")
            raise HTTPException(
                status_code=500, detail="Не удалось изменить статус задачи в Bitrix24"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при изменении статуса задачи {task_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Ошибка при изменении статуса задачи: {str(e)}"
        )


@app.post("/tasks/{task_id}/reminder")
async def send_task_reminder(
    task_id: int,
    reminder_data: dict,
    current_user: User = Depends(
        require_role(["manager", "specialist", "supervisor", "administrator"])
    ),
):
    """
    Отправить напоминание по задаче в Bitrix24

    Args:
        task_id: ID задачи в Bitrix24
        reminder_data: Данные напоминания (сообщение, получатели, тип)

    Returns:
        dict: Результат отправки напоминания
    """
    try:
        message = reminder_data.get("message")
        recipients = reminder_data.get("recipients", [])
        reminder_type = reminder_data.get("type", "comment")

        if not message:
            raise HTTPException(
                status_code=400, detail="Не указано сообщение напоминания"
            )

        logger.info(
            f"Пользователь {current_user['username']} отправляет напоминание по задаче {task_id}"
        )

        # Аудит отправки напоминания
        log_api_access(
            user_id=current_user.get("user_id", current_user["username"]),
            username=current_user["username"],
            endpoint=f"/tasks/{task_id}/reminder",
            method="POST",
        )
        audit_user_action(
            current_user,
            "send_task_reminder",
            "task_management",
            "reminder_sent",
            {
                "task_id": task_id,
                "message": message,
                "recipients": recipients,
                "type": reminder_type,
            },
        )

        # Отправляем напоминание в Bitrix24
        from src.bitrix_integration import send_task_reminder

        success = send_task_reminder(task_id, message, recipients, reminder_type)

        if success:
            logger.info(f"Напоминание по задаче {task_id} успешно отправлено")
            return {
                "status": "success",
                "message": "Напоминание успешно отправлено",
                "task_id": task_id,
                "reminder_type": reminder_type,
                "recipients_count": len(recipients),
            }
        else:
            logger.error(f"Не удалось отправить напоминание по задаче {task_id}")
            raise HTTPException(
                status_code=500, detail="Не удалось отправить напоминание в Bitrix24"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при отправке напоминания по задаче {task_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Ошибка при отправке напоминания: {str(e)}"
        )


@app.get("/tasks/{task_id}/details")
async def get_task_details(
    task_id: int,
    current_user: User = Depends(
        require_role(["manager", "specialist", "supervisor", "administrator"])
    ),
):
    """
    Получить детальную информацию о задаче из Bitrix24

    Args:
        task_id: ID задачи в Bitrix24

    Returns:
        dict: Детальная информация о задаче
    """
    try:
        logger.info(
            f"Пользователь {current_user['username']} запрашивает детали задачи {task_id}"
        )

        # Аудит доступа к задаче
        log_api_access(
            user_id=current_user.get("user_id", current_user["username"]),
            username=current_user["username"],
            endpoint=f"/tasks/{task_id}/details",
            method="GET",
        )
        audit_user_action(
            current_user,
            "get_task_details",
            "task_management",
            "view_task",
            {"task_id": task_id},
        )

        # Получаем детали задачи из Bitrix24
        from src.bitrix_integration import get_task_details

        task_details = get_task_details(task_id)

        if task_details:
            return {"status": "success", "data": task_details}
        else:
            logger.error(f"Задача {task_id} не найдена")
            raise HTTPException(
                status_code=404, detail=f"Задача с ID {task_id} не найдена"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении деталей задачи {task_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Ошибка при получении деталей задачи: {str(e)}"
        )


@app.get("/tasks")
async def get_tasks_list(
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(
        require_role(["manager", "specialist", "supervisor", "administrator"])
    ),
):
    """
    Получить список задач из Bitrix24 с фильтрацией

    Args:
        status: Фильтр по статусу задачи
        assigned_to: Фильтр по исполнителю
        created_after: Фильтр по дате создания (YYYY-MM-DD)
        created_before: Фильтр по дате создания (YYYY-MM-DD)
        limit: Максимальное количество задач

    Returns:
        dict: Список задач с фильтрами
    """
    try:
        logger.info(f"Пользователь {current_user['username']} запрашивает список задач")

        # Аудит доступа к списку задач
        log_api_access(
            user_id=current_user.get("user_id", current_user["username"]),
            username=current_user["username"],
            endpoint="/tasks",
            method="GET",
        )
        audit_user_action(
            current_user,
            "get_tasks_list",
            "task_management",
            "view_tasks",
            {"filters": {"status": status, "assigned_to": assigned_to, "limit": limit}},
        )

        # Формируем фильтры
        filters = {}
        if status:
            filters["status"] = status
        if assigned_to:
            filters["assigned_to"] = assigned_to
        if created_after:
            filters["created_after"] = created_after
        if created_before:
            filters["created_before"] = created_before

        # Получаем список задач из Bitrix24
        from src.bitrix_integration import get_tasks_list

        tasks = get_tasks_list(filters=filters, limit=limit)

        return {
            "status": "success",
            "data": {
                "tasks": tasks,
                "total_count": len(tasks),
                "filters_applied": filters,
            },
        }

    except Exception as e:
        logger.error(f"Ошибка при получении списка задач: {e}")
        raise HTTPException(
            status_code=500, detail=f"Ошибка при получении списка задач: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
