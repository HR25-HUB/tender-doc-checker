"""Интеграция с системой электронного документооборота для автоматической отправки документов на подпись."""

import base64
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

import aiohttp

from src.models import WorkflowInstanceModel


class DocumentType(Enum):
    """Типы документов для ЭДО."""

    CONTRACT = "contract"  # Договор
    COMMERCIAL_PROPOSAL = "commercial_proposal"  # Коммерческое предложение
    SPECIFICATION = "specification"  # Спецификация
    INVOICE = "invoice"  # Счет
    ACT = "act"  # Акт
    WAYBILL = "waybill"  # Накладная
    CERTIFICATE = "certificate"  # Сертификат
    OTHER = "other"  # Прочие документы


class SignatureType(Enum):
    """Типы подписи."""

    SIMPLE = "simple"  # Простая электронная подпись
    ENHANCED = "enhanced"  # Усиленная неквалифицированная подпись
    QUALIFIED = "qualified"  # Усиленная квалифицированная подпись


class DocumentStatus(Enum):
    """Статусы документа в ЭДО."""

    DRAFT = "draft"  # Черновик
    SENT = "sent"  # Отправлен
    DELIVERED = "delivered"  # Доставлен
    VIEWED = "viewed"  # Просмотрен
    SIGNED = "signed"  # Подписан
    REJECTED = "rejected"  # Отклонен
    EXPIRED = "expired"  # Истек срок
    CANCELLED = "cancelled"  # Отменен


class EDOProvider(Enum):
    """Провайдеры ЭДО."""

    DIADOC = "diadoc"  # Диадок
    SBIS = "sbis"  # СБИС
    KONTUR = "kontur"  # Контур
    TAXCOM = "taxcom"  # Такском
    TENSOR = "tensor"  # Тензор
    CUSTOM = "custom"  # Кастомный провайдер


@dataclass
class SignerInfo:
    """Информация о подписанте."""

    signer_id: str
    name: str
    email: str
    phone: Optional[str] = None
    position: Optional[str] = None
    organization: Optional[str] = None
    certificate_thumbprint: Optional[str] = None
    signature_type: SignatureType = SignatureType.ENHANCED
    is_required: bool = True
    signing_order: int = 1


@dataclass
class DocumentPackage:
    """Пакет документов для отправки в ЭДО."""

    package_id: str
    title: str
    description: Optional[str] = None
    document_type: DocumentType = DocumentType.OTHER
    files: list[dict[str, Any]] = None
    signers: list[SignerInfo] = None
    deadline: Optional[datetime] = None
    priority: str = "normal"  # low, normal, high, urgent
    metadata: dict[str, Any] = None
    workflow_instance_id: Optional[str] = None
    created_at: datetime = None

    def __post_init__(self):
        if self.files is None:
            self.files = []
        if self.signers is None:
            self.signers = []
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class DocumentFlowResult:
    """Результат операции с ЭДО."""

    success: bool
    package_id: str
    edo_document_id: Optional[str] = None
    status: Optional[DocumentStatus] = None
    message: Optional[str] = None
    error_code: Optional[str] = None
    tracking_url: Optional[str] = None
    signatures: list[dict[str, Any]] = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.signatures is None:
            self.signatures = []
        if self.metadata is None:
            self.metadata = {}


