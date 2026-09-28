from __future__ import annotations

import datetime as dt
import json
import logging
import re
from pathlib import Path

from src.domain.schedule import DaySchedule, ScheduleLesson

logger = logging.getLogger(__name__)

_GROUPS_PATH = Path(__file__).resolve().parent / "isu_groups.json"
_SCHEDULE_URL = "https://www.isu.uust.ru/module/schedule/schedule_2024_script.php"

# Извлечение места проведения из текста пары. Реальный формат ИСУ - "Корпус <N> - <комната>"
# (например "Корпус 7 - 404") - сворачиваем в привычное "кабинет N-комната". Остальные два
# паттерна - запасной вариант на случай другого формата ячейки.
_BUILDING_ROOM_PATTERN = re.compile(r"[Кк]орпус\s*№?\s*(\d+)\s*-\s*(\d+\w*)")
_VENUE_PATTERN = re.compile(r"(ауд\.?\s?\d+\w*|каб\.?\s?\d+\w*|корпус\s?№?\s?\d+)", re.IGNORECASE)


# Латинские буквы, внешне неотличимые от кирилличских (после lower()) - частая опечатка
# при смешанной раскладке: "TOП-106Б".
_LATIN_TO_CYRILLIC = str.maketrans("abekmhopctyx", "авекмнорстух")


def _group_key(name: str) -> str:
    """Ключ для сравнения названий групп: без регистра, пробелов, дефисов и точек.
    "топ106б", "ТОП 106 Б" и "ТОП-106Б" дают один и тот же ключ."""
    return "".join(ch for ch in name.lower().translate(_LATIN_TO_CYRILLIC) if ch.isalnum())


def _load_groups() -> dict[str, int]:
    return json.loads(_GROUPS_PATH.read_text(encoding="utf-8"))


def _week_number_for_date(target: dt.date) -> int:
    """Номер учебной недели для произвольной даты - эвристика на основе начала семестра
    (те же правила, что в example/raspisanie/isu_api.py, только не только для 'сегодня')."""
    if target.month >= 8:
        base_date = dt.date(target.year, 9, 1)
    elif target.month == 1:
        base_date = dt.date(target.year - 1, 9, 1)
    else:
        base_date = dt.date(target.year, 2, 9)
    start_monday = base_date - dt.timedelta(days=base_date.weekday())
    days_passed = (target - start_monday).days
    return max(1, (days_passed // 7) + 1)


def _extract_venue(subject_text: str) -> tuple[str, str | None]:
    """Вырезает место проведения из текста пары и возвращает (текст без него, само место).
    Так избегаем дублирования - формат ИСУ и так включает место прямо в тексте пары."""
    match = _BUILDING_ROOM_PATTERN.search(subject_text)
    if match:
        building, room = match.groups()
        cleaned = (subject_text[: match.start()] + subject_text[match.end():]).strip(" ,-")
        return cleaned, f"кабинет {building}-{room}"

    match = _VENUE_PATTERN.search(subject_text)
    if match:
        cleaned = (subject_text[: match.start()] + subject_text[match.end():]).strip(" ,-")
        return cleaned, match.group(0).strip()

    return subject_text, None


class IsuScheduleRepository:
    """ScheduleRepository поверх недокументированного эндпоинта ИСУ УУНиТ.

    Логика разбора HTML портирована с example/raspisanie/isu_api.py (та же структура
    таблицы/inline-скриптов), переписана асинхронно (httpx вместо aiohttp, чтобы не
    тащить лишнюю зависимость) и без глобального состояния модуля."""

    def __init__(self) -> None:
        self._groups = _load_groups()
        self._canonical_by_key = {_group_key(name): name for name in self._groups}

    def resolve_group(self, group: str) -> str | None:
        """Находит группу в справочнике ИСУ, как бы студент её ни написал ("топ106б" -> "ТОП-106Б")."""
        return self._canonical_by_key.get(_group_key(group))

    async def get_day_schedule(self, group: str, date: str) -> DaySchedule | None:
        normalized_group = self.resolve_group(group)
        if normalized_group is None:
            logger.warning("IsuScheduleRepository: группа не найдена в справочнике: %s", group)
            return None
        group_id = self._groups[normalized_group]

        target_date = dt.date.fromisoformat(date)
        week = _week_number_for_date(target_date)

        html = await self._fetch_html(group_id, week)
        if html is None:
            logger.warning("IsuScheduleRepository: не удалось получить HTML с ИСУ")
            return None

        schedule_by_day = self._extract_schedule_data(html)
        target_date_str = target_date.strftime("%d.%m.%Y")
        day_label = next((day for day in schedule_by_day if target_date_str in day), None)
        if day_label is None:
            logger.info("IsuScheduleRepository: день %s не найден в неделе %d", target_date_str, week)
            return DaySchedule(group=normalized_group, date=date, day_label=target_date_str, lessons=[])

        lessons = []
        for _, time_str, subject_text in sorted(schedule_by_day[day_label], key=lambda item: item[0]):
            cleaned_subject, venue = _extract_venue(subject_text)
            lessons.append(ScheduleLesson(time=time_str, subject=cleaned_subject, venue=venue))
        return DaySchedule(group=normalized_group, date=date, day_label=day_label, lessons=lessons)

    @staticmethod
    async def _fetch_html(group_id: int, week: int) -> str | None:
        import httpx

        payload = {"group_id": str(group_id), "week": str(week), "funct": "group"}
        try:
            async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
                response = await client.post(_SCHEDULE_URL, data=payload)
                if response.status_code == 200:
                    return response.text
        except httpx.HTTPError:
            logger.exception("IsuScheduleRepository: ошибка запроса к ИСУ")
        return None

    @staticmethod
    def _extract_schedule_data(html: str) -> dict[str, list[tuple[int, str, str]]]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", class_="table-bordered")
        if not table:
            return {}

        headers = table.find("thead").find_all("th") if table.find("thead") else []
        days = []
        for header in headers[2:]:
            day_text = header.get_text(separator=" ", strip=True).split("Сегодня:")[0].strip()
            days.append(day_text)

        rows = table.find("tbody").find_all("tr") if table.find("tbody") else table.find_all("tr")
        rows = [row for row in rows if not row.find("th")]
        time_slots: dict[int, str] = {}
        for index, row in enumerate(rows):
            cols = row.find_all("td")
            if len(cols) >= 2:
                time_slots[index + 1] = cols[1].get_text(strip=True).replace("\n", " ")

        schedule_by_day: dict[str, list[tuple[int, str, str]]] = {day: [] for day in days}
        for script in soup.find_all("script"):
            if not script.string:
                continue
            matches = re.finditer(r"\$\('#(\d+)_(\d+)_group'\)\.append\('(.*?)'\);", script.string, re.DOTALL)
            for match in matches:
                row_id, col_id = int(match.group(1)), int(match.group(2))
                cell_soup = BeautifulSoup(match.group(3).strip(), "html.parser")
                for br in cell_soup.find_all("br"):
                    br.replace_with(" ")
                subject_text = re.sub(r"\s+", " ", cell_soup.get_text(separator=" ", strip=True)).strip()
                subject_text = subject_text.replace("|", "/")
                day_index = col_id - 1
                if day_index < len(days) and row_id in time_slots:
                    schedule_by_day[days[day_index]].append((row_id, time_slots[row_id], subject_text))
        return schedule_by_day
