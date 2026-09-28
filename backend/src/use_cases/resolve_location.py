import logging
import re

from src.domain.location import Location

logger = logging.getLogger(__name__)

# Вопрос считается навигационным, только если в нём есть одно из этих слов - иначе упоминание
# корпуса где-то в ответе не повод показывать карту.
_NAVIGATION_WORDS = re.compile(r"где|дойти|добрать|пройти|найти|корпус|кабинет|аудитор", re.IGNORECASE)

# "7-404", "кабинет 3-106б". Ровно три цифры кабинета + граница слова, чтобы не цеплять даты
# (30-09-2026), время (09:00-10:30) и коды групп (1-1.1.1.-26А).
_ROOM = re.compile(r"(?<![\d.\-])(\d{1,2})\s*-\s*(\d{3}[а-яa-z]?)(?![\d\w])", re.IGNORECASE)
# "корпус 7", "корпусе №2"
_BUILDING_AFTER = re.compile(r"корпус\w*\s*№?\s*(\d{1,2})(?!\d)", re.IGNORECASE)
# "5 корпуса", "3-м корпусе"
_BUILDING_BEFORE = re.compile(r"(?<!\d)(\d{1,2})(?:-?[а-я]{1,2})?\s+корпус", re.IGNORECASE)


def _parse(text: str) -> Location | None:
    room_match = _ROOM.search(text)
    if room_match:
        building, room = room_match.group(1), room_match.group(2).lower()
        return Location(building=building, room=room, floor=int(room[0]))

    for pattern in (_BUILDING_AFTER, _BUILDING_BEFORE):
        building_match = pattern.search(text)
        if building_match:
            return Location(building=building_match.group(1))
    return None


class ResolveLocation:
    """Достаёт из вопроса (приоритетно) или ответа место на территории - чтобы фронт мог показать
    его на карте. Чистые регулярки, без LLM: ответ уже сгенерирован, и если в нём есть корпус или
    кабинет, он там написан явно (формат "кабинет 7-404" выдаёт и модуль расписания)."""

    async def execute(self, question: str, answer: str) -> Location | None:
        if not _NAVIGATION_WORDS.search(question):
            return None

        location = _parse(question) or _parse(answer)
        logger.debug("ResolveLocation: %s", location)
        return location
