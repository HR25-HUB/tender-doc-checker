import csv
import io
from pathlib import Path

import docx
import fitz  # PyMuPDF

from src.logger import logger


class DocumentExtractor:
    """Улучшенный извлекатель текста из документов с обработкой ошибок и fallback-механизмами."""

    def __init__(self):
        self.supported_formats = {".pdf", ".docx", ".txt", ".md", ".rtf", ".csv"}
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.logger = logger

    def extract_text_from_file(self, file, filename: str | None = None) -> str:
        """
        Извлечение текста из файла с улучшенной обработкой ошибок.

        Args:
            file: Файловый объект
            filename: Имя файла для определения формата

        Returns:
            str: Извлеченный текст

        Raises:
            ValueError: Неподдерживаемый формат или поврежденный файл
            IOError: Ошибки чтения файла
        """
        try:
            if not file:
                raise ValueError("Файл не предоставлен")

            # Определение формата файла
            detected_filename = filename
            if not detected_filename and hasattr(file, "name"):
                file_name_attr = file.name
                if isinstance(file_name_attr, str):
                    detected_filename = file_name_attr

            if detected_filename:
                file_extension = Path(detected_filename).suffix.lower()
            else:
                # Fallback: попытка определить по содержимому
                file_extension = self._detect_file_format(file)

            if file_extension not in self.supported_formats:
                self.logger.warning(f"Неподдерживаемый формат файла: {file_extension}")
                return self._extract_text_fallback(file)

            # Проверка размера файла
            content: bytes | None = None
            try:
                file.seek(0, 2)  # Переход в конец
                file_size = file.tell()
                file.seek(0)  # Возврат в начало
            except (AttributeError, OSError, TypeError):
                content = file.read()
                file_size = len(content)

            if file_size > self.max_file_size:
                self.logger.warning(f"Файл слишком большой: {file_size} байт")
                return self._extract_text_large_file(file, file_extension)

            # Извлечение текста в зависимости от формата
            if content is None:
                content = file.read()
                try:
                    file.seek(0)  # Возврат в начало для повторного использования
                except (AttributeError, OSError, TypeError):
                    pass

            if file_extension == ".pdf":
                return self._extract_from_pdf_safe(content, detected_filename)
            elif file_extension == ".docx":
                return self._extract_from_docx_safe(content, detected_filename)
            elif file_extension == ".csv":
                return self._extract_from_csv_safe(content, detected_filename)
            else:
                return self._extract_text_plain(content)

        except ValueError as e:
            self.logger.error(f"Ошибка извлечения текста из файла {filename}: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Ошибка извлечения текста из файла {filename}: {str(e)}")
            return self._extract_text_fallback(file)

    def _detect_file_format(self, file) -> str:
        """Определение формата файла по сигнатуре."""
        try:
            header = file.read(1024)
            file.seek(0)

            if header.startswith(b"%PDF"):
                return ".pdf"
            elif header.startswith(b"PK\x03\x04"):
                return ".docx"
            elif b"<?xml" in header[:100]:
                return ".xml"
            else:
                return ".txt"
        except Exception:
            return ".txt"

    def _extract_from_pdf_safe(
        self, content: bytes, filename: str | None = None
    ) -> str:
        """Безопасное извлечение текста из PDF с обработкой ошибок."""
        try:
            with fitz.open(stream=content, filetype="pdf") as doc:
                if doc.page_count == 0:
                    raise ValueError("PDF документ пуст")

                text_parts = []
                for page_num, page in enumerate(doc):
                    try:
                        page_text = page.get_text()
                        if page_text.strip():
                            text_parts.append(page_text)
                        else:
                            self.logger.warning(
                                f"Страница {page_num + 1} в {filename or 'PDF'} пустая"
                            )
                    except Exception as e:
                        self.logger.error(
                            f"Ошибка чтения страницы {page_num + 1}: {str(e)}"
                        )
                        continue

                if not text_parts:
                    raise ValueError("Не удалось извлечь текст из PDF")

                return "\n".join(text_parts)

        except fitz.FileDataError as e:
            self.logger.error(f"Поврежденный PDF файл: {str(e)}")
            return self._extract_text_pdf_fallback(content)
        except Exception as e:
            self.logger.error(f"Ошибка извлечения из PDF: {str(e)}")
            return self._extract_text_pdf_fallback(content)

    def _extract_from_docx_safe(
        self, content: bytes, filename: str | None = None
    ) -> str:
        """Безопасное извлечение текста из DOCX с обработкой ошибок."""
        try:
            # Создаем временный файл для docx
            import os
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp_file:
                tmp_file.write(content)
                tmp_path = tmp_file.name

            try:
                doc = docx.Document(tmp_path)
                paragraphs = [
                    para.text.strip() for para in doc.paragraphs if para.text.strip()
                ]

                if not paragraphs:
                    # Fallback: извлечение из таблиц
                    tables_text = []
                    for table in doc.tables:
                        for row in table.rows:
                            for cell in row.cells:
                                if cell.text.strip():
                                    tables_text.append(cell.text.strip())

                    if tables_text:
                        return "\n".join(tables_text)
                    else:
                        raise ValueError("DOCX документ не содержит текста")

                return "\n".join(paragraphs)

            finally:
                os.unlink(tmp_path)

        except docx.opc.exceptions.PackageNotFoundError as e:
            self.logger.error(f"Поврежденный DOCX файл: {str(e)}")
            return self._extract_text_docx_fallback(content)
        except Exception as e:
            self.logger.error(f"Ошибка извлечения из DOCX: {str(e)}")
            return self._extract_text_docx_fallback(content)

    def _extract_text_plain(self, content: bytes) -> str:
        """Извлечение текста из plain text файлов."""
        try:
            # Попытка декодирования с разными кодировками
            encodings = ["utf-8", "utf-16", "cp1251", "iso-8859-1"]

            for encoding in encodings:
                try:
                    return content.decode(encoding)
                except UnicodeDecodeError:
                    continue

            # Последний fallback
            return content.decode("utf-8", errors="ignore")

        except Exception as e:
            self.logger.error(f"Ошибка декодирования текста: {str(e)}")
            return ""

    def _extract_from_csv_safe(
        self, content: bytes, filename: str | None = None
    ) -> str:
        """Безопасное извлечение текста из CSV."""
        decoded_text = content.decode("utf-8-sig")
        if not decoded_text.strip():
            raise ValueError("CSV файл пуст")

        lines = [line for line in decoded_text.splitlines() if line.strip()]
        sample = "\n".join(lines[:5])

        delimiter = ","
        if ";" in sample and "," not in sample:
            delimiter = ";"
        elif "," in sample and ";" in sample:
            try:
                delimiter = csv.Sniffer().sniff(sample, delimiters=",;").delimiter
            except csv.Error:
                delimiter = ","

        try:
            reader = csv.reader(
                io.StringIO(decoded_text),
                delimiter=delimiter,
                quotechar='"',
                strict=True,
            )
            normalized_rows = []
            for row in reader:
                stripped_row = [cell.strip() for cell in row]
                if any(cell for cell in stripped_row):
                    normalized_rows.append(" | ".join(stripped_row))
        except csv.Error as e:
            raise ValueError(f"Некорректный CSV формат: {str(e)}") from e

        if not normalized_rows:
            error_target = filename or "CSV"
            raise ValueError(f"{error_target} не содержит извлекаемых данных")

        return "\n".join(normalized_rows)

    def _extract_text_large_file(self, file, file_extension: str) -> str:
        """Обработка больших файлов с ограничением по памяти."""
        self.logger.info("Обработка большого файла с chunking'ом")

        try:
            chunk_size = 1024 * 1024  # 1MB chunks
            text_parts = []

            if file_extension == ".pdf":
                # Для PDF используем постраничную обработку
                return self._extract_from_pdf_safe(file.read(), "large_file.pdf")
            elif file_extension == ".csv":
                return self._extract_from_csv_safe(file.read(), "large_file.csv")
            else:
                # Для других форматов читаем по частям
                while True:
                    chunk = file.read(chunk_size)
                    if not chunk:
                        break
                    text_parts.append(self._extract_text_plain(chunk))

                return "".join(text_parts)

        except Exception as e:
            self.logger.error(f"Ошибка обработки большого файла: {str(e)}")
            return ""

    def _extract_text_fallback(self, file) -> str:
        """Fallback механизм для извлечения текста при всех ошибках."""
        try:
            content = file.read()
            return self._extract_text_plain(content)
        except Exception as e:
            self.logger.error(f"Критическая ошибка в fallback механизме: {str(e)}")
            return ""

    def _extract_text_pdf_fallback(self, content: bytes) -> str:
        """Fallback для PDF с использованием альтернативных методов."""
        try:
            # Попытка извлечения текста как plain text
            text = content.decode("utf-8", errors="ignore")
            if len(text) > 100:  # Минимальная длина для считывания как текста
                return text
            return ""
        except Exception:
            return ""

    def _extract_text_docx_fallback(self, content: bytes) -> str:
        """Fallback для DOCX с использованием альтернативных методов."""
        try:
            # Простое извлечение текста из XML
            import re

            text = content.decode("utf-8", errors="ignore")

            # Ищем текст между тегами <w:t>
            pattern = r"<w:t[^>]*>([^<]+)</w:t>"
            matches = re.findall(pattern, text)

            if matches:
                return " ".join(matches)
            return ""
        except Exception:
            return ""


# Обратная совместимость - функции-обертки
def extract_text_from_file(file) -> str:
    """Совместимая функция для обратной совместимости."""
    extractor = DocumentExtractor()
    return extractor.extract_text_from_file(file)


def extract_from_pdf(file) -> str:
    """Совместимая функция для обратной совместимости."""
    extractor = DocumentExtractor()
    return extractor.extract_text_from_file(file, "document.pdf")


def extract_from_docx(file) -> str:
    """Совместимая функция для обратной совместимости."""
    extractor = DocumentExtractor()
    return extractor.extract_text_from_file(file, "document.docx")
