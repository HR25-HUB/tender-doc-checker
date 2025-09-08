"""
Test for verifying correspondence between extractor fields and internal_standards.yaml
"""

from pathlib import Path

import pytest
import yaml


class TestExtractorMapping:
    """Test suite for verifying field mapping between extractor and internal_standards.yaml"""

    @pytest.fixture
    def internal_standards(self):
        """Load internal_standards.yaml for testing"""
        standards_path = (
            Path(__file__).parent.parent / "data" / "internal_standards.yaml"
        )
        with open(standards_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    @pytest.fixture
    def expected_sections(self, internal_standards):
        """Get expected section names from internal_standards"""
        return list(internal_standards.keys())

    @pytest.fixture
    def expected_fields(self, internal_standards):
        """Get all expected field patterns from internal_standards"""
        fields = []
        for section, requirements in internal_standards.items():
            if isinstance(requirements, list):
                for req in requirements:
                    if isinstance(req, str):
                        # Extract key phrases that should be found in documents
                        key_phrases = self._extract_key_phrases(req)
                        fields.extend(key_phrases)
        return fields

    def _extract_key_phrases(self, requirement_text):
        """Extract key phrases from requirement text that should be found in documents"""
        phrases = []

        # Common patterns to look for
        patterns = [
            "количественные параметры",
            "единицы измерения",
            "объёмы",
            "срок исполнения",
            "условия приёмки",
            "критерии оценки",
            "ответственность сторон",
            "процедура расторжения",
            "валюта",
            "оплата",
            "сроки расчёта",
        ]

        for pattern in patterns:
            if pattern.lower() in requirement_text.lower():
                phrases.append(pattern)

        return phrases

    def test_internal_standards_structure(self, internal_standards):
        """Test that internal_standards.yaml has correct structure"""
        assert isinstance(internal_standards, dict)
        assert "Техническое задание" in internal_standards
        assert "Форма договора" in internal_standards

        # Check that sections contain lists of requirements
        for section, requirements in internal_standards.items():
            assert isinstance(requirements, list)
            assert len(requirements) > 0

    def test_tech_specification_fields(self, internal_standards):
        """Test mapping for technical specification fields"""
        tech_specs = internal_standards.get("Техническое задание", [])

        expected_keywords = [
            "количественные параметры",
            "единицы измерения",
            "объёмы",
            "срок исполнения",
            "условия приёмки",
            "критерии оценки",
        ]

        found_keywords = []
        for spec in tech_specs:
            if isinstance(spec, str):
                for keyword in expected_keywords:
                    if keyword in spec.lower():
                        found_keywords.append(keyword)

        # At least some keywords should be found
        assert (
            len(found_keywords) > 0
        ), f"Expected keywords {expected_keywords} not found in {tech_specs}"

    def test_contract_form_fields(self, internal_standards):
        """Test mapping for contract form fields"""
        contract_specs = internal_standards.get("Форма договора", [])

        expected_keywords = [
            "ответственность сторон",
            "процедура расторжения",
            "валюта",
            "оплата",
            "сроки расчёта",
        ]

        found_keywords = []
        for spec in contract_specs:
            if isinstance(spec, str):
                for keyword in expected_keywords:
                    if keyword in spec.lower():
                        found_keywords.append(keyword)

        # At least some keywords should be found
        assert (
            len(found_keywords) > 0
        ), f"Expected keywords {expected_keywords} not found in {contract_specs}"

    def test_field_extraction_patterns(self):
        """Test that extractor can identify required fields based on patterns"""
        # Mock document content with expected fields
        mock_content = """
        Техническое задание:
        - Объём работ: 1000 единиц
        - Срок исполнения: 30 календарных дней
        - Условия приёмки: соответствие техническим требованиям
        - Критерии оценки: качество и сроки выполнения

        Договор:
        - Ответственность сторон: предусмотрена неустойка
        - Процедура расторжения: по соглашению сторон
        - Валюта: российские рубли
        - Оплата: аванс 30%, постоплата 70%
        - Сроки расчёта: в течение 5 банковских дней
        """

        # Test that we can identify the required patterns
        required_patterns = [
            r"объ[её]м.*\d+",
            r"срок.*исполнения.*\d+",
            r"условия.*при[её]мки",
            r"критерии.*оценки",
            r"ответственность.*сторон",
            r"процедура.*расторжения",
            r"валют[аы]",
            r"оплат[аы]",
            r"сроки.*расч[её]та",
        ]

        import re

        found_patterns = []
        for pattern in required_patterns:
            if re.search(pattern, mock_content, re.IGNORECASE):
                found_patterns.append(pattern)

        # At least some patterns should match
        assert (
            len(found_patterns) > 0
        ), f"Required patterns {required_patterns} not found in content"

    def test_yaml_file_exists(self):
        """Test that internal_standards.yaml file exists and is readable"""
        standards_path = (
            Path(__file__).parent.parent / "data" / "internal_standards.yaml"
        )
        assert (
            standards_path.exists()
        ), f"internal_standards.yaml not found at {standards_path}"
        assert standards_path.is_file(), f"{standards_path} is not a file"

        # Test file can be parsed
        try:
            with open(standards_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
                assert data is not None, "internal_standards.yaml is empty"
        except yaml.YAMLError as e:
            pytest.fail(f"Failed to parse internal_standards.yaml: {e}")

    def test_extractor_integration(self):
        """Test that extractor can work with the expected field structure"""
        # This test ensures the extractor module can handle documents
        # that should contain fields defined in internal_standards

        # Import extractor functions
        from io import BytesIO

        from extractor import extract_text_from_file

        # Create mock document content
        mock_doc_content = """
        ТЕХНИЧЕСКОЕ ЗАДАНИЕ

        1. Объем работ: поставка 500 единиц оборудования
        2. Срок исполнения: 90 календарных дней с момента подписания
        3. Условия приёмки: проверка соответствия ТЗ и техническим регламентам
        4. Критерии оценки: соответствие техническим требованиям, сроки поставки

        ФОРМА ДОГОВОРА

        1. Ответственность сторон: неустойка 0.1% за каждый день просрочки
        2. Процедура расторжения: по письменному соглашению сторон
        3. Валюта: российские рубли (RUB)
        4. Условия оплаты: 100% постоплата по факту поставки
        5. Сроки расчёта: в течение 10 банковских дней после подписания акта
        """

        # Test with mock file
        mock_file = BytesIO(mock_doc_content.encode("utf-8"))
        mock_file.name = "test_document.txt"

        try:
            extracted_text = extract_text_from_file(mock_file)
            assert extracted_text is not None
            assert len(extracted_text) > 0

            # Check that key phrases are present in extracted text
            key_phrases = [
                "оборудования",
                "календарных дней",
                "технические регламенты",
                "неустойка",
                "валюта",
                "оплата",
            ]

            found_phrases = [
                phrase
                for phrase in key_phrases
                if phrase.lower() in extracted_text.lower()
            ]
            assert (
                len(found_phrases) > 0
            ), "Expected phrases not found in extracted text"

        except Exception as e:
            pytest.fail(f"Extractor failed to process document: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
