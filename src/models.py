"""Pydantic модели для валидации данных."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class User(BaseModel):
    """Модель пользователя для аутентификации."""

    username: str = Field(..., description="Имя пользователя")
    email: str | None = Field(None, description="Email пользователя")
    full_name: str | None = Field(None, description="Полное имя")
    disabled: bool = Field(default=False, description="Заблокирован ли пользователь")
    role: str = Field(default="user", description="Роль пользователя")
    hashed_password: str | None = Field(None, description="Хешированный пароль")


class DocumentChunk(BaseModel):
    """Модель для части документа."""

    title: str = Field(..., description="Заголовок раздела")
    content: str = Field(..., description="Содержимое раздела")


class CheckResult(BaseModel):
    """Результат проверки раздела документа."""

    section: str = Field(..., description="Название раздела")
    match: Literal["да", "нет", "частично"] = Field(
        ..., description="Соответствие требованиям"
    )
    comments: str = Field(default="", description="Комментарии к проверке")
    confidence: float | None = Field(
        None, ge=0.0, le=1.0, description="Уверенность в результате"
    )

    # === ПОЛЯ ДЛЯ ТОВАРНЫХ ПРОВЕРОК ===
    price_check: Literal[
        "соответствует", "завышена", "занижена", "не проверялась"
    ] | None = Field(None, description="Результат проверки цены")
    availability_check: Literal[
        "в наличии", "под заказ", "нет в наличии", "не проверялась"
    ] | None = Field(None, description="Результат проверки наличия товара")
    quantity_check: Literal[
        "достаточно", "недостаточно", "избыток", "не проверялось"
    ] | None = Field(None, description="Результат проверки количества")
    product_code: str | None = Field(None, description="Артикул проверяемого товара")
    expected_price: float | None = Field(None, ge=0, description="Ожидаемая цена")
    actual_price: float | None = Field(
        None, ge=0, description="Фактическая цена в документе"
    )
    price_deviation_percent: float | None = Field(
        None, description="Отклонение цены в процентах"
    )
    expected_quantity: int | None = Field(
        None, ge=0, description="Ожидаемое количество"
    )
    actual_quantity: int | None = Field(
        None, ge=0, description="Фактическое количество в документе"
    )
    supplier_name: str | None = Field(None, description="Наименование поставщика")
    check_type: Literal["общий", "товарный", "ценовой", "складской"] = Field(
        default="общий", description="Тип проверки"
    )


class DocumentReport(BaseModel):
    """Полный отчет по документу."""

    filename: str = Field(..., description="Имя файла")
    checked_at: datetime = Field(
        default_factory=datetime.now, description="Время проверки"
    )
    results: list[CheckResult] = Field(
        ..., description="Результаты проверки по разделам"
    )
    overall_status: Literal[
        "соответствует", "не соответствует", "частично соответствует"
    ] = Field(..., description="Общий статус документа")


class BitrixTaskRequest(BaseModel):
    """Запрос на создание задачи в Bitrix24."""

    title: str = Field(..., description="Заголовок задачи")
    description: str = Field(..., description="Описание задачи")
    responsible_id: int | None = Field(None, description="ID ответственного")
    deadline: datetime | None = Field(None, description="Срок выполнения")


class EmailRequest(BaseModel):
    """Запрос на отправку email."""

    recipient: str = Field(..., description="Email получателя")
    subject: str = Field(..., description="Тема письма")
    body: str = Field(..., description="Текст письма")
    pdf_path: str | None = Field(None, description="Путь к PDF-отчету")


class UploadResponse(BaseModel):
    """Ответ на загрузку документа."""

    filename: str = Field(..., description="Имя файла")
    report: list[CheckResult] = Field(..., description="Результаты проверки")
    task_id: int | None = Field(None, description="ID созданной задачи в Bitrix24")
    pdf_path: str | None = Field(None, description="Путь к сгенерированному PDF")


# === МОДЕЛИ ДЛЯ ОПТОВОЙ ТОРГОВЛИ ===


class ProductSpecification(BaseModel):
    """Модель для товарной спецификации."""

    product_code: str = Field(..., description="Артикул товара")
    product_name: str = Field(..., description="Наименование товара")
    quantity: int = Field(..., ge=1, description="Количество")
    unit: str = Field(..., description="Единица измерения (шт, кг, м и т.д.)")
    unit_price: float = Field(..., ge=0, description="Цена за единицу")
    total_amount: float = Field(..., ge=0, description="Общая сумма")
    availability_status: Literal["в наличии", "под заказ", "нет в наличии"] = Field(
        ..., description="Статус наличия товара"
    )
    supplier_code: str | None = Field(None, description="Артикул поставщика")
    category: str | None = Field(None, description="Категория товара")
    brand: str | None = Field(None, description="Бренд товара")
    description: str | None = Field(None, description="Описание товара")


class SupplierInfo(BaseModel):
    """Информация о поставщике."""

    supplier_id: int | None = Field(None, description="ID поставщика в системе")
    name: str = Field(..., description="Наименование поставщика")
    inn: str | None = Field(None, description="ИНН поставщика")
    kpp: str | None = Field(None, description="КПП поставщика")
    contact_person: str | None = Field(None, description="Контактное лицо")
    phone: str | None = Field(None, description="Телефон")
    email: str | None = Field(None, description="Email")
    address: str | None = Field(None, description="Адрес")
    rating: float | None = Field(None, ge=0, le=5, description="Рейтинг поставщика")


class PaymentTerms(BaseModel):
    """Условия оплаты."""

    payment_type: Literal["предоплата", "постоплата", "частичная предоплата"] = Field(
        ..., description="Тип оплаты"
    )
    payment_period_days: int | None = Field(
        None, ge=0, description="Срок оплаты в днях"
    )
    prepayment_percent: float | None = Field(
        None, ge=0, le=100, description="Процент предоплаты"
    )
    payment_method: str | None = Field(None, description="Способ оплаты")
    currency: str = Field(default="RUB", description="Валюта")


class DeliveryTerms(BaseModel):
    """Условия поставки."""

    delivery_type: Literal["самовывоз", "доставка", "транспортная компания"] = Field(
        ..., description="Тип доставки"
    )
    delivery_period_days: int | None = Field(
        None, ge=0, description="Срок поставки в днях"
    )
    delivery_cost: float | None = Field(None, ge=0, description="Стоимость доставки")
    delivery_address: str | None = Field(None, description="Адрес доставки")
    min_order_amount: float | None = Field(
        None, ge=0, description="Минимальная сумма заказа"
    )


class CommercialProposal(BaseModel):
    """Модель коммерческого предложения."""

    proposal_id: str | None = Field(None, description="ID предложения")
    supplier: SupplierInfo = Field(..., description="Информация о поставщике")
    products: list[ProductSpecification] = Field(
        ..., description="Список товаров в предложении"
    )
    payment_terms: PaymentTerms = Field(..., description="Условия оплаты")
    delivery_terms: DeliveryTerms = Field(..., description="Условия поставки")
    total_amount: float = Field(..., ge=0, description="Общая сумма предложения")
    valid_until: datetime | None = Field(None, description="Действительно до")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Дата создания"
    )
    notes: str | None = Field(None, description="Дополнительные примечания")


class SupplierDocument(BaseModel):
    """Модель документа поставщика."""

    document_id: str | None = Field(None, description="ID документа")
    document_type: Literal[
        "коммерческое предложение",
        "спецификация",
        "договор",
        "счет",
        "накладная",
        "сертификат",
    ] = Field(..., description="Тип документа")
    supplier: SupplierInfo = Field(..., description="Информация о поставщике")
    filename: str | None = Field(None, description="Имя файла документа")
    upload_date: datetime = Field(
        default_factory=datetime.now, description="Дата загрузки документа"
    )
    status: str = Field(default="новый", description="Статус документа")
    content_summary: str | None = Field(
        None, description="Краткое содержание документа"
    )


# === СХЕМЫ ЗАПРОСОВ/ОТВЕТОВ ДЛЯ API ===


class LoginRequest(BaseModel):
    """Схема запроса для аутентификации."""

    username: str = Field(..., description="Имя пользователя")
    password: str = Field(..., description="Пароль")


class LoginResponse(BaseModel):
    """Схема ответа для аутентификации."""

    access_token: str = Field(..., description="Токен доступа JWT")
    token_type: str = Field(default="bearer", description="Тип токена")
    user: dict = Field(..., description="Информация о пользователе")


class RegisterRequest(BaseModel):
    """Схема запроса для регистрации пользователя."""

    username: str = Field(..., description="Имя пользователя")
    password: str = Field(..., description="Пароль")
    role: str = Field(default="manager", description="Роль пользователя")


class RegisterResponse(BaseModel):
    """Схема ответа для регистрации пользователя."""

    message: str = Field(..., description="Сообщение об успешной регистрации")
    user: dict = Field(..., description="Информация о созданном пользователе")


class UserInfoResponse(BaseModel):
    """Схема ответа с информацией о текущем пользователе."""

    username: str = Field(..., description="Имя пользователя")
    role: str = Field(..., description="Роль пользователя")
    is_active: bool = Field(..., description="Активен ли пользователь")
    permissions: list[str] = Field(..., description="Список разрешений")
    role_info: dict = Field(..., description="Информация о роли")


class UpdateRoleRequest(BaseModel):
    """Схема запроса для обновления роли пользователя."""

    new_role: str = Field(..., description="Новая роль пользователя")


class UpdateRoleResponse(BaseModel):
    """Схема ответа для обновления роли пользователя."""

    message: str = Field(..., description="Сообщение об успешном обновлении")
    user: dict = Field(..., description="Информация об обновленном пользователе")


class DeactivateUserResponse(BaseModel):
    """Схема ответа для деактивации пользователя."""

    message: str = Field(..., description="Сообщение об успешной деактивации")
    user: dict = Field(..., description="Информация о деактивированном пользователе")


class AuditLogsRequest(BaseModel):
    """Схема запроса для получения логов аудита."""

    start_date: str | None = Field(None, description="Дата начала (ISO формат)")
    end_date: str | None = Field(None, description="Дата окончания (ISO формат)")
    user_id: str | None = Field(None, description="ID пользователя")
    event_type: str | None = Field(None, description="Тип события")
    limit: int = Field(default=100, ge=1, le=1000, description="Лимит записей")


class AuditLogsResponse(BaseModel):
    """Схема ответа для получения логов аудита."""

    status: str = Field(..., description="Статус операции")
    data: dict = Field(..., description="Данные логов и фильтры")


class UserAuditTrailRequest(BaseModel):
    """Схема запроса для получения аудиторского следа пользователя."""

    start_date: str | None = Field(None, description="Дата начала (ISO формат)")
    end_date: str | None = Field(None, description="Дата окончания (ISO формат)")
    resource_type: str | None = Field(None, description="Тип ресурса")
    limit: int = Field(default=100, ge=1, le=1000, description="Лимит записей")


class UserAuditTrailResponse(BaseModel):
    """Схема ответа для получения аудиторского следа пользователя."""

    status: str = Field(..., description="Статус операции")
    data: dict = Field(..., description="Данные аудиторского следа")


class AuditExportRequest(BaseModel):
    """Схема запроса для экспорта аудита."""

    export_format: str = Field(..., description="Формат экспорта (txt или json)")
    start_date: str | None = Field(None, description="Дата начала (ISO формат)")
    end_date: str | None = Field(None, description="Дата окончания (ISO формат)")
    doc_type: str | None = Field(None, description="Тип документа")
    user_id: str | None = Field(None, description="ID пользователя")
    limit: int = Field(default=10000, ge=1, le=100000, description="Лимит записей")
    offset: int = Field(default=0, ge=0, description="Смещение")


class AuditExportResponse(BaseModel):
    """Схема ответа для экспорта аудита."""

    status: str = Field(..., description="Статус операции")
    data: dict = Field(..., description="Информация о файле экспорта")


class DocumentCheckRequest(BaseModel):
    """Схема запроса для проверки документа."""

    filename: str = Field(..., description="Имя файла")
    content: str = Field(..., description="Содержимое документа")


class DocumentCheckResponse(BaseModel):
    """Схема ответа для проверки документа."""

    filename: str = Field(..., description="Имя файла")
    report: list[CheckResult] = Field(..., description="Результаты проверки")
    overall_status: str = Field(..., description="Общий статус документа")


class UploadDocumentResponse(BaseModel):
    """Схема ответа для загрузки документа."""

    filename: str = Field(..., description="Имя файла")
    report: list[CheckResult] = Field(..., description="Результаты проверки")
    task_id: int | None = Field(None, description="ID задачи в Bitrix24")
    pdf_path: str | None = Field(None, description="Путь к PDF отчету")


class HealthCheckResponse(BaseModel):
    """Схема ответа для проверки здоровья сервиса."""

    status: str = Field(..., description="Статус сервиса")
    timestamp: datetime = Field(..., description="Временная метка")
    version: str = Field(..., description="Версия API")
    database: str = Field(..., description="Статус базы данных")


class ErrorResponse(BaseModel):
    """Схема ответа для ошибок."""

    detail: str = Field(..., description="Описание ошибки")
    status_code: int = Field(..., description="HTTP код ошибки")


class PriceRecord(BaseModel):
    """Модель для записи цены товара."""

    sku: str = Field(..., description="Артикул товара")
    price: float = Field(..., ge=0, description="Цена товара")
    currency: str = Field(..., description="Валюта цены (USD, EUR, RUB и т.д.)")
    supplier: str = Field(..., description="Наименование поставщика")
    category: str | None = Field(None, description="Категория товара")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Время записи цены"
    )


class CurrencyRate(BaseModel):
    """Модель курса валюты."""

    source_currency: str = Field(..., description="Исходная валюта")
    target_currency: str = Field(..., description="Целевая валюта")
    rate: float = Field(..., gt=0, description="Курс обмена")
    timestamp: datetime = Field(default_factory=datetime.now, description="Время курса")
    provider: str = Field(default="mock", description="Источник курса")
    filename: str = Field(..., description="Имя файла")
    upload_date: datetime = Field(
        default_factory=datetime.now, description="Дата загрузки"
    )
    content_summary: str | None = Field(None, description="Краткое содержание")
    status: Literal["новый", "на проверке", "одобрен", "отклонен"] = Field(
        default="новый", description="Статус документа"
    )


class PriceComparison(BaseModel):
    """Результат сравнения цен."""

    product_code: str = Field(..., description="Артикул товара")
    current_price: float = Field(..., ge=0, description="Текущая цена")
    proposed_price: float = Field(..., ge=0, description="Предложенная цена")
    price_difference: float = Field(..., description="Разница в цене")
    price_difference_percent: float = Field(..., description="Разница в процентах")
    recommendation: Literal["принять", "отклонить", "требует согласования"] = Field(
        ..., description="Рекомендация по цене"
    )


class CommercialProposalAnalysis(BaseModel):
    """Модель для анализа коммерческого предложения."""

    proposal_id: str | None = Field(None, description="ID анализируемого предложения")
    supplier_name: str = Field(..., description="Наименование поставщика")
    analysis_date: datetime = Field(
        default_factory=datetime.now, description="Дата проведения анализа"
    )

    # === ОБЩАЯ ОЦЕНКА ===
    overall_score: float = Field(
        ..., ge=0, le=10, description="Общая оценка предложения (0-10)"
    )
    overall_recommendation: Literal[
        "принять", "отклонить", "требует доработки", "требует согласования"
    ] = Field(..., description="Общая рекомендация по предложению")

    # === АНАЛИЗ ЦЕН ===
    price_competitiveness: Literal[
        "конкурентоспособные", "завышенные", "заниженные", "средние"
    ] = Field(..., description="Конкурентоспособность цен")
    total_cost_analysis: str | None = Field(None, description="Анализ общей стоимости")
    price_comparisons: list[PriceComparison] = Field(
        default_factory=list, description="Детальные сравнения цен по товарам"
    )
    cost_savings_potential: float | None = Field(
        None, description="Потенциальная экономия в рублях"
    )
    cost_savings_percent: float | None = Field(
        None, description="Потенциальная экономия в процентах"
    )

    # === АНАЛИЗ УСЛОВИЙ ===
    payment_terms_rating: float = Field(
        ..., ge=0, le=5, description="Оценка условий оплаты (0-5)"
    )
    delivery_terms_rating: float = Field(
        ..., ge=0, le=5, description="Оценка условий поставки (0-5)"
    )
    terms_analysis: str | None = Field(None, description="Анализ условий сделки")

    # === АНАЛИЗ ПОСТАВЩИКА ===
    supplier_reliability_score: float = Field(
        ..., ge=0, le=5, description="Оценка надежности поставщика (0-5)"
    )
    supplier_history_analysis: str | None = Field(
        None, description="Анализ истории работы с поставщиком"
    )
    supplier_strengths: list[str] = Field(
        default_factory=list, description="Сильные стороны поставщика"
    )
    supplier_weaknesses: list[str] = Field(
        default_factory=list, description="Слабые стороны поставщика"
    )

    # === АНАЛИЗ ТОВАРОВ ===
    product_availability_score: float = Field(
        ..., ge=0, le=5, description="Оценка доступности товаров (0-5)"
    )
    product_quality_assessment: str | None = Field(
        None, description="Оценка качества товаров"
    )
    missing_products: list[str] = Field(
        default_factory=list, description="Отсутствующие товары"
    )
    alternative_products: list[str] = Field(
        default_factory=list, description="Альтернативные товары"
    )

    # === РИСКИ И ВОЗМОЖНОСТИ ===
    identified_risks: list[str] = Field(
        default_factory=list, description="Выявленные риски"
    )
    risk_level: Literal["низкий", "средний", "высокий", "критический"] = Field(
        ..., description="Общий уровень риска"
    )
    opportunities: list[str] = Field(
        default_factory=list, description="Выявленные возможности"
    )

    # === РЕКОМЕНДАЦИИ ===
    action_items: list[str] = Field(
        default_factory=list, description="Рекомендуемые действия"
    )
    negotiation_points: list[str] = Field(
        default_factory=list, description="Пункты для переговоров"
    )
    decision_deadline: datetime | None = Field(
        None, description="Рекомендуемый срок принятия решения"
    )

    # === ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ ===
    analyst_name: str | None = Field(None, description="Имя аналитика")
    analysis_notes: str | None = Field(None, description="Дополнительные заметки")
    confidence_level: float = Field(
        ..., ge=0, le=1, description="Уровень уверенности в анализе"
    )

    # === МЕТРИКИ ===
    analysis_duration_minutes: int | None = Field(
        None, ge=0, description="Время анализа в минутах"
    )
    data_completeness_percent: float | None = Field(
        None, ge=0, le=100, description="Полнота данных для анализа в процентах"
    )


# === МОДЕЛИ ДЛЯ ИСТОРИИ ПОСТАВЩИКА ===


class SupplierTransaction(BaseModel):
    """Модель транзакции с поставщиком."""

    transaction_id: str = Field(..., description="ID транзакции")
    transaction_type: Literal[
        "заказ", "поставка", "оплата", "возврат", "рекламация", "договор"
    ] = Field(..., description="Тип транзакции")
    date: datetime = Field(..., description="Дата транзакции")
    amount: float | None = Field(None, ge=0, description="Сумма транзакции")
    currency: str = Field(default="RUB", description="Валюта")
    status: Literal[
        "создана", "в обработке", "выполнена", "отменена", "просрочена"
    ] = Field(..., description="Статус транзакции")
    description: str | None = Field(None, description="Описание транзакции")
    products: list[ProductSpecification] = Field(
        default_factory=list, description="Товары в транзакции"
    )
    documents: list[str] = Field(
        default_factory=list, description="Связанные документы"
    )
    notes: str | None = Field(None, description="Дополнительные заметки")


class SupplierPerformanceMetrics(BaseModel):
    """Метрики производительности поставщика."""

    period_start: datetime = Field(..., description="Начало периода")
    period_end: datetime = Field(..., description="Конец периода")

    # === ОСНОВНЫЕ МЕТРИКИ ===
    total_orders: int = Field(..., ge=0, description="Общее количество заказов")
    completed_orders: int = Field(..., ge=0, description="Выполненные заказы")
    cancelled_orders: int = Field(..., ge=0, description="Отмененные заказы")
    total_amount: float = Field(..., ge=0, description="Общая сумма заказов")

    # === КАЧЕСТВО ОБСЛУЖИВАНИЯ ===
    on_time_delivery_rate: float = Field(
        ..., ge=0, le=100, description="Процент своевременных поставок"
    )
    quality_rating: float = Field(
        ..., ge=0, le=5, description="Средняя оценка качества товаров"
    )
    customer_satisfaction: float = Field(
        ..., ge=0, le=5, description="Удовлетворенность клиентов"
    )

    # === ФИНАНСОВЫЕ ПОКАЗАТЕЛИ ===
    average_order_value: float = Field(
        ..., ge=0, description="Средняя стоимость заказа"
    )
    payment_terms_compliance: float = Field(
        ..., ge=0, le=100, description="Соблюдение условий оплаты (%)"
    )
    discount_rate: float = Field(
        ..., ge=0, le=100, description="Средний размер скидки (%)"
    )

    # === ПРОБЛЕМЫ И РИСКИ ===
    complaints_count: int = Field(..., ge=0, description="Количество жалоб")
    returns_count: int = Field(..., ge=0, description="Количество возвратов")
    late_deliveries: int = Field(..., ge=0, description="Количество просрочек")
    quality_issues: int = Field(..., ge=0, description="Проблемы с качеством")


class SupplierHistory(BaseModel):
    """Модель истории поставщика."""

    supplier_id: int = Field(..., description="ID поставщика")
    supplier_info: SupplierInfo = Field(..., description="Информация о поставщике")

    # === ОБЩАЯ ИНФОРМАЦИЯ ===
    first_cooperation_date: datetime | None = Field(
        None, description="Дата начала сотрудничества"
    )
    last_transaction_date: datetime | None = Field(
        None, description="Дата последней транзакции"
    )
    cooperation_status: Literal[
        "активный", "неактивный", "заблокирован", "на проверке"
    ] = Field(..., description="Статус сотрудничества")

    # === ТРАНЗАКЦИИ ===
    transactions: list[SupplierTransaction] = Field(
        default_factory=list, description="История транзакций"
    )
    total_transactions: int = Field(
        ..., ge=0, description="Общее количество транзакций"
    )

    # === МЕТРИКИ ПРОИЗВОДИТЕЛЬНОСТИ ===
    current_metrics: SupplierPerformanceMetrics | None = Field(
        None, description="Текущие метрики производительности"
    )
    historical_metrics: list[SupplierPerformanceMetrics] = Field(
        default_factory=list, description="Исторические метрики по периодам"
    )

    # === РЕЙТИНГИ И ОЦЕНКИ ===
    overall_rating: float = Field(
        ..., ge=0, le=5, description="Общий рейтинг поставщика"
    )
    reliability_score: float = Field(
        ..., ge=0, le=100, description="Оценка надежности (%)"
    )
    risk_level: Literal["низкий", "средний", "высокий", "критический"] = Field(
        ..., description="Уровень риска"
    )

    # === КАТЕГОРИИ И СПЕЦИАЛИЗАЦИЯ ===
    product_categories: list[str] = Field(
        default_factory=list, description="Категории товаров"
    )
    specializations: list[str] = Field(
        default_factory=list, description="Специализации поставщика"
    )

    # === КОНТРАКТЫ И СОГЛАШЕНИЯ ===
    active_contracts: list[str] = Field(
        default_factory=list, description="Активные контракты"
    )
    contract_history: list[str] = Field(
        default_factory=list, description="История контрактов"
    )

    # === ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ ===
    notes: str | None = Field(None, description="Дополнительные заметки")
    tags: list[str] = Field(default_factory=list, description="Теги поставщика")
    last_updated: datetime = Field(
        default_factory=datetime.now, description="Дата последнего обновления"
    )


# === МОДЕЛИ ДЛЯ WORKFLOW ===


class WorkflowStepModel(BaseModel):
    """Pydantic модель для шага workflow."""

    step_id: str = Field(..., description="Уникальный ID шага")
    name: str = Field(..., description="Название шага")
    step_type: Literal[
        "validation",
        "processing",
        "approval",
        "notification",
        "integration",
        "escalation",
        "completion",
    ] = Field(..., description="Тип шага")
    action_type: Literal[
        "send_email",
        "create_task",
        "update_status",
        "generate_report",
        "call_api",
        "escalate",
        "approve",
        "reject",
    ] = Field(..., description="Тип действия")
    status: Literal[
        "pending", "in_progress", "completed", "failed", "cancelled", "waiting"
    ] = Field(default="pending", description="Статус шага")

    # Конфигурация шага
    timeout_minutes: int = Field(
        default=60, ge=1, description="Таймаут выполнения в минутах"
    )
    retry_count: int = Field(default=3, ge=0, description="Количество попыток")
    auto_execute: bool = Field(default=True, description="Автоматическое выполнение")
    requires_approval: bool = Field(default=False, description="Требует одобрения")

    # Условия и параметры
    conditions: dict[str, str | int | float | bool] = Field(
        default_factory=dict, description="Условия выполнения"
    )
    parameters: dict[str, str | int | float | bool] = Field(
        default_factory=dict, description="Параметры выполнения"
    )

    # Результаты выполнения
    result: dict[str, str | int | float | bool] | None = Field(
        None, description="Результат выполнения"
    )
    error_message: str | None = Field(None, description="Сообщение об ошибке")
    started_at: datetime | None = Field(None, description="Время начала выполнения")
    completed_at: datetime | None = Field(None, description="Время завершения")

    # Связи с другими шагами
    depends_on: list[str] = Field(
        default_factory=list, description="Зависимости от других шагов"
    )
    next_steps: list[str] = Field(default_factory=list, description="Следующие шаги")


class WorkflowInstanceModel(BaseModel):
    """Pydantic модель для экземпляра workflow."""

    instance_id: str = Field(..., description="Уникальный ID экземпляра")
    workflow_name: str = Field(..., description="Название workflow")
    document_id: str = Field(..., description="ID связанного документа")
    document_type: Literal[
        "коммерческое предложение",
        "спецификация",
        "договор",
        "счет",
        "накладная",
        "сертификат",
        "тендерная документация",
    ] = Field(..., description="Тип документа")

    status: Literal[
        "pending", "in_progress", "completed", "failed", "cancelled", "waiting"
    ] = Field(default="pending", description="Статус workflow")

    steps: list[WorkflowStepModel] = Field(
        default_factory=list, description="Шаги workflow"
    )

    # Метаданные
    created_at: datetime = Field(
        default_factory=datetime.now, description="Время создания"
    )
    started_at: datetime | None = Field(None, description="Время начала выполнения")
    completed_at: datetime | None = Field(None, description="Время завершения")

    # Контекст выполнения
    context: dict[str, str | int | float | bool] = Field(
        default_factory=dict, description="Контекст выполнения"
    )

    # Результаты
    final_result: dict[str, str | int | float | bool] | None = Field(
        None, description="Финальный результат"
    )
    error_message: str | None = Field(None, description="Сообщение об ошибке")

    # Дополнительная информация
    priority: Literal["low", "medium", "high", "critical"] = Field(
        default="medium", description="Приоритет выполнения"
    )
    assigned_to: str | None = Field(None, description="Назначен пользователю")
    tags: list[str] = Field(default_factory=list, description="Теги workflow")


class WorkflowTemplateModel(BaseModel):
    """Pydantic модель для шаблона workflow."""

    template_name: str = Field(..., description="Название шаблона")
    description: str = Field(..., description="Описание шаблона")
    document_types: list[str] = Field(
        ..., description="Типы документов, для которых применим шаблон"
    )

    steps: list[WorkflowStepModel] = Field(..., description="Шаги шаблона")

    # Метаданные шаблона
    version: str = Field(default="1.0", description="Версия шаблона")
    created_by: str | None = Field(None, description="Создатель шаблона")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Дата создания"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="Дата обновления"
    )

    # Настройки шаблона
    is_active: bool = Field(default=True, description="Активен ли шаблон")
    auto_start: bool = Field(default=False, description="Автоматический запуск")

    # Условия запуска
    trigger_conditions: dict[str, str | int | float | bool] = Field(
        default_factory=dict, description="Условия автоматического запуска"
    )

    # Настройки уведомлений
    notification_settings: dict[str, str | bool] = Field(
        default_factory=dict, description="Настройки уведомлений"
    )


class WorkflowExecutionLog(BaseModel):
    """Модель для логирования выполнения workflow."""

    log_id: str = Field(..., description="ID записи лога")
    instance_id: str = Field(..., description="ID экземпляра workflow")
    step_id: str | None = Field(None, description="ID шага (если применимо)")

    event_type: Literal[
        "workflow_started",
        "workflow_completed",
        "workflow_failed",
        "workflow_cancelled",
        "step_started",
        "step_completed",
        "step_failed",
        "step_skipped",
        "escalation_triggered",
        "approval_requested",
        "notification_sent",
    ] = Field(..., description="Тип события")

    timestamp: datetime = Field(
        default_factory=datetime.now, description="Время события"
    )

    message: str = Field(..., description="Сообщение о событии")
    details: dict[str, str | int | float | bool] | None = Field(
        None, description="Дополнительные детали"
    )

    # Контекст выполнения
    user_id: str | None = Field(None, description="ID пользователя")
    system_info: dict[str, str] | None = Field(None, description="Системная информация")

    # Уровень важности
    severity: Literal["info", "warning", "error", "critical"] = Field(
        default="info", description="Уровень важности"
    )


class WorkflowMetrics(BaseModel):
    """Модель для метрик workflow."""

    workflow_name: str = Field(..., description="Название workflow")
    period_start: datetime = Field(..., description="Начало периода")
    period_end: datetime = Field(..., description="Конец периода")

    # Общие метрики
    total_instances: int = Field(..., ge=0, description="Общее количество экземпляров")
    completed_instances: int = Field(..., ge=0, description="Завершенные экземпляры")
    failed_instances: int = Field(..., ge=0, description="Неудачные экземпляры")
    cancelled_instances: int = Field(..., ge=0, description="Отмененные экземпляры")

    # Временные метрики
    average_execution_time_minutes: float = Field(
        ..., ge=0, description="Среднее время выполнения в минутах"
    )
    median_execution_time_minutes: float = Field(
        ..., ge=0, description="Медианное время выполнения в минутах"
    )

    # Метрики качества
    success_rate_percent: float = Field(
        ..., ge=0, le=100, description="Процент успешных выполнений"
    )
    sla_compliance_percent: float = Field(
        ..., ge=0, le=100, description="Соблюдение SLA в процентах"
    )

    # Метрики по шагам
    most_failed_steps: list[str] = Field(
        default_factory=list, description="Шаги с наибольшим количеством ошибок"
    )
    bottleneck_steps: list[str] = Field(
        default_factory=list, description="Узкие места в workflow"
    )

    # Дополнительные метрики
    escalation_count: int = Field(..., ge=0, description="Количество эскалаций")
    manual_intervention_count: int = Field(
        ..., ge=0, description="Количество ручных вмешательств"
    )

    generated_at: datetime = Field(
        default_factory=datetime.now, description="Время генерации метрик"
    )


class SupplierScore(BaseModel):
    """Модель для оценки поставщика по множеству критериев."""

    supplier_id: int = Field(..., description="ID поставщика")
    supplier_name: str = Field(..., description="Наименование поставщика")

    # === ВЕСА КРИТЕРИЕВ (сумма должна быть = 1.0) ===
    price_weight: float = Field(..., ge=0.0, le=1.0, description="Вес критерия цены")
    delivery_weight: float = Field(
        ..., ge=0.0, le=1.0, description="Вес критерия доставки"
    )
    rating_weight: float = Field(
        ..., ge=0.0, le=1.0, description="Вес критерия рейтинга"
    )
    quality_weight: float = Field(
        ..., ge=0.0, le=1.0, description="Вес критерия качества"
    )
    reliability_weight: float = Field(
        ..., ge=0.0, le=1.0, description="Вес критерия надежности"
    )

    # === ОЦЕНКИ ПО КРИТЕРИЯМ (0-10 баллов) ===
    price_score: float = Field(..., ge=0.0, le=10.0, description="Оценка по цене")
    delivery_score: float = Field(
        ..., ge=0.0, le=10.0, description="Оценка по условиям доставки"
    )
    rating_score: float = Field(
        ..., ge=0.0, le=10.0, description="Оценка по рейтингу поставщика"
    )
    quality_score: float = Field(
        ..., ge=0.0, le=10.0, description="Оценка по качеству товаров"
    )
    reliability_score: float = Field(
        ..., ge=0.0, le=10.0, description="Оценка по надежности поставщика"
    )

    # === РАСЧЕТНЫЕ ПОЛЯ ===
    weighted_price_score: float = Field(
        ..., ge=0.0, le=10.0, description="Взвешенная оценка по цене"
    )
    weighted_delivery_score: float = Field(
        ..., ge=0.0, le=10.0, description="Взвешенная оценка по доставке"
    )
    weighted_rating_score: float = Field(
        ..., ge=0.0, le=10.0, description="Взвешенная оценка по рейтингу"
    )
    weighted_quality_score: float = Field(
        ..., ge=0.0, le=10.0, description="Взвешенная оценка по качеству"
    )
    weighted_reliability_score: float = Field(
        ..., ge=0.0, le=10.0, description="Взвешенная оценка по надежности"
    )

    # === ИТОГОВАЯ ОЦЕНКА ===
    total_score: float = Field(
        ..., ge=0.0, le=10.0, description="Общая взвешенная оценка поставщика"
    )

    # === МЕТАДАННЫЕ ===
    calculated_at: datetime = Field(
        default_factory=datetime.now, description="Время расчета оценки"
    )
    proposal_id: str | None = Field(
        None, description="ID связанного коммерческого предложения"
    )
    analyst_notes: str | None = Field(None, description="Заметки аналитика")

    # Удалено устаревшее json_encoders - datetime автоматически сериализуется в ISO формат

    def normalize_weights(self) -> None:
        """Нормализует веса критериев так, чтобы их сумма была равна 1.0."""
        total_weight = (
            self.price_weight
            + self.delivery_weight
            + self.rating_weight
            + self.quality_weight
            + self.reliability_weight
        )

        if total_weight > 0:
            self.price_weight = self.price_weight / total_weight
            self.delivery_weight = self.delivery_weight / total_weight
            self.rating_weight = self.rating_weight / total_weight
            self.quality_weight = self.quality_weight / total_weight
            self.reliability_weight = self.reliability_weight / total_weight

    def calculate_weighted_scores(self) -> None:
        """Рассчитывает взвешенные оценки по каждому критерию."""
        self.weighted_price_score = self.price_score * self.price_weight
        self.weighted_delivery_score = self.delivery_score * self.delivery_weight
        self.weighted_rating_score = self.rating_score * self.rating_weight
        self.weighted_quality_score = self.quality_score * self.quality_weight
        self.weighted_reliability_score = (
            self.reliability_score * self.reliability_weight
        )

    def calculate_total_score(self) -> None:
        """Рассчитывает общую взвешенную оценку поставщика."""
        self.total_score = (
            self.weighted_price_score
            + self.weighted_delivery_score
            + self.weighted_rating_score
            + self.weighted_quality_score
            + self.weighted_reliability_score
        )

    def recalculate_scores(self) -> None:
        """Пересчитывает все оценки с учетом текущих весов."""
        self.normalize_weights()
        self.calculate_weighted_scores()
        self.calculate_total_score()


class CriteriaWeights(BaseModel):
    """Модель для хранения весов критериев оценки поставщиков."""

    # Идентификатор конфигурации весов
    weights_id: str = Field(..., description="Уникальный ID конфигурации весов")
    name: str = Field(..., description="Название конфигурации весов")
    description: str | None = Field(None, description="Описание конфигурации")

    # Веса критериев
    price_weight: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Вес критерия цены"
    )
    delivery_weight: float = Field(
        default=0.2, ge=0.0, le=1.0, description="Вес критерия доставки"
    )
    rating_weight: float = Field(
        default=0.2, ge=0.0, le=1.0, description="Вес критерия рейтинга"
    )
    quality_weight: float = Field(
        default=0.15, ge=0.0, le=1.0, description="Вес критерия качества"
    )
    reliability_weight: float = Field(
        default=0.15, ge=0.0, le=1.0, description="Вес критерия надежности"
    )

    # Метаданные
    created_at: datetime = Field(
        default_factory=datetime.now, description="Время создания конфигурации"
    )
    created_by: str | None = Field(None, description="Создатель конфигурации")
    is_default: bool = Field(
        default=False, description="Является ли конфигурацией по умолчанию"
    )

    def validate_weights(self) -> bool:
        """Проверяет, что сумма всех весов равна 1.0."""
        total = (
            self.price_weight
            + self.delivery_weight
            + self.rating_weight
            + self.quality_weight
            + self.reliability_weight
        )
        return abs(total - 1.0) < 0.001

    def normalize_weights(self) -> None:
        """Нормализует веса так, чтобы их сумма была равна 1.0."""
        total = (
            self.price_weight
            + self.delivery_weight
            + self.rating_weight
            + self.quality_weight
            + self.reliability_weight
        )

        if total > 0:
            self.price_weight = self.price_weight / total
            self.delivery_weight = self.delivery_weight / total
            self.rating_weight = self.rating_weight / total
            self.quality_weight = self.quality_weight / total
            self.reliability_weight = self.reliability_weight / total

    def get_weights_dict(self) -> dict[str, float]:
        """Возвращает словарь весов критериев."""
        return {
            "price": self.price_weight,
            "delivery": self.delivery_weight,
            "rating": self.rating_weight,
            "quality": self.quality_weight,
            "reliability": self.reliability_weight,
        }
