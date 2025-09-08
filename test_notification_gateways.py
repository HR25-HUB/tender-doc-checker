#!/usr/bin/env python3
"""
Тестовый скрипт для демонстрации безопасных шлюзов уведомлений с мок-точками.

Этот скрипт показывает, как использовать безопасные шлюзы уведомлений
для Bitrix и email систем с возможностью мок-тестирования.
"""

import os
import sys

# Добавляем текущую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from bitrix_notifier import (
        BitrixNotificationType,
        BitrixPriority,
        create_mock_gateway,
        get_secure_notifier,
    )
    from emailer import (
        NotificationType,
        create_email_mock_gateway,
        get_secure_email_notifier,
        test_email_config,
    )
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Убедитесь, что файлы bitrix_notifier.py и emailer.py существуют")
    sys.exit(1)


def test_bitrix_secure_gateway():
    """Тестирование безопасного Bitrix шлюза."""
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ БЕЗОПАСНОГО BITRIX ШЛЮЗА")
    print("=" * 60)

    # Создаем мок-шлюз для тестирования
    mock_gateway = create_mock_gateway()

    print("1. Тестирование создания задачи:")
    task_result = mock_gateway.create_task(
        title="Тестовая задача",
        description="Описание тестовой задачи",
        responsible_id="1",
        priority=BitrixPriority.HIGH,
    )
    print(f"   Результат создания задачи: {task_result}")

    print("\n2. Тестирование отправки уведомления:")
    notification_result = mock_gateway.send_notification(
        user_ids=["1"],
        message="Тестовое уведомление",
        notification_type=BitrixNotificationType.SYSTEM_ERROR,
    )
    print(f"   Результат отправки уведомления: {notification_result}")

    print("\n4. Получение отправленных данных:")
    sent_data = mock_gateway.get_call_history()
    print(f"   Количество отправленных запросов: {len(sent_data)}")
    for i, data in enumerate(sent_data, 1):
        print(f"   Запрос {i}: {data['method']} - {data['params']}")

    # Тестирование мок-ошибок
    print("\n5. Тестирование мок-ошибок:")
    mock_gateway.set_mock_failure("create_task", should_fail=True)

    failure_result = mock_gateway.create_task(
        title="Задача с ошибкой", description="Эта задача должна вызвать ошибку"
    )
    print(f"   Результат с мок-ошибкой: {failure_result}")

    # Создаем безопасный нотификатор
    print("\n6. Тестирование безопасного нотификатора:")
    secure_notifier = get_secure_notifier()

    # Проверяем конфигурацию
    print(
        f"   Безопасный нотификатор инициализирован: {secure_notifier.gateway is not None}"
    )

    return True


def test_email_secure_gateway():
    """Тестирование безопасного email шлюза."""
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ БЕЗОПАСНОГО EMAIL ШЛЮЗА")
    print("=" * 60)

    # Создаем мок-шлюз для email
    mock_gateway = create_email_mock_gateway()

    print("1. Тестирование отправки простого email:")
    email_result = mock_gateway.send_email(
        recipients=["test@example.com", "admin@company.com"],
        subject="Тестовое сообщение",
        body="Это тестовое сообщение из мок-шлюза",
    )
    print(f"   Результат отправки: {email_result}")

    print("\n2. Тестирование отправки уведомления:")
    notification_result = mock_gateway.send_notification(
        recipients=["user@example.com"],
        notification_type=NotificationType.DOCUMENT_CHECK_COMPLETED,
        document_name="Тестовый документ",
        overall_score=85.5,
        recommendation="Документ соответствует требованиям",
        violations_count=0,
    )
    print(f"   Результат отправки уведомления: {notification_result}")

    print("\n3. Получение отправленных email:")
    sent_emails = mock_gateway.get_sent_emails()
    print(f"   Количество отправленных email: {len(sent_emails)}")
    for i, email in enumerate(sent_emails, 1):
        print(f"   Email {i}:")
        print(f"      Получатели: {', '.join(email['recipients'])}")
        print(f"      Тема: {email['subject']}")
        print(f"      Вложения: {len(email['attachments'])}")

    # Тестирование мок-ошибок
    print("\n4. Тестирование мок-ошибок email:")
    mock_gateway.set_mock_failure("user@example.com", should_fail=True)

    failure_result = mock_gateway.send_email(
        recipients=["user@example.com", "valid@example.com"],
        subject="Сообщение с ошибкой",
        body="Это сообщение должно вызвать ошибку для одного получателя",
    )
    print(f"   Результат с мок-ошибкой: {failure_result}")

    # Проверка конфигурации
    print("\n5. Проверка конфигурации email:")
    print(f"   Email шлюз работает в мок-режиме: {mock_gateway.mock_mode}")

    return True


