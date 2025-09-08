#!/usr/bin/env python3
"""
Скрипт для проверки качества проекта после миграции на UV и Ruff.
Проверяет все аспекты проекта и выдает отчет о готовности.
"""

import subprocess
import sys
from pathlib import Path


# Цвета для вывода
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def run_command(cmd: list[str], cwd: Path = None) -> tuple[bool, str]:
    """Выполняет команду и возвращает результат."""
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=60
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)


def check_uv_installation() -> bool:
    """Проверяет установку UV."""
    success, output = run_command(["uv", "--version"])
    if success:
        print(f"{Colors.GREEN}✓{Colors.END} UV установлен: {output.strip()}")
        return True
    else:
        print(f"{Colors.RED}✗{Colors.END} UV не установлен")
        return False


def check_dependencies() -> bool:
    """Проверяет синхронизацию зависимостей."""
    print(f"{Colors.BLUE}Проверка зависимостей...{Colors.END}")
    success, output = run_command(["uv", "sync", "--extra", "dev"])
    if success:
        print(f"{Colors.GREEN}✓{Colors.END} Зависимости синхронизированы")
        return True
    else:
        print(f"{Colors.RED}✗{Colors.END} Ошибка синхронизации зависимостей:")
        print(output)
        return False


def check_ruff_format() -> bool:
    """Проверяет форматирование кода."""
    print(f"{Colors.BLUE}Проверка форматирования...{Colors.END}")
    success, output = run_command(["uv", "run", "ruff", "format", "--check", "."])
    if success:
        print(f"{Colors.GREEN}✓{Colors.END} Код отформатирован правильно")
        return True
    else:
        print(f"{Colors.YELLOW}⚠{Colors.END} Код требует форматирования")
        print("Запустите: uv run ruff format .")
        return False


def check_ruff_lint() -> bool:
    """Проверяет линтинг кода."""
    print(f"{Colors.BLUE}Проверка линтинга...{Colors.END}")
    success, output = run_command(["uv", "run", "ruff", "check", "."])
    if success:
        print(f"{Colors.GREEN}✓{Colors.END} Линтинг прошел успешно")
        return True
    else:
        print(f"{Colors.YELLOW}⚠{Colors.END} Найдены проблемы линтинга:")
        print(output)
        print("Запустите: uv run ruff check --fix .")
        return False


def check_mypy() -> bool:
    """Проверяет типизацию."""
    print(f"{Colors.BLUE}Проверка типизации...{Colors.END}")
    success, output = run_command(["uv", "run", "mypy", "."])
    if success:
        print(f"{Colors.GREEN}✓{Colors.END} Типизация корректна")
        return True
    else:
        print(f"{Colors.YELLOW}⚠{Colors.END} Найдены проблемы типизации:")
        print(output)
        return False


def check_tests() -> bool:
    """Запускает тесты."""
    print(f"{Colors.BLUE}Запуск тестов...{Colors.END}")
    success, output = run_command(["uv", "run", "pytest", "-v"])
    if success:
        print(f"{Colors.GREEN}✓{Colors.END} Все тесты прошли")
        return True
    else:
        print(f"{Colors.RED}✗{Colors.END} Тесты не прошли:")
        print(output)
        return False


def check_file_structure() -> bool:
    """Проверяет структуру файлов."""
    print(f"{Colors.BLUE}Проверка структуры проекта...{Colors.END}")

    required_files = [
        "pyproject.toml",
        ".pre-commit-config.yaml",
        "Makefile",
        ".env.example",
        ".gitignore",
        "README.md",
        "MIGRATION_GUIDE.md",
        "src/__init__.py",
        "src/models.py",
        "src/config.py",
        "src/logger.py",
        "scripts/setup.py",
        "scripts/setup.ps1",
        "tests/test_models.py",
        "tests/test_api.py",
    ]

    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)

    if not missing_files:
        print(f"{Colors.GREEN}✓{Colors.END} Структура проекта корректна")
        return True
    else:
        print(f"{Colors.RED}✗{Colors.END} Отсутствуют файлы:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        return False


def check_env_file() -> bool:
    """Проверяет наличие .env файла."""
    if Path(".env").exists():
        print(f"{Colors.GREEN}✓{Colors.END} Файл .env существует")
        return True
    else:
        print(f"{Colors.YELLOW}⚠{Colors.END} Файл .env не найден")
        print("Скопируйте .env.example в .env и настройте переменные")
        return False


def check_pre_commit() -> bool:
    """Проверяет pre-commit hooks."""
    print(f"{Colors.BLUE}Проверка pre-commit hooks...{Colors.END}")
    success, output = run_command(["uv", "run", "pre-commit", "run", "--all-files"])
    if success:
        print(f"{Colors.GREEN}✓{Colors.END} Pre-commit hooks прошли успешно")
        return True
    else:
        print(f"{Colors.YELLOW}⚠{Colors.END} Pre-commit hooks нашли проблемы:")
        print(output)
        return False


def main():
    """Основная функция проверки."""
    print(
        f"{Colors.BOLD}🔍 Проверка качества проекта Tender Document Checker{Colors.END}"
    )
    print("=" * 60)

    checks = [
        ("UV Installation", check_uv_installation),
        ("Dependencies", check_dependencies),
        ("File Structure", check_file_structure),
        ("Environment File", check_env_file),
        ("Code Formatting", check_ruff_format),
        ("Code Linting", check_ruff_lint),
        ("Type Checking", check_mypy),
        ("Tests", check_tests),
        ("Pre-commit Hooks", check_pre_commit),
    ]

    results = {}
    for name, check_func in checks:
        print(f"\n{Colors.BOLD}{name}:{Colors.END}")
        results[name] = check_func()

    # Итоговый отчет
    print(f"\n{Colors.BOLD}📊 Итоговый отчет:{Colors.END}")
    print("=" * 60)

    passed = sum(results.values())
    total = len(results)

    for name, result in results.items():
        status = (
            f"{Colors.GREEN}✓{Colors.END}" if result else f"{Colors.RED}✗{Colors.END}"
        )
        print(f"{status} {name}")

    print(f"\n{Colors.BOLD}Результат: {passed}/{total} проверок прошли{Colors.END}")

    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 Проект готов к работе!{Colors.END}")
        return 0
    else:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠ Требуются доработки{Colors.END}")
        print("\nРекомендации:")

        if not results.get("UV Installation"):
            print(
                "1. Установите UV: https://docs.astral.sh/uv/getting-started/installation/"
            )

        if not results.get("Dependencies"):
            print("2. Синхронизируйте зависимости: uv sync --extra dev")

        if not results.get("Environment File"):
            print("3. Создайте .env файл: cp .env.example .env")

        if not results.get("Code Formatting"):
            print("4. Отформатируйте код: uv run ruff format .")

        if not results.get("Code Linting"):
            print("5. Исправьте проблемы линтинга: uv run ruff check --fix .")

        if not results.get("Pre-commit Hooks"):
            print("6. Установите pre-commit hooks: uv run pre-commit install")

        return 1


if __name__ == "__main__":
    sys.exit(main())
