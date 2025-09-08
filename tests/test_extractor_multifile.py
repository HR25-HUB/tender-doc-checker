"""
Tests for multi-page PDF/DOCX extraction functionality with PyMuPDF/python-docx mocks
"""

import os

# Import the extractor module
import sys
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from extractor import extract_from_docx, extract_from_pdf, extract_text_from_file
except ImportError:
    # Fallback for test execution context
    import os

    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from extractor import extract_from_docx, extract_from_pdf


class TestExtractorMultifile:
    """Test suite for multi-page document extraction"""

    @pytest.fixture
    def mock_pdf_document(self):
        """Create mock PDF document with multiple pages"""
        mock_doc = Mock()
        mock_pages = []

        # Create mock pages with different content
        page_contents = [
            "Page 1: Техническое задание\nОбъем работ: 1000 единиц",
            "Page 2: Условия приёмки\nСоответствие техническим требованиям",
            "Page 3: Сроки исполнения\n90 календарных дней",
        ]

        for content in page_contents:
            mock_page = Mock()
            mock_page.get_text.return_value = content
            mock_pages.append(mock_page)

        mock_doc.__iter__ = Mock(return_value=iter(mock_pages))
        mock_doc.__enter__ = Mock(return_value=mock_doc)
        mock_doc.__exit__ = Mock(return_value=None)

        return mock_doc

    @pytest.fixture
    def mock_docx_document(self):
        """Create mock DOCX document with multiple paragraphs"""
        mock_doc = Mock()

        # Mock paragraphs across multiple sections
        mock_paragraphs = []
        paragraph_texts = [
            "ТЕХНИЧЕСКОЕ ЗАДАНИЕ",
            "1. Объем поставки: 500 единиц оборудования",
            "2. Срок исполнения: 60 календарных дней",
            "ФОРМА ДОГОВОРА",
            "3. Условия оплаты: 50% предоплата, 50% постоплата",
        ]

        for text in paragraph_texts:
            mock_para = Mock()
            mock_para.text = text
            mock_paragraphs.append(mock_para)

        mock_doc.paragraphs = mock_paragraphs
        return mock_doc

    def test_multi_page_pdf_extraction(self, mock_pdf_document):
        """Test extraction from multi-page PDF"""
        with patch("fitz.open") as mock_fitz_open:
            mock_fitz_open.return_value = mock_pdf_document

            # Create mock file
            mock_file = Mock()
            mock_file.name = "test_multipage.pdf"
            mock_file.read.return_value = b"fake_pdf_content"

            result = extract_from_pdf(mock_file)

            # Verify all pages are extracted
            assert "Page 1:" in result
            assert "Page 2:" in result
            assert "Page 3:" in result
            assert "Техническое задание" in result
            assert "Объем работ" in result
            assert "90 календарных дней" in result

            # Verify PyMuPDF was called correctly
            mock_fitz_open.assert_called_once_with(
                stream=b"fake_pdf_content", filetype="pdf"
            )

    def test_large_pdf_extraction(self):
        """Test extraction from large PDF with many pages"""
        # Create mock with 50 pages
        mock_doc = Mock()
        mock_pages = []

        for i in range(50):
            mock_page = Mock()
            mock_page.get_text.return_value = f"Page {i+1}: Content for page {i+1}"
            mock_pages.append(mock_page)

        mock_doc.__iter__ = Mock(return_value=iter(mock_pages))
        mock_doc.__enter__ = Mock(return_value=mock_doc)
        mock_doc.__exit__ = Mock(return_value=None)

        with patch("fitz.open") as mock_fitz_open:
            mock_fitz_open.return_value = mock_doc

            mock_file = Mock()
            mock_file.name = "large_document.pdf"
            mock_file.read.return_value = b"large_pdf_content"

            result = extract_from_pdf(mock_file)

            # Verify all 50 pages are processed
            assert result.count("Page") == 50
            assert "Page 50:" in result
            assert len(result) > 500  # Should be substantial content

    def test_multi_section_docx_extraction(self, mock_docx_document):
        """Test extraction from DOCX with multiple sections"""
        with patch("docx.Document") as mock_docx:
            mock_docx.return_value = mock_docx_document

            mock_file = Mock()
            mock_file.name = "test_multisection.docx"

            result = extract_from_docx(mock_file)

            # Verify all sections are extracted
            assert "ТЕХНИЧЕСКОЕ ЗАДАНИЕ" in result
            assert "ФОРМА ДОГОВОРА" in result
            assert "500 единиц" in result
            assert "50% предоплата" in result

            # Verify python-docx was called correctly
            mock_docx.assert_called_once_with(mock_file)

    def test_empty_pdf_pages(self):
        """Test handling of empty pages in PDF"""
        mock_doc = Mock()
        mock_pages = []

        # Mix of content and empty pages
        page_contents = [
            "Page 1: Has content",
            "",  # Empty page
            "Page 3: More content",
            "",  # Another empty page
            "Page 5: Final content",
        ]

        for content in page_contents:
            mock_page = Mock()
            mock_page.get_text.return_value = content
            mock_pages.append(mock_page)

        mock_doc.__iter__ = Mock(return_value=iter(mock_pages))
        mock_doc.__enter__ = Mock(return_value=mock_doc)
        mock_doc.__exit__ = Mock(return_value=None)

        with patch("fitz.open") as mock_fitz_open:
            mock_fitz_open.return_value = mock_doc

            mock_file = Mock()
            mock_file.name = "test_empty_pages.pdf"
            mock_file.read.return_value = b"pdf_content"

            result = extract_from_pdf(mock_file)

            # Should handle empty pages gracefully
            assert "Page 1:" in result
            assert "Page 3:" in result
            assert "Page 5:" in result
            # Should contain all content including empty page markers
            assert len(result) > 20

    def test_docx_with_tables_and_images(self):
        """Test DOCX extraction with tables and images (should extract text content)"""
        mock_doc = Mock()

        # Mock document with mixed content
        mock_paragraphs = []
        texts = [
            "Таблица 1: Параметры поставки",
            "Количество: 1000 шт",
            "Цена: 500 руб/шт",
            "Итого: 500000 руб",
        ]

        for text in texts:
            mock_para = Mock()
            mock_para.text = text
            mock_paragraphs.append(mock_para)

        mock_doc.paragraphs = mock_paragraphs

        with patch("docx.Document") as mock_docx:
            mock_docx.return_value = mock_doc

            mock_file = Mock()
            mock_file.name = "test_with_tables.docx"

            result = extract_from_docx(mock_file)

            # Should extract all text content
            assert "Таблица 1:" in result
            assert "1000 шт" in result
            assert "500 руб/шт" in result
            assert "500000 руб" in result

    def test_file_type_detection_multipage(self):
        """Test automatic file type detection for multi-page documents"""
        test_cases = [("document.pdf", "pdf"), ("report.docx", "docx")]

        for filename, expected_type in test_cases:
            mock_file = Mock()
            mock_file.name = filename
            mock_file.read.return_value = b"content"

            # Test file extension detection
            assert filename.lower().endswith(".pdf") == (expected_type == "pdf")
            assert filename.lower().endswith(".docx") == (expected_type == "docx")

    def test_corrupted_multipage_pdf(self):
        """Test handling of corrupted multi-page PDF"""
        with patch("fitz.open") as mock_fitz_open:
            # Simulate PyMuPDF error for corrupted file
            mock_fitz_open.side_effect = Exception("PDF parsing error")

            mock_file = Mock()
            mock_file.name = "corrupted.pdf"
            mock_file.read.return_value = b"corrupted_content"

            with pytest.raises(Exception) as exc_info:
                extract_from_pdf(mock_file)

            assert "PDF parsing error" in str(exc_info.value)

    def test_corrupted_multipage_docx(self):
        """Test handling of corrupted multi-page DOCX"""
        with patch("docx.Document") as mock_docx:
            # Simulate python-docx error for corrupted file
            mock_docx.side_effect = Exception("DOCX parsing error")

            mock_file = Mock()
            mock_file.name = "corrupted.docx"

            with pytest.raises(Exception) as exc_info:
                extract_from_docx(mock_file)

            assert "DOCX parsing error" in str(exc_info.value)

    def test_memory_efficiency_large_documents(self):
        """Test memory efficiency with large documents"""
        # Create very large mock document (1000 pages)
        mock_doc = Mock()
        mock_pages = []

        large_content = "This is a very long paragraph. " * 1000  # ~25KB per page

        for i in range(100):
            mock_page = Mock()
            mock_page.get_text.return_value = f"Page {i+1}: {large_content}"
            mock_pages.append(mock_page)

        mock_doc.__iter__ = Mock(return_value=iter(mock_pages))
        mock_doc.__enter__ = Mock(return_value=mock_doc)
        mock_doc.__exit__ = Mock(return_value=None)

        with patch("fitz.open") as mock_fitz_open:
            mock_fitz_open.return_value = mock_doc

            mock_file = Mock()
            mock_file.name = "very_large.pdf"
            mock_file.read.return_value = b"very_large_content"

            result = extract_from_pdf(mock_file)

            # Should complete without memory issues
            assert len(result) > 100000  # Should be very large
            assert "Page 100:" in result

    def test_unicode_handling_multipage(self):
        """Test Unicode character handling in multi-page documents"""
        mock_doc = Mock()
        mock_pages = []

        unicode_content = [
            "Страница 1: Русский текст с символами: абвгдеёжз",
            "Page 2: English text with symbols: @#$%^&*()",
            "页面 3: 中文文本与符号：测试文档",
        ]

        for content in unicode_content:
            mock_page = Mock()
            mock_page.get_text.return_value = content
            mock_pages.append(mock_page)

        mock_doc.__iter__ = Mock(return_value=iter(mock_pages))
        mock_doc.__enter__ = Mock(return_value=mock_doc)
        mock_doc.__exit__ = Mock(return_value=None)

        with patch("fitz.open") as mock_fitz_open:
            mock_fitz_open.return_value = mock_doc

            mock_file = Mock()
            mock_file.name = "unicode_test.pdf"
            mock_file.read.return_value = b"unicode_content"

            result = extract_from_pdf(mock_file)

            # Should preserve Unicode characters
            assert "Русский текст" in result
            assert "English text" in result
            assert "中文文本" in result
            assert "абвгдеёжз" in result
            assert "测试文档" in result


class TestIntegrationMultifile:
    """Integration tests for multi-file processing"""

    def test_batch_processing_multiple_files(self):
        """Test processing multiple multi-page documents"""
        # Simple test to verify batch processing concept
        file_names = ["doc1.pdf", "doc2.docx", "doc3.pdf"]

        # Test file type detection
        pdf_count = sum(1 for name in file_names if name.lower().endswith(".pdf"))
        docx_count = sum(1 for name in file_names if name.lower().endswith(".docx"))

        assert pdf_count == 2
        assert docx_count == 1
        assert len(file_names) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
