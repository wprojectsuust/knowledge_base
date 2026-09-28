from src.domain.division import DivisionInfo, DivisionKind, UustDivision, detect_division, divisions_by_kind, divisions_by_slug


def test_label_includes_short_name_when_present() -> None:
    info = DivisionInfo(title="Институт права", short="ИП", slug="ip", kind=DivisionKind.INSTITUTE, url="/ip/")

    assert info.label == "Институт права / ИП"


def test_label_falls_back_to_title_without_short_name() -> None:
    info = DivisionInfo(title="Институт права", short=None, slug="ip", kind=DivisionKind.INSTITUTE, url="/ip/")

    assert info.label == "Институт права"


def test_uust_division_properties_proxy_to_info() -> None:
    division = UustDivision.IP

    assert division.info == division.value
    assert division.title == "Институт права"
    assert division.short is None
    assert division.slug == "ip"
    assert division.kind == DivisionKind.INSTITUTE
    assert division.url == "/education/ip/"
    assert division.label == "Институт права"


def test_divisions_by_kind_filters_correctly() -> None:
    branches = divisions_by_kind(DivisionKind.BRANCH)

    assert UustDivision.BIRSK in branches
    assert UustDivision.IP not in branches
    assert all(d.kind is DivisionKind.BRANCH for d in branches)


def test_divisions_by_slug_is_keyed_by_slug_and_covers_everything() -> None:
    by_slug = divisions_by_slug()

    assert by_slug["ip"] is UustDivision.IP
    assert len(by_slug) == len(list(UustDivision))


def test_detect_division_matches_short_abbreviation() -> None:
    assert detect_division("Где находится деканат ИИМРТ?") == UustDivision.IIMRT


def test_detect_division_matches_extra_keyword() -> None:
    assert detect_division("что нужно чтобы попасть в клуб моторы будущего") == UustDivision.PISH


def test_detect_division_prefers_longer_keyword_match() -> None:
    assert detect_division("расписание иимрт") == UustDivision.IIMRT


def test_detect_division_returns_none_when_nothing_matches() -> None:
    assert detect_division("когда стипендия") is None


def test_short_abbreviations_do_not_match_inside_ordinary_words() -> None:
    from src.domain.division import detect_division

    # раньше «испо» находилось в «использовать», «пиш» в «напишите», «итм» в «алгоритм»
    assert detect_division("как использовать электронную библиотеку") is None
    assert detect_division("напишите, куда обращаться") is None
    assert detect_division("где проходит курс по алгоритмам") is None


def test_abbreviation_still_matches_as_a_separate_word() -> None:
    from src.domain.division import detect_division

    assert detect_division("институт ИТМ где находится").slug == "itm"
    assert detect_division("деканат ФИРТ,") is not None
