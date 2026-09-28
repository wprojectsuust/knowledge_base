# УУНиТ Knowledge Base

Монорепозиторий: FastAPI-бэкенд (`backend/`) + Next.js-фронтенд (`frontend/`).

- **`backend/`** — RAG-сервис базы знаний (FastAPI, PostgreSQL, ChromaDB, Gemini). Подробности,
  API, переменные окружения, тесты — в `backend/README.md`.
- **`frontend/`** — веб-интерфейс (Next.js/React), обращается к `backend/` по HTTP.

## Быстрый старт

```bash
cp .env.example .env   # заполнить GEMINI_API_KEY
make up                # поднимет backend + frontend + postgres
```

Фронтенд — `http://localhost:3000`, backend — `http://localhost:8000` (`/docs` для API).

Остальные команды — в `Makefile` (`make help`-подобного списка нет, см. сам файл: `build`,
`up`/`down`/`restart`, `logs`, `shell`/`shell-frontend`, `test`/`test-docker`,
`test-integration`/`test-e2e`, `stress`, `hooks`).

## Структура проекта

Актуальное дерево файлов и подсчёт строк — в `backend/doc/tree` (перегенерируется
автоматически перед каждым коммитом, см. `scripts/tree.py` и `.githooks/pre-commit`).
