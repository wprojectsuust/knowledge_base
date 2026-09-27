COMPOSE = docker compose

.PHONY: env hooks build up down restart logs ps shell test test-docker test-integration test-e2e stress clean

env:
	test -f .env || cp .env.example .env

# Подключает .githooks (pre-commit перегенерирует doc/tree перед каждым коммитом).
# Нужно выполнить один раз после клонирования репозитория.
hooks:
	git config core.hooksPath .githooks

build: env
	$(COMPOSE) build

up: env
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

restart: down up

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

shell:
	$(COMPOSE) exec app bash

test:
	.venv/bin/python -m pytest

test-docker: build
	$(COMPOSE) run --rm app pytest

# Требуют поднятого стека (make up): реальные Postgres/Chroma, никаких моков.
test-integration:
	.venv/bin/python -m pytest -m integration

# Требуют поднятого стека (make up) и валидного GEMINI_API_KEY - тратит токены LLM.
test-e2e:
	.venv/bin/python -m pytest -m e2e

# Нагрузочный тест (k6), требует поднятого стека и валидного GEMINI_API_KEY.
# k6 - отдельный бинарь, не входит в requirements: https://k6.io/docs/get-started/installation/
stress:
	k6 run tests/stress/question_load_test.js

clean:
	$(COMPOSE) down -v
