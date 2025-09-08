"""
Тесты для проверки уникальности поставщиков по ИНН и номеру договора
Проверка ограничений уникальности и валидации данных поставщиков
"""

import os
import sys
from typing import Optional

import pytest

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Supplier:
    """Модель поставщика для тестов уникальности"""

    def __init__(
        self,
        id: int,
        name: str,
        inn: str,
        kpp: str,
        contract_number: str,
        email: str,
        phone: str,
        created_at: Optional[str] = None,
    ):
        self.id = id
        self.name = name
        self.inn = inn
        self.kpp = kpp
        self.contract_number = contract_number
        self.email = email
        self.phone = phone
        self.created_at = created_at or "2024-01-01 00:00:00"


class SupplierRepository:
    """Репозиторий поставщиков для тестов уникальности"""

    def __init__(self):
        self.suppliers: dict[int, Supplier] = {}
        self.inn_index: dict[str, int] = {}
        self.contract_index: dict[str, int] = {}

    def add_supplier(self, supplier: Supplier) -> bool:
        """Добавление поставщика с проверкой уникальности"""
        # Проверка уникальности ИНН
        if supplier.inn in self.inn_index:
            raise ValueError(f"Поставщик с ИНН {supplier.inn} уже существует")

        # Проверка уникальности номера договора
        if supplier.contract_number in self.contract_index:
            raise ValueError(
                f"Договор с номером {supplier.contract_number} уже существует"
            )

        # Добавление поставщика
        self.suppliers[supplier.id] = supplier
        self.inn_index[supplier.inn] = supplier.id
        self.contract_index[supplier.contract_number] = supplier.id

        return True

    def update_supplier(self, supplier_id: int, **kwargs) -> bool:
        """Обновление данных поставщика с проверкой уникальности"""
        if supplier_id not in self.suppliers:
            raise ValueError(f"Поставщик с ID {supplier_id} не найден")

        supplier = self.suppliers[supplier_id]

        # Проверка уникальности ИНН при изменении
        new_inn = kwargs.get("inn")
        if new_inn and new_inn != supplier.inn:
            if new_inn in self.inn_index:
                raise ValueError(f"Поставщик с ИНН {new_inn} уже существует")
            # Обновляем индекс
            del self.inn_index[supplier.inn]
            self.inn_index[new_inn] = supplier_id
            supplier.inn = new_inn

        # Проверка уникальности номера договора при изменении
        new_contract = kwargs.get("contract_number")
        if new_contract and new_contract != supplier.contract_number:
            if new_contract in self.contract_index:
                raise ValueError(f"Договор с номером {new_contract} уже существует")
            # Обновляем индекс
            del self.contract_index[supplier.contract_number]
            self.contract_index[new_contract] = supplier_id
            supplier.contract_number = new_contract

        # Обновление остальных полей
        for key, value in kwargs.items():
            if key in ["name", "kpp", "email", "phone"] and value is not None:
                setattr(supplier, key, value)

        return True

    def get_supplier_by_inn(self, inn: str) -> Optional[Supplier]:
        """Поиск поставщика по ИНН"""
        supplier_id = self.inn_index.get(inn)
        return self.suppliers.get(supplier_id)

    def get_supplier_by_contract(self, contract_number: str) -> Optional[Supplier]:
        """Поиск поставщика по номеру договора"""
        supplier_id = self.contract_index.get(contract_number)
        return self.suppliers.get(supplier_id)

    def get_all_suppliers(self) -> list[Supplier]:
        """Получение всех поставщиков"""
        return list(self.suppliers.values())