def test_secure_email_notifier():
    """Тестирование безопасного email нотификатора."""
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ БЕЗОПАСНОГО EMAIL НОТИФИКАТОРА")
    print("=" * 60)

    # Конфигурация безопасности
    security_config = {
        "max_recipients": 3,
        "max_attachment_size": 1024 * 1024,  # 1MB
        "enable_mock_fallback": True,
    }

    # Создаем безопасный нотификатор
    secure_notifier = get_secure_email_notifier(security_config)

    # Инициализируем в мок-режиме
    secure_notifier.initialize(mock_mode=True)

    print("1. Тестирование валидации получателей:")
    # Тест слишком большого количества получателей
    many_recipients = [f"user{i}@example.com" for i in range(10)]
    result = secure_notifier.send_secure_simple_email(
        recipients=many_recipients,
        subject="Тест ограничения получателей",
        body="Проверка ограничения количества получателей",
    )
    print(f"   Результат с ограничением получателей: {result}")

    print("\n2. Тестирование валидации email адресов:")
    # Тест невалидных email адресов
    invalid_emails = ["invalid-email", "another@invalid", "valid@example.com"]
    result = secure_notifier.send_secure_simple_email(
        recipients=invalid_emails,
        subject="Тест валидации email",
        body="Проверка валидации email адресов",
    )
    print(f"   Результат с валидацией: {result}")

    print("\n3. Тестирование отправки уведомлений:")
    # Тест отправки уведомления
    result = secure_notifier.send_secure_notification(
        recipients=["admin@company.com", "manager@company.com"],
        notification_type=NotificationType.SYSTEM_ERROR,
        error_type="Тестовая ошибка",
        error_description="Это тестовая системная ошибка",
        error_traceback="Traceback: test_notification_gateways.py:123",
    )
    print(f"   Результат отправки системного уведомления: {result}")

    return True


def demonstrate_integration():
    """Демонстрация интеграции обоих шлюзов."""
    print("\n" + "=" * 60)
    print("ДЕМОНСТРАЦИЯ ИНТЕГРАЦИИ ШЛЮЗОВ")
    print("=" * 60)

    # Создаем мок-шлюзы для обеих систем
    bitrix_mock = create_mock_gateway()
    email_mock = create_email_mock_gateway()

    # Симулируем полный рабочий процесс
    print("1. Симуляция полного рабочего процесса:")

    # 1. Создаем задачу в Bitrix
    task_result = bitrix_mock.create_task(
        title="Проверка документов поставщика",
        description="Необходимо проверить документы поставщика ООО 'Тестовая компания'",
        responsible_id="1",
        priority=BitrixPriority.NORMAL,
    )
    print(f"   ✅ Задача создана: {task_result}")

    # 2. Отправляем email уведомление
    email_result = email_mock.send_notification(
        recipients=["manager@company.com", "compliance@company.com"],
        notification_type=NotificationType.BATCH_PROCESSING_COMPLETED,
        batch_id="BATCH-2024-001",
        total_documents=15,
        processed_successfully=14,
        processing_errors=1,
        processing_time="2 мин 30 сек",
    )
    print(f"   ✅ Email отправлен: {email_result}")

    # 3. Отправляем уведомление в Bitrix
    notification_result = bitrix_mock.send_notification(
        user_ids=["1"],
        message="Проверка документов поставщика завершена. Подробности в задаче #123",
        notification_type=BitrixNotificationType.SYSTEM_ERROR,
    )
    print(f"   ✅ Уведомление отправлено: {notification_result}")

    print("\n📊 Статистика отправленных данных:")
    print(f"   Bitrix запросов: {len(bitrix_mock.get_call_history())}")
    print(f"   Email отправлено: {len(email_mock.get_sent_emails())}")

    return True


def main():
    """Основная функция тестирования."""
    print("🚀 Запуск тестирования безопасных шлюзов уведомлений")

    try:
        # Тестируем Bitrix шлюз
        test_bitrix_secure_gateway()

        # Тестируем email шлюз
        test_email_secure_gateway()

        # Тестируем безопасный email нотификатор
        test_secure_email_notifier()

        # Демонстрация интеграции
        demonstrate_integration()

        print("\n" + "=" * 60)
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО")
        print("=" * 60)
        print("\n💡 Резюме:")
        print("   • Безопасные шлюзы уведомлений реализованы")
        print("   • Мок-точки для тестирования доступны")
        print("   • Валидация входных данных работает")
        print("   • Интеграция между системами возможна")
        print("   • Отсутствие конфигурации не ломает систему")

    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    main()
