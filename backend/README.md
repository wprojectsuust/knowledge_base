# Бэкенд - УУНиТ База знаний

FastAPI-сервис: RAG по базе знаний с источниками и «вторым шансом», расписание групп из ИСУ,
навигатор по кампусу, автоимпорт новостей и документов uust.ru. Общий обзор проекта -
[корневой README](../README.md).

## Запуск

```bash
# из корня репозитория, весь стек в Docker
make env && make up              # http://localhost:8000, Swagger UI - /docs

# или только бэкенд, без Docker (нужен PostgreSQL)
python -m venv .venv
.venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv/bin/pip install -e ".[dev]"
POSTGRES_HOST=localhost .venv/bin/python main.py
```

## Тесты

```bash
.venv/bin/python -m pytest              # unit + покрытие (по умолчанию)
.venv/bin/python -m pytest -m integration   # реальные Postgres/Chroma, нужен make up
.venv/bin/python -m pytest -m e2e           # весь стек + ключ LLM
```

Подробно - [docs/testing.md](../docs/testing.md).

## Устройство

```
src/
├── domain/        сущности и чистая логика: Data, QuestionPlan, CampusNavigator, порции документов
├── use_cases/     Question (оркестратор), PlanQuestion, ResearchAnswer, GetSchedule, BuildRoute,
│                  ComposeAnswer, NewData, RemoveDataById, ImportNews, ImportDocuments…
├── services/      прокси: LLMService, EmbeddingService, VectorSearchService, DataStoreService…
├── repositories/  Protocol + реализации: Postgres, Chroma, ИСУ, uust.ru, campus.json
├── api/           app.py (фоновые задачи, CORS, 503), routes.py, schemas.py, dependencies.py
└── config.py      настройки из окружения
main.py            точка входа uvicorn, логирование
```

Пайплайн вопроса:

```
вопрос + history + facts
  -> PlanQuestion               1 вызов LLM: план {search, schedule, route, clarify}
  -> параллельно, только нужные части:
       search:   ResearchAnswer   поиск -> LLM: ответ | ещё поиск | уточнение (до 2 доп. шагов)
       schedule: GetSchedule      ИСУ + кэш -> ответ на конкретный вопрос
       route:    BuildRoute       Dijkstra по графу кампуса, шаблонный текст
  -> ComposeAnswer              если частей несколько - один связный ответ
```

## Документация

| | |
|---|---|
| [Архитектура](../docs/architecture.md) | слои, путь вопроса, диаграммы |
| [API](../docs/api.md) | эндпоинты, SSE, ошибки |
| [Конфигурация](../docs/configuration.md) | переменные окружения |
| [База знаний](../docs/knowledge-base.md) | как добавлять данные |
| [Карта кампуса](../docs/campus-map.md) | `campus.json` и навигатор |
| [ADR](../docs/adr/README.md) | почему сделано так |