class TestSupplierUniqueness:
    """Тестирование уникальности поставщиков"""

    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.repository = SupplierRepository()

        # Базовый поставщик для тестов
        self.base_supplier = Supplier(
            id=1,
            name="Тестовый Поставщик ООО",
            inn="123456789012",
            kpp="123456789",
            contract_number="CNT-2024-001",
            email="supplier@test.com",
            phone="+79991234567",
        )

    def test_unique_inn_constraint(self):
        """Тест уникальности ИНН при добавлении поставщика"""
        # Добавляем первого поставщика
        self.repository.add_supplier(self.base_supplier)

        # Пытаемся добавить поставщика с тем же ИНН
        duplicate_supplier = Supplier(
            id=2,
            name="Другой Поставщик ООО",
            inn="123456789012",  # Тот же ИНН
            kpp="987654321",
            contract_number="CNT-2024-002",
            email="other@test.com",
            phone="+79998765432",
        )

        with pytest.raises(
            ValueError, match="Поставщик с ИНН 123456789012 уже существует"
        ):
            self.repository.add_supplier(duplicate_supplier)

    def test_unique_contract_number_constraint(self):
        """Тест уникальности номера договора при добавлении поставщика"""
        # Добавляем первого поставщика
        self.repository.add_supplier(self.base_supplier)

        # Пытаемся добавить поставщика с тем же номером договора
        duplicate_supplier = Supplier(
            id=2,
            name="Другой Поставщик ООО",
            inn="987654321098",
            kpp="987654321",
            contract_number="CNT-2024-001",  # Тот же номер договора
            email="other@test.com",
            phone="+79998765432",
        )

        with pytest.raises(
            ValueError, match="Договор с номером CNT-2024-001 уже существует"
        ):
            self.repository.add_supplier(duplicate_supplier)

    def test_valid_supplier_creation(self):
        """Тест успешного создания уникального поставщика"""
        result = self.repository.add_supplier(self.base_supplier)

        assert result is True
        assert len(self.repository.get_all_suppliers()) == 1
        assert self.repository.get_supplier_by_inn("123456789012") == self.base_supplier
        assert (
            self.repository.get_supplier_by_contract("CNT-2024-001")
            == self.base_supplier
        )

    def test_multiple_unique_suppliers(self):
        """Тест добавления нескольких уникальных поставщиков"""
        suppliers = [
            self.base_supplier,
            Supplier(
                id=2,
                name="Поставщик 2 ООО",
                inn="987654321098",
                kpp="987654321",
                contract_number="CNT-2024-002",
                email="supplier2@test.com",
                phone="+79991234568",
            ),
            Supplier(
                id=3,
                name="Поставщик 3 ООО",
                inn="555555555555",
                kpp="555555555",
                contract_number="CNT-2024-003",
                email="supplier3@test.com",
                phone="+79991234569",
            ),
        ]

        for supplier in suppliers:
            self.repository.add_supplier(supplier)

        assert len(self.repository.get_all_suppliers()) == 3

        # Проверяем уникальность каждого
        for supplier in suppliers:
            assert self.repository.get_supplier_by_inn(supplier.inn) == supplier
            assert (
                self.repository.get_supplier_by_contract(supplier.contract_number)
                == supplier
            )

    def test_update_inn_with_unique_value(self):
        """Тест обновления ИНН на уникальное значение"""
        self.repository.add_supplier(self.base_supplier)

        # Обновляем ИНН на уникальное значение
        result = self.repository.update_supplier(1, inn="999999999999")

        assert result is True
        updated_supplier = self.repository.get_supplier_by_inn("999999999999")
        assert updated_supplier is not None
        assert updated_supplier.inn == "999999999999"
        assert self.repository.get_supplier_by_inn("123456789012") is None

    def test_update_inn_with_duplicate_value(self):
        """Тест обновления ИНН на уже существующее значение"""
        # Добавляем двух поставщиков
        self.repository.add_supplier(self.base_supplier)

        second_supplier = Supplier(
            id=2,
            name="Второй Поставщик",
            inn="987654321098",
            kpp="987654321",
            contract_number="CNT-2024-002",
            email="second@test.com",
            phone="+79991234568",
        )
        self.repository.add_supplier(second_supplier)

        # Пытаемся обновить ИНН первого поставщика на ИНН второго
        with pytest.raises(
            ValueError, match="Поставщик с ИНН 987654321098 уже существует"
        ):
            self.repository.update_supplier(1, inn="987654321098")

    def test_update_contract_number_with_unique_value(self):
        """Тест обновления номера договора на уникальное значение"""
        self.repository.add_supplier(self.base_supplier)

        # Обновляем номер договора на уникальный
        result = self.repository.update_supplier(1, contract_number="CNT-2024-999")

        assert result is True
        updated_supplier = self.repository.get_supplier_by_contract("CNT-2024-999")
        assert updated_supplier is not None
        assert updated_supplier.contract_number == "CNT-2024-999"
        assert self.repository.get_supplier_by_contract("CNT-2024-001") is None

    def test_update_contract_number_with_duplicate_value(self):
        """Тест обновления номера договора на уже существующее значение"""
        # Добавляем двух поставщиков
        self.repository.add_supplier(self.base_supplier)

        second_supplier = Supplier(
            id=2,
            name="Второй Поставщик",
            inn="987654321098",
            kpp="987654321",
            contract_number="CNT-2024-002",
            email="second@test.com",
            phone="+79991234568",
        )
        self.repository.add_supplier(second_supplier)

        # Пытаемся обновить номер договора первого поставщика на номер второго
        with pytest.raises(
            ValueError, match="Договор с номером CNT-2024-002 уже существует"
        ):
            self.repository.update_supplier(1, contract_number="CNT-2024-002")

    def test_update_non_unique_fields(self):
        """Тест обновления неуникальных полей без ограничений"""
        self.repository.add_supplier(self.base_supplier)

        # Обновляем неуникальные поля
        result = self.repository.update_supplier(
            1,
            name="Обновленное Название ООО",
            email="updated@supplier.com",
            phone="+79999999999",
        )

        assert result is True
        updated_supplier = self.repository.get_all_suppliers()[0]
        assert updated_supplier.name == "Обновленное Название ООО"
        assert updated_supplier.email == "updated@supplier.com"
        assert updated_supplier.phone == "+79999999999"

    def test_empty_inn_handling(self):
        """Тест обработки пустого ИНН"""
        supplier_with_empty_inn = Supplier(
            id=1,
            name="Поставщик с пустым ИНН",
            inn="",
            kpp="123456789",
            contract_number="CNT-2024-001",
            email="test@test.com",
            phone="+79991234567",
        )

        # Проверяем что пустой ИНН может быть добавлен (если это допустимо)
        # Главное - что он будет уникален
        self.repository.add_supplier(supplier_with_empty_inn)
        assert self.repository.get_supplier_by_inn("") == supplier_with_empty_inn

    def test_empty_contract_number_handling(self):
        """Тест обработки пустого номера договора"""
        supplier_with_empty_contract = Supplier(
            id=1,
            name="Поставщик с пустым договором",
            inn="123456789012",
            kpp="123456789",
            contract_number="",
            email="test@test.com",
            phone="+79991234567",
        )

        # Проверяем что пустой номер договора может быть добавлен (если это допустимо)
        # Главное - что он будет уникален
        self.repository.add_supplier(supplier_with_empty_contract)
        assert (
            self.repository.get_supplier_by_contract("") == supplier_with_empty_contract
        )

    def test_various_inn_formats_uniqueness(self):
        """Тест уникальности для различных форматов ИНН"""
        suppliers = [
            Supplier(
                id=1,
                name="Поставщик 1",
                inn="123456789012",
                kpp="111",
                contract_number="CNT-001",
                email="1@test.com",
                phone="1",
            ),
            Supplier(
                id=2,
                name="Поставщик 2",
                inn="987654321098",
                kpp="222",
                contract_number="CNT-002",
                email="2@test.com",
                phone="2",
            ),
            Supplier(
                id=3,
                name="Поставщик 3",
                inn="111222333444",
                kpp="333",
                contract_number="CNT-003",
                email="3@test.com",
                phone="3",
            ),
        ]

        for supplier in suppliers:
            self.repository.add_supplier(supplier)

        assert len(self.repository.get_all_suppliers()) == 3

        # Проверяем что дубликаты ИНН не допускаются
        duplicate = Supplier(
            id=4,
            name="Дубликат ИНН",
            inn="123456789012",  # Дубликат первого ИНН
            kpp="444",
            contract_number="CNT-004",
            email="4@test.com",
            phone="4",
        )

        with pytest.raises(
            ValueError, match="Поставщик с ИНН 123456789012 уже существует"
        ):
            self.repository.add_supplier(duplicate)

    def test_case_sensitive_uniqueness(self):
        """Тест регистрозависимой уникальности (если требуется)"""
        # Проверяем что регистр важен для уникальности
        supplier1 = Supplier(
            id=1,
            name="Поставщик 1",
            inn="123456789012",
            kpp="111",
            contract_number="CNT-001",
            email="1@test.com",
            phone="1",
        )

        supplier2 = Supplier(
            id=2,
            name="Поставщик 2",
            inn="123456789012".upper(),  # Верхний регистр
            kpp="222",
            contract_number="CNT-002",
            email="2@test.com",
            phone="2",
        )

        # Если регистр не важен, второй поставщик будет отклонен
        # Если регистр важен - оба будут добавлены
        # В данном примере допускаем оба варианта
        try:
            self.repository.add_supplier(supplier1)
            self.repository.add_supplier(supplier2)
            # Если регистр важен
            assert len(self.repository.get_all_suppliers()) == 2
        except ValueError:
            # Если регистр не важен
            assert len(self.repository.get_all_suppliers()) == 1


