"""
УУНиТ — единый Enum подразделений (институты, факультеты, филиалы,
школы, центры, СПО/колледжи).

Сущность называется Division — нейтральное слово, покрывающее все типы
подразделений. Тип хранится в поле kind (DivisionKind).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DivisionKind(str, Enum):
    INSTITUTE = "institute"  # институты
    FACULTY = "faculty"  # факультеты
    BRANCH = "branch"  # филиалы
    SCHOOL = "school"  # передовая инженерная школа
    CENTER = "center"  # военный учебный центр
    COLLEGE = "college"  # СПО, колледжи, отделения СПО


@dataclass(frozen=True)
class DivisionInfo:
    title: str  # человекочитаемое название
    short: Optional[str]  # аббревиатура / короткое имя
    slug: str  # машинный код
    kind: DivisionKind  # тип подразделения
    url: str  # ссылка

    @property
    def label(self) -> str:
        return f"{self.title} / {self.short}" if self.short else self.title


class UustDivision(Enum):
    # --- Институты ---
    IGS = DivisionInfo(
        "Институт гуманитарных и социальных наук", "ИГСН",
        "igsn", DivisionKind.INSTITUTE, "/education/igsn/",
    )
    IIMRT = DivisionInfo(
        "Институт информатики, математики и робототехники", "ИИМРТ",
        "iimrt", DivisionKind.INSTITUTE, "/education/iimrt/",
    )
    IIGU = DivisionInfo(
        "Институт истории и государственного управления", "ИИГУ",
        "iigu", DivisionKind.INSTITUTE, "/education/iigu/",
    )
    IP = DivisionInfo(
        "Институт права", None,
        "ip", DivisionKind.INSTITUTE, "/education/ip/",
    )
    IPCH = DivisionInfo(
        "Институт природы и человека", "ИПЧ",
        "ipch", DivisionKind.INSTITUTE, "/education/ipch/",
    )
    ITM = DivisionInfo(
        "Институт технологий и материалов", "ИТМ",
        "itm", DivisionKind.INSTITUTE, "/education/itm/",
    )
    IHZCHS = DivisionInfo(
        "Институт химии и защиты в чрезвычайных ситуациях", "ИХЗЧС",
        "ihzchs", DivisionKind.INSTITUTE, "/education/ihzchs/",
    )
    INEB = DivisionInfo(
        "Институт экономики, управления и бизнеса", "ИНЭБ",
        "ineb", DivisionKind.INSTITUTE, "/education/ineb/",
    )
    IETI = DivisionInfo(
        "Институт электротехнического инжиниринга", "ИЭТИ",
        "ieti", DivisionKind.INSTITUTE, "/education/ieti/",
    )
    FTI = DivisionInfo(
        "Физико-технический институт", "ФТИ",
        "fti", DivisionKind.INSTITUTE, "/education/fti/",
    )

    # --- Факультеты, школа, центр ---
    VUC = DivisionInfo(
        "Военный учебный центр", "ВУЦ",
        "vuc", DivisionKind.CENTER, "/education/vuc/",
    )
    PISH = DivisionInfo(
        "Передовая инженерная школа «Моторы будущего»", None,
        "pish", DivisionKind.SCHOOL, "/education/pish/",
    )
    FADET = DivisionInfo(
        "Факультет авиационных двигателей, энергетики и транспорта", "ФАДЭТ",
        "fadet", DivisionKind.FACULTY, "/education/fadet/",
    )
    FBFVIZH = DivisionInfo(
        "Факультет башкирской филологии, востоковедения и журналистики", "ФБФВиЖ",
        "fbfvizh", DivisionKind.FACULTY, "/education/fbfvizh/",
    )
    FPIK = DivisionInfo(
        "Факультет подготовки инженерных кадров при «ОДК-УМПО»", None,
        "fpik", DivisionKind.FACULTY, "/education/fpik/",
    )

    # --- Филиалы ---
    BIRSK = DivisionInfo(
        "Бирский филиал", None,
        "branch-birsk", DivisionKind.BRANCH, "https://birsk.uust.ru/",
    )
    ISHIMBAY = DivisionInfo(
        "Филиал в г. Ишимбае", None,
        "branch-ishimbay", DivisionKind.BRANCH, "/education/branch-ishimbay",
    )
    KUMERTAU = DivisionInfo(
        "Филиал в г. Кумертау", None,
        "branch-kumertau", DivisionKind.BRANCH, "/education/branch-kumertau",
    )
    NEFTEKAMSK = DivisionInfo(
        "Нефтекамский филиал", None,
        "branch-neftekamsk", DivisionKind.BRANCH, "https://nf.uust.ru/",
    )
    SIBAY = DivisionInfo(
        "Сибайский институт", None,
        "branch-sibay", DivisionKind.BRANCH, "/education/branch-sibay/",
    )
    STERLITAMAK = DivisionInfo(
        "Стерлитамакский филиал", None,
        "branch-sterlitamak", DivisionKind.BRANCH, "/education/branch-sterlitamak/",
    )

    # --- Среднее профессиональное образование ---
    ISPO = DivisionInfo(
        "Институт среднего профессионального образования", "ИСПО",
        "ispo", DivisionKind.COLLEGE, "https://uust.ru/ispo/",
    )
    SPO_ISHIMBAY = DivisionInfo(
        "Отделение СПО в г. Ишимбае", None,
        "spo-ishimbay", DivisionKind.COLLEGE, "https://uust.ru/if/",
    )
    SPO_KUMERTAU = DivisionInfo(
        "Отделение СПО филиала г. Кумертау «Авиационный технический колледж»", None,
        "spo-kumertau", DivisionKind.COLLEGE, "https://uust.ru/kumertau/",
    )
    COLLEGE_STERLITAMAK = DivisionInfo(
        "Колледж в г. Стерлитамак", None,
        "college-sterlitamak", DivisionKind.COLLEGE, "/education/branch-sterlitamak/",
    )
    COLLEGE_BIRSK = DivisionInfo(
        "Колледж в Бирске", None,
        "college-birsk", DivisionKind.COLLEGE, "https://birsk.uust.ru",
    )
    COLLEGE_NEFTEKAMSK = DivisionInfo(
        "Колледж Нефтекамского филиала", None,
        "college-neftekamsk", DivisionKind.COLLEGE, "https://nf.uust.ru/c-833",
    )

    @property
    def info(self) -> DivisionInfo:
        return self.value

    @property
    def title(self) -> str:
        return self.value.title

    @property
    def short(self) -> Optional[str]:
        return self.value.short

    @property
    def slug(self) -> str:
        return self.value.slug

    @property
    def kind(self) -> DivisionKind:
        return self.value.kind

    @property
    def url(self) -> str:
        return self.value.url

    @property
    def label(self) -> str:
        return self.value.label


def divisions_by_kind(kind: DivisionKind) -> list[UustDivision]:
    return [d for d in UustDivision if d.kind is kind]


def divisions_by_slug() -> dict[str, UustDivision]:
    return {d.slug: d for d in UustDivision}


if __name__ == "__main__":
    for d in UustDivision:
        print(f"{d.kind.value:9} | {d.slug:22} | {d.label}")
