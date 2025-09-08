"""Тесты для модуля chunker."""


from chunker import chunk_document


class TestChunker:
    """Тесты для чанкера документов."""

    def test_chunk_document_basic(self):
        """Тест базового разбиения документа на части."""
        text = """Техническое задание
Описание технических требований

Коммерческие условия
Цены и сроки поставки

Юридические аспекты
Условия договора"""

        result = chunk_document(text)

        assert len(result) == 3
        assert result[0]["title"] == "Техническое задание"
        assert result[0]["content"] == "Описание технических требований"
        assert result[1]["title"] == "Коммерческие условия"
        assert result[1]["content"] == "Цены и сроки поставки"
        assert result[2]["title"] == "Юридические аспекты"
        assert result[2]["content"] == "Условия договора"

    def test_chunk_document_single_section(self):
        """Тест разбиения документа с одной секцией."""
        text = "Единственная секция\nСодержимое секции"

        result = chunk_document(text)

        assert len(result) == 1
        assert result[0]["title"] == "Единственная секция"
        assert result[0]["content"] == "Содержимое секции"

    def test_chunk_document_empty_sections(self):
        """Тест обработки пустых секций."""
        text = """Первая секция
Содержимое первой секции



Вторая секция
Содержимое второй секции"""

        result = chunk_document(text)

        assert len(result) == 2
        assert result[0]["title"] == "Первая секция"
        assert result[0]["content"] == "Содержимое первой секции"
        assert result[1]["title"] == "Вторая секция"
        assert result[1]["content"] == "Содержимое второй секции"

    def test_chunk_document_title_only(self):
        """Тест секций только с заголовком."""
        text = """Заголовок без содержимого

Другой заголовок
С содержимым"""

        result = chunk_document(text)

        assert len(result) == 2
        assert result[0]["title"] == "Заголовок без содержимого"
        assert result[0]["content"] == ""
        assert result[1]["title"] == "Другой заголовок"
        assert result[1]["content"] == "С содержимым"

    def test_chunk_document_multiline_content(self):
        """Тест секций с многострочным содержимым."""
        text = """Многострочная секция
Первая строка содержимого
Вторая строка содержимого
Третья строка содержимого

Другая секция
Еще одна строка"""

        result = chunk_document(text)

        assert len(result) == 2
        assert result[0]["title"] == "Многострочная секция"
        assert (
            result[0]["content"]
            == "Первая строка содержимого\nВторая строка содержимого\nТретья строка содержимого"
        )
        assert result[1]["title"] == "Другая секция"
        assert result[1]["content"] == "Еще одна строка"

    def test_chunk_document_empty_text(self):
        """Тест обработки пустого текста."""
        text = ""

        result = chunk_document(text)

        assert len(result) == 0

    def test_chunk_document_whitespace_only(self):
        """Тест обработки текста только с пробелами."""
        text = "   \n\n   \n\n   "

        result = chunk_document(text)

        assert len(result) == 0

    def test_chunk_document_with_leading_trailing_whitespace(self):
        """Тест обработки секций с пробелами в начале и конце."""
        text = """  Заголовок с пробелами
  Содержимое с пробелами

  Другой заголовок
  Другое содержимое  """

        result = chunk_document(text)

        assert len(result) == 2
        assert result[0]["title"] == "Заголовок с пробелами"
        assert result[0]["content"] == "Содержимое с пробелами"
        assert result[1]["title"] == "Другой заголовок"
        assert result[1]["content"] == "Другое содержимое"

    def test_chunk_document_complex_structure(self):
        """Тест сложной структуры документа."""
        text = """ТЕХНИЧЕСКОЕ ЗАДАНИЕ
Поставка кабельной продукции
Требования к качеству
Сертификация по ГОСТ

КОММЕРЧЕСКИЕ УСЛОВИЯ
Цена: 1000 руб/м
Срок поставки: 30 дней
Условия оплаты: 50% предоплата

ЮРИДИЧЕСКИЕ ТРЕБОВАНИЯ
Договор поставки
Ответственность сторон
Порядок приемки товара"""

        result = chunk_document(text)

        assert len(result) == 3

        # Проверяем техническое задание
        assert result[0]["title"] == "ТЕХНИЧЕСКОЕ ЗАДАНИЕ"
        expected_tech_content = (
            "Поставка кабельной продукции\nТребования к качеству\nСертификация по ГОСТ"
        )
        assert result[0]["content"] == expected_tech_content

        # Проверяем коммерческие условия
        assert result[1]["title"] == "КОММЕРЧЕСКИЕ УСЛОВИЯ"
        expected_comm_content = (
            "Цена: 1000 руб/м\nСрок поставки: 30 дней\nУсловия оплаты: 50% предоплата"
        )
        assert result[1]["content"] == expected_comm_content

        # Проверяем юридические требования
        assert result[2]["title"] == "ЮРИДИЧЕСКИЕ ТРЕБОВАНИЯ"
        expected_legal_content = (
            "Договор поставки\nОтветственность сторон\nПорядок приемки товара"
        )
        assert result[2]["content"] == expected_legal_content