class BaseEDOProvider:
    """Базовый класс для провайдеров ЭДО."""

    def __init__(self, provider_config: dict[str, Any]):
        self.config = provider_config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.session: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        """Инициализация провайдера."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30), headers=self._get_default_headers()
        )

    async def cleanup(self):
        """Очистка ресурсов."""
        if self.session:
            await self.session.close()

    def _get_default_headers(self) -> dict[str, str]:
        """Получает заголовки по умолчанию."""
        return {
            "Content-Type": "application/json",
            "User-Agent": "TenderDocChecker/1.0",
        }

    async def send_document_package(
        self, package: DocumentPackage
    ) -> DocumentFlowResult:
        """Отправляет пакет документов в ЭДО."""
        raise NotImplementedError

    async def get_document_status(self, edo_document_id: str) -> DocumentFlowResult:
        """Получает статус документа в ЭДО."""
        raise NotImplementedError

    async def download_signed_document(self, edo_document_id: str) -> bytes:
        """Скачивает подписанный документ."""
        raise NotImplementedError

    async def cancel_document(
        self, edo_document_id: str, reason: str
    ) -> DocumentFlowResult:
        """Отменяет документ в ЭДО."""
        raise NotImplementedError


class DiadocProvider(BaseEDOProvider):
    """Провайдер для интеграции с Диадок."""

    def __init__(self, provider_config: dict[str, Any]):
        super().__init__(provider_config)
        self.api_url = provider_config.get("api_url", "https://diadoc-api.kontur.ru")
        self.api_key = provider_config.get("api_key")
        self.organization_id = provider_config.get("organization_id")

    def _get_default_headers(self) -> dict[str, str]:
        headers = super()._get_default_headers()
        if self.api_key:
            headers["Authorization"] = f"DiadocAuth ddauth_api_client_id={self.api_key}"
        return headers

    async def send_document_package(
        self, package: DocumentPackage
    ) -> DocumentFlowResult:
        """Отправляет пакет документов в Диадок."""
        try:
            # Подготавливаем данные для отправки
            document_data = {
                "MessageFromBoxId": self.organization_id,
                "MessageToBoxId": package.metadata.get("recipient_box_id"),
                "Documents": [],
            }

            # Добавляем файлы
            for file_info in package.files:
                doc_data = {
                    "TypeNamedId": self._map_document_type(package.document_type),
                    "Function": "Invoice",
                    "Version": "5.02",
                    "Content": base64.b64encode(file_info["content"]).decode("utf-8"),
                    "FileName": file_info["filename"],
                }
                document_data["Documents"].append(doc_data)

            # Отправляем запрос
            async with self.session.post(
                f"{self.api_url}/V3/PostMessage", json=document_data
            ) as response:
                if response.status == 200:
                    result_data = await response.json()
                    return DocumentFlowResult(
                        success=True,
                        package_id=package.package_id,
                        edo_document_id=result_data.get("MessageId"),
                        status=DocumentStatus.SENT,
                        message="Документ успешно отправлен в Диадок",
                        tracking_url=f"{self.api_url}/Messages/{result_data.get('MessageId')}",
                    )
                else:
                    error_text = await response.text()
                    return DocumentFlowResult(
                        success=False,
                        package_id=package.package_id,
                        message=f"Ошибка отправки в Диадок: {error_text}",
                        error_code=str(response.status),
                    )

        except Exception as e:
            self.logger.error(f"Ошибка при отправке в Диадок: {str(e)}")
            return DocumentFlowResult(
                success=False,
                package_id=package.package_id,
                message=f"Ошибка при отправке в Диадок: {str(e)}",
                error_code="INTERNAL_ERROR",
            )

    def _map_document_type(self, doc_type: DocumentType) -> str:
        """Маппинг типов документов для Диадок."""
        mapping = {
            DocumentType.CONTRACT: "Contract",
            DocumentType.INVOICE: "Invoice",
            DocumentType.ACT: "Act",
            DocumentType.WAYBILL: "Waybill",
            DocumentType.OTHER: "Nonformalized",
        }
        return mapping.get(doc_type, "Nonformalized")

    async def get_document_status(self, edo_document_id: str) -> DocumentFlowResult:
        """Получает статус документа в Диадок."""
        try:
            async with self.session.get(
                f"{self.api_url}/V3/GetMessage",
                params={"messageId": edo_document_id, "boxId": self.organization_id},
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    status = self._map_diadoc_status(data.get("MessageStatus"))

                    return DocumentFlowResult(
                        success=True,
                        package_id="",
                        edo_document_id=edo_document_id,
                        status=status,
                        message=f"Статус документа: {status.value}",
                    )
                else:
                    return DocumentFlowResult(
                        success=False,
                        package_id="",
                        edo_document_id=edo_document_id,
                        message="Ошибка получения статуса",
                        error_code=str(response.status),
                    )

        except Exception as e:
            return DocumentFlowResult(
                success=False,
                package_id="",
                edo_document_id=edo_document_id,
                message=f"Ошибка: {str(e)}",
                error_code="INTERNAL_ERROR",
            )

    def _map_diadoc_status(self, diadoc_status: str) -> DocumentStatus:
        """Маппинг статусов Диадок."""
        mapping = {
            "Draft": DocumentStatus.DRAFT,
            "Sent": DocumentStatus.SENT,
            "Delivered": DocumentStatus.DELIVERED,
            "Read": DocumentStatus.VIEWED,
            "Signed": DocumentStatus.SIGNED,
            "Rejected": DocumentStatus.REJECTED,
        }
        return mapping.get(diadoc_status, DocumentStatus.SENT)


class SBISProvider(BaseEDOProvider):
    """Провайдер для интеграции с СБИС."""

    def __init__(self, provider_config: dict[str, Any]):
        super().__init__(provider_config)
        self.api_url = provider_config.get("api_url", "https://api.sbis.ru")
        self.login = provider_config.get("login")
        self.password = provider_config.get("password")
        self.session_id = None

    async def initialize(self):
        """Инициализация с аутентификацией."""
        await super().initialize()
        await self._authenticate()

    async def _authenticate(self):
        """Аутентификация в СБИС."""
        auth_data = {
            "jsonrpc": "2.0",
            "method": "СБИС.Аутентифицировать",
            "params": {"Логин": self.login, "Пароль": self.password},
            "id": 1,
        }

        async with self.session.post(
            f"{self.api_url}/auth/service/", json=auth_data
        ) as response:
            if response.status == 200:
                result = await response.json()
                self.session_id = result.get("result")

    async def send_document_package(
        self, package: DocumentPackage
    ) -> DocumentFlowResult:
        """Отправляет пакет документов в СБИС."""
        # Реализация для СБИС
        return DocumentFlowResult(
            success=True, package_id=package.package_id, message="Заглушка для СБИС"
        )


class CustomEDOProvider(BaseEDOProvider):
    """Кастомный провайдер ЭДО для специфических интеграций."""

    async def send_document_package(
        self, package: DocumentPackage
    ) -> DocumentFlowResult:
        """Отправляет пакет документов через кастомный API."""
        # Реализация кастомной логики
        return DocumentFlowResult(
            success=True, package_id=package.package_id, message="Кастомная интеграция"
        )


class DocumentFlowIntegration:
    """Основной класс для интеграции с системами ЭДО."""

    def __init__(self):
        self.providers: dict[EDOProvider, BaseEDOProvider] = {}
        self.default_provider: Optional[EDOProvider] = None
        self.document_templates: dict[str, dict[str, Any]] = {}
        self.signing_workflows: dict[str, list[SignerInfo]] = {}
        self.logger = logging.getLogger(__name__)

        # Инициализация шаблонов документов
        self._initialize_document_templates()

        # Инициализация workflow подписания
        self._initialize_signing_workflows()

    def _initialize_document_templates(self):
        """Инициализирует шаблоны документов."""

        self.document_templates = {
            "contract": {
                "title_template": "Договор №{contract_number} от {date}",
                "description_template": "Договор на поставку товаров/услуг",
                "document_type": DocumentType.CONTRACT,
                "signature_type": SignatureType.QUALIFIED,
                "deadline_days": 5,
                "required_signers": ["supplier", "customer"],
            },
            "commercial_proposal": {
                "title_template": "Коммерческое предложение №{proposal_number}",
                "description_template": "Коммерческое предложение от {supplier_name}",
                "document_type": DocumentType.COMMERCIAL_PROPOSAL,
                "signature_type": SignatureType.ENHANCED,
                "deadline_days": 3,
                "required_signers": ["customer"],
            },
            "specification": {
                "title_template": "Спецификация к договору №{contract_number}",
                "description_template": "Техническая спецификация товаров/услуг",
                "document_type": DocumentType.SPECIFICATION,
                "signature_type": SignatureType.ENHANCED,
                "deadline_days": 2,
                "required_signers": ["supplier", "customer"],
            },
            "invoice": {
                "title_template": "Счет №{invoice_number} от {date}",
                "description_template": "Счет на оплату товаров/услуг",
                "document_type": DocumentType.INVOICE,
                "signature_type": SignatureType.QUALIFIED,
                "deadline_days": 1,
                "required_signers": ["customer"],
            },
        }

    def _initialize_signing_workflows(self):
        """Инициализирует workflow подписания."""

        self.signing_workflows = {
            "simple_approval": [
                SignerInfo(
                    signer_id="manager",
                    name="Менеджер",
                    email="manager@company.com",
                    position="Менеджер по закупкам",
                    signature_type=SignatureType.ENHANCED,
                    signing_order=1,
                )
            ],
            "contract_approval": [
                SignerInfo(
                    signer_id="legal_dept",
                    name="Юридический отдел",
                    email="legal@company.com",
                    position="Начальник юридического отдела",
                    signature_type=SignatureType.ENHANCED,
                    signing_order=1,
                ),
                SignerInfo(
                    signer_id="director",
                    name="Директор",
                    email="director@company.com",
                    position="Генеральный директор",
                    signature_type=SignatureType.QUALIFIED,
                    signing_order=2,
                ),
            ],
            "financial_approval": [
                SignerInfo(
                    signer_id="accountant",
                    name="Главный бухгалтер",
                    email="accountant@company.com",
                    position="Главный бухгалтер",
                    signature_type=SignatureType.QUALIFIED,
                    signing_order=1,
                ),
                SignerInfo(
                    signer_id="cfo",
                    name="Финансовый директор",
                    email="cfo@company.com",
                    position="Финансовый директор",
                    signature_type=SignatureType.QUALIFIED,
                    signing_order=2,
                ),
            ],
        }

    def add_provider(
        self,
        provider_type: EDOProvider,
        provider: BaseEDOProvider,
        is_default: bool = False,
    ):
        """Добавляет провайдера ЭДО."""
        self.providers[provider_type] = provider
        if is_default or not self.default_provider:
            self.default_provider = provider_type
        self.logger.info(f"Добавлен провайдер ЭДО: {provider_type.value}")

    async def initialize_providers(self):
        """Инициализирует всех провайдеров."""
        for provider in self.providers.values():
            await provider.initialize()

    async def cleanup_providers(self):
        """Очищает ресурсы провайдеров."""
        for provider in self.providers.values():
            await provider.cleanup()

    def create_document_package(
        self,
        template_name: str,
        document_files: list[dict[str, Any]],
        workflow_instance: WorkflowInstanceModel,
        custom_signers: Optional[list[SignerInfo]] = None,
        custom_metadata: Optional[dict[str, Any]] = None,
    ) -> DocumentPackage:
        """Создает пакет документов для отправки в ЭДО."""

        template = self.document_templates.get(template_name)
        if not template:
            raise ValueError(f"Шаблон документа '{template_name}' не найден")

        # Генерируем метаданные
        metadata = {
            "template_name": template_name,
            "workflow_instance_id": workflow_instance.instance_id,
            "document_id": workflow_instance.document_id,
            "created_by": "system",
        }
        if custom_metadata:
            metadata.update(custom_metadata)

        # Определяем подписантов
        signers = custom_signers or self._get_default_signers(
            template_name, workflow_instance
        )

        # Создаем пакет
        package = DocumentPackage(
            package_id=f"pkg_{workflow_instance.instance_id}_{int(datetime.now().timestamp())}",
            title=template["title_template"].format(
                contract_number=metadata.get("contract_number", "N/A"),
                proposal_number=metadata.get("proposal_number", "N/A"),
                invoice_number=metadata.get("invoice_number", "N/A"),
                date=datetime.now().strftime("%d.%m.%Y"),
                supplier_name=metadata.get("supplier_name", "N/A"),
            ),
            description=template["description_template"],
            document_type=template["document_type"],
            files=document_files,
            signers=signers,
            deadline=datetime.now() + timedelta(days=template["deadline_days"]),
            metadata=metadata,
            workflow_instance_id=workflow_instance.instance_id,
        )

        return package

    def _get_default_signers(
        self, template_name: str, workflow_instance: WorkflowInstanceModel
    ) -> list[SignerInfo]:
        """Получает подписантов по умолчанию для шаблона."""

        # Определяем workflow подписания на основе типа документа
        if template_name == "contract":
            workflow_name = "contract_approval"
        elif template_name in ["invoice", "act"]:
            workflow_name = "financial_approval"
        else:
            workflow_name = "simple_approval"

        return self.signing_workflows.get(workflow_name, [])

    async def send_document_for_signing(
        self, package: DocumentPackage, provider_type: Optional[EDOProvider] = None
    ) -> DocumentFlowResult:
        """Отправляет документ на подписание через ЭДО."""

        # Выбираем провайдера
        provider_type = provider_type or self.default_provider
        if not provider_type or provider_type not in self.providers:
            return DocumentFlowResult(
                success=False,
                package_id=package.package_id,
                message="Провайдер ЭДО не настроен",
                error_code="NO_PROVIDER",
            )

        provider = self.providers[provider_type]

        try:
            # Отправляем документ
            result = await provider.send_document_package(package)

            # Логируем результат
            if result.success:
                self.logger.info(
                    f"Документ {package.package_id} успешно отправлен через {provider_type.value}"
                )
            else:
                self.logger.error(
                    f"Ошибка отправки документа {package.package_id}: {result.message}"
                )

            return result

        except Exception as e:
            self.logger.error(
                f"Ошибка при отправке документа через {provider_type.value}: {str(e)}"
            )
            return DocumentFlowResult(
                success=False,
                package_id=package.package_id,
                message=f"Ошибка отправки: {str(e)}",
                error_code="SEND_ERROR",
            )

    async def check_document_status(
        self, edo_document_id: str, provider_type: Optional[EDOProvider] = None
    ) -> DocumentFlowResult:
        """Проверяет статус документа в ЭДО."""

        provider_type = provider_type or self.default_provider
        if not provider_type or provider_type not in self.providers:
            return DocumentFlowResult(
                success=False,
                package_id="",
                edo_document_id=edo_document_id,
                message="Провайдер ЭДО не настроен",
                error_code="NO_PROVIDER",
            )

        provider = self.providers[provider_type]
        return await provider.get_document_status(edo_document_id)

    async def download_signed_document(
        self, edo_document_id: str, provider_type: Optional[EDOProvider] = None
    ) -> Optional[bytes]:
        """Скачивает подписанный документ."""

        provider_type = provider_type or self.default_provider
        if not provider_type or provider_type not in self.providers:
            return None

        provider = self.providers[provider_type]
        try:
            return await provider.download_signed_document(edo_document_id)
        except Exception as e:
            self.logger.error(
                f"Ошибка скачивания документа {edo_document_id}: {str(e)}"
            )
            return None

    async def cancel_document(
        self,
        edo_document_id: str,
        reason: str,
        provider_type: Optional[EDOProvider] = None,
    ) -> DocumentFlowResult:
        """Отменяет документ в ЭДО."""

        provider_type = provider_type or self.default_provider
        if not provider_type or provider_type not in self.providers:
            return DocumentFlowResult(
                success=False,
                package_id="",
                edo_document_id=edo_document_id,
                message="Провайдер ЭДО не настроен",
                error_code="NO_PROVIDER",
            )

        provider = self.providers[provider_type]
        return await provider.cancel_document(edo_document_id, reason)

    def get_document_template(self, template_name: str) -> Optional[dict[str, Any]]:
        """Получает шаблон документа."""
        return self.document_templates.get(template_name)

    def add_document_template(
        self, template_name: str, template_config: dict[str, Any]
    ):
        """Добавляет новый шаблон документа."""
        self.document_templates[template_name] = template_config
        self.logger.info(f"Добавлен шаблон документа: {template_name}")

    def get_signing_workflow(self, workflow_name: str) -> Optional[list[SignerInfo]]:
        """Получает workflow подписания."""
        return self.signing_workflows.get(workflow_name)

    def add_signing_workflow(self, workflow_name: str, signers: list[SignerInfo]):
        """Добавляет новый workflow подписания."""
        self.signing_workflows[workflow_name] = signers
        self.logger.info(f"Добавлен workflow подписания: {workflow_name}")


# Функции для интеграции с workflow_engine
def create_edo_integration() -> DocumentFlowIntegration:
    """Создает экземпляр интеграции с ЭДО."""
    return DocumentFlowIntegration()


def setup_diadoc_provider(
    api_key: str, organization_id: str, api_url: str = "https://diadoc-api.kontur.ru"
) -> DiadocProvider:
    """Настраивает провайдера Диадок."""
    config = {
        "api_key": api_key,
        "organization_id": organization_id,
        "api_url": api_url,
    }
    return DiadocProvider(config)


def setup_sbis_provider(
    login: str, password: str, api_url: str = "https://api.sbis.ru"
) -> SBISProvider:
    """Настраивает провайдера СБИС."""
    config = {"login": login, "password": password, "api_url": api_url}
    return SBISProvider(config)


async def send_workflow_document_for_signing(
    edo_integration: DocumentFlowIntegration,
    workflow_instance: WorkflowInstanceModel,
    document_files: list[dict[str, Any]],
    template_name: str = "contract",
) -> DocumentFlowResult:
    """Отправляет документ из workflow на подписание в ЭДО."""

    try:
        # Создаем пакет документов
        package = edo_integration.create_document_package(
            template_name=template_name,
            document_files=document_files,
            workflow_instance=workflow_instance,
        )

        # Отправляем на подписание
        result = await edo_integration.send_document_for_signing(package)

        return result

    except Exception as e:
        logging.error(
            f"Ошибка отправки документа workflow {workflow_instance.instance_id} в ЭДО: {str(e)}"
        )
        return DocumentFlowResult(
            success=False,
            package_id="",
            message=f"Ошибка отправки в ЭДО: {str(e)}",
            error_code="WORKFLOW_SEND_ERROR",
        )


async def monitor_edo_documents(
    edo_integration: DocumentFlowIntegration, edo_document_ids: list[str]
) -> dict[str, DocumentFlowResult]:
    """Мониторит статусы документов в ЭДО."""

    results = {}

    for edo_document_id in edo_document_ids:
        try:
            result = await edo_integration.check_document_status(edo_document_id)
            results[edo_document_id] = result
        except Exception as e:
            logging.error(
                f"Ошибка проверки статуса документа {edo_document_id}: {str(e)}"
            )
            results[edo_document_id] = DocumentFlowResult(
                success=False,
                package_id="",
                edo_document_id=edo_document_id,
                message=f"Ошибка проверки статуса: {str(e)}",
                error_code="STATUS_CHECK_ERROR",
            )

    return results
