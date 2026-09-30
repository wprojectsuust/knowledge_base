# Документация

| Документ | О чём |
|---|---|
| [architecture.md](architecture.md) | Как устроена система: компоненты, слои бэкенда, путь вопроса, диаграммы |
| [api.md](api.md) | HTTP API: все эндпоинты, форматы, потоковый ответ (SSE), ошибки |
| [configuration.md](configuration.md) | Все переменные окружения бэкенда и фронтенда |
| [deployment.md](deployment.md) | Локальный запуск, прод, nginx, CI/CD, обслуживание |
| [knowledge-base.md](knowledge-base.md) | Как наполнять базу знаний и писать фрагменты, автоимпорт с uust.ru |
| [campus-map.md](campus-map.md) | 3D-карта и навигатор: формат `campus.json`, как строится маршрут |
| [frontend.md](frontend.md) | Страницы, компоненты, состояние в браузере, адаптив |
| [testing.md](testing.md) | Пирамида тестов, как писать и запускать |
| [roadmap.md](roadmap.md) | Что сделано и что планируем |
| [adr/](adr/README.md) | Архитектурные решения - почему сделано именно так |
| [tree](tree) | Дерево файлов с подсчётом строк (генерируется хуком) |

Для участников проекта - [CONTRIBUTING.md](../CONTRIBUTING.md), история изменений -
[CHANGELOG.md](../CHANGELOG.md), безопасность - [SECURITY.md](../SECURITY.md).

## С чего начать

- **Хочу попробовать** - https://karrad.tech/uunit/ или локально: [deployment.md](deployment.md#локально-через-docker-рекомендуется).
- **Хочу добавить данные** - [knowledge-base.md](knowledge-base.md).
- **Хочу поправить код** - [architecture.md](architecture.md), затем [CONTRIBUTING.md](../CONTRIBUTING.md).
- **Хочу интегрироваться** - [api.md](api.md).
