import hashlib
from dataclasses import dataclass
from itertools import groupby

from src.domain.data import Data

DOCUMENTS_PAGE_URL = "https://uust.ru/sveden/document/"


@dataclass(frozen=True, kw_only=True)
class OfficialDocument:
    """Документ со страницы «Документы» сайта вуза: название и ссылка (сам файл не качаем),
    раздел-аккордеон и подраздел внутри него (может быть пустым)."""

    title: str
    url: str
    section: str
    group: str = ""


def document_batches(documents: list[OfficialDocument], size: int) -> list[Data]:
    """Режет список на записи базы знаний по `size` документов - по одной на каждый документ было бы
    ~1000 LLM-вызовов. Разделы/подразделы не смешиваются: их название - контекст для поиска.

    source = адрес страницы + хэш содержимого: изменилась порция - изменился source, импорт
    загружает новую и удаляет устаревшую; не изменилась - ни одного вызова LLM."""
    batches = []
    for (section, group), items in groupby(documents, key=lambda doc: (doc.section, doc.group)):
        items = list(items)
        heading = f"«{section}» / «{group}»" if group else f"«{section}»"
        for start in range(0, len(items), size):
            lines = "\n".join(f"- {doc.title}: {doc.url}" for doc in items[start : start + size])
            content = f"Официальные документы УУНиТ ({DOCUMENTS_PAGE_URL}), раздел {heading}:\n{lines}"
            digest = hashlib.sha1(content.encode()).hexdigest()[:12]
            batches.append(Data(source=f"{DOCUMENTS_PAGE_URL}#{digest}", content=content))
    return batches
