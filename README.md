# УУНиТ Knowledge Base

Монорепозиторий: FastAPI-бэкенд (`backend/`) + Next.js-фронтенд (`frontend/`).

- **`backend/`** — RAG-сервис базы знаний (FastAPI, PostgreSQL, ChromaDB, любой OpenAI-совместимый
  LLM). Подробности, API, переменные окружения, тесты — в `backend/README.md`.
- **`frontend/`** — веб-интерфейс (Next.js/React): чат с ответами в Markdown и источниками,
  3D-карта кампуса УГАТУ с маршрутами, адаптив под телефоны. Обращается к `backend/` по HTTP.

Прод: https://karrad.tech/uunit/ (API — `/uunit/api/`, там же страница загрузки данных).

## Быстрый старт

```bash
cp .env.example .env   # заполнить LLM_API_KEY (или GEMINI_API_KEY)
make up                # поднимет backend + frontend + postgres
```

Фронтенд — `http://localhost:3000`, backend — `http://localhost:8000` (`/docs` для API).

Остальные команды — в `Makefile` (`make help`-подобного списка нет, см. сам файл: `build`,
`up`/`down`/`restart`, `logs`, `shell`/`shell-frontend`, `test`/`test-docker`,
`test-integration`/`test-e2e`, `stress`, `hooks`).

## CI/CD и деплой

`.github/workflows/ci-cd.yml`: на каждый push и PR — тесты бэкенда и сборка фронтенда; на push в
`main` — сборка образов в GitHub Actions, доставка на сервер по SSH (`docker save | docker load`,
на сервере ничего не собирается), `docker compose up` с `docker-compose.prod.yml` и проверка
здоровья. Перед доставкой проверяется свободное место на сервере (нужно ≥1,5 ГБ).

Коммит без тестов и деплоя (например, только документация) — `[skip ci]` в сообщении коммита.

## Структура проекта

Актуальное дерево файлов и подсчёт строк — в `doc/tree` (перегенерируется
автоматически перед каждым коммитом, см. `scripts/tree.py` и `.githooks/pre-commit`).
