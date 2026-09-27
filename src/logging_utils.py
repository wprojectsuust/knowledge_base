def preview(text: str, limit: int = 200) -> str:
    """Обрезает текст для лога, чтобы длинный промпт/контент не заваливал вывод."""
    text = text.replace("\n", " ").strip()
    return text if len(text) <= limit else text[:limit] + "…"
