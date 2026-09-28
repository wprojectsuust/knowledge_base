from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class ClarificationRequest:
    """ИИ не может ответить без сведений о самом студенте и просит систему их уточнить.

    field - машинное имя сведения (group, faculty, course, ...), по нему фронт запоминает ответ;
    question - что показать студенту."""

    field: str
    question: str


@dataclass(frozen=True, kw_only=True)
class KnownFact:
    """Уже известное сведение о студенте (ответ на ClarificationRequest)."""

    field: str
    value: str


def compose_question(question: str, facts: list[KnownFact]) -> str:
    """Склеивает вопрос с известными сведениями о студенте в один текст для пайплайна."""
    if not facts:
        return question
    lines = "\n".join(f"- {fact.field}: {fact.value}" for fact in facts)
    return f"{question}\n\nИзвестно о студенте:\n{lines}"
