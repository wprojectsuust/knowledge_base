from pathlib import Path

from src.domain.official_document import OfficialDocument
from src.repositories.uust_documents_repository import parse_documents

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_parse_documents_reads_collapsed_sections_and_skips_menu_signatures_and_latest() -> None:
    documents = parse_documents((FIXTURES / "uust_documents.html").read_text(encoding="utf-8"))

    assert documents == [
        OfficialDocument(
            title="Приказ №1285 «Об утверждении Правил внутреннего распорядка обучающихся»",
            url="https://uust.ru/media/eduInfo/1285_22.05.2023_pvro.pdf",
            section="Локальные акты",
        ),
        OfficialDocument(
            title="Приказ №1905 «О внесении изменений в Правила внутреннего распорядка обучающихся»",
            url="https://uust.ru/media/eduInfo/1905_10.06.2024.pdf",
            section="Локальные акты",
        ),
        OfficialDocument(
            title="Протокол заседания Комиссии по переходу на бюджет от 28.09.2026 №1",
            url="https://uust.ru/media/eduInfo/protokol_1.pdf",
            section="Локальные акты",
            group="Результаты заседания комиссии по переходу с платного обучения на бесплатное",
        ),
        OfficialDocument(
            title="Заявление на материальную помощь",
            url="https://uust.ru/media/eduInfo/zayavlenie.docx",
            section="Шаблоны документов",
        ),
    ]


def test_parse_documents_returns_empty_list_for_unknown_layout() -> None:
    assert parse_documents("<html><body><p>Технические работы</p></body></html>") == []
