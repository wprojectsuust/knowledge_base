# Тестирование

Проект пишется через TDD (ADR 000): сначала падающий тест, потом код. Текущее состояние:
**194 юнит-теста, покрытие бэкенда ~88%**; ещё 8 интеграционных и e2e запускаются отдельно.

## Пирамида

| Уровень | Где | Что проверяет | Внешние зависимости | Запуск |
|---|---|---|---|---|
| unit | `backend/tests/{domain,use_cases,services,repositories,api}` | Логику слоёв с фейками вместо БД, LLM и сети | нет | `make test` |
| integration | `backend/tests/integration` | Реальные Postgres, Chroma, ИСУ | `make up` | `make test-integration` |
| e2e | `backend/tests/e2e` | Весь сценарий «добавить данные -> спросить -> удалить» через HTTP | `make up` + ключ LLM | `make test-e2e` |
| stress | `backend/tests/stress/question_load_test.js` | Нагрузка на `/question` (k6) | `make up` + ключ LLM + [k6](https://k6.io) | `make stress` |
| фронтенд | CI | Типы (`tsc --noEmit`) и сборка (`next build`) | нет | `npx tsc --noEmit && npm run build` |

По умолчанию `pytest` запускает только unit: в `pyproject.toml` стоит
`-m "not integration and not e2e"`. Интеграционные тесты помечены `@pytest.mark.integration`,
e2e - `@pytest.mark.e2e`. e2e и stress тратят реальные токены LLM.

```bash
cd backend
.venv/bin/python -m pytest                       # unit + отчёт о покрытии
.venv/bin/python -m pytest tests/use_cases -q    # один каталог
.venv/bin/python -m pytest -k research -q        # по имени
.venv/bin/python -m pytest -m integration        # нужен make up
E2E_BASE_URL=http://localhost:8000 .venv/bin/python -m pytest -m e2e
```

## Как устроены юнит-тесты

- Структура `tests/` повторяет `src/`: `src/use_cases/question.py` -> `tests/use_cases/test_question.py`.
- Фейки сервисов - в [`tests/conftest.py`](../backend/tests/conftest.py): `FakeLLMService`
  (заданный ответ, счётчик вызовов, последний промпт), `FakeEmbeddingService`,
  `FakeVectorSearchService`, `FakeDataStoreService`, кэши, расписание. Юз-кейсы получают их
  через конструктор - так же, как в проде получают настоящие.
- Для многошаговых сценариев LLM - заскриптованная очередь ответов (см. `ScriptedLLM` в
  `test_research_answer.py`).
- Парсеры внешних сайтов проверяются на сохранённых HTML в `tests/fixtures/` - без сети.
- Роуты - через `fastapi.testclient.TestClient` с `app.dependency_overrides`; потоковый
  `/question/stream` - разбором событий `data: …`.
- Навигатор - на настоящем `campus.json`: «из 6 в 7 - подземным переходом», «маршрут между
  корпусами не выходит на улицу», «уличные отрезки не пересекают здания».
- `asyncio_mode = "auto"`: асинхронные тесты - просто `async def test_…`.

## Что тестировать при изменениях

| Меняете | Добавьте тест |
|---|---|
| Промпт (`PlanQuestion`, `ResearchAnswer`, `AnalyzeData…`) | Что нужное правило есть в промпте и что ответ LLM разбирается, включая невалидный JSON |
| Юз-кейс | Сценарий через фейки: что вызвано, что сохранено, что вернулось |
| Парсер uust.ru / ИСУ | Обновите фикстуру реальной страницей и проверьте разбор |
| `campus.json` / навигатор | Маршрут, который должен измениться |
| API | Форма ответа и коды ошибок |

## CI

Каждый push и PR прогоняет unit-тесты бэкенда (с облегчёнными зависимостями, без torch) и
проверку типов и сборку фронтенда - см. [deployment.md](deployment.md#cicd). Красный CI -
в `main` не мёржим.
