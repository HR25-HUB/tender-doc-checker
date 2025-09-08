"""Тесты для модуля extractor."""

from unittest.mock import Mock, patch

from extractor import extract_from_docx, extract_from_pdf, extract_text_from_file


class TestExtractor:
    """Тесты для экстрактора текста из документов."""

    def test_extract_text_from_txt_file(self):
        """Тест извлечения текста из текстового файла."""
        # Создаем mock файл
        mock_file = Mock()
        mock_file.name = "test.txt"
        mock_file.read.return_value = b"Test content"

        result = extract_text_from_file(mock_file)
        assert result == "Test content"

    @patch("extractor.extract_from_pdf")
    def test_extract_text_from_pdf_file(self, mock_extract_pdf):
        """Тест извлечения текста из PDF файла."""
        mock_extract_pdf.return_value = "PDF content"

        mock_file = Mock()
        mock_file.name = "test.pdf"

        result = extract_text_from_file(mock_file)
        assert result == "PDF content"
        mock_extract_pdf.assert_called_once_with(mock_file)

    @patch("extractor.extract_from_docx")
    def test_extract_text_from_docx_file(self, mock_extract_docx):
        """Тест извлечения текста из DOCX файла."""
        mock_extract_docx.return_value = "DOCX content"

        mock_file = Mock()
        mock_file.name = "test.docx"

        result = extract_text_from_file(mock_file)
        assert result == "DOCX content"
        mock_extract_docx.assert_called_once_with(mock_file)

    @patch("fitz.open")
    def test_extract_from_pdf(self, mock_fitz_open):
        """Тест извлечения текста из PDF через PyMuPDF."""
        # Настраиваем mock для PyMuPDF
        mock_doc = Mock()
        mock_page = Mock()
        mock_page.get_text.return_value = "Page content"
        mock_doc.__iter__ = Mock(return_value=iter([mock_page]))
        mock_doc.__enter__ = Mock(return_value=mock_doc)
        mock_doc.__exit__ = Mock(return_value=None)
        mock_fitz_open.return_value = mock_doc

        mock_file = Mock()
        mock_file.read.return_value = b"PDF bytes"

        result = extract_from_pdf(mock_file)
        assert result == "Page content"
        mock_fitz_open.assert_called_once_with(stream=b"PDF bytes", filetype="pdf")

    @patch("docx.Document")
    def test_extract_from_docx(self, mock_docx_document):
        """Тест извлечения текста из DOCX через python-docx."""
        # Настраиваем mock для python-docx
        mock_para1 = Mock()
        mock_para1.text = "First paragraph"
        mock_para2 = Mock()
        mock_para2.text = "Second paragraph"

        mock_doc = Mock()
        mock_doc.paragraphs = [mock_para1, mock_para2]
        mock_docx_document.return_value = mock_doc

        mock_file = Mock()

        result = extract_from_docx(mock_file)
        assert result == "First paragraph\nSecond paragraph"
        mock_docx_document.assert_called_once_with(mock_file)

    def test_extract_from_docx_empty_document(self):
        """Тест извлечения текста из пустого DOCX документа."""
        with patch("docx.Document") as mock_docx_document:
            mock_doc = Mock()
            mock_doc.paragraphs = []
            mock_docx_document.return_value = mock_doc

            mock_file = Mock()

            result = extract_from_docx(mock_file)
            assert result == ""

    def test_extract_text_unknown_extension(self):
        """Тест обработки файла с неизвестным расширением."""
        mock_file = Mock()
        mock_file.name = "test.unknown"
        mock_file.read.return_value = b"Unknown file content"

        result = extract_text_from_file(mock_file)
        assert result == "Unknown file content"
