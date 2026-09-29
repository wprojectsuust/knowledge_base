from src.domain.official_document import DOCUMENTS_PAGE_URL, OfficialDocument, document_batches


def _doc(n: int, section: str = "Локальные акты", group: str = "") -> OfficialDocument:
    return OfficialDocument(title=f"Положение №{n}", url=f"https://uust.ru/media/{n}.pdf", section=section, group=group)


def test_batch_lists_titles_with_links_under_section_heading() -> None:
    [batch] = document_batches([_doc(1), _doc(2)], size=10)

    assert batch.source.startswith(DOCUMENTS_PAGE_URL)
    assert "раздел «Локальные акты»" in batch.content
    assert "- Положение №1: https://uust.ru/media/1.pdf" in batch.content
    assert "- Положение №2: https://uust.ru/media/2.pdf" in batch.content


def test_splits_long_sections_and_never_mixes_sections_or_groups() -> None:
    docs = [_doc(n) for n in range(5)] + [_doc(9, group="Правила приёма"), _doc(10, section="Шаблоны документов")]

    batches = document_batches(docs, size=2)

    assert len(batches) == 5  # 2+2+1 локальных актов, 1 правил приёма, 1 шаблон
    assert "«Локальные акты» / «Правила приёма»" in batches[3].content
    assert "Шаблоны документов" in batches[4].content


def test_source_changes_only_when_batch_content_changes() -> None:
    first = document_batches([_doc(1), _doc(2)], size=10)
    same = document_batches([_doc(1), _doc(2)], size=10)
    changed = document_batches([_doc(1), _doc(3)], size=10)

    assert first[0].source == same[0].source
    assert first[0].source != changed[0].source