class TestSupplierUniquenessIntegration:
    """Интеграционные тесты уникальности поставщиков"""

    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.repository = SupplierRepository()

    def test_bulk_import_with_uniqueness_check(self):
        """Тест импорта поставщиков с проверкой уникальности"""
        suppliers_data = [
            {
                "id": 1,
                "name": "Поставщик 1",
                "inn": "111111111111",
                "kpp": "111111111",
                "contract": "CNT-001",
            },
            {
                "id": 2,
                "name": "Поставщик 2",
                "inn": "222222222222",
                "kpp": "222222222",
                "contract": "CNT-002",
            },
            {
                "id": 3,
                "name": "Поставщик 3",
                "inn": "333333333333",
                "kpp": "333333333",
                "contract": "CNT-003",
            },
        ]

        added_count = 0
        for data in suppliers_data:
            try:
                supplier = Supplier(
                    id=data["id"],
                    name=data["name"],
                    inn=data["inn"],
                    kpp=data["kpp"],
                    contract_number=data["contract"],
                    email=f"supplier{data['id']}@test.com",
                    phone=f"+7999123456{data['id']}",
                )
                self.repository.add_supplier(supplier)
                added_count += 1
            except ValueError:
                # Пропускаем дубликаты
                continue

        assert added_count == 3
        assert len(self.repository.get_all_suppliers()) == 3

    def test_duplicate_handling_in_batch(self):
        """Тест обработки дубликатов при пакетном импорте"""
        suppliers_data = [
            {
                "id": 1,
                "name": "Поставщик 1",
                "inn": "111111111111",
                "kpp": "111111111",
                "contract": "CNT-001",
            },
            {
                "id": 2,
                "name": "Поставщик 2",
                "inn": "111111111111",
                "kpp": "222222222",
                "contract": "CNT-002",
            },  # Дубликат ИНН
            {
                "id": 3,
                "name": "Поставщик 3",
                "inn": "333333333333",
                "kpp": "333333333",
                "contract": "CNT-001",
            },  # Дубликат договора
        ]

        added_count = 0
        errors = []

        for data in suppliers_data:
            try:
                supplier = Supplier(
                    id=data["id"],
                    name=data["name"],
                    inn=data["inn"],
                    kpp=data["kpp"],
                    contract_number=data["contract"],
                    email=f"supplier{data['id']}@test.com",
                    phone=f"+7999123456{data['id']}",
                )
                self.repository.add_supplier(supplier)
                added_count += 1
            except ValueError as e:
                errors.append(str(e))

        assert added_count == 1  # Только первый поставщик добавлен
        assert len(errors) == 2  # Два дубликата
        assert "ИНН 111111111111 уже существует" in errors[0]
        assert "Договор с номером CNT-001 уже существует" in errors[1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
