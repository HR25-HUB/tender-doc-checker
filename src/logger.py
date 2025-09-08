"""Улучшенная настройка логирования с детальным логированием исключений парсинга."""

import json
import sys
import traceback
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from .config import settings


class ParsingLogger:
    """Специализированный логгер для операций парсинга и извлечения текста."""

    def __init__(self):
        self.logger = logger
        self.setup_parsing_logger()

    def setup_parsing_logger(self):
        """Настройка специализированного логгера для парсинга."""
        # Дополнительный формат для структурированного логирования
        structured_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>PARSING</cyan> | "
            "<cyan>{extra[operation]}</cyan> | "
            "<level>{message}</level> | "
            "<dim>{extra[context]}</dim>"
        )

        # Консольный вывод для парсинга
        logger.add(
            sys.stderr,
            format=structured_format,
            level=settings.log_level,
            colorize=True,
            backtrace=True,
            diagnose=True,
            filter=lambda record: record["extra"]
            .get("operation", "")
            .startswith("parsing_"),
        )

        # Файловый вывод для парсинга
        if settings.log_file:
            log_path = Path(settings.log_file)
            parsing_log_path = log_path.parent / "parsing.log"

            logger.add(
                parsing_log_path,
                format=structured_format,
                level=settings.log_level,
                rotation="5 MB",
                retention="2 weeks",
                compression="zip",
                backtrace=True,
                diagnose=True,
                filter=lambda record: record["extra"]
                .get("operation", "")
                .startswith("parsing_"),
            )

    def log_parsing_operation(self, operation: str, **context):
        """Декоратор для логирования операций парсинга."""

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = datetime.now()
                operation_id = f"{operation}_{start_time.strftime('%Y%m%d_%H%M%S_%f')}"

                # Логирование начала операции
                with logger.contextualize(
                    operation=f"parsing_{operation}",
                    context=json.dumps(
                        {
                            "operation_id": operation_id,
                            "function": func.__name__,
                            "args_count": len(args),
                            "kwargs_keys": list(kwargs.keys()),
                            "start_time": start_time.isoformat(),
                        }
                    ),
                ):
                    logger.info(f"Начало операции парсинга: {operation}")

                try:
                    result = func(*args, **kwargs)

                    # Логирование успешного завершения
                    duration = (datetime.now() - start_time).total_seconds()
                    with logger.contextualize(
                        operation=f"parsing_{operation}",
                        context=json.dumps(
                            {
                                "operation_id": operation_id,
                                "duration_seconds": duration,
                                "result_length": len(str(result)) if result else 0,
                                "status": "success",
                            }
                        ),
                    ):
                        logger.info(f"Операция парсинга завершена успешно: {operation}")

                    return result

                except Exception as e:
                    # Детальное логирование исключения
                    duration = (datetime.now() - start_time).total_seconds()
                    error_details = self._extract_error_details(e)

                    with logger.contextualize(
                        operation=f"parsing_{operation}",
                        context=json.dumps(
                            {
                                "operation_id": operation_id,
                                "duration_seconds": duration,
                                "error_type": type(e).__name__,
                                "error_message": str(e),
                                "error_details": error_details,
                                "traceback": traceback.format_exc(),
                                "status": "error",
                            }
                        ),
                    ):
                        logger.error(f"Ошибка при операции парсинга: {operation}")

                    # Повторное исключение для обработки выше
                    raise

            return wrapper

        return decorator

    def _extract_error_details(self, exception: Exception) -> dict[str, Any]:
        """Извлечение детальной информации об ошибке."""
        error_info = {
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
            "exception_args": getattr(exception, "args", []),
            "filename": None,
            "file_size": None,
            "file_type": None,
        }

        # Дополнительная информация для специфических типов ошибок
        if isinstance(exception, (IOError, OSError)):
            error_info.update(
                {
                    "errno": getattr(exception, "errno", None),
                    "strerror": getattr(exception, "strerror", None),
                }
            )

        return error_info

    def log_file_metadata(
        self, file_path: str, operation: str, metadata: dict[str, Any]
    ):
        """Логирование метаданных файла перед операцией парсинга."""
        with logger.contextualize(
            operation=f"parsing_{operation}",
            context=json.dumps(
                {
                    "file_path": file_path,
                    "file_size": metadata.get("file_size"),
                    "file_type": metadata.get("file_type"),
                    "last_modified": metadata.get("last_modified"),
                    "operation": "file_metadata",
                }
            ),
        ):
            logger.info(f"Метаданные файла: {file_path}")

    def log_parsing_performance(self, operation: str, metrics: dict[str, Any]):
        """Логирование метрик производительности парсинга."""
        with logger.contextualize(
            operation=f"parsing_{operation}",
            context=json.dumps(
                {"metrics": metrics, "operation": "performance_metrics"}
            ),
        ):
            logger.info(f"Метрики производительности: {operation}")


def setup_logging() -> None:
    """Улучшенная настройка системы логирования с поддержкой парсинга."""
    # Удаляем стандартный обработчик
    logger.remove()

    # Улучшенный формат логов с контекстом
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # Консольный вывод
    logger.add(
        sys.stderr,
        format=log_format,
        level=settings.log_level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # Файловый вывод (если указан)
    if settings.log_file:
        log_path = Path(settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_path,
            format=log_format,
            level=settings.log_level,
            rotation="10 MB",
            retention="1 month",
            compression="zip",
            backtrace=True,
            diagnose=True,
        )

    # Инициализация специализированного логгера для парсинга
    parsing_logger = ParsingLogger()

    logger.info(
        "Логирование настроено с поддержкой детального логирования исключений парсинга"
    )


# Глобальный экземпляр логгера для парсинга
parsing_logger = ParsingLogger()


def log_parsing_exception(
    operation: str, exception: Exception, context: Optional[dict[str, Any]] = None
):
    """
    Утилита для быстрого логирования исключений парсинга.

    Args:
        operation: Название операции парсинга
        exception: Исключение для логирования
        context: Дополнительный контекст
    """
    error_details = {
        "error_type": type(exception).__name__,
        "error_message": str(exception),
        "traceback": traceback.format_exc(),
        **(context or {}),
    }

    logger.error(
        f"Исключение при парсинге: {operation}",
        extra={
            "operation": f"parsing_{operation}",
            "context": json.dumps(error_details),
        },
    )


def log_file_processing_start(
    file_path: str, operation: str, metadata: Optional[dict[str, Any]] = None
):
    """Логирование начала обработки файла."""
    context = {
        "file_path": file_path,
        "operation": operation,
        "metadata": metadata or {},
    }

    logger.info(
        f"Начало обработки файла: {file_path}",
        extra={"operation": f"parsing_{operation}", "context": json.dumps(context)},
    )


def log_file_processing_complete(
    file_path: str, operation: str, metrics: dict[str, Any]
):
    """Логирование завершения обработки файла."""
    context = {"file_path": file_path, "operation": operation, "metrics": metrics}

    logger.info(
        f"Завершение обработки файла: {file_path}",
        extra={"operation": f"parsing_{operation}", "context": json.dumps(context)},
    )


# Настраиваем логирование при импорте модуля
setup_logging()
