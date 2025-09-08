"""
Тестовый скрипт для проверки новых эндпоинтов управления задачами
"""


import requests


def test_task_endpoints():
    """Тестирование новых эндпоинтов для управления задачами"""

    base_url = "http://localhost:8000"

    # Тест 1: Получение списка задач
    print("=== Тест 1: Получение списка задач ===")
    try:
        response = requests.get(f"{base_url}/tasks")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Успешно получено {len(data['data']['tasks'])} задач")
            for task in data["data"]["tasks"][:2]:  # Показать первые 2 задачи
                print(
                    f"  - Задача #{task['id']}: {task['title']} (статус: {task['status']})"
                )
        else:
            print(f"❌ Ошибка: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Ошибка при получении списка задач: {e}")

    # Тест 2: Получение деталей задачи
    print("\n=== Тест 2: Получение деталей задачи ===")
    try:
        response = requests.get(f"{base_url}/tasks/1/details")
        if response.status_code == 200:
            data = response.json()
            task = data["data"]
            print(f"✅ Детали задачи #{task['id']} получены")
            print(f"  Название: {task['title']}")
            print(f"  Статус: {task['status']}")
            print(f"  Приоритет: {task['priority']}")
        else:
            print(f"❌ Ошибка: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Ошибка при получении деталей задачи: {e}")

    # Тест 3: Изменение статуса задачи (без авторизации - ожидаем 401)
    print("\n=== Тест 3: Изменение статуса задачи ===")
    try:
        status_data = {"status": "completed", "comment": "Тестовое изменение статуса"}
        response = requests.post(f"{base_url}/tasks/1/status", json=status_data)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Статус задачи изменен: {data['message']}")
        elif response.status_code == 401:
            print("✅ Ожидаемая ошибка авторизации (401)")
        else:
            print(f"❌ Ошибка: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Ошибка при изменении статуса: {e}")

    # Тест 4: Отправка напоминания (без авторизации - ожидаем 401)
    print("\n=== Тест 4: Отправка напоминания ===")
    try:
        reminder_data = {
            "message": "Тестовое напоминание",
            "recipients": [1, 2],
            "type": "comment",
        }
        response = requests.post(f"{base_url}/tasks/1/reminder", json=reminder_data)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Напоминание отправлено: {data['message']}")
        elif response.status_code == 401:
            print("✅ Ожидаемая ошибка авторизации (401)")
        else:
            print(f"❌ Ошибка: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Ошибка при отправке напоминания: {e}")

    print("\n=== Тестирование завершено ===")


if __name__ == "__main__":
    test_task_endpoints()
