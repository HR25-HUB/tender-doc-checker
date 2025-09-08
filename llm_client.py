import json
import os

from openai import OpenAI


def get_openai_client() -> OpenAI:
    """Получить клиент OpenAI с ленивой инициализацией."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY не установлен")
    return OpenAI(api_key=api_key)


def query_llm(prompt: str) -> dict[str, str]:
    """Запрос к LLM для анализа документа."""
    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4", messages=[{"role": "user", "content": prompt}], temperature=0
        )
        content = response.choices[0].message.content
        if content and content.startswith("{"):
            return json.loads(content)
        else:
            return {"match": "неопределено", "comments": content or ""}
    except Exception:
        return {"match": "неопределено", "comments": "Ошибка обработки"}
