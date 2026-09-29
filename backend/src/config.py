"""Централизованные настройки, которые удобно держать в одном месте и легко
поправить руками (в отличие от разрозненных os.environ.get() по коду)."""

import datetime as dt
import os

# Часовой пояс вуза (Уфа, UTC+5, без перехода на летнее время) - «сегодня»/«завтра» в
# вопросах считаются по нему, а не по часам сервера (в контейнере обычно UTC).
LOCAL_TZ = dt.timezone(dt.timedelta(hours=5), name="Asia/Yekaterinburg")

# Максимум одновременных запросов к LLM (Gemini) - защита от перегрузки внешнего API
# и от слишком большого числа параллельных сетевых вызовов с одного инстанса.
LLM_MAX_CONCURRENCY: int = int(os.environ.get("LLM_MAX_CONCURRENCY", "5"))

# Сколько раз повторять запрос к LLM при временной ошибке (503 перегрузка, 429, сеть) -
# с экспоненциальной паузой. Gemini регулярно отвечает 503 "high demand" на пиках.
# Повторы - на каждую модель из GEMINI_MODEL, только на 5xx/таймауты (не на 429).
LLM_MAX_RETRIES: int = int(os.environ.get("LLM_MAX_RETRIES", "2"))

# Сколько секунд модель «остывает» после ответа 429 (исчерпан лимит запросов бесплатного
# тарифа): пока остывает, запросы сразу идут на запасную модель из GEMINI_MODEL.
LLM_RATE_LIMIT_COOLDOWN_SECONDS: int = int(os.environ.get("LLM_RATE_LIMIT_COOLDOWN_SECONDS", "60"))

# Таймаут одной попытки запроса к LLM и общий бюджет на весь вызов (все повторы и все
# запасные модели) - чтобы при перегрузке студент получил «попробуйте позже», а не ждал минутами.
LLM_TIMEOUT_SECONDS: float = float(os.environ.get("LLM_TIMEOUT_SECONDS", "45"))
LLM_TOTAL_BUDGET_SECONDS: float = float(os.environ.get("LLM_TOTAL_BUDGET_SECONDS", "90"))

# Максимум одновременных запросов к локальной модели эмбеддингов (CPU-bound) -
# защита от перегрузки CPU при большом числе параллельных запросов.
EMBEDDING_MAX_CONCURRENCY: int = int(os.environ.get("EMBEDDING_MAX_CONCURRENCY", "5"))

# Сколько секунд считать закэшированное в Postgres расписание свежим, прежде чем
# снова дёргать живой сайт ИСУ.
SCHEDULE_CACHE_TTL_SECONDS: int = int(os.environ.get("SCHEDULE_CACHE_TTL_SECONDS", str(60 * 60)))

# Импорт новостей с uust.ru в базу знаний: как часто (минуты, 0 - только вручную через
# POST /news/import) и сколько свежих новостей проверять за раз. Каждая НОВАЯ новость - один
# вызов LLM (генерация поисковых вопросов), уже загруженные пропускаются без запросов.
NEWS_IMPORT_INTERVAL_MINUTES: int = int(os.environ.get("NEWS_IMPORT_INTERVAL_MINUTES", "180"))
NEWS_IMPORT_LIMIT: int = int(os.environ.get("NEWS_IMPORT_LIMIT", "14"))
# Пауза между новостями при импорте - фоновый импорт не должен выедать лимит запросов к LLM,
# нужный живым вопросам студентов (на пустой базе при старте новых новостей сразу 14).
NEWS_IMPORT_PAUSE_SECONDS: float = float(os.environ.get("NEWS_IMPORT_PAUSE_SECONDS", "20"))

# Список официальных документов (uust.ru/sveden/document/, только названия и ссылки) в базе знаний:
# как часто синхронизировать (часы, 0 - выключено) и по сколько документов в одной записи базы.
# Первый прогон - ~100 вызовов LLM (с той же паузой, что у новостей), дальше - только изменения.
DOCUMENTS_IMPORT_INTERVAL_HOURS: int = int(os.environ.get("DOCUMENTS_IMPORT_INTERVAL_HOURS", "24"))
DOCUMENTS_IMPORT_BATCH_SIZE: int = int(os.environ.get("DOCUMENTS_IMPORT_BATCH_SIZE", "20"))

# Порог косинусового сходства для обычного поиска по базе знаний: фрагменты ниже него не
# попадают в контекст LLM - иначе на вопрос без ответа в базе модель пересказывает всё
# подряд из топ-N. Реальные значения видны в DEBUG-логах SearchDataByListOfStr - по ним
# и калибровать.
SEARCH_SIMILARITY_THRESHOLD: float = float(os.environ.get("SEARCH_SIMILARITY_THRESHOLD", "0.5"))

# Порог косинусового сходства для "как добраться до места проведения": ниже этого
# значения найденный в базе знаний фрагмент не считается достаточно релевантным,
# чтобы добавлять его в ответ про расписание. Разумный дефолт, требует калибровки
# на реальных данных.
SCHEDULE_DIRECTIONS_SIMILARITY_THRESHOLD: float = float(
    os.environ.get("SCHEDULE_DIRECTIONS_SIMILARITY_THRESHOLD", "0.55")
)
