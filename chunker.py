import re
from typing import Any, Optional

import tiktoken

from src.logger import logger


class SemanticChunker:
    """Улучшенный чанкер с семантической нарезкой и лимитом по токенам."""

    def __init__(self, max_tokens: int = 1000, overlap: int = 100):
        """
        Инициализация чанкера.

        Args:
            max_tokens: Максимальное количество токенов в чанке
            overlap: Количество токенов перекрытия между чанками
        """
        self.max_tokens = max_tokens
        self.overlap = overlap
        self.encoding = tiktoken.get_encoding("cl100k_base")
        self.logger = logger

    def chunk_document(
        self, text: str, metadata: Optional[dict[str, Any]] = None
    ) -> list[dict[str, Any]]:
        """
        Семантическая нарезка документа с учетом лимита токенов.

        Args:
            text: Исходный текст документа
            metadata: Дополнительные метаданные документа

        Returns:
            List[Dict[str, Any]]: Список чанков с метаданными
        """
        if not text or not text.strip():
            self.logger.warning("Пустой документ для нарезки")
            return []

        try:
            # Очистка и предобработка текста
            cleaned_text = self._preprocess_text(text)

            # Определение семантических разделов
            sections = self._identify_semantic_sections(cleaned_text)

            # Нарезка на чанки с учетом лимита токенов
            chunks = self._create_token_limited_chunks(sections)

            # Добавление метаданных
            enriched_chunks = self._add_chunk_metadata(chunks, metadata or {})

            self.logger.info(f"Создано {len(enriched_chunks)} чанков из документа")
            return enriched_chunks

        except Exception as e:
            self.logger.error(f"Ошибка при нарезке документа: {str(e)}")
            return self._fallback_chunking(text)

    def _preprocess_text(self, text: str) -> str:
        """Предобработка текста для улучшения качества нарезки."""
        # Удаление лишних пробелов и переносов строк
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\n\s*\n", "\n\n", text)

        # Удаление специальных символов и нормализация
        text = text.strip()

        return text

    def _identify_semantic_sections(self, text: str) -> list[dict[str, Any]]:
        """Определение семантических разделов документа."""
        sections = []

        # Разделение по заголовкам и абзацам
        paragraphs = text.split("\n\n")

        current_section = {"title": "", "content": "", "type": "text"}

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Определение заголовков
            if self._is_heading(para):
                if current_section["content"]:
                    sections.append(current_section)
                current_section = {"title": para, "content": "", "type": "section"}
            else:
                if current_section["content"]:
                    current_section["content"] += " " + para
                else:
                    current_section["content"] = para

        if current_section["content"] or current_section["title"]:
            sections.append(current_section)

        return sections

    def _is_heading(self, text: str) -> bool:
        """Определение, является ли текст заголовком."""
        # Простые эвристики для определения заголовков
        if len(text) < 100 and text.endswith(":"):
            return True

        if re.match(r"^(?:\d+\.?\s*)?[A-Z][a-z\s]+$", text) and len(text) < 50:
            return True

        if text.isupper() and len(text) < 50:
            return True

        return False

    def _create_token_limited_chunks(
        self, sections: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Создание чанков с учетом лимита токенов."""
        chunks = []

        for section in sections:
            title = section["title"]
            content = section["content"]

            if not content and not title:
                continue

            # Подсчет токенов
            title_tokens = len(self.encoding.encode(title)) if title else 0
            content_tokens = len(self.encoding.encode(content))
            total_tokens = title_tokens + content_tokens

            if total_tokens <= self.max_tokens:
                # Весь раздел помещается в один чанк
                chunks.append(
                    {
                        "title": title,
                        "content": content,
                        "tokens": total_tokens,
                        "type": "complete",
                    }
                )
            else:
                # Разделение на подчанки
                sub_chunks = self._split_into_sub_chunks(
                    title, content, title_tokens, content_tokens
                )
                chunks.extend(sub_chunks)

        return chunks

    def _split_into_sub_chunks(
        self, title: str, content: str, title_tokens: int, content_tokens: int
    ) -> list[dict[str, Any]]:
        """Разделение большого раздела на подчанки."""
        chunks = []

        # Если заголовок сам по себе превышает лимит
        if title_tokens > self.max_tokens * 0.8:
            title_chunks = self._split_text_by_sentences(title, self.max_tokens // 2)
            for i, title_chunk in enumerate(title_chunks):
                chunks.append(
                    {
                        "title": f"{title} (часть {i+1})",
                        "content": "",
                        "tokens": len(self.encoding.encode(title_chunk)),
                        "type": "title_split",
                    }
                )

        # Разделение контента
        if content_tokens > 0:
            content_chunks = self._split_text_by_sentences(
                content, self.max_tokens - min(title_tokens, 100)
            )

            for i, content_chunk in enumerate(content_chunks):
                chunk_title = title if i == 0 else f"{title} (продолжение {i+1})"
                chunks.append(
                    {
                        "title": chunk_title,
                        "content": content_chunk,
                        "tokens": len(self.encoding.encode(chunk_title))
                        + len(self.encoding.encode(content_chunk)),
                        "type": "content_split",
                    }
                )

        return chunks

    def _split_text_by_sentences(self, text: str, max_tokens: int) -> list[str]:
        """Разделение текста на предложения с учетом лимита токенов."""
        sentences = self._split_into_sentences(text)
        chunks = []
        current_chunk = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = len(self.encoding.encode(sentence))

            if current_tokens + sentence_tokens <= max_tokens:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
            else:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))

                # Начинаем новый чанк с перекрытием
                if self.overlap > 0 and chunks:
                    overlap_sentences = (
                        current_chunk[-2:] if len(current_chunk) >= 2 else current_chunk
                    )
                    current_chunk = overlap_sentences + [sentence]
                    current_tokens = sum(
                        len(self.encoding.encode(s)) for s in current_chunk
                    )
                else:
                    current_chunk = [sentence]
                    current_tokens = sentence_tokens

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def _split_into_sentences(self, text: str) -> list[str]:
        """Разделение текста на предложения."""
        # Простое разделение по точкам, восклицательным и вопросительным знакам
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences

    def _add_chunk_metadata(
        self, chunks: list[dict[str, Any]], metadata: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Добавление метаданных к чанкам."""
        enriched_chunks = []

        for i, chunk in enumerate(chunks):
            enriched_chunk = {
                **chunk,
                "chunk_id": f"chunk_{i+1}",
                "chunk_index": i,
                "total_chunks": len(chunks),
                "metadata": {
                    **metadata,
                    "processing_timestamp": self._get_timestamp(),
                    "extraction_method": "semantic_chunking",
                },
            }
            enriched_chunks.append(enriched_chunk)

        return enriched_chunks

    def _get_timestamp(self) -> str:
        """Получение текущей временной метки."""
        from datetime import datetime

        return datetime.now().isoformat()

    def _fallback_chunking(self, text: str) -> list[dict[str, Any]]:
        """Fallback механизм при ошибке семантической нарезки."""
        self.logger.warning("Использование fallback механизма для нарезки")

        try:
            # Простое разделение по символам
            chunk_size = 1000  # ~1000 символов
            chunks = []

            for i in range(0, len(text), chunk_size):
                chunk_text = text[i : i + chunk_size]
                chunks.append(
                    {
                        "title": f"Раздел {i//chunk_size + 1}",
                        "content": chunk_text,
                        "tokens": len(self.encoding.encode(chunk_text)),
                        "type": "fallback",
                        "chunk_id": f"fallback_chunk_{i//chunk_size + 1}",
                        "chunk_index": i // chunk_size,
                        "total_chunks": (len(text) + chunk_size - 1) // chunk_size,
                    }
                )

            return chunks

        except Exception as e:
            self.logger.error(f"Ошибка в fallback механизме: {str(e)}")
            return []


# Обратная совместимость
def chunk_document(text: str) -> list:
    """Совместимая функция для обратной совместимости."""
    chunker = SemanticChunker()
    chunks = chunker.chunk_document(text)

    # Преобразование в старый формат
    return [{"title": chunk["title"], "content": chunk["content"]} for chunk in chunks]
