#!/usr/bin/env python3
"""Скрипт для настройки проекта."""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    """Выполнить команду в shell."""
    print(f"🔄 Выполняю: {cmd}")
    result = subprocess.run(
        cmd, shell=True, check=check, capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"❌ Ошибка выполнения команды: {cmd}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
        if check:
            sys.exit(1)
    else:
        print("✅ Команда выполнена успешно")
    return result


def check_uv_installed() -> bool:
    """Проверить, установлен ли UV."""
    try:
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def install_uv() -> None:
    """Установить UV."""
    print("📦 UV не найден. Устанавливаю UV...")

    if os.name == "nt":  # Windows
        cmd = 'powershell -c "irm https://astral.sh/uv/install.ps1 | iex"'
    else:  # macOS/Linux
        cmd = "curl -LsSf https://astral.sh/uv/install.sh | sh"

    run_command(cmd)
    print("✅ UV установлен")


def setup_project() -> None:
    """Настроить проект."""
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    print("🚀 Настройка проекта Tender Document Checker")

    # Проверка UV
    if not check_uv_installed():
        install_uv()

    # Синхронизация зависимостей
    print("📦 Устанавливаю зависимости...")
    run_command("uv sync --extra dev")

    # Установка pre-commit hooks
    print("🔧 Настраиваю pre-commit hooks...")
    run_command("uv run pre-commit install")

    # Создание необходимых директорий
    print("📁 Создаю необходимые директории...")
    dirs_to_create = [
        "data/reports",
        "logs",
        "tests/fixtures",
    ]

    for dir_path in dirs_to_create:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✅ Создана директория: {dir_path}")

    # Копирование .env файла
    env_example = Path(".env.example")
    env_file = Path(".env")

    if env_example.exists() and not env_file.exists():
        print("📝 Создаю .env файл из примера...")
        env_file.write_text(env_example.read_text(encoding="utf-8"), encoding="utf-8")
        print("⚠️  Не забудьте настроить переменные окружения в .env файле!")

    # Инициализация базы данных
    print("🗄️ Инициализирую базу данных...")
    try:
        run_command('uv run python -c "from db import init_db; init_db()"')
    except Exception as e:
        print(f"⚠️  Не удалось инициализировать БД: {e}")

    print("\n🎉 Проект успешно настроен!")
    print("\n📋 Следующие шаги:")
    print("1. Настройте переменные окружения в .env файле")
    print("2. Запустите тесты: make test")
    print("3. Запустите API: make run-api")
    print("4. Запустите UI: make run-ui")
    print("\n💡 Используйте 'make help' для просмотра всех доступных команд")


if __name__ == "__main__":
    setup_project()
