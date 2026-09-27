from dataclasses import dataclass, field


@dataclass(kw_only=True)
class ScheduleRequest:
    """Извлечённый из вопроса пользователя запрос расписания: группа + дата (ISO)."""

    group: str
    date: str  # YYYY-MM-DD


@dataclass(kw_only=True)
class ScheduleLesson:
    time: str
    subject: str
    venue: str | None = None


@dataclass(kw_only=True)
class DaySchedule:
    group: str
    date: str  # YYYY-MM-DD, тот самый запрошенный день
    day_label: str  # человекочитаемый заголовок дня из ИСУ (например "Вторник 30.09.2026")
    lessons: list[ScheduleLesson] = field(default_factory=list)
