"""
Bitrix24 интеграция для управления задачами
"""

import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class Bitrix24API:
    """Класс для работы с Bitrix24 API"""

    def __init__(self):
        self.webhook_url = os.getenv("BITRIX_WEBHOOK_URL")
        if not self.webhook_url:
            raise ValueError("BITRIX_WEBHOOK_URL не установлен в переменных окружения")

    def _make_request(self, method: str, params: dict = None) -> dict:
        """Выполнить запрос к Bitrix24 API"""
        try:
            url = f"{self.webhook_url}/{method}"
            response = requests.post(url, json=params or {})
            response.raise_for_status()

            result = response.json()
            if "error" in result:
                logger.error(f"Ошибка Bitrix24 API: {result}")
                return None

            return result.get("result", {})

        except Exception as e:
            logger.error(f"Ошибка при запросе к Bitrix24: {e}")
            return None


# Глобальный клиент Bitrix24 (инициализируется при первом использовании)
_bitrix_client = None


def get_bitrix_client():
    """Получить клиент Bitrix24 с ленивой инициализацией"""
    global _bitrix_client
    if _bitrix_client is None:
        try:
            _bitrix_client = Bitrix24API()
        except ValueError as e:
            logger.warning(f"Bitrix24 не настроен: {e}")
            return None
    return _bitrix_client


def update_task_status(task_id: int, new_status: str, comment: str = "") -> bool:
    """
    Обновить статус задачи в Bitrix24

    Args:
        task_id: ID задачи в Bitrix24
        new_status: Новый статус задачи
        comment: Комментарий к изменению

    Returns:
        bool: Успешность операции
    """
    client = get_bitrix_client()
    if not client:
        logger.warning("Bitrix24 не настроен, используем мок-режим")
        return True  # Возвращаем True для мок-режима

    try:
        # Получаем текущую задачу
        task_data = client._make_request("tasks.task.get", {"taskId": task_id})
        if not task_data:
            logger.error(f"Не удалось получить задачу {task_id}")
            return False

        # Обновляем статус задачи
        update_params = {"taskId": task_id, "fields": {"STATUS": new_status}}

        result = client._make_request("tasks.task.update", update_params)
        if not result:
            logger.error(f"Не удалось обновить статус задачи {task_id}")
            return False

        # Добавляем комментарий если он указан
        if comment:
            comment_params = {
                "taskId": task_id,
                "fields": {
                    "POST_MESSAGE": comment,
                    "AUTHOR_ID": 1,  # ID пользователя по умолчанию
                },
            }
            client._make_request("task.commentitem.add", comment_params)

        logger.info(f"Статус задачи {task_id} успешно обновлен на {new_status}")
        return True

    except Exception as e:
        logger.error(f"Ошибка при обновлении статуса задачи {task_id}: {e}")
        return False


def send_task_reminder(
    task_id: int,
    message: str,
    recipients: list[str] = None,
    reminder_type: str = "comment",
) -> bool:
    """
    Отправить напоминание по задаче в Bitrix24

    Args:
        task_id: ID задачи в Bitrix24
        message: Текст напоминания
        recipients: Список получателей (если не указан, отправляется всем участникам)
        reminder_type: Тип напоминания (comment, notification, email)

    Returns:
        bool: Успешность операции
    """
    client = get_bitrix_client()
    if not client:
        logger.warning("Bitrix24 не настроен, используем мок-режим")
        return True  # Возвращаем True для мок-режима

    try:
        # Получаем информацию о задаче
        task_data = client._make_request("tasks.task.get", {"taskId": task_id})
        if not task_data:
            logger.error(f"Не удалось получить задачу {task_id}")
            return False

        task_info = task_data.get("task", {})

        # Определяем получателей
        if not recipients:
            # Получаем участников задачи
            participants = []
            if task_info.get("responsible"):
                participants.append(str(task_info["responsible"]["id"]))
            if task_info.get("accomplices"):
                participants.extend(
                    [str(acc["id"]) for acc in task_info["accomplices"]]
                )
            if task_info.get("auditors"):
                participants.extend([str(aud["id"]) for aud in task_info["auditors"]])
            recipients = list(set(participants))

        # Отправляем напоминание в зависимости от типа
        if reminder_type == "comment":
            # Добавляем комментарий к задаче
            comment_params = {
                "taskId": task_id,
                "fields": {
                    "POST_MESSAGE": f"🔔 Напоминание: {message}",
                    "AUTHOR_ID": 1,  # ID пользователя по умолчанию
                },
            }
            result = client._make_request("task.commentitem.add", comment_params)

        elif reminder_type == "notification":
            # Отправляем уведомление пользователям
            for recipient_id in recipients:
                notification_params = {
                    "USER_ID": recipient_id,
                    "MESSAGE": f"Напоминание по задаче #{task_id}: {message}",
                    "MESSAGE_OUT": f"Напоминание по задаче #{task_id}: {message}",
                    "TAG": f"TASK_REMINDER_{task_id}",
                    "SUB_TAG": "TASK_REMINDER",
                }
                client._make_request("im.notify", notification_params)
            result = True

        elif reminder_type == "email":
            # Отправляем email-уведомление
            for recipient_id in recipients:
                email_params = {
                    "USER_ID": recipient_id,
                    "MESSAGE": f"Напоминание по задаче #{task_id}",
                    "SUBJECT": f"Напоминание: {task_info.get('title', 'Без названия')}",
                    "MESSAGE_PHP": f"<p>Напоминание по задаче #{task_id}:</p><p>{message}</p>",
                }
                client._make_request("im.notify.system.add", email_params)
            result = True

        if result:
            logger.info(
                f"Напоминание по задаче {task_id} успешно отправлено типом {reminder_type}"
            )
            return True
        else:
            logger.error(f"Не удалось отправить напоминание по задаче {task_id}")
            return False

    except Exception as e:
        logger.error(f"Ошибка при отправке напоминания по задаче {task_id}: {e}")
        return False


