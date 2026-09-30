from collections.abc import Awaitable, Callable

# Что сейчас делает консультант («Ищу в базе знаний», «Смотрю расписание») - фронт показывает
# это, пока ответ готовится. Колбэк не должен влиять на ответ: по умолчанию - no_progress.
Progress = Callable[[str], Awaitable[None]]


async def no_progress(text: str) -> None:
    return None
