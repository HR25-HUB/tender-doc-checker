"""Предустановленные шаблоны workflow для типовых процессов."""

from datetime import datetime
from typing import Any, Optional

from src.models import WorkflowStepModel, WorkflowTemplateModel


class WorkflowTemplates:
    """Класс для управления предустановленными шаблонами workflow."""

    def __init__(self):
        self.templates: dict[str, WorkflowTemplateModel] = {}
        self._initialize_default_templates()

    def _initialize_default_templates(self):
        """Инициализирует стандартные шаблоны workflow."""

        # Шаблон для обработки коммерческих предложений
        self.templates[
            "commercial_proposal_processing"
        ] = self._create_commercial_proposal_workflow()

        # Шаблон для обработки договоров
        self.templates["contract_processing"] = self._create_contract_workflow()

        # Шаблон для обработки спецификаций
        self.templates[
            "specification_processing"
        ] = self._create_specification_workflow()

        # Шаблон для срочной обработки документов
        self.templates["urgent_document_processing"] = self._create_urgent_workflow()

        # Шаблон для обработки счетов
        self.templates["invoice_processing"] = self._create_invoice_workflow()

        # Шаблон для обработки накладных
        self.templates[
            "delivery_note_processing"
        ] = self._create_delivery_note_workflow()

        # Шаблон для полного цикла закупки
        self.templates[
            "full_procurement_cycle"
        ] = self._create_full_procurement_workflow()

    def _create_commercial_proposal_workflow(self) -> WorkflowTemplateModel:
        """Создает шаблон workflow для обработки коммерческих предложений."""

        steps = [
            WorkflowStepModel(
                step_id="cp_01_receive",
                name="Получение коммерческого предложения",
                description="Автоматическая регистрация полученного коммерческого предложения",
                step_type="automatic",
                order=1,
                conditions={},
                actions=[
                    {
                        "type": "update_status",
                        "parameters": {
                            "status": "получено",
                            "reason": "Автоматическая регистрация",
                        },
                    },
                    {
                        "type": "send_email",
                        "parameters": {
                            "template": "document_received",
                            "recipient": "procurement@company.com",
                            "document_type": "коммерческое предложение",
                        },
                    },
                ],
                sla_hours=1,
                required_roles=["system"],
                next_steps=["cp_02_initial_check"],
            ),
            WorkflowStepModel(
                step_id="cp_02_initial_check",
                name="Первичная проверка",
                description="Автоматическая проверка комплектности и корректности документа",
                step_type="automatic",
                order=2,
                conditions={},
                actions=[
                    {
                        "type": "validate_document",
                        "parameters": {
                            "check_completeness": True,
                            "check_format": True,
                            "check_required_fields": True,
                        },
                    }
                ],
                sla_hours=2,
                required_roles=["system"],
                next_steps=["cp_03_technical_review", "cp_02_fix_issues"],
            ),
            WorkflowStepModel(
                step_id="cp_02_fix_issues",
                name="Исправление замечаний",
                description="Возврат документа поставщику для исправления замечаний",
                step_type="manual",
                order=2.1,
                conditions={"validation_failed": True},
                actions=[
                    {
                        "type": "reject_document",
                        "parameters": {
                            "notify_supplier": True,
                            "rejection_reason": "Обнаружены ошибки в документе",
                        },
                    },
                    {
                        "type": "create_task",
                        "parameters": {
                            "title": "Отслеживание исправления замечаний",
                            "description": "Ожидание исправленного документа от поставщика",
                            "deadline_hours": 72,
                        },
                    },
                ],
                sla_hours=4,
                required_roles=["procurement_specialist"],
                next_steps=["cp_01_receive"],
            ),
            WorkflowStepModel(
                step_id="cp_03_technical_review",
                name="Техническая экспертиза",
                description="Проверка технических характеристик и соответствия требованиям",
                step_type="manual",
                order=3,
                conditions={"validation_passed": True},
                actions=[
                    {
                        "type": "create_task",
                        "parameters": {
                            "title": "Техническая экспертиза коммерческого предложения",
                            "description": "Проверка технических характеристик и соответствия ТЗ",
                            "deadline_hours": 48,
                        },
                    },
                    {
                        "type": "update_status",
                        "parameters": {"status": "на технической экспертизе"},
                    },
                ],
                sla_hours=48,
                required_roles=["technical_expert"],
                next_steps=["cp_04_commercial_review", "cp_03_technical_reject"],
            ),
            WorkflowStepModel(
                step_id="cp_03_technical_reject",
                name="Техническое отклонение",
                description="Отклонение по техническим причинам",
                step_type="manual",
                order=3.1,
                conditions={"technical_review_failed": True},
                actions=[
                    {
                        "type": "reject_document",
                        "parameters": {
                            "notify_supplier": True,
                            "rejection_reason": "Не соответствует техническим требованиям",
                        },
                    },
                    {
                        "type": "archive_document",
                        "parameters": {"reason": "Техническое отклонение"},
                    },
                ],
                sla_hours=8,
                required_roles=["technical_expert"],
                next_steps=[],
            ),
            WorkflowStepModel(
                step_id="cp_04_commercial_review",
                name="Коммерческая экспертиза",
                description="Анализ цен, условий поставки и коммерческих условий",
                step_type="manual",
                order=4,
                conditions={"technical_review_passed": True},
                actions=[
                    {
                        "type": "create_task",
                        "parameters": {
                            "title": "Коммерческая экспертиза предложения",
                            "description": "Анализ цен, сроков поставки и коммерческих условий",
                            "deadline_hours": 24,
                        },
                    },
                    {
                        "type": "update_status",
                        "parameters": {"status": "на коммерческой экспертизе"},
                    },
                ],
                sla_hours=24,
                required_roles=["commercial_expert"],
                next_steps=[
                    "cp_05_approval",
                    "cp_04_commercial_reject",
                    "cp_04_negotiate",
                ],
            ),
            WorkflowStepModel(
                step_id="cp_04_commercial_reject",
                name="Коммерческое отклонение",
                description="Отклонение по коммерческим причинам",
                step_type="manual",
                order=4.1,
                conditions={"commercial_review_failed": True},
                actions=[
                    {
                        "type": "reject_document",
                        "parameters": {
                            "notify_supplier": True,
                            "rejection_reason": "Неприемлемые коммерческие условия",
                        },
                    },
                    {
                        "type": "archive_document",
                        "parameters": {"reason": "Коммерческое отклонение"},
                    },
                ],
                sla_hours=8,
                required_roles=["commercial_expert"],
                next_steps=[],
            ),
            WorkflowStepModel(
                step_id="cp_04_negotiate",
                name="Переговоры с поставщиком",
                description="Проведение переговоров для улучшения условий",
                step_type="manual",
                order=4.2,
                conditions={"negotiation_required": True},
                actions=[
                    {
                        "type": "schedule_meeting",
                        "parameters": {
                            "meeting_type": "переговоры",
                            "subject": "Обсуждение коммерческих условий",
                            "duration_minutes": 60,
                        },
                    },
                    {
                        "type": "create_task",
                        "parameters": {
                            "title": "Переговоры с поставщиком",
                            "description": "Обсуждение улучшения коммерческих условий",
                            "deadline_hours": 72,
                        },
                    },
                ],
                sla_hours=72,
                required_roles=["commercial_expert", "procurement_manager"],
                next_steps=["cp_04_commercial_review"],
            ),
            WorkflowStepModel(
                step_id="cp_05_approval",
                name="Утверждение предложения",
                description="Финальное утверждение коммерческого предложения",
                step_type="manual",
                order=5,
                conditions={"commercial_review_passed": True},
                actions=[
                    {
                        "type": "approve_document",
                        "parameters": {
                            "notify_supplier": True,
                            "next_steps": "Ожидайте договор для подписания",
                        },
                    },
                    {
                        "type": "create_order",
                        "parameters": {"delivery_date": "auto_calculate"},
                    },
                    {
                        "type": "create_task",
                        "parameters": {
                            "title": "Подготовка договора",
                            "description": "Подготовка договора на основе одобренного предложения",
                            "deadline_hours": 48,
                        },
                    },
                ],
                sla_hours=24,
                required_roles=["procurement_manager"],
                next_steps=["cp_06_contract_preparation"],
            ),
            WorkflowStepModel(
                step_id="cp_06_contract_preparation",
                name="Подготовка договора",
                description="Подготовка и отправка договора поставщику",
                step_type="manual",
                order=6,
                conditions={},
                actions=[
                    {
                        "type": "generate_report",
                        "parameters": {"report_type": "contract_draft"},
                    },
                    {
                        "type": "send_contract",
                        "parameters": {"contract_type": "supply_agreement"},
                    },
                    {
                        "type": "update_status",
                        "parameters": {"status": "договор отправлен"},
                    },
                ],
                sla_hours=48,
                required_roles=["legal_specialist"],
                next_steps=["cp_07_completion"],
            ),
            WorkflowStepModel(
                step_id="cp_07_completion",
                name="Завершение процесса",
                description="Архивирование документов и завершение workflow",
                step_type="automatic",
                order=7,
                conditions={},
                actions=[
                    {
                        "type": "archive_document",
                        "parameters": {"reason": "Успешное завершение процесса"},
                    },
                    {"type": "update_status", "parameters": {"status": "завершено"}},
                    {
                        "type": "generate_report",
                        "parameters": {"report_type": "completion_summary"},
                    },
                ],
                sla_hours=4,
                required_roles=["system"],
                next_steps=[],
            ),
        ]

        return WorkflowTemplateModel(
            template_id="commercial_proposal_processing",
            name="Обработка коммерческих предложений",
            description="Полный цикл обработки коммерческого предложения от получения до заключения договора",
            document_types=["коммерческое предложение"],
            steps=steps,
            total_sla_hours=168,  # 7 дней
            created_at=datetime.now(),
            version="1.0",
            is_active=True,
            metadata={
                "category": "procurement",
                "complexity": "high",
                "automation_level": "medium",
                "estimated_duration_days": 7,
            },
        )

    def _create_contract_workflow(self) -> WorkflowTemplateModel:
        """Создает шаблон workflow для обработки договоров."""

        steps = [
            WorkflowStepModel(
                step_id="ct_01_receive",
                name="Получение договора",
                description="Регистрация полученного договора",
                step_type="automatic",
                order=1,
                conditions={},
                actions=[
                    {
                        "type": "update_status",
                        "parameters": {
                            "status": "получен",
                            "reason": "Автоматическая регистрация",
                        },
                    },
                    {
                        "type": "create_task",
                        "parameters": {
                            "title": "Новый договор для рассмотрения",
                            "description": "Поступил новый договор, требуется правовая экспертиза",
                            "deadline_hours": 24,
                        },
                    },
                ],
                sla_hours=2,
                required_roles=["system"],
                next_steps=["ct_02_legal_review"],
            ),
            WorkflowStepModel(
                step_id="ct_02_legal_review",
                name="Правовая экспертиза",
                description="Проверка договора на соответствие законодательству и корпоративным стандартам",
                step_type="manual",
                order=2,
                conditions={},
                actions=[
                    {
                        "type": "update_status",
                        "parameters": {"status": "на правовой экспертизе"},
                    }
                ],
                sla_hours=48,
                required_roles=["legal_expert"],
                next_steps=["ct_03_financial_review", "ct_02_legal_reject"],
            ),
            WorkflowStepModel(
                step_id="ct_02_legal_reject",
                name="Правовое отклонение",
                description="Отклонение договора по правовым основаниям",
                step_type="manual",
                order=2.1,
                conditions={"legal_review_failed": True},
                actions=[
                    {
                        "type": "reject_document",
                        "parameters": {
                            "notify_supplier": True,
                            "rejection_reason": "Не соответствует правовым требованиям",
                        },
                    }
                ],
                sla_hours=8,
                required_roles=["legal_expert"],
                next_steps=[],
            ),
            WorkflowStepModel(
                step_id="ct_03_financial_review",
                name="Финансовая экспертиза",
                description="Проверка финансовых условий договора",
                step_type="manual",
                order=3,
                conditions={"legal_review_passed": True},
                actions=[
                    {
                        "type": "update_status",
                        "parameters": {"status": "на финансовой экспертизе"},
                    }
                ],
                sla_hours=24,
                required_roles=["financial_expert"],
                next_steps=["ct_04_approval", "ct_03_financial_reject"],
            ),
            WorkflowStepModel(
                step_id="ct_03_financial_reject",
                name="Финансовое отклонение",
                description="Отклонение договора по финансовым основаниям",
                step_type="manual",
                order=3.1,
                conditions={"financial_review_failed": True},
                actions=[
                    {
                        "type": "reject_document",
                        "parameters": {
                            "notify_supplier": True,
                            "rejection_reason": "Неприемлемые финансовые условия",
                        },
                    }
                ],
                sla_hours=8,
                required_roles=["financial_expert"],
                next_steps=[],
            ),
            WorkflowStepModel(
                step_id="ct_04_approval",
                name="Утверждение договора",
                description="Финальное утверждение и подписание договора",
                step_type="manual",
                order=4,
                conditions={"financial_review_passed": True},
                actions=[
                    {
                        "type": "approve_document",
                        "parameters": {
                            "notify_supplier": True,
                            "next_steps": "Договор утвержден и готов к исполнению",
                        },
                    },
                    {
                        "type": "send_contract",
                        "parameters": {"contract_type": "signed_agreement"},
                    },
                ],
                sla_hours=24,
                required_roles=["director"],
                next_steps=["ct_05_execution"],
            ),
            WorkflowStepModel(
                step_id="ct_05_execution",
                name="Исполнение договора",
                description="Контроль исполнения договорных обязательств",
                step_type="automatic",
                order=5,
                conditions={},
                actions=[
                    {"type": "update_status", "parameters": {"status": "в исполнении"}},
                    {
                        "type": "create_task",
                        "parameters": {
                            "title": "Контроль исполнения договора",
                            "description": "Мониторинг выполнения договорных обязательств",
                            "deadline_hours": 720,  # 30 дней
                        },
                    },
                ],
                sla_hours=720,
                required_roles=["contract_manager"],
                next_steps=[],
            ),
        ]

        return WorkflowTemplateModel(
            template_id="contract_processing",
            name="Обработка договоров",
            description="Процесс правовой и финансовой экспертизы договоров",
            document_types=["договор", "соглашение", "контракт"],
            steps=steps,
            total_sla_hours=120,  # 5 дней
            created_at=datetime.now(),
            version="1.0",
            is_active=True,
            metadata={
                "category": "legal",
                "complexity": "high",
                "automation_level": "low",
                "estimated_duration_days": 5,
            },
        )

    def _create_specification_workflow(self) -> WorkflowTemplateModel:
        """Создает шаблон workflow для обработки спецификаций."""

        steps = [
            WorkflowStepModel(
                step_id="sp_01_receive",
                name="Получение спецификации",
                description="Автоматическая обработка полученной спецификации",
                step_type="automatic",
                order=1,
                conditions={},
                actions=[
                    {"type": "update_status", "parameters": {"status": "получена"}},
                    {
                        "type": "validate_document",
                        "parameters": {
                            "check_format": True,
                            "check_required_fields": True,
                        },
                    },
                ],
                sla_hours=1,
                required_roles=["system"],
                next_steps=["sp_02_technical_check"],
            ),
            WorkflowStepModel(
                step_id="sp_02_technical_check",
                name="Техническая проверка",
                description="Проверка технических характеристик в спецификации",
                step_type="manual",
                order=2,
                conditions={},
                actions=[
                    {
                        "type": "create_task",
                        "parameters": {
                            "title": "Техническая проверка спецификации",
                            "description": "Проверка соответствия технических характеристик требованиям",
                            "deadline_hours": 24,
                        },
                    }
                ],
                sla_hours=24,
                required_roles=["technical_specialist"],
                next_steps=["sp_03_approval", "sp_02_reject"],
            ),
            WorkflowStepModel(
                step_id="sp_02_reject",
                name="Отклонение спецификации",
                description="Отклонение спецификации с указанием причин",
                step_type="manual",
                order=2.1,
                conditions={"technical_check_failed": True},
                actions=[
                    {
                        "type": "reject_document",
                        "parameters": {
                            "notify_supplier": True,
                            "rejection_reason": "Техническая спецификация не соответствует требованиям",
                        },
                    }
                ],
                sla_hours=4,
                required_roles=["technical_specialist"],
                next_steps=[],
            ),
            WorkflowStepModel(
                step_id="sp_03_approval",
                name="Утверждение спецификации",
                description="Утверждение технической спецификации",
                step_type="manual",
                order=3,
                conditions={"technical_check_passed": True},
                actions=[
                    {
                        "type": "approve_document",
                        "parameters": {
                            "notify_supplier": True,
                            "next_steps": "Спецификация утверждена, ожидайте коммерческое предложение",
                        },
                    },
                    {
                        "type": "archive_document",
                        "parameters": {"reason": "Успешное утверждение"},
                    },
                ],
                sla_hours=8,
                required_roles=["technical_manager"],
                next_steps=[],
            ),
        ]

        return WorkflowTemplateModel(
            template_id="specification_processing",
            name="Обработка спецификаций",
            description="Процесс технической проверки и утверждения спецификаций",
            document_types=["спецификация", "техническое задание"],
            steps=steps,
            total_sla_hours=48,  # 2 дня
            created_at=datetime.now(),
            version="1.0",
            is_active=True,
            metadata={
                "category": "technical",
                "complexity": "medium",
                "automation_level": "medium",
                "estimated_duration_days": 2,
            },
        )

    def _create_urgent_workflow(self) -> WorkflowTemplateModel:
        """Создает шаблон workflow для срочной обработки документов."""

        steps = [
            WorkflowStepModel(
                step_id="ur_01_receive",
                name="Срочное получение",
                description="Немедленная обработка срочного документа",
                step_type="automatic",
                order=1,
                conditions={},
                actions=[
                    {
                        "type": "update_status",
                        "parameters": {"status": "срочная обработка"},
                    },
                    {
                        "type": "send_email",
                        "parameters": {
                            "template": "urgent_notification",
                            "recipient": "urgent@company.com",
                            "subject": "СРОЧНО: Поступил документ для немедленной обработки",
                        },
                    },
                ],
                sla_hours=0.5,
                required_roles=["system"],
                next_steps=["ur_02_express_review"],
            ),
            WorkflowStepModel(
                step_id="ur_02_express_review",
                name="Экспресс-экспертиза",
                description="Ускоренная экспертиза документа",
                step_type="manual",
                order=2,
                conditions={},
                actions=[
                    {
                        "type": "create_task",
                        "parameters": {
                            "title": "СРОЧНО: Экспресс-экспертиза документа",
                            "description": "Требуется немедленная экспертиза срочного документа",
                            "deadline_hours": 4,
                            "priority": "высокий",
                        },
                    }
                ],
                sla_hours=4,
                required_roles=["senior_expert"],
                next_steps=["ur_03_express_approval", "ur_02_reject"],
            ),
            WorkflowStepModel(
                step_id="ur_02_reject",
                name="Срочное отклонение",
                description="Немедленное отклонение документа",
                step_type="manual",
                order=2.1,
                conditions={"express_review_failed": True},
                actions=[
                    {
                        "type": "reject_document",
                        "parameters": {
                            "notify_supplier": True,
                            "rejection_reason": "Документ не прошел срочную экспертизу",
                        },
                    }
                ],
                sla_hours=1,
                required_roles=["senior_expert"],
                next_steps=[],
            ),
            WorkflowStepModel(
                step_id="ur_03_express_approval",
                name="Экспресс-утверждение",
                description="Ускоренное утверждение документа",
                step_type="manual",
                order=3,
                conditions={"express_review_passed": True},
                actions=[
                    {
                        "type": "approve_document",
                        "parameters": {
                            "notify_supplier": True,
                            "next_steps": "Документ утвержден в срочном порядке",
                        },
                    },
                    {
                        "type": "send_email",
                        "parameters": {
                            "template": "urgent_approved",
                            "recipient": "management@company.com",
                            "subject": "Срочный документ утвержден",
                        },
                    },
                ],
                sla_hours=2,
                required_roles=["director"],
                next_steps=[],
            ),
        ]

        return WorkflowTemplateModel(
            template_id="urgent_document_processing",
            name="Срочная обработка документов",
            description="Ускоренный процесс обработки срочных документов",
            document_types=["срочный документ"],
            steps=steps,
            total_sla_hours=8,  # 8 часов
            created_at=datetime.now(),
            version="1.0",
            is_active=True,
            metadata={
                "category": "urgent",
                "complexity": "low",
                "automation_level": "high",
                "estimated_duration_hours": 8,
            },
        )

    def _create_invoice_workflow(self) -> WorkflowTemplateModel:
        """Создает шаблон workflow для обработки счетов."""

        steps = [
            WorkflowStepModel(
                step_id="inv_01_receive",
                name="Получение счета",
                description="Автоматическая обработка полученного счета",
                step_type="automatic",
                order=1,
                conditions={},
                actions=[
                    {"type": "update_status", "parameters": {"status": "получен"}},
                    {
                        "type": "validate_document",
                        "parameters": {
                            "check_format": True,
                            "check_amounts": True,
                            "check_details": True,
                        },
                    },
                ],
                sla_hours=1,
                required_roles=["system"],
                next_steps=["inv_02_verification"],
            ),
            WorkflowStepModel(
                step_id="inv_02_verification",
                name="Проверка счета",
                description="Проверка корректности счета и соответствия договору",
                step_type="manual",
                order=2,
                conditions={},
                actions=[
                    {
                        "type": "create_task",
                        "parameters": {
                            "title": "Проверка счета",
                            "description": "Проверка корректности реквизитов и сумм",
                            "deadline_hours": 8,
                        },
                    }
                ],
                sla_hours=8,
                required_roles=["accountant"],
                next_steps=["inv_03_payment_approval", "inv_02_reject"],
            ),
            WorkflowStepModel(
                step_id="inv_02_reject",
                name="Отклонение счета",
                description="Отклонение некорректного счета",
                step_type="manual",
                order=2.1,
                conditions={"verification_failed": True},
                actions=[
                    {
                        "type": "reject_document",
                        "parameters": {
                            "notify_supplier": True,
                            "rejection_reason": "Ошибки в счете",
                        },
                    }
                ],
                sla_hours=2,
                required_roles=["accountant"],
                next_steps=[],
            ),
            WorkflowStepModel(
                step_id="inv_03_payment_approval",
                name="Утверждение к оплате",
                description="Утверждение счета к оплате",
                step_type="manual",
                order=3,
                conditions={"verification_passed": True},
                actions=[
                    {
                        "type": "approve_document",
                        "parameters": {
                            "notify_supplier": True,
                            "next_steps": "Счет утвержден к оплате",
                        },
                    },
                    {
                        "type": "create_task",
                        "parameters": {
                            "title": "Оплата счета",
                            "description": "Произвести оплату утвержденного счета",
                            "deadline_hours": 24,
                        },
                    },
                ],
                sla_hours=4,
                required_roles=["finance_manager"],
                next_steps=[],
            ),
        ]

        return WorkflowTemplateModel(
            template_id="invoice_processing",
            name="Обработка счетов",
            description="Процесс проверки и утверждения счетов к оплате",
            document_types=["счет", "счет-фактура"],
            steps=steps,
            total_sla_hours=24,  # 1 день
            created_at=datetime.now(),
            version="1.0",
            is_active=True,
            metadata={
                "category": "finance",
                "complexity": "low",
                "automation_level": "medium",
                "estimated_duration_hours": 24,
            },
        )

    def _create_delivery_note_workflow(self) -> WorkflowTemplateModel:
        """Создает шаблон workflow для обработки накладных."""

        steps = [
            WorkflowStepModel(
                step_id="dn_01_receive",
                name="Получение накладной",
                description="Регистрация полученной накладной",
                step_type="automatic",
                order=1,
                conditions={},
                actions=[
                    {"type": "update_status", "parameters": {"status": "получена"}}
                ],
                sla_hours=1,
                required_roles=["system"],
                next_steps=["dn_02_goods_verification"],
            ),
            WorkflowStepModel(
                step_id="dn_02_goods_verification",
                name="Проверка товара",
                description="Проверка соответствия поставленного товара накладной",
                step_type="manual",
                order=2,
                conditions={},
                actions=[
                    {
                        "type": "create_task",
                        "parameters": {
                            "title": "Проверка поставки по накладной",
                            "description": "Сверка фактической поставки с накладной",
                            "deadline_hours": 4,
                        },
                    }
                ],
                sla_hours=4,
                required_roles=["warehouse_manager"],
                next_steps=["dn_03_acceptance", "dn_02_discrepancy"],
            ),
            WorkflowStepModel(
                step_id="dn_02_discrepancy",
                name="Обработка расхождений",
                description="Обработка расхождений между накладной и фактической поставкой",
                step_type="manual",
                order=2.1,
                conditions={"goods_verification_failed": True},
                actions=[
                    {
                        "type": "create_task",
                        "parameters": {
                            "title": "Урегулирование расхождений по поставке",
                            "description": "Обнаружены расхождения, требуется урегулирование",
                            "deadline_hours": 8,
                        },
                    },
                    {
                        "type": "send_email",
                        "parameters": {
                            "template": "discrepancy_notification",
                            "recipient": "supplier@company.com",
                            "subject": "Обнаружены расхождения в поставке",
                        },
                    },
                ],
                sla_hours=8,
                required_roles=["warehouse_manager"],
                next_steps=["dn_03_acceptance"],
            ),
            WorkflowStepModel(
                step_id="dn_03_acceptance",
                name="Приемка товара",
                description="Окончательная приемка товара на склад",
                step_type="manual",
                order=3,
                conditions={},
                actions=[
                    {
                        "type": "approve_document",
                        "parameters": {
                            "notify_supplier": True,
                            "next_steps": "Товар принят на склад",
                        },
                    },
                    {"type": "update_status", "parameters": {"status": "товар принят"}},
                    {
                        "type": "archive_document",
                        "parameters": {"reason": "Успешная приемка"},
                    },
                ],
                sla_hours=2,
                required_roles=["warehouse_manager"],
                next_steps=[],
            ),
        ]

        return WorkflowTemplateModel(
            template_id="delivery_note_processing",
            name="Обработка накладных",
            description="Процесс приемки товара по накладным",
            document_types=["накладная", "товарная накладная"],
            steps=steps,
            total_sla_hours=16,  # 16 часов
            created_at=datetime.now(),
            version="1.0",
            is_active=True,
            metadata={
                "category": "warehouse",
                "complexity": "medium",
                "automation_level": "medium",
                "estimated_duration_hours": 16,
            },
        )

    def _create_full_procurement_workflow(self) -> WorkflowTemplateModel:
        """Создает шаблон workflow для полного цикла закупки."""

        steps = [
            WorkflowStepModel(
                step_id="fp_01_request",
                name="Заявка на закупку",
                description="Создание и утверждение заявки на закупку",
                step_type="manual",
                order=1,
                conditions={},
                actions=[
                    {
                        "type": "create_task",
                        "parameters": {
                            "title": "Рассмотрение заявки на закупку",
                            "description": "Новая заявка на закупку требует рассмотрения",
                            "deadline_hours": 24,
                        },
                    }
                ],
                sla_hours=24,
                required_roles=["procurement_manager"],
                next_steps=["fp_02_supplier_selection"],
            ),
            WorkflowStepModel(
                step_id="fp_02_supplier_selection",
                name="Выбор поставщиков",
                description="Поиск и выбор потенциальных поставщиков",
                step_type="manual",
                order=2,
                conditions={},
                actions=[
                    {
                        "type": "create_task",
                        "parameters": {
                            "title": "Поиск поставщиков",
                            "description": "Найти и отобрать поставщиков для запроса предложений",
                            "deadline_hours": 48,
                        },
                    }
                ],
                sla_hours=48,
                required_roles=["procurement_specialist"],
                next_steps=["fp_03_rfp_sending"],
            ),
            WorkflowStepModel(
                step_id="fp_03_rfp_sending",
                name="Отправка запросов предложений",
                description="Отправка технических заданий поставщикам",
                step_type="manual",
                order=3,
                conditions={},
                actions=[
                    {
                        "type": "send_email",
                        "parameters": {
                            "template": "rfp_request",
                            "subject": "Запрос коммерческого предложения",
                        },
                    }
                ],
                sla_hours=8,
                required_roles=["procurement_specialist"],
                next_steps=["fp_04_proposal_analysis"],
            ),
            WorkflowStepModel(
                step_id="fp_04_proposal_analysis",
                name="Анализ предложений",
                description="Сравнительный анализ полученных предложений",
                step_type="manual",
                order=4,
                conditions={},
                actions=[
                    {
                        "type": "create_task",
                        "parameters": {
                            "title": "Анализ коммерческих предложений",
                            "description": "Провести сравнительный анализ предложений",
                            "deadline_hours": 72,
                        },
                    },
                    {
                        "type": "generate_report",
                        "parameters": {"report_type": "comparative_analysis"},
                    },
                ],
                sla_hours=72,
                required_roles=["procurement_analyst"],
                next_steps=["fp_05_supplier_selection"],
            ),
            WorkflowStepModel(
                step_id="fp_05_supplier_selection",
                name="Выбор поставщика",
                description="Принятие решения о выборе поставщика",
                step_type="manual",
                order=5,
                conditions={},
                actions=[
                    {
                        "type": "create_task",
                        "parameters": {
                            "title": "Принятие решения по поставщику",
                            "description": "Выбрать поставщика на основе анализа",
                            "deadline_hours": 24,
                        },
                    }
                ],
                sla_hours=24,
                required_roles=["procurement_manager"],
                next_steps=["fp_06_contract_preparation"],
            ),
            WorkflowStepModel(
                step_id="fp_06_contract_preparation",
                name="Подготовка договора",
                description="Подготовка и согласование договора с выбранным поставщиком",
                step_type="manual",
                order=6,
                conditions={},
                actions=[
                    {
                        "type": "create_task",
                        "parameters": {
                            "title": "Подготовка договора поставки",
                            "description": "Подготовить договор с выбранным поставщиком",
                            "deadline_hours": 48,
                        },
                    }
                ],
                sla_hours=48,
                required_roles=["legal_specialist"],
                next_steps=["fp_07_contract_signing"],
            ),
            WorkflowStepModel(
                step_id="fp_07_contract_signing",
                name="Подписание договора",
                description="Подписание договора и начало исполнения",
                step_type="manual",
                order=7,
                conditions={},
                actions=[
                    {
                        "type": "send_contract",
                        "parameters": {"contract_type": "supply_agreement"},
                    },
                    {
                        "type": "create_task",
                        "parameters": {
                            "title": "Контроль исполнения договора",
                            "description": "Мониторинг выполнения договорных обязательств",
                            "deadline_hours": 168,  # 7 дней
                        },
                    },
                ],
                sla_hours=24,
                required_roles=["contract_manager"],
                next_steps=[],
            ),
        ]

        return WorkflowTemplateModel(
            template_id="full_procurement_cycle",
            name="Полный цикл закупки",
            description="Комплексный процесс закупки от заявки до заключения договора",
            document_types=["заявка на закупку"],
            steps=steps,
            total_sla_hours=336,  # 14 дней
            created_at=datetime.now(),
            version="1.0",
            is_active=True,
            metadata={
                "category": "procurement",
                "complexity": "very_high",
                "automation_level": "low",
                "estimated_duration_days": 14,
            },
        )

    def get_template(self, template_id: str) -> Optional[WorkflowTemplateModel]:
        """Получает шаблон workflow по ID."""
        return self.templates.get(template_id)

    def get_templates_by_document_type(
        self, document_type: str
    ) -> list[WorkflowTemplateModel]:
        """Получает шаблоны workflow для определенного типа документа."""
        matching_templates = []

        for template in self.templates.values():
            if document_type.lower() in [dt.lower() for dt in template.document_types]:
                matching_templates.append(template)

        return matching_templates

    def get_all_templates(self) -> list[WorkflowTemplateModel]:
        """Получает все доступные шаблоны workflow."""
        return list(self.templates.values())

    def get_active_templates(self) -> list[WorkflowTemplateModel]:
        """Получает только активные шаблоны workflow."""
        return [template for template in self.templates.values() if template.is_active]

    def add_custom_template(self, template: WorkflowTemplateModel):
        """Добавляет пользовательский шаблон workflow."""
        self.templates[template.template_id] = template

    def deactivate_template(self, template_id: str):
        """Деактивирует шаблон workflow."""
        if template_id in self.templates:
            self.templates[template_id].is_active = False

    def activate_template(self, template_id: str):
        """Активирует шаблон workflow."""
        if template_id in self.templates:
            self.templates[template_id].is_active = True

    def get_templates_by_category(self, category: str) -> list[WorkflowTemplateModel]:
        """Получает шаблоны workflow по категории."""
        matching_templates = []

        for template in self.templates.values():
            if template.metadata.get("category", "").lower() == category.lower():
                matching_templates.append(template)

        return matching_templates

    def get_templates_by_complexity(
        self, complexity: str
    ) -> list[WorkflowTemplateModel]:
        """Получает шаблоны workflow по уровню сложности."""
        matching_templates = []

        for template in self.templates.values():
            if template.metadata.get("complexity", "").lower() == complexity.lower():
                matching_templates.append(template)

        return matching_templates


# Глобальный экземпляр менеджера шаблонов
workflow_templates = WorkflowTemplates()


# Функции для интеграции с workflow_engine
def get_workflow_template(template_id: str) -> Optional[WorkflowTemplateModel]:
    """Получает шаблон workflow для использования в движке."""
    return workflow_templates.get_template(template_id)


def suggest_workflow_template(document_type: str) -> Optional[WorkflowTemplateModel]:
    """Предлагает подходящий шаблон workflow для типа документа."""
    templates = workflow_templates.get_templates_by_document_type(document_type)

    if templates:
        # Возвращаем первый активный шаблон
        for template in templates:
            if template.is_active:
                return template

    return None


def get_available_templates() -> list[dict[str, Any]]:
    """Получает список доступных шаблонов для UI."""
    templates = workflow_templates.get_active_templates()

    return [
        {
            "id": template.template_id,
            "name": template.name,
            "description": template.description,
            "document_types": template.document_types,
            "estimated_duration": template.metadata.get(
                "estimated_duration_days", "Неизвестно"
            ),
            "complexity": template.metadata.get("complexity", "medium"),
            "category": template.metadata.get("category", "general"),
        }
        for template in templates
    ]
