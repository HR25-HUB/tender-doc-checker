"""Движок для обработки workflow документов."""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional


class WorkflowStatus(Enum):
    """Статусы workflow."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING = "waiting"


class StepType(Enum):
    """Типы шагов workflow."""

    VALIDATION = "validation"
    PROCESSING = "processing"
    APPROVAL = "approval"
    NOTIFICATION = "notification"
    INTEGRATION = "integration"
    ESCALATION = "escalation"
    COMPLETION = "completion"


class ActionType(Enum):
    """Типы автоматических действий."""

    SEND_EMAIL = "send_email"
    CREATE_TASK = "create_task"
    UPDATE_STATUS = "update_status"
    GENERATE_REPORT = "generate_report"
    CALL_API = "call_api"
    ESCALATE = "escalate"
    APPROVE = "approve"
    REJECT = "reject"


@dataclass
class WorkflowStep:
    """Шаг workflow."""

    step_id: str
    name: str
    step_type: StepType
    action_type: ActionType
    status: WorkflowStatus = WorkflowStatus.PENDING

    # Конфигурация шага
    timeout_minutes: int = 60
    retry_count: int = 3
    auto_execute: bool = True
    requires_approval: bool = False

    # Условия выполнения
    conditions: dict[str, Any] = field(default_factory=dict)
    parameters: dict[str, Any] = field(default_factory=dict)

    # Результаты выполнения
    result: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Связи с другими шагами
    depends_on: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)

    def is_ready_to_execute(self, completed_steps: list[str]) -> bool:
        """Проверяет, готов ли шаг к выполнению."""
        if self.status != WorkflowStatus.PENDING:
            return False

        # Проверяем зависимости
        for dependency in self.depends_on:
            if dependency not in completed_steps:
                return False

        return True

    def start_execution(self):
        """Начинает выполнение шага."""
        self.status = WorkflowStatus.IN_PROGRESS
        self.started_at = datetime.now()

    def complete_execution(self, result: dict[str, Any]):
        """Завершает выполнение шага."""
        self.status = WorkflowStatus.COMPLETED
        self.completed_at = datetime.now()
        self.result = result

    def fail_execution(self, error: str):
        """Отмечает шаг как неудачный."""
        self.status = WorkflowStatus.FAILED
        self.completed_at = datetime.now()
        self.error_message = error


@dataclass
class WorkflowInstance:
    """Экземпляр workflow."""

    instance_id: str
    workflow_name: str
    document_id: str
    document_type: str

    status: WorkflowStatus = WorkflowStatus.PENDING
    steps: list[WorkflowStep] = field(default_factory=list)

    # Метаданные
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Контекст выполнения
    context: dict[str, Any] = field(default_factory=dict)

    # Результаты
    final_result: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None

    def get_completed_steps(self) -> list[str]:
        """Возвращает список завершенных шагов."""
        return [
            step.step_id
            for step in self.steps
            if step.status == WorkflowStatus.COMPLETED
        ]

    def get_ready_steps(self) -> list[WorkflowStep]:
        """Возвращает шаги, готовые к выполнению."""
        completed = self.get_completed_steps()
        return [step for step in self.steps if step.is_ready_to_execute(completed)]

    def is_completed(self) -> bool:
        """Проверяет, завершен ли workflow."""
        return all(
            step.status in [WorkflowStatus.COMPLETED, WorkflowStatus.CANCELLED]
            for step in self.steps
        )

    def has_failed_steps(self) -> bool:
        """Проверяет, есть ли неудачные шаги."""
        return any(step.status == WorkflowStatus.FAILED for step in self.steps)


class WorkflowEngine:
    """Движок для выполнения workflow."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.active_workflows: dict[str, WorkflowInstance] = {}
        self.workflow_templates: dict[str, list[WorkflowStep]] = {}
        self.action_handlers: dict[ActionType, Callable] = {}

        # Регистрируем базовые обработчики действий
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Регистрирует базовые обработчики действий."""
        self.action_handlers[ActionType.UPDATE_STATUS] = self._handle_update_status
        self.action_handlers[ActionType.SEND_EMAIL] = self._handle_send_email
        self.action_handlers[ActionType.CREATE_TASK] = self._handle_create_task
        self.action_handlers[ActionType.GENERATE_REPORT] = self._handle_generate_report
        self.action_handlers[ActionType.ESCALATE] = self._handle_escalate
        self.action_handlers[ActionType.APPROVE] = self._handle_approve
        self.action_handlers[ActionType.REJECT] = self._handle_reject

    def register_workflow_template(self, name: str, steps: list[WorkflowStep]):
        """Регистрирует шаблон workflow."""
        self.workflow_templates[name] = steps
        self.logger.info(f"Зарегистрирован шаблон workflow: {name}")

    def register_action_handler(self, action_type: ActionType, handler: Callable):
        """Регистрирует обработчик действия."""
        self.action_handlers[action_type] = handler
        self.logger.info(f"Зарегистрирован обработчик для {action_type.value}")

    async def start_workflow(
        self,
        workflow_name: str,
        document_id: str,
        document_type: str,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """Запускает новый workflow."""

        if workflow_name not in self.workflow_templates:
            raise ValueError(f"Неизвестный шаблон workflow: {workflow_name}")

        # Создаем экземпляр workflow
        instance_id = f"{workflow_name}_{document_id}_{datetime.now().timestamp()}"

        # Копируем шаги из шаблона
        template_steps = self.workflow_templates[workflow_name]
        instance_steps = [
            WorkflowStep(
                step_id=f"{instance_id}_{step.step_id}",
                name=step.name,
                step_type=step.step_type,
                action_type=step.action_type,
                timeout_minutes=step.timeout_minutes,
                retry_count=step.retry_count,
                auto_execute=step.auto_execute,
                requires_approval=step.requires_approval,
                conditions=step.conditions.copy(),
                parameters=step.parameters.copy(),
                depends_on=[f"{instance_id}_{dep}" for dep in step.depends_on],
                next_steps=[
                    f"{instance_id}_{next_step}" for next_step in step.next_steps
                ],
            )
            for step in template_steps
        ]

        workflow_instance = WorkflowInstance(
            instance_id=instance_id,
            workflow_name=workflow_name,
            document_id=document_id,
            document_type=document_type,
            steps=instance_steps,
            context=context or {},
        )

        self.active_workflows[instance_id] = workflow_instance

        # Запускаем выполнение
        await self._execute_workflow(workflow_instance)

        return instance_id

    async def _execute_workflow(self, workflow: WorkflowInstance):
        """Выполняет workflow."""
        workflow.status = WorkflowStatus.IN_PROGRESS
        workflow.started_at = datetime.now()

        self.logger.info(
            f"Запуск workflow {workflow.workflow_name} для документа {workflow.document_id}"
        )

        try:
            while not workflow.is_completed() and not workflow.has_failed_steps():
                ready_steps = workflow.get_ready_steps()

                if not ready_steps:
                    # Нет готовых шагов - возможно, ждем внешнего события
                    workflow.status = WorkflowStatus.WAITING
                    break

                # Выполняем готовые шаги
                for step in ready_steps:
                    if step.auto_execute:
                        await self._execute_step(workflow, step)
                    else:
                        # Шаг требует ручного выполнения
                        step.status = WorkflowStatus.WAITING
                        self.logger.info(f"Шаг {step.name} ожидает ручного выполнения")

            # Проверяем финальный статус
            if workflow.is_completed():
                workflow.status = WorkflowStatus.COMPLETED
                workflow.completed_at = datetime.now()
                self.logger.info(f"Workflow {workflow.workflow_name} завершен успешно")
            elif workflow.has_failed_steps():
                workflow.status = WorkflowStatus.FAILED
                workflow.completed_at = datetime.now()
                self.logger.error(
                    f"Workflow {workflow.workflow_name} завершен с ошибками"
                )

        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.error_message = str(e)
            workflow.completed_at = datetime.now()
            self.logger.error(
                f"Ошибка выполнения workflow {workflow.workflow_name}: {e}"
            )

    async def _execute_step(self, workflow: WorkflowInstance, step: WorkflowStep):
        """Выполняет отдельный шаг workflow."""
        step.start_execution()

        try:
            # Проверяем условия выполнения
            if not self._check_step_conditions(workflow, step):
                step.status = WorkflowStatus.CANCELLED
                self.logger.info(f"Шаг {step.name} пропущен из-за условий")
                return

            # Получаем обработчик действия
            handler = self.action_handlers.get(step.action_type)
            if not handler:
                raise ValueError(
                    f"Нет обработчика для действия {step.action_type.value}"
                )

            # Выполняем действие
            result = await handler(workflow, step)
            step.complete_execution(result)

            self.logger.info(f"Шаг {step.name} выполнен успешно")

        except Exception as e:
            step.fail_execution(str(e))
            self.logger.error(f"Ошибка выполнения шага {step.name}: {e}")

    def _check_step_conditions(
        self, workflow: WorkflowInstance, step: WorkflowStep
    ) -> bool:
        """Проверяет условия выполнения шага."""
        if not step.conditions:
            return True

        # Простая проверка условий на основе контекста
        for condition_key, expected_value in step.conditions.items():
            actual_value = workflow.context.get(condition_key)
            if actual_value != expected_value:
                return False

        return True

    async def _handle_update_status(
        self, workflow: WorkflowInstance, step: WorkflowStep
    ) -> dict[str, Any]:
        """Обработчик обновления статуса."""
        new_status = step.parameters.get("status")
        workflow.context["document_status"] = new_status
        return {"status_updated": new_status}

    async def _handle_send_email(
        self, workflow: WorkflowInstance, step: WorkflowStep
    ) -> dict[str, Any]:
        """Обработчик отправки email."""
        # Здесь будет интеграция с emailer.py
        recipient = step.parameters.get("recipient")
        subject = step.parameters.get("subject")
        body = step.parameters.get("body")

        self.logger.info(f"Отправка email: {recipient}, {subject}")
        return {"email_sent": True, "recipient": recipient}

    async def _handle_create_task(
        self, workflow: WorkflowInstance, step: WorkflowStep
    ) -> dict[str, Any]:
        """Обработчик создания задачи."""
        # Здесь будет интеграция с bitrix_api.py
        title = step.parameters.get("title")
        description = step.parameters.get("description")

        self.logger.info(f"Создание задачи: {title}")
        return {"task_created": True, "title": title}

    async def _handle_generate_report(
        self, workflow: WorkflowInstance, step: WorkflowStep
    ) -> dict[str, Any]:
        """Обработчик генерации отчета."""
        # Здесь будет интеграция с report_generator.py
        report_type = step.parameters.get("report_type")

        self.logger.info(f"Генерация отчета: {report_type}")
        return {"report_generated": True, "type": report_type}

    async def _handle_escalate(
        self, workflow: WorkflowInstance, step: WorkflowStep
    ) -> dict[str, Any]:
        """Обработчик эскалации."""
        escalation_level = step.parameters.get("level", 1)
        reason = step.parameters.get("reason", "Превышение SLA")

        self.logger.warning(f"Эскалация уровня {escalation_level}: {reason}")
        return {"escalated": True, "level": escalation_level, "reason": reason}

    async def _handle_approve(
        self, workflow: WorkflowInstance, step: WorkflowStep
    ) -> dict[str, Any]:
        """Обработчик одобрения."""
        workflow.context["approval_status"] = "approved"
        workflow.context["approved_at"] = datetime.now().isoformat()

        return {"approved": True}

    async def _handle_reject(
        self, workflow: WorkflowInstance, step: WorkflowStep
    ) -> dict[str, Any]:
        """Обработчик отклонения."""
        reason = step.parameters.get("reason", "Не указана")
        workflow.context["approval_status"] = "rejected"
        workflow.context["rejection_reason"] = reason
        workflow.context["rejected_at"] = datetime.now().isoformat()

        return {"rejected": True, "reason": reason}

    def get_workflow_status(self, instance_id: str) -> Optional[dict[str, Any]]:
        """Возвращает статус workflow."""
        workflow = self.active_workflows.get(instance_id)
        if not workflow:
            return None

        return {
            "instance_id": workflow.instance_id,
            "workflow_name": workflow.workflow_name,
            "document_id": workflow.document_id,
            "status": workflow.status.value,
            "created_at": workflow.created_at.isoformat(),
            "started_at": workflow.started_at.isoformat()
            if workflow.started_at
            else None,
            "completed_at": workflow.completed_at.isoformat()
            if workflow.completed_at
            else None,
            "steps": [
                {
                    "step_id": step.step_id,
                    "name": step.name,
                    "status": step.status.value,
                    "started_at": step.started_at.isoformat()
                    if step.started_at
                    else None,
                    "completed_at": step.completed_at.isoformat()
                    if step.completed_at
                    else None,
                    "error_message": step.error_message,
                }
                for step in workflow.steps
            ],
            "context": workflow.context,
            "error_message": workflow.error_message,
        }

    async def resume_workflow(self, instance_id: str):
        """Возобновляет выполнение workflow."""
        workflow = self.active_workflows.get(instance_id)
        if not workflow:
            raise ValueError(f"Workflow {instance_id} не найден")

        if workflow.status == WorkflowStatus.WAITING:
            await self._execute_workflow(workflow)

    async def cancel_workflow(
        self, instance_id: str, reason: str = "Отменено пользователем"
    ):
        """Отменяет выполнение workflow."""
        workflow = self.active_workflows.get(instance_id)
        if not workflow:
            raise ValueError(f"Workflow {instance_id} не найден")

        workflow.status = WorkflowStatus.CANCELLED
        workflow.error_message = reason
        workflow.completed_at = datetime.now()

        # Отменяем все незавершенные шаги
        for step in workflow.steps:
            if step.status in [
                WorkflowStatus.PENDING,
                WorkflowStatus.IN_PROGRESS,
                WorkflowStatus.WAITING,
            ]:
                step.status = WorkflowStatus.CANCELLED

        self.logger.info(f"Workflow {instance_id} отменен: {reason}")

    def cleanup_completed_workflows(self, older_than_hours: int = 24):
        """Очищает завершенные workflow старше указанного времени."""
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)

        to_remove = []
        for instance_id, workflow in self.active_workflows.items():
            if (
                workflow.status
                in [
                    WorkflowStatus.COMPLETED,
                    WorkflowStatus.FAILED,
                    WorkflowStatus.CANCELLED,
                ]
                and workflow.completed_at
                and workflow.completed_at < cutoff_time
            ):
                to_remove.append(instance_id)

        for instance_id in to_remove:
            del self.active_workflows[instance_id]

        self.logger.info(f"Очищено {len(to_remove)} завершенных workflow")


# Глобальный экземпляр движка
workflow_engine = WorkflowEngine()
