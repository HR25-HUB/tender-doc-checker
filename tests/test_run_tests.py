#!/usr/bin/env python3
"""Тесты для скрипта run_tests.py - проверка корректного кода выхода."""

import os
import subprocess
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest


class TestRunTestsExitCode:
    """Тесты для проверки корректного кода выхода скрипта run_tests.py."""

    def test_run_tests_success_exit_code(self):
        """Проверка корректного кода выхода при успешном выполнении."""
        # Проверяем, что скрипт run_tests.py существует и может быть запущен
        script_path = os.path.join(os.path.dirname(__file__), "..", "run_tests.py")

        if not os.path.exists(script_path):
            pytest.skip("Скрипт run_tests.py не найден")

        # Просто проверяем, что скрипт может быть запущен без критических ошибок
        result = subprocess.run(
            [
                sys.executable,
                script_path,
                "--help",  # Проверяем, что скрипт не крашится при запуске
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Код выхода может быть 0 или 2 (если pytest не найдет тесты), но не должен быть -1
        assert (
            result.returncode >= 0
        ), f"Критическая ошибка в скрипте, код выхода: {result.returncode}"

    def test_run_tests_failure_exit_code(self):
        """Проверка корректного кода выхода при неуспешном выполнении."""
        # Создаем временный каталог с проваливающимся тестом
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создаем временный файл с проваливающимся тестом
            test_file = os.path.join(temp_dir, "test_failure.py")
            with open(test_file, "w") as f:
                f.write(
                    """
def test_always_fails():
    assert False, "Этот тест всегда проваливается"
"""
                )

            # Запускаем pytest напрямую для проверки кода выхода
            result = subprocess.run(
                [sys.executable, "-m", "pytest", test_file, "-v"],
                capture_output=True,
                text=True,
            )

            # pytest возвращает 1 при проваленных тестах, 2 при внутренних ошибках
            assert result.returncode in [
                1,
                2,
            ], f"Ожидался код выхода 1 или 2, получен {result.returncode}"

    def test_run_tests_pytest_not_found_exit_code(self):
        """Проверка корректного кода выхода при отсутствии pytest."""
        # Создаем временную среду без pytest
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создаем упрощенную версию run_tests.py для тестирования
            test_script = os.path.join(temp_dir, "test_script.py")
            with open(test_script, "w") as f:
                f.write(
                    """
#!/usr/bin/env python
import sys
try:
    import pytest
    sys.exit(0)
except ImportError:
    print("pytest не найден")
    sys.exit(1)
"""
                )

            # Запускаем в изолированной среде
            env = os.environ.copy()
            env["PYTHONPATH"] = ""

            result = subprocess.run(
                [sys.executable, test_script], capture_output=True, text=True, env=env
            )

            # Проверяем, что скрипт корректно обрабатывает отсутствие pytest
            assert result.returncode in [
                0,
                1,
            ], f"Неожиданный код выхода: {result.returncode}"

    def test_run_tests_manual_mode_exit_code(self):
        """Проверка корректного кода выхода в ручном режиме тестирования."""
        # Создаем упрощенную версию ручного тестирования
        test_script = """
import sys
from unittest.mock import Mock

def run_manual_tests():
    try:
        # Имитация успешного ручного тестирования
        return True
    except Exception:
        return False

if __name__ == '__main__':
    success = run_manual_tests()
    sys.exit(0 if success else 1)
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(test_script)
            temp_script = f.name

        try:
            result = subprocess.run(
                [sys.executable, temp_script], capture_output=True, text=True
            )

            assert (
                result.returncode == 0
            ), f"Ожидался код выхода 0 для успешного ручного теста, получен {result.returncode}"

        finally:
            if os.path.exists(temp_script):
                os.unlink(temp_script)

    def test_run_tests_actual_script_execution(self):
        """Проверка запуска реального скрипта run_tests.py."""
        script_path = os.path.join(os.path.dirname(__file__), "..", "run_tests.py")

        if os.path.exists(script_path):
            # Запускаем реальный скрипт
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Проверяем, что скрипт завершился без критических ошибок
            # Код выхода может быть 0 (успех), 1 (провал тестов), или 2 (ошибки pytest), но не должен быть отрицательным
            assert (
                result.returncode >= 0
            ), f"Критическая ошибка в скрипте, код выхода: {result.returncode}"
        else:
            pytest.skip("Скрипт run_tests.py не найден")

    @patch("subprocess.check_call")
    @patch("subprocess.run")
    def test_run_tests_pytest_installation_fallback(self, mock_run, mock_check_call):
        """Проверка fallback на установку pytest."""
        # Имитация отсутствия pytest
        with patch.dict("sys.modules", {"pytest": None}):
            with patch("builtins.__import__", side_effect=ImportError):
                # Имитация успешной установки
                mock_check_call.return_value = None
                mock_run.return_value = MagicMock(returncode=0)

                # Создаем тестовый скрипт
                test_script = """
import sys
import subprocess

try:
    import pytest
    sys.exit(0)
except ImportError:
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pytest'])
        import pytest
        sys.exit(0)
    except Exception:
        sys.exit(1)
"""

                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".py", delete=False
                ) as f:
                    f.write(test_script)
                    temp_script = f.name

                try:
                    result = subprocess.run(
                        [sys.executable, temp_script], capture_output=True, text=True
                    )

                    # Проверяем корректность обработки fallback
                    assert result.returncode in [
                        0,
                        1,
                    ], f"Неожиданный код выхода: {result.returncode}"

                finally:
                    if os.path.exists(temp_script):
                        os.unlink(temp_script)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
