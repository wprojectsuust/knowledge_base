COMPOSE = docker compose

.PHONY: env build up down restart logs ps shell test test-docker clean

env:
	test -f .env || cp .env.example .env

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

clean:
	$(COMPOSE) down -v
