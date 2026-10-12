import json
import logging

from src.domain.event import FORMATS, TOPICS, Event, RawEvent, normalize_format, normalize_topic
from src.logging_utils import preview
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class ClassifyEvents:
    """Размечает события тематикой, форматом и признаком «онлайн» - на uust.ru этого нет, а без
    этого каталог не отфильтровать. Один вызов LLM на пачку событий (по названию и дате).
    Неразобранный ответ не теряет события: они попадают в каталог как «Другое»."""

    # 10 названий - ответ укладывается в таймаут LLM даже когда провайдер медленный
    def __init__(self, llm_service: LLMService, batch_size: int = 10) -> None:
        self._llm_service = llm_service
        self.batch_size = batch_size

    async def execute(self, events: list[RawEvent]) -> list[Event]:
        result: list[Event] = []
        for start in range(0, len(events), self.batch_size):
            batch = events[start : start + self.batch_size]
            labels = self._parse(await self._llm_service.generate(self._prompt(batch)))
            for n, raw in enumerate(batch, start=1):
                label = labels.get(n, {})
                result.append(
                    Event(
                        slug=raw.slug,
                        title=raw.title,
                        starts_at=raw.starts_at,
                        url=raw.url,
                        image=raw.image,
                        topic=normalize_topic(label.get("topic")),
                        format=normalize_format(label.get("format")),
                        online=bool(label.get("online", False)),
                    )
                )
        return result

    @staticmethod
    def _prompt(batch: list[RawEvent]) -> str:
        lines = "\n".join(f"{n}. {event.title} ({event.starts_at:%d.%m.%Y})" for n, event in enumerate(batch, start=1))
        return (
            "Ты размечаешь мероприятия университета УУНиТ для каталога студентов.\n"
            f"Тематика - ровно одно из: {', '.join(TOPICS)}.\n"
            f"Формат - ровно одно из: {', '.join(FORMATS)}.\n"
            "online - true, только если из названия ясно, что мероприятие онлайн/дистанционное.\n"
            'Ответь ТОЛЬКО JSON-массивом: [{"n": <номер>, "topic": "...", "format": "...", "online": false}, ...] '
            "- по элементу на каждое мероприятие.\n\n"
            f"Мероприятия:\n{lines}"
        )

    @staticmethod
    def _parse(raw: str) -> dict[int, dict]:
        start, end = raw.find("["), raw.rfind("]")
        try:
            items = json.loads(raw[start : end + 1]) if start != -1 and end > start else []
        except json.JSONDecodeError:
            items = []
        if not items:
            logger.warning("ClassifyEvents: не разобрал ответ LLM, события пойдут как «Другое»: %s", preview(raw))
        return {item["n"]: item for item in items if isinstance(item, dict) and isinstance(item.get("n"), int)}
