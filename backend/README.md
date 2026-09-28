# УУНиТ Knowledge Base

RAG-сервис базы знаний Уфимского университета науки и технологий: пользователь задаёт
вопрос на естественном языке, сервис ищет релевантные фрагменты базы знаний и просит LLM
сформулировать ответ со ссылкой на источник.

## Как это устроено

Чистая архитектура (см. `doc/adrs/000-clean-architecture-tdd-two-databases.md`):
домен и юз-кейсы ничего не знают о конкретных базах данных или LLM-провайдере, только
про интерфейсы (`Protocol`).

```
Вопрос пользователя
  -> GetReallyQuestions        (LLM выделяет реальные поисковые вопросы из сообщения)
  -> SearchDataByListOfStr     (эмбеддинг вопросов -> поиск в Chroma -> подтяжка из Postgres)
  -> AnalyzeDataByLLMForUser   (LLM формирует ответ по найденному контексту, с указанием источника)
```

Две базы данных:
- **PostgreSQL** - хранилище документов (`documents`) и кэша вопрос-ответ (`question_cache`),
  доступ через `asyncpg` нативным SQL, без ORM (см. `doc/adrs/001-relational-db-for-documents.md`).
- **ChromaDB** - векторный индекс поверх эмбеддингов (`cointegrated/rubert-tiny2`), локальный
  персистентный клиент, без отдельного сервера.

Дополнительно:
- Ответы кэшируются по вопросу в Postgres - повторный вопрос не тратит токены LLM и CPU на эмбеддинг.
- Документы можно опционально пометить тегом `division` (подразделение УУНиТ) - при поиске
  используется мягкая приоритизация: сначала документы с тегом, совпавшим по ключевым словам
  вопроса (`src/domain/division.py: detect_division`), затем обычный поиск как fallback.
- Число одновременных запросов к LLM и к модели эмбеддингов ограничено `asyncio.Semaphore`
  (см. `src/config.py`) - защита от перегрузки внешнего API и CPU.

## Стек

FastAPI (async) - PostgreSQL/asyncpg - ChromaDB - Gemini (через OpenAI-совместимый эндпоинт) -
sentence-transformers (CPU) - pytest.

## Быстрый старт

Команды запускаются из корня репозитория (см. корневой `README.md` и `Makefile`):

```bash
cp .env.example .env   # заполнить GEMINI_API_KEY
make up                # поднимет backend + frontend + postgres
```

Сервис будет на `http://localhost:8000`, интерактивная документация - на `/docs`.

Другие команды (см. `Makefile`):

| Команда | Что делает |
|---|---|
| `make build` | собрать образ |
| `make up` / `make down` / `make restart` | поднять / остановить / перезапустить стек |
| `make logs` | логи (по умолчанию DEBUG - видно запросы к API, БД, LLM, что нашлось) |
| `make shell` / `make shell-frontend` | зайти в контейнер backend / frontend |
| `make test` | юнит-тесты (локально, без докера) |
| `make test-docker` | юнит-тесты внутри контейнера |
| `make test-integration` | тесты на реальных Postgres/Chroma (нужен `make up`) |
| `make test-e2e` | e2e-тесты на реально запущенный сервер (нужен `make up` + валидный ключ) |
| `make stress` | нагрузочный тест k6 на `/question` |
| `make hooks` | подключить `.githooks` (pre-commit пересобирает `doc/tree`) |

## API

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/question` | Задать вопрос, получить ответ с указанием источника |
| `POST` | `/search` | Сырой поиск по списку "реальных вопросов", без похода в LLM |
| `POST` | `/data` | Добавить документ в базу знаний (`id` присваивает Postgres) |
| `GET` | `/data/{id}` | Получить документ по id |
| `DELETE` | `/data/{id}` | Удалить документ (из Postgres и из векторного индекса) |

Пример:

```bash
curl -X POST http://localhost:8000/data \
  -H 'Content-Type: application/json' \
  -d '{"source": "uust.ru", "content": "Деканат находится в корпусе 2, каб. 204."}'

curl -X POST http://localhost:8000/question \
  -H 'Content-Type: application/json' \
  -d '{"question": "Где находится деканат?"}'
```

## Переменные окружения

См. `.env.example` - LLM (`GEMINI_API_KEY`, `GEMINI_MODEL` - одна модель или несколько через запятую как запасные при перегрузке, опционально `PROXY_URL`),
PostgreSQL (`POSTGRES_*`), путь для Chroma (`CHROMA_PATH`), уровень логирования (`LOG_LEVEL`).

## Тесты

Пирамида: `unit` (моки, по умолчанию) - `integration` (реальные Postgres/Chroma) -
`e2e` (реальный HTTP-сервер целиком) - `stress` (k6). Подробности - в `make test*`/`make stress`
выше и в комментариях самих тестовых файлов (`tests/integration/`, `tests/e2e/`, `tests/stress/`).

## Структура проекта

Актуальное дерево файлов всего репозитория (backend + frontend) и подсчёт строк - в
корневом `doc/tree` (перегенерируется автоматически перед каждым коммитом хуком в корне
репозитория - `scripts/tree.py` и `.githooks/pre-commit`).

## Архитектурные решения

`doc/adrs/` - ADR (Architecture Decision Records), коротко и по-русски, без пафоса.
