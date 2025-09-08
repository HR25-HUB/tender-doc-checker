# Docker Health Check Script
# Проверяет состояние Docker и контейнеров

Write-Host "=== Docker Health Check ===" -ForegroundColor Green

# Проверка установки Docker
try {
    $dockerVersion = docker --version
    Write-Host "✓ Docker установлен: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker не установлен или недоступен" -ForegroundColor Red
    exit 1
}

# Проверка состояния Docker daemon
try {
    docker info | Out-Null
    Write-Host "✓ Docker daemon запущен" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker daemon не запущен" -ForegroundColor Red
    exit 1
}

# Проверка запущенных контейнеров
Write-Host "\n=== Запущенные контейнеры ===" -ForegroundColor Yellow
$runningContainers = docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
if ($runningContainers) {
    Write-Host $runningContainers
} else {
    Write-Host "Нет запущенных контейнеров" -ForegroundColor Yellow
}

# Проверка всех контейнеров
Write-Host "\n=== Все контейнеры ===" -ForegroundColor Yellow
$allContainers = docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
if ($allContainers) {
    Write-Host $allContainers
} else {
    Write-Host "Нет контейнеров" -ForegroundColor Yellow
}

# Проверка образов
Write-Host "\n=== Docker образы ===" -ForegroundColor Yellow
$images = docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
if ($images) {
    Write-Host $images
} else {
    Write-Host "Нет Docker образов" -ForegroundColor Yellow
}

# Проверка использования дискового пространства
Write-Host "\n=== Использование дискового пространства ===" -ForegroundColor Yellow
try {
    docker system df
} catch {
    Write-Host "Не удалось получить информацию о дисковом пространстве" -ForegroundColor Red
}

Write-Host "\n=== Проверка завершена ===" -ForegroundColor Green
