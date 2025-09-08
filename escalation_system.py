"""Система эскалации для обработки просроченных задач и превышения SLA."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from auto_actions import AutoActionExecutor
from src.models import WorkflowInstanceModel


class EscalationLevel(Enum):
    """Уровни эскалации."""

    WARNING = "warning"  # Предупреждение
    MINOR = "minor"  # Незначительная эскалация
    MAJOR = "major"  # Серьезная эскалация
    CRITICAL = "critical"  # Критическая эскалация
    EMERGENCY = "emergency"  # Чрезвычайная ситуация


class EscalationTrigger(Enum):
    """Триггеры эскалации."""

    SLA_EXCEEDED = "sla_exceeded"  # Превышение SLA
    TASK_OVERDUE = "task_overdue"  # Просроченная задача
    NO_RESPONSE = "no_response"  # Отсутствие ответа
    QUALITY_ISSUE = "quality_issue"  # Проблемы с качеством
    SYSTEM_ERROR = "system_error"  # Системная ошибка
    MANUAL_ESCALATION = "manual_escalation"  # Ручная эскалация


@dataclass
class EscalationRule:
    """Правило эскалации."""

    rule_id: str
    name: str
    description: str
    trigger: EscalationTrigger
    level: EscalationLevel
    conditions: dict[str, Any]
    delay_hours: float  # Задержка перед эскалацией
    escalation_actions: list[dict[str, Any]]
    target_roles: list[str]
    is_active: bool = True
    priority: int = 1  # Приоритет правила (1 - высший)
    max_escalations: int = 3  # Максимальное количество эскалаций
    cooldown_hours: float = 24  # Период охлаждения между эскалациями


@dataclass
class EscalationEvent:
    """Событие эскалации."""

    event_id: str
    workflow_instance_id: str
    step_id: str
    rule_id: str
    trigger: EscalationTrigger
    level: EscalationLevel
    created_at: datetime
    escalated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    escalation_count: int = 0
    last_escalation_at: Optional[datetime] = None
    status: str = "pending"  # pending, escalated, resolved, cancelled
    metadata: dict[str, Any] = None
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None


class EscalationSystem:
    """Система управления эскалациями."""

    def __init__(self, auto_action_executor: AutoActionExecutor):
        self.auto_action_executor = auto_action_executor
        self.escalation_rules: dict[str, EscalationRule] = {}
        self.active_escalations: dict[str, EscalationEvent] = {}
        self.escalation_history: list[EscalationEvent] = []
        self.logger = logging.getLogger(__name__)

        # Инициализация стандартных правил эскалации
        self._initialize_default_rules()

        # Запуск фонового процесса мониторинга
        self._monitoring_active = False

    def _initialize_default_rules(self):
        """Инициализирует стандартные правила эскалации."""

        # Правило для превышения SLA на 25%
        self.escalation_rules["sla_warning"] = EscalationRule(
            rule_id="sla_warning",
            name="Предупреждение о приближении к SLA",
            description="Предупреждение когда осталось 25% времени до превышения SLA",
            trigger=EscalationTrigger.SLA_EXCEEDED,
            level=EscalationLevel.WARNING,
            conditions={"sla_usage_percent": 75},
            delay_hours=0,
            escalation_actions=[
                {
                    "type": "send_email",
                    "parameters": {
                        "template": "sla_warning",
                        "subject": "Предупреждение: приближение к превышению SLA",
                        "urgency": "medium",
                    },
                },
                {
                    "type": "create_task",
                    "parameters": {
                        "title": "Внимание: SLA скоро будет превышен",
                        "description": "Требуется ускорить обработку задачи",
                        "priority": "medium",
                    },
                },
            ],
            target_roles=["task_assignee", "team_lead"],
            priority=3,
        )

        # Правило для превышения SLA
        self.escalation_rules["sla_exceeded"] = EscalationRule(
            rule_id="sla_exceeded",
            name="Превышение SLA",
            description="Эскалация при превышении установленного SLA",
            trigger=EscalationTrigger.SLA_EXCEEDED,
            level=EscalationLevel.MINOR,
            conditions={"sla_usage_percent": 100},
            delay_hours=0,
            escalation_actions=[
                {
                    "type": "send_email",
                    "parameters": {
                        "template": "sla_exceeded",
                        "subject": "ВНИМАНИЕ: SLA превышен",
                        "urgency": "high",
                    },
                },
                {
                    "type": "create_task",
                    "parameters": {
                        "title": "СРОЧНО: SLA превышен",
                        "description": "Требуется немедленное вмешательство руководства",
                        "priority": "high",
                    },
                },
            ],
            target_roles=["team_lead", "department_manager"],
            priority=2,
        )

        # Правило для критического превышения SLA
        self.escalation_rules["sla_critical"] = EscalationRule(
            rule_id="sla_critical",
            name="Критическое превышение SLA",
            description="Критическая эскалация при превышении SLA более чем в 2 раза",
            trigger=EscalationTrigger.SLA_EXCEEDED,
            level=EscalationLevel.CRITICAL,
            conditions={"sla_usage_percent": 200},
            delay_hours=0,
            escalation_actions=[
                {
                    "type": "send_email",
                    "parameters": {
                        "template": "sla_critical",
                        "subject": "КРИТИЧНО: SLA превышен в 2 раза",
                        "urgency": "critical",
                    },
                },
                {
                    "type": "create_task",
                    "parameters": {
                        "title": "КРИТИЧНО: Серьезное превышение SLA",
                        "description": "Требуется экстренное вмешательство высшего руководства",
                        "priority": "critical",
                    },
                },
                {
                    "type": "schedule_meeting",
                    "parameters": {
                        "meeting_type": "emergency",
                        "subject": "Экстренное совещание по превышению SLA",
                        "duration_minutes": 30,
                    },
                },
            ],
            target_roles=["department_manager", "director"],
            priority=1,
        )

        # Правило для просроченных задач
        self.escalation_rules["task_overdue"] = EscalationRule(
            rule_id="task_overdue",
            name="Просроченная задача",
            description="Эскалация для просроченных задач",
            trigger=EscalationTrigger.TASK_OVERDUE,
            level=EscalationLevel.MINOR,
            conditions={"overdue_hours": 24},
            delay_hours=2,
            escalation_actions=[
                {
                    "type": "send_email",
                    "parameters": {
                        "template": "task_overdue",
                        "subject": "Задача просрочена",
                        "urgency": "medium",
                    },
                },
                {
                    "type": "reassign_task",
                    "parameters": {
                        "reason": "Задача просрочена, требуется переназначение"
                    },
                },
            ],
            target_roles=["team_lead"],
            priority=2,
        )

        # Правило для отсутствия ответа
        self.escalation_rules["no_response"] = EscalationRule(
            rule_id="no_response",
            name="Отсутствие ответа",
            description="Эскалация при отсутствии ответа в течение установленного времени",
            trigger=EscalationTrigger.NO_RESPONSE,
            level=EscalationLevel.MINOR,
            conditions={"no_response_hours": 48},
            delay_hours=4,
            escalation_actions=[
                {
                    "type": "send_email",
                    "parameters": {
                        "template": "no_response",
                        "subject": "Требуется ответ по задаче",
                        "urgency": "medium",
                    },
                },
                {
                    "type": "create_task",
                    "parameters": {
                        "title": "Отсутствует ответ по задаче",
                        "description": "Требуется связаться с ответственным",
                        "priority": "medium",
                    },
                },
            ],
            target_roles=["team_lead", "project_manager"],
            priority=3,
        )

        # Правило для системных ошибок
        self.escalation_rules["system_error"] = EscalationRule(
            rule_id="system_error",
            name="Системная ошибка",
            description="Эскалация при возникновении системных ошибок",
            trigger=EscalationTrigger.SYSTEM_ERROR,
            level=EscalationLevel.MAJOR,
            conditions={"error_count": 3},
            delay_hours=0.5,
            escalation_actions=[
                {
                    "type": "send_email",
                    "parameters": {
                        "template": "system_error",
                        "subject": "Системная ошибка в workflow",
                        "urgency": "high",
                    },
                },
                {
                    "type": "create_task",
                    "parameters": {
                        "title": "Системная ошибка требует вмешательства",
                        "description": "Обнаружена повторяющаяся системная ошибка",
                        "priority": "high",
                    },
                },
            ],
            target_roles=["system_admin", "technical_lead"],
            priority=1,
        )

    def add_escalation_rule(self, rule: EscalationRule):
        """Добавляет новое правило эскалации."""
        self.escalation_rules[rule.rule_id] = rule
        self.logger.info(f"Добавлено правило эскалации: {rule.name}")

    def remove_escalation_rule(self, rule_id: str):
        """Удаляет правило эскалации."""
        if rule_id in self.escalation_rules:
            del self.escalation_rules[rule_id]
            self.logger.info(f"Удалено правило эскалации: {rule_id}")

    def activate_rule(self, rule_id: str):
        """Активирует правило эскалации."""
        if rule_id in self.escalation_rules:
            self.escalation_rules[rule_id].is_active = True
            self.logger.info(f"Активировано правило эскалации: {rule_id}")

    def deactivate_rule(self, rule_id: str):
        """Деактивирует правило эскалации."""
        if rule_id in self.escalation_rules:
            self.escalation_rules[rule_id].is_active = False
            self.logger.info(f"Деактивировано правило эскалации: {rule_id}")

    def check_escalation_conditions(
        self, workflow_instance: WorkflowInstanceModel, current_step_id: str
    ) -> list[EscalationRule]:
        """Проверяет условия эскалации для workflow instance."""
        triggered_rules = []
        current_time = datetime.now()

        for rule in self.escalation_rules.values():
            if not rule.is_active:
                continue

            # Проверяем, не было ли недавней эскалации по этому правилу
            if self._is_in_cooldown(
                workflow_instance.instance_id, rule.rule_id, current_time
            ):
                continue

            # Проверяем условия эскалации
            if self._evaluate_escalation_conditions(
                workflow_instance, current_step_id, rule, current_time
            ):
                triggered_rules.append(rule)

        # Сортируем по приоритету
        triggered_rules.sort(key=lambda r: r.priority)
        return triggered_rules

    def _is_in_cooldown(
        self, workflow_instance_id: str, rule_id: str, current_time: datetime
    ) -> bool:
        """Проверяет, находится ли правило в периоде охлаждения."""
        for escalation in self.escalation_history:
            if (
                escalation.workflow_instance_id == workflow_instance_id
                and escalation.rule_id == rule_id
                and escalation.last_escalation_at
            ):
                rule = self.escalation_rules.get(rule_id)
                if rule:
                    cooldown_end = escalation.last_escalation_at + timedelta(
                        hours=rule.cooldown_hours
                    )
                    if current_time < cooldown_end:
                        return True
        return False

    def _evaluate_escalation_conditions(
        self,
        workflow_instance: WorkflowInstanceModel,
        current_step_id: str,
        rule: EscalationRule,
        current_time: datetime,
    ) -> bool:
        """Оценивает условия эскалации для конкретного правила."""

        if rule.trigger == EscalationTrigger.SLA_EXCEEDED:
            return self._check_sla_conditions(
                workflow_instance, current_step_id, rule, current_time
            )

        elif rule.trigger == EscalationTrigger.TASK_OVERDUE:
            return self._check_overdue_conditions(
                workflow_instance, current_step_id, rule, current_time
            )

        elif rule.trigger == EscalationTrigger.NO_RESPONSE:
            return self._check_no_response_conditions(
                workflow_instance, current_step_id, rule, current_time
            )

        elif rule.trigger == EscalationTrigger.SYSTEM_ERROR:
            return self._check_system_error_conditions(
                workflow_instance, current_step_id, rule
            )

        return False

    def _check_sla_conditions(
        self,
        workflow_instance: WorkflowInstanceModel,
        current_step_id: str,
        rule: EscalationRule,
        current_time: datetime,
    ) -> bool:
        """Проверяет условия превышения SLA."""

        # Находим текущий шаг
        current_step = None
        for step in workflow_instance.steps:
            if step.step_id == current_step_id:
                current_step = step
                break

        if not current_step or not current_step.sla_hours:
            return False

        # Вычисляем время выполнения
        step_start_time = workflow_instance.started_at
        if workflow_instance.execution_log:
            for log_entry in workflow_instance.execution_log:
                if (
                    log_entry.step_id == current_step_id
                    and log_entry.action == "step_started"
                ):
                    step_start_time = log_entry.timestamp
                    break

        elapsed_hours = (current_time - step_start_time).total_seconds() / 3600
        sla_usage_percent = (elapsed_hours / current_step.sla_hours) * 100

        required_percent = rule.conditions.get("sla_usage_percent", 100)
        return sla_usage_percent >= required_percent

    def _check_overdue_conditions(
        self,
        workflow_instance: WorkflowInstanceModel,
        current_step_id: str,
        rule: EscalationRule,
        current_time: datetime,
    ) -> bool:
        """Проверяет условия просроченной задачи."""

        # Проверяем, есть ли просроченные задачи
        if workflow_instance.metadata and "overdue_tasks" in workflow_instance.metadata:
            overdue_hours = rule.conditions.get("overdue_hours", 24)

            for task in workflow_instance.metadata["overdue_tasks"]:
                if task.get("overdue_duration_hours", 0) >= overdue_hours:
                    return True

        return False

    def _check_no_response_conditions(
        self,
        workflow_instance: WorkflowInstanceModel,
        current_step_id: str,
        rule: EscalationRule,
        current_time: datetime,
    ) -> bool:
        """Проверяет условия отсутствия ответа."""

        # Проверяем время последней активности
        last_activity = workflow_instance.updated_at
        if workflow_instance.execution_log:
            for log_entry in reversed(workflow_instance.execution_log):
                if log_entry.step_id == current_step_id:
                    last_activity = log_entry.timestamp
                    break

        hours_since_activity = (current_time - last_activity).total_seconds() / 3600
        required_hours = rule.conditions.get("no_response_hours", 48)

        return hours_since_activity >= required_hours

    def _check_system_error_conditions(
        self,
        workflow_instance: WorkflowInstanceModel,
        current_step_id: str,
        rule: EscalationRule,
    ) -> bool:
        """Проверяет условия системных ошибок."""

        if not workflow_instance.execution_log:
            return False

        # Подсчитываем количество ошибок
        error_count = 0
        for log_entry in workflow_instance.execution_log:
            if (
                log_entry.step_id == current_step_id
                and log_entry.action == "error"
                and log_entry.details
                and "system_error" in log_entry.details
            ):
                error_count += 1

        required_count = rule.conditions.get("error_count", 3)
        return error_count >= required_count

    async def trigger_escalation(
        self,
        workflow_instance: WorkflowInstanceModel,
        current_step_id: str,
        rule: EscalationRule,
        manual_trigger: bool = False,
    ) -> EscalationEvent:
        """Запускает процесс эскалации."""

        current_time = datetime.now()

        # Создаем событие эскалации
        escalation_event = EscalationEvent(
            event_id=f"esc_{workflow_instance.instance_id}_{rule.rule_id}_{int(current_time.timestamp())}",
            workflow_instance_id=workflow_instance.instance_id,
            step_id=current_step_id,
            rule_id=rule.rule_id,
            trigger=rule.trigger,
            level=rule.level,
            created_at=current_time,
            metadata={
                "workflow_name": workflow_instance.workflow_name,
                "document_id": workflow_instance.document_id,
                "manual_trigger": manual_trigger,
            },
        )

        # Проверяем максимальное количество эскалаций
        existing_escalations = self._count_existing_escalations(
            workflow_instance.instance_id, rule.rule_id
        )
        if existing_escalations >= rule.max_escalations:
            self.logger.warning(
                f"Достигнуто максимальное количество эскалаций для правила {rule.rule_id}"
            )
            escalation_event.status = "cancelled"
            escalation_event.resolution_notes = (
                "Достигнуто максимальное количество эскалаций"
            )
            return escalation_event

        # Добавляем в активные эскалации
        self.active_escalations[escalation_event.event_id] = escalation_event

        # Планируем выполнение эскалации с задержкой
        if rule.delay_hours > 0 and not manual_trigger:
            await asyncio.sleep(rule.delay_hours * 3600)

        # Выполняем действия эскалации
        await self._execute_escalation_actions(
            escalation_event, rule, workflow_instance
        )

        # Обновляем статус
        escalation_event.escalated_at = datetime.now()
        escalation_event.status = "escalated"
        escalation_event.escalation_count = existing_escalations + 1
        escalation_event.last_escalation_at = escalation_event.escalated_at

        # Добавляем в историю
        self.escalation_history.append(escalation_event)

        self.logger.info(
            f"Выполнена эскалация {escalation_event.event_id} по правилу {rule.name}"
        )

        return escalation_event

    def _count_existing_escalations(
        self, workflow_instance_id: str, rule_id: str
    ) -> int:
        """Подсчитывает количество существующих эскалаций."""
        count = 0
        for escalation in self.escalation_history:
            if (
                escalation.workflow_instance_id == workflow_instance_id
                and escalation.rule_id == rule_id
                and escalation.status == "escalated"
            ):
                count += 1
        return count

    async def _execute_escalation_actions(
        self,
        escalation_event: EscalationEvent,
        rule: EscalationRule,
        workflow_instance: WorkflowInstanceModel,
    ):
        """Выполняет действия эскалации."""

        for action in rule.escalation_actions:
            try:
                # Подготавливаем контекст для действия
                action_context = {
                    "escalation_event": escalation_event,
                    "workflow_instance": workflow_instance,
                    "rule": rule,
                    "target_roles": rule.target_roles,
                }

                # Выполняем действие через AutoActionExecutor
                await self.auto_action_executor.execute_action(
                    action["type"], action["parameters"], action_context
                )

                self.logger.info(f"Выполнено действие эскалации: {action['type']}")

            except Exception as e:
                self.logger.error(
                    f"Ошибка при выполнении действия эскалации {action['type']}: {str(e)}"
                )

    def resolve_escalation(
        self, event_id: str, resolution_notes: str = None, resolved_by: str = None
    ):
        """Разрешает эскалацию."""

        if event_id in self.active_escalations:
            escalation = self.active_escalations[event_id]
            escalation.resolved_at = datetime.now()
            escalation.status = "resolved"
            escalation.resolution_notes = resolution_notes
            escalation.assigned_to = resolved_by

            # Удаляем из активных
            del self.active_escalations[event_id]

            self.logger.info(f"Разрешена эскалация {event_id}")

    def cancel_escalation(self, event_id: str, cancellation_reason: str = None):
        """Отменяет эскалацию."""

        if event_id in self.active_escalations:
            escalation = self.active_escalations[event_id]
            escalation.status = "cancelled"
            escalation.resolution_notes = cancellation_reason

            # Удаляем из активных
            del self.active_escalations[event_id]

            self.logger.info(f"Отменена эскалация {event_id}")

    async def start_monitoring(self, check_interval_minutes: int = 15):
        """Запускает фоновый мониторинг эскалаций."""

        self._monitoring_active = True
        self.logger.info("Запущен мониторинг эскалаций")

        while self._monitoring_active:
            try:
                await self._check_all_workflows()
                await asyncio.sleep(check_interval_minutes * 60)
            except Exception as e:
                self.logger.error(f"Ошибка в мониторинге эскалаций: {str(e)}")
                await asyncio.sleep(60)  # Короткая пауза при ошибке

    def stop_monitoring(self):
        """Останавливает фоновый мониторинг."""
        self._monitoring_active = False
        self.logger.info("Остановлен мониторинг эскалаций")

    async def _check_all_workflows(self):
        """Проверяет все активные workflow на предмет эскалации."""
        # Здесь должна быть логика получения всех активных workflow
        # Пока оставляем заглушку
        pass

    def get_escalation_statistics(self) -> dict[str, Any]:
        """Получает статистику эскалаций."""

        total_escalations = len(self.escalation_history)
        active_escalations = len(self.active_escalations)

        # Статистика по уровням
        level_stats = {}
        for escalation in self.escalation_history:
            level = escalation.level.value
            level_stats[level] = level_stats.get(level, 0) + 1

        # Статистика по триггерам
        trigger_stats = {}
        for escalation in self.escalation_history:
            trigger = escalation.trigger.value
            trigger_stats[trigger] = trigger_stats.get(trigger, 0) + 1

        # Статистика по правилам
        rule_stats = {}
        for escalation in self.escalation_history:
            rule_id = escalation.rule_id
            rule_stats[rule_id] = rule_stats.get(rule_id, 0) + 1

        return {
            "total_escalations": total_escalations,
            "active_escalations": active_escalations,
            "level_statistics": level_stats,
            "trigger_statistics": trigger_stats,
            "rule_statistics": rule_stats,
            "average_resolution_time_hours": self._calculate_average_resolution_time(),
        }

    def _calculate_average_resolution_time(self) -> float:
        """Вычисляет среднее время разрешения эскалаций."""

        resolved_escalations = [
            e
            for e in self.escalation_history
            if e.status == "resolved" and e.resolved_at and e.escalated_at
        ]

        if not resolved_escalations:
            return 0.0

        total_hours = 0
        for escalation in resolved_escalations:
            resolution_time = escalation.resolved_at - escalation.escalated_at
            total_hours += resolution_time.total_seconds() / 3600

        return total_hours / len(resolved_escalations)

    def get_active_escalations(self) -> list[EscalationEvent]:
        """Получает список активных эскалаций."""
        return list(self.active_escalations.values())

    def get_escalation_history(self, limit: int = 100) -> list[EscalationEvent]:
        """Получает историю эскалаций."""
        return sorted(
            self.escalation_history, key=lambda e: e.created_at, reverse=True
        )[:limit]

    def get_escalations_for_workflow(
        self, workflow_instance_id: str
    ) -> list[EscalationEvent]:
        """Получает эскалации для конкретного workflow."""
        return [
            e
            for e in self.escalation_history
            if e.workflow_instance_id == workflow_instance_id
        ]


# Функции для интеграции с workflow_engine
def create_escalation_system(
    auto_action_executor: AutoActionExecutor
) -> EscalationSystem:
    """Создает экземпляр системы эскалации."""
    return EscalationSystem(auto_action_executor)


async def check_and_escalate(
    escalation_system: EscalationSystem,
    workflow_instance: WorkflowInstanceModel,
    current_step_id: str,
) -> list[EscalationEvent]:
    """Проверяет условия и запускает эскалацию при необходимости."""

    triggered_rules = escalation_system.check_escalation_conditions(
        workflow_instance, current_step_id
    )
    escalation_events = []

    for rule in triggered_rules:
        try:
            event = await escalation_system.trigger_escalation(
                workflow_instance, current_step_id, rule
            )
            escalation_events.append(event)
        except Exception as e:
            logging.error(
                f"Ошибка при запуске эскалации по правилу {rule.rule_id}: {str(e)}"
            )

    return escalation_events


def get_escalation_dashboard_data(
    escalation_system: EscalationSystem
) -> dict[str, Any]:
    """Получает данные для дашборда эскалаций."""

    stats = escalation_system.get_escalation_statistics()
    active_escalations = escalation_system.get_active_escalations()
    recent_history = escalation_system.get_escalation_history(limit=20)

    return {
        "statistics": stats,
        "active_escalations": [
            {
                "event_id": e.event_id,
                "workflow_instance_id": e.workflow_instance_id,
                "level": e.level.value,
                "trigger": e.trigger.value,
                "created_at": e.created_at.isoformat(),
                "escalation_count": e.escalation_count,
            }
            for e in active_escalations
        ],
        "recent_history": [
            {
                "event_id": e.event_id,
                "workflow_instance_id": e.workflow_instance_id,
                "level": e.level.value,
                "trigger": e.trigger.value,
                "status": e.status,
                "created_at": e.created_at.isoformat(),
                "resolved_at": e.resolved_at.isoformat() if e.resolved_at else None,
            }
            for e in recent_history
        ],
    }
