# PowerShell скрипт для настройки проекта на Windows

Write-Host "🚀 Настройка проекта Tender Document Checker" -ForegroundColor Green

# Проверка установки UV
function Test-UvInstalled {
    try {
        $null = Get-Command uv -ErrorAction Stop
        return $true
    }
    catch {
        return $false
    }
}

# Установка UV
function Install-Uv {
    Write-Host "📦 UV не найден. Устанавливаю UV..." -ForegroundColor Yellow
    try {
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
        Write-Host "✅ UV установлен" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Ошибка установки UV: $_" -ForegroundColor Red
        exit 1
    }
}

# Выполнение команды с проверкой
function Invoke-CommandWithCheck {
    param(
        [string]$Command,
        [string]$Description
    )

    Write-Host "🔄 $Description" -ForegroundColor Cyan
    Write-Host "   Выполняю: $Command" -ForegroundColor Gray

    try {
        Invoke-Expression $Command
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ $Description - выполнено" -ForegroundColor Green
        } else {
            Write-Host "❌ $Description - ошибка (код: $LASTEXITCODE)" -ForegroundColor Red
            exit $LASTEXITCODE
        }
    }
    catch {
        Write-Host "❌ $Description - исключение: $_" -ForegroundColor Red
        exit 1
    }
}

# Основная логика
try {
    # Переход в корень проекта
    $ProjectRoot = Split-Path -Parent $PSScriptRoot
    Set-Location $ProjectRoot
    Write-Host "📁 Рабочая директория: $ProjectRoot" -ForegroundColor Blue

    # Проверка UV
    if (-not (Test-UvInstalled)) {
        Install-Uv
        # Обновляем PATH для текущей сессии
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "Machine")
    } else {
        Write-Host "✅ UV уже установлен" -ForegroundColor Green
    }

    # Синхронизация зависимостей
    Invoke-CommandWithCheck "uv sync --extra dev" "Установка зависимостей"

    # Установка pre-commit hooks
    Invoke-CommandWithCheck "uv run pre-commit install" "Настройка pre-commit hooks"

    # Создание необходимых директорий
    Write-Host "📁 Создание необходимых директорий..." -ForegroundColor Cyan
    $DirsToCreate = @(
        "data\reports",
        "logs",
        "tests\fixtures"
    )

    foreach ($Dir in $DirsToCreate) {
        if (-not (Test-Path $Dir)) {
            New-Item -ItemType Directory -Path $Dir -Force | Out-Null
            Write-Host "✅ Создана директория: $Dir" -ForegroundColor Green
        } else {
            Write-Host "ℹ️  Директория уже существует: $Dir" -ForegroundColor Blue
        }
    }

    # Копирование .env файла
    if ((Test-Path ".env.example") -and (-not (Test-Path ".env"))) {
        Write-Host "📝 Создание .env файла из примера..." -ForegroundColor Cyan
        Copy-Item ".env.example" ".env"
        Write-Host "⚠️  Не забудьте настроить переменные окружения в .env файле!" -ForegroundColor Yellow
    }

    # Инициализация базы данных
    Write-Host "🗄️ Инициализация базы данных..." -ForegroundColor Cyan
    try {
        Invoke-Expression "uv run python -c `"from db import init_db; init_db()`""
        Write-Host "✅ База данных инициализирована" -ForegroundColor Green
    }
    catch {
        Write-Host "⚠️  Не удалось инициализировать БД: $_" -ForegroundColor Yellow
    }

    # Успешное завершение
    Write-Host ""
    Write-Host "🎉 Проект успешно настроен!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 Следующие шаги:" -ForegroundColor Blue
    Write-Host "1. Настройте переменные окружения в .env файле"
    Write-Host "2. Запустите тесты: make test (или uv run pytest)"
    Write-Host "3. Запустите API: make run-api (или uv run uvicorn main:app --reload)"
    Write-Host "4. Запустите UI: make run-ui (или uv run streamlit run streamlit_ui.py)"
    Write-Host ""
    Write-Host "💡 Используйте 'make help' для просмотра всех доступных команд" -ForegroundColor Cyan
}
catch {
    Write-Host "❌ Критическая ошибка: $_" -ForegroundColor Red
    exit 1
}