def get_task_details(task_id: int) -> Optional[dict]:
    """
    Получить детальную информацию о задаче из Bitrix24

    Args:
        task_id: ID задачи в Bitrix24

    Returns:
        dict: Детальная информация о задаче или None
    """
    client = get_bitrix_client()
    if not client:
        logger.warning("Bitrix24 не настроен, возвращаем мок-данные")
        return {
            "id": task_id,
            "title": f"Мок-задача #{task_id}",
            "description": "Это мок-задача для тестирования",
            "status": "in_progress",
            "priority": "2",
            "created_date": "2024-01-01T00:00:00+00:00",
            "deadline": "2024-12-31T23:59:59+00:00",
            "responsible": {
                "id": 1,
                "name": "Тестовый пользователь",
                "email": "test@example.com",
            },
            "creator": {"id": 1, "name": "Тестовый пользователь"},
            "accomplices": [],
            "auditors": [],
            "tags": ["тест"],
            "comments_count": 0,
        }

    try:
        result = client._make_request("tasks.task.get", {"taskId": task_id})
        if not result or "task" not in result:
            logger.error(f"Задача {task_id} не найдена")
            return None

        task = result["task"]

        # Дополнительная информация о задаче
        task_details = {
            "id": task.get("id"),
            "title": task.get("title"),
            "description": task.get("description"),
            "status": task.get("status"),
            "priority": task.get("priority"),
            "created_date": task.get("createdDate"),
            "deadline": task.get("deadline"),
            "start_date_plan": task.get("startDatePlan"),
            "end_date_plan": task.get("endDatePlan"),
            "responsible": {
                "id": task.get("responsible", {}).get("id"),
                "name": task.get("responsible", {}).get("name"),
                "email": task.get("responsible", {}).get("email"),
            },
            "creator": {
                "id": task.get("creator", {}).get("id"),
                "name": task.get("creator", {}).get("name"),
            },
            "accomplices": [acc["id"] for acc in task.get("accomplices", [])],
            "auditors": [aud["id"] for aud in task.get("auditors", [])],
            "tags": [tag["name"] for tag in task.get("tags", [])],
            "time_estimate": task.get("timeEstimate"),
            "time_spent": task.get("timeSpentInLogs"),
            "comments_count": task.get("commentsCount"),
            "attachments": task.get("attachments", []),
        }

        return task_details

    except Exception as e:
        logger.error(f"Ошибка при получении деталей задачи {task_id}: {e}")
        return None


def get_tasks_list(filters: dict = None, limit: int = 50) -> list[dict]:
    """
    Получить список задач из Bitrix24 с фильтрацией

    Args:
        filters: Словарь с фильтрами
        limit: Максимальное количество задач

    Returns:
        list: Список задач
    """
    client = get_bitrix_client()
    if not client:
        logger.warning("Bitrix24 не настроен, возвращаем мок-данные")
        return [
            {
                "id": 1,
                "title": "Тестовая задача 1",
                "status": "new",
                "priority": "2",
                "created_date": "2024-01-01T00:00:00+00:00",
                "deadline": "2024-12-31T23:59:59+00:00",
                "responsible_id": 1,
                "creator_id": 1,
                "description": "Тестовая задача для демонстрации",
                "tags": ["тест", "демо"],
            },
            {
                "id": 2,
                "title": "Тестовая задача 2",
                "status": "in_progress",
                "priority": "1",
                "created_date": "2024-01-02T00:00:00+00:00",
                "deadline": "2024-12-30T23:59:59+00:00",
                "responsible_id": 2,
                "creator_id": 1,
                "description": "Вторая тестовая задача",
                "tags": ["тест"],
            },
        ]

    try:
        # Формируем параметры фильтрации
        params = {
            "order": {"ID": "DESC"},
            "filter": {},
            "select": [
                "ID",
                "TITLE",
                "STATUS",
                "PRIORITY",
                "CREATED_DATE",
                "DEADLINE",
                "RESPONSIBLE_ID",
                "CREATED_BY",
                "DESCRIPTION",
                "TAGS",
            ],
            "start": 0,
        }

        # Применяем фильтры
        if filters:
            if filters.get("status"):
                params["filter"]["STATUS"] = filters["status"]
            if filters.get("assigned_to"):
                params["filter"]["RESPONSIBLE_ID"] = filters["assigned_to"]
            if filters.get("created_after"):
                params["filter"][">=CREATED_DATE"] = filters["created_after"]
            if filters.get("created_before"):
                params["filter"]["<=CREATED_DATE"] = filters["created_before"]

        # Получаем список задач
        result = client._make_request("tasks.task.list", params)
        if not result or "tasks" not in result:
            logger.warning("Не удалось получить список задач")
            return []

        tasks = result["tasks"]

        # Форматируем задачи для ответа
        formatted_tasks = []
        for task in tasks[:limit]:
            formatted_task = {
                "id": task.get("id"),
                "title": task.get("title"),
                "status": task.get("status"),
                "priority": task.get("priority"),
                "created_date": task.get("createdDate"),
                "deadline": task.get("deadline"),
                "responsible_id": task.get("responsible", {}).get("id"),
                "creator_id": task.get("creator", {}).get("id"),
                "description": task.get("description"),
                "tags": [tag["name"] for tag in task.get("tags", [])],
            }
            formatted_tasks.append(formatted_task)

        logger.info(f"Получено {len(formatted_tasks)} задач")
        return formatted_tasks

    except Exception as e:
        logger.error(f"Ошибка при получении списка задач: {e}")
        return []
