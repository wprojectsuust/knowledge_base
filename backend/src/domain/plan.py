from dataclasses import dataclass
from datetime import date

from src.domain.clarification import ClarificationRequest
from src.domain.route import RouteRequest
from src.domain.schedule import ScheduleRequest


@dataclass(frozen=True, kw_only=True)
class SearchTask:
    """Часть сообщения, на которую отвечает база знаний: самостоятельная формулировка вопроса
    (для ответа) и поисковые запросы (для векторного поиска)."""

    question: str
    queries: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class EventsTask:
    """Часть сообщения про мероприятия университета («будут ли хакатоны в октябре?»): ищется в
    каталоге мероприятий по словам названия, датам и тематике, а не в базе знаний."""

    question: str
    keywords: tuple[str, ...] = ()
    date_from: date | None = None
    date_to: date | None = None
    topic: str | None = None


@dataclass(frozen=True, kw_only=True)
class QuestionPlan:
    """Что нужно сделать, чтобы ответить на сообщение. Частей может быть несколько сразу -
    «какие завтра пары и где деканат» = schedule + search; они выполняются параллельно."""

    search: SearchTask | None = None
    schedule: ScheduleRequest | None = None
    route: RouteRequest | None = None
    events: EventsTask | None = None
    clarification: ClarificationRequest | None = None
    # «тривиальный» вопрос: ответ целиком выводится из диалога и текущего времени («через сколько
    # это?», «спасибо») - планировщик отвечает сам, в базу знаний не ходим. Только без других частей.
    reply: str | None = None
