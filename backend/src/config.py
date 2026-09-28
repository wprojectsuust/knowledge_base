"""Централизованные настройки, которые удобно держать в одном месте и легко
поправить руками (в отличие от разрозненных os.environ.get() по коду)."""

import os

# Максимум одновременных запросов к LLM (Gemini) - защита от перегрузки внешнего API
# и от слишком большого числа параллельных сетевых вызовов с одного инстанса.
LLM_MAX_CONCURRENCY: int = int(os.environ.get("LLM_MAX_CONCURRENCY", "5"))

# Максимум одновременных запросов к локальной модели эмбеддингов (CPU-bound) -
# защита от перегрузки CPU при большом числе параллельных запросов.
EMBEDDING_MAX_CONCURRENCY: int = int(os.environ.get("EMBEDDING_MAX_CONCURRENCY", "5"))

# Сколько секунд считать закэшированное в Postgres расписание свежим, прежде чем
# снова дёргать живой сайт ИСУ.
SCHEDULE_CACHE_TTL_SECONDS: int = int(os.environ.get("SCHEDULE_CACHE_TTL_SECONDS", str(60 * 60)))

# Порог косинусового сходства для "как добраться до места проведения": ниже этого
# значения найденный в базе знаний фрагмент не считается достаточно релевантным,
# чтобы добавлять его в ответ про расписание. Разумный дефолт, требует калибровки
# на реальных данных.
SCHEDULE_DIRECTIONS_SIMILARITY_THRESHOLD: float = float(
    os.environ.get("SCHEDULE_DIRECTIONS_SIMILARITY_THRESHOLD", "0.55")
)
