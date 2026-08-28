"""Tests for CSV extraction support in document intake flow."""

from io import BytesIO

import pytest

from extractor import extract_text_from_file


def _csv_file(content: bytes, name: str = "tender.csv") -> BytesIO:
    file_obj = BytesIO(content)
    file_obj.name = name
    return file_obj


def test_extract_comma_delimited_csv() -> None:
    file_obj = _csv_file(b"item,quantity,unit\ncement,100,bag\nbrick,250,piece")

    extracted = extract_text_from_file(file_obj)

    assert extracted == (
        "item | quantity | unit\ncement | 100 | bag\nbrick | 250 | piece"
    )


def test_extract_semicolon_delimited_csv() -> None:
    file_obj = _csv_file(b"item;quantity;unit\ncement;100;bag\nbrick;250;piece")

    extracted = extract_text_from_file(file_obj)

    assert extracted == (
        "item | quantity | unit\ncement | 100 | bag\nbrick | 250 | piece"
    )


def test_extract_utf8_bom_csv() -> None:
    file_obj = _csv_file("\ufeffsection,match\nТехническое задание,да".encode("utf-8"))

    extracted = extract_text_from_file(file_obj)

    assert extracted == "section | match\nТехническое задание | да"


def test_empty_csv_raises_explicit_error() -> None:
    file_obj = _csv_file(b"")

    with pytest.raises(ValueError, match="CSV файл пуст"):
        extract_text_from_file(file_obj)


def test_malformed_csv_raises_explicit_error() -> None:
    file_obj = _csv_file(b'item,quantity\n"cement,100')

    with pytest.raises(ValueError, match="Некорректный CSV формат"):
        extract_text_from_file(file_obj)


def test_invalid_utf8_csv_raises_explicit_error() -> None:
    file_obj = _csv_file(b"\xff\xfe\xfa\xfd")

    with pytest.raises(ValueError, match="кодировке UTF-8"):
        extract_text_from_file(file_obj)


def test_csv_extraction_with_read_only_wrapper() -> None:
    class ReadOnlyUpload:
        def __init__(self, name: str, content: bytes) -> None:
            self.name = name
            self._content = content

        def read(self) -> bytes:
            return self._content

    file_obj = ReadOnlyUpload("tender.csv", b"item,quantity\ncement,100")

    extracted = extract_text_from_file(file_obj)

    assert extracted == "item | quantity\ncement | 100"
