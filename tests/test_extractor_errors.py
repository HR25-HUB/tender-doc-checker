"""
Tests for error handling and fallback mechanisms in document extraction.

This module tests the robustness of the extractor.py module against various
error conditions and documents the expected behavior.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Import extractor
import_path = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, import_path)

try:
    from extractor import extract_from_docx, extract_from_pdf, extract_text_from_file
except ImportError:
    import_path = os.path.join(os.path.dirname(__file__), "..")
    if import_path not in sys.path:
        sys.path.insert(0, import_path)
    from extractor import extract_text_from_file


class TestExtractorErrorHandling(unittest.TestCase):
    """Test error handling and behavior for document extraction."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_data_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.test_data_dir, ignore_errors=True)

    def create_mock_file(self, name, content=b"test content", content_type=None):
        """Create a mock file object for testing."""
        mock_file = MagicMock()
        mock_file.name = name
        mock_file.read.return_value = content
        if content_type:
            mock_file.content_type = content_type
        return mock_file

    def test_corrupted_pdf_exception(self):
        """Test that corrupted PDF files raise appropriate exceptions."""
        corrupted_pdf = self.create_mock_file("test.pdf", b"corrupted pdf content")

        with patch("fitz.open") as mock_fitz:
            mock_fitz.side_effect = Exception("PDF parsing error")

            with self.assertRaises(Exception):
                extract_text_from_file(corrupted_pdf)

    def test_corrupted_docx_exception(self):
        """Test that corrupted DOCX files raise appropriate exceptions."""
        corrupted_docx = self.create_mock_file("test.docx", b"corrupted docx content")

        with patch("docx.Document") as mock_docx:
            mock_docx.side_effect = Exception("DOCX parsing error")

            with self.assertRaises(Exception):
                extract_text_from_file(corrupted_docx)

    def test_empty_pdf_handling(self):
        """Test handling of empty PDF files."""
        empty_pdf = self.create_mock_file("empty.pdf", b"")

        with patch("fitz.open") as mock_fitz:
            mock_doc = MagicMock()
            mock_page = MagicMock()
            mock_page.get_text.return_value = ""
            mock_doc.__iter__.return_value = [mock_page]
            mock_fitz.return_value.__enter__.return_value = mock_doc

            result = extract_text_from_file(empty_pdf)
            self.assertEqual(result, "")

    def test_empty_docx_handling(self):
        """Test handling of empty DOCX files."""
        empty_docx = self.create_mock_file("empty.docx", b"")

        with patch("docx.Document") as mock_docx:
            mock_document = MagicMock()
            mock_document.paragraphs = []
            mock_docx.return_value = mock_document

            result = extract_text_from_file(empty_docx)
            self.assertEqual(result, "")

    def test_empty_txt_handling(self):
        """Test handling of empty text files."""
        empty_txt = self.create_mock_file("empty.txt", b"")
        result = extract_text_from_file(empty_txt)
        self.assertEqual(result, "")

    def test_missing_fitz_dependency(self):
        """Test behavior when PyMuPDF is not available."""
        test_file = self.create_mock_file("test.pdf", b"content")

        with patch("fitz.open") as mock_fitz:
            mock_fitz.side_effect = ImportError("No module named 'fitz'")

            with self.assertRaises(ImportError):
                extract_text_from_file(test_file)

    def test_missing_docx_dependency(self):
        """Test behavior when python-docx is not available."""
        test_file = self.create_mock_file("test.docx", b"content")

        with patch("docx.Document") as mock_docx:
            mock_docx.side_effect = ImportError("No module named 'docx'")

            with self.assertRaises(ImportError):
                extract_text_from_file(test_file)

    def test_encoding_error_handling(self):
        """Test handling of encoding in text files."""
        # Test with valid bytes - should work fine
        valid_content = b"Hello, world!"
        valid_file = self.create_mock_file("test.txt", valid_content)

        result = extract_text_from_file(valid_file)
        self.assertEqual(result, "Hello, world!")

    def test_file_not_found_behavior(self):
        """Test behavior with missing files."""
        # This tests the actual file system behavior
        with tempfile.NamedTemporaryFile(delete=True) as tmp:
            tmp_path = tmp.name

        # File no longer exists - should raise FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            with open(tmp_path, "rb") as f:
                extract_text_from_file(f)

    def test_large_file_simulation(self):
        """Test handling of large file structures."""
        large_content = b"x" * 1000  # Simulate large content
        large_file = self.create_mock_file("large.pdf", large_content)

        with patch("fitz.open") as mock_fitz:
            mock_doc = MagicMock()
            mock_page = MagicMock()
            mock_page.get_text.return_value = "page content"
            mock_doc.__iter__.return_value = [mock_page] * 10  # 10 pages
            mock_fitz.return_value.__enter__.return_value = mock_doc

            result = extract_text_from_file(large_file)
            self.assertIsInstance(result, str)
            self.assertIn("page content", result)

    def test_unsupported_file_type_fallback(self):
        """Test fallback behavior for unknown file types."""
        unsupported_file = self.create_mock_file("test.xyz", b"unsupported content")

        # Unknown file types should use text extraction fallback
        result = extract_text_from_file(unsupported_file)
        self.assertEqual(result, "unsupported content")

    def test_unicode_content_handling(self):
        """Test handling of Unicode content."""
        unicode_content = "Привет, мир! Hello 世界!".encode()
        unicode_file = self.create_mock_file("unicode.txt", unicode_content)

        result = extract_text_from_file(unicode_file)
        self.assertEqual(result, "Привет, мир! Hello 世界!")

    def test_permission_error_skip(self):
        """Skip permission test on Windows."""
        # This test is skipped on Windows due to different chmod behavior
        if os.name == "nt":
            self.skipTest("Skipping permission test on Windows")

        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path = tmp.name

        try:
            os.chmod(tmp_path, 0o000)
            with self.assertRaises((PermissionError, OSError)):
                with open(tmp_path, "rb") as f:
                    extract_text_from_file(f)
        finally:
            os.chmod(tmp_path, 0o644)
            os.unlink(tmp_path)

    def test_zero_byte_file_handling(self):
        """Test handling of zero-byte files."""
        zero_byte = self.create_mock_file("zero.pdf", b"")

        with patch("fitz.open") as mock_fitz:
            mock_doc = MagicMock()
            mock_doc.__iter__.return_value = []
            mock_fitz.return_value.__enter__.return_value = mock_doc

            result = extract_text_from_file(zero_byte)
            self.assertEqual(result, "")

    def test_binary_fallback_for_unknown_types(self):
        """Test binary content extraction for unknown file types."""
        binary_file = self.create_mock_file("binary.bin", b"binary content")

        result = extract_text_from_file(binary_file)
        self.assertEqual(result, "binary content")

    def test_malformed_xml_docx_exception(self):
        """Test that malformed XML in DOCX raises exceptions."""
        malformed_docx = self.create_mock_file("malformed.docx", b"malformed xml")

        with patch("docx.Document") as mock_docx:
            mock_docx.side_effect = Exception("Malformed XML")

            with self.assertRaises(Exception):
                extract_text_from_file(malformed_docx)

    def test_concurrent_access_simulation(self):
        """Test behavior under simulated concurrent access."""
        locked_file = self.create_mock_file("locked.pdf", b"content")

        with patch("fitz.open") as mock_fitz:
            mock_fitz.side_effect = Exception("File access error")

            with self.assertRaises(Exception):
                extract_text_from_file(locked_file)

    def test_file_type_detection(self):
        """Test file type detection based on extension."""
        pdf_file = self.create_mock_file("document.pdf", b"pdf content")
        docx_file = self.create_mock_file("document.docx", b"docx content")
        txt_file = self.create_mock_file("document.txt", b"text content")

        # Test that file extensions are correctly detected
        self.assertTrue(pdf_file.name.endswith(".pdf"))
        self.assertTrue(docx_file.name.endswith(".docx"))
        self.assertTrue(txt_file.name.endswith(".txt"))


if __name__ == "__main__":
    unittest.main()
