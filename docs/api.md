# HTTP API

Базовый адрес:
- локально - `http://localhost:8000`;
- прод - `https://karrad.tech/uunit/api`.

Интерактивная документация (Swagger UI) - `/docs`, схема OpenAPI - `/openapi.json`.
Все тела запросов и ответов - JSON в UTF-8. Авторизации нет (см. [SECURITY.md](../SECURITY.md)).

| Метод | Путь | Назначение |
|---|---|---|
| `POST` | [`/question`](#post-question) | Вопрос консультанту, ответ целиком |
| `POST` | [`/question/stream`](#post-questionstream) | То же, потоком: статусы, затем результат (SSE) |
| `POST` | [`/search`](#post-search) | Сырой поиск по базе знаний, без LLM |
| `POST` | [`/data`](#post-data) | Добавить фрагмент в базу знаний |
| `GET` | [`/data/{id}`](#get-dataid) | Получить фрагмент |
| `DELETE` | [`/data/{id}`](#delete-dataid) | Удалить фрагмент (Postgres + векторы) |
| `GET` | [`/campus`](#get-campus) | Данные 3D-карты кампуса |
| `POST` | [`/route`](#post-route) | Маршрут по кампусу |
| `POST` | [`/news/import`](#post-newsimport) | Подтянуть новости uust.ru прямо сейчас |
| `GET` | `/` | HTML-страница загрузки данных в базу знаний |

## Ошибки

| Код | Когда | Тело |
|---|---|---|
| `404` | фрагмент или место на карте не найдено | `{"detail": "…"}` |
| `422` | невалидный запрос (pydantic), неизвестный `division`, LLM не смогла проиндексировать фрагмент | `{"detail": …}` |
| `503` | LLM недоступна: все модели перегружены или исчерпан бюджет времени | `{"detail": "ИИ-модель сейчас перегружена, попробуйте ещё раз через минуту."}` |

Ответ `503` отдаётся с CORS-заголовками, поэтому браузер показывает его текст, а не «ошибку CORS».

---

## `POST /question`

Задать вопрос. Бэкенд сам решает, что нужно: поиск по базе знаний, расписание, маршрут или
уточнение. Подробнее в [architecture.md](architecture.md#как-отвечаем-на-вопрос).

**Запрос**

```json
{
  "question": "во сколько завтра кончаются пары?",
  "history": [
    {"question": "где деканат ФИРТ?", "answer": "Деканат ФИРТ - корпус 1, кабинет 1-212."}
  ],
  "facts": [
    {"field": "group", "value": "ТОП-106Б"}
  ]
}
```

| Поле | Тип | Ограничения | Смысл |
|---|---|---|---|
| `question` | string | 1-2000 символов | Сообщение студента |
| `history` | array | до 10 реплик; `question` ≤ 2000, `answer` ≤ 6000 | Последние реплики чата для контекста («а туда как пройти?»). Сервер их не хранит |
| `facts` | array | до 10; `field` - `^[a-z_]+$`, `value` 1-200 | Что студент уже сообщил о себе в ответ на уточнения |

**Ответ** - ровно одно из `answer` / `clarification`:

```json
{
  "answer": "Завтра у ТОП-106Б последняя пара заканчивается в **15:25** (корпус 7, ауд. 7-404).",
  "clarification": null,
  "location": {"building": "7", "room": "404", "floor": 4},
  "route": null
}
```

| Поле | Когда заполнено |
|---|---|
| `answer` | Текст ответа в Markdown. Источники - пометки `[Источник: <ссылка>]` (фронт выносит их в отдельный блок) |
| `clarification` | Не хватает сведений о студенте: `{"field": "group", "question": "Из какой вы группы?"}`. Повторите тот же вопрос, добавив ответ в `facts` |
| `location` | В ответе упомянуто место на кампусе - для мини-карты |
| `route` | Студент спросил, как пройти: см. [`/route`](#post-route) (тогда `location` = `null`) |

```bash
curl -X POST http://localhost:8000/question \
  -H 'Content-Type: application/json' \
  -d '{"question": "Где находится деканат ФИРТ?"}'
```

## `POST /question/stream`

Тот же запрос, но ответ приходит потоком [Server-Sent Events](https://developer.mozilla.org/ru/docs/Web/API/Server-sent_events)
(`Content-Type: text/event-stream`), пока консультант работает (ADR 009). Каждое событие -
строка `data: <json>` и пустая строка.

```text
data: {"type": "status", "text": "Разбираю вопрос"}

data: {"type": "status", "text": "Ищу в базе знаний"}

data: {"type": "status", "text": "Ищу, кто декан ФИРТ"}

data: {"type": "result", "data": {"answer": "…", "clarification": null, "location": null, "route": null}}
```

| `type` | Поля | Смысл |
|---|---|---|
| `status` | `text` | Что делается сейчас - показывать пользователю |
| `result` | `data` | Итог - то же, что ответ `/question` |
| `error` | `detail` | Ошибка (в т.ч. недоступность LLM); поток на этом заканчивается |

Если клиент закрыл соединение, обработка вопроса отменяется. Для nginx выставлен
`X-Accel-Buffering: no` - события не копятся.

```bash
curl -N -X POST http://localhost:8000/question/stream \
  -H 'Content-Type: application/json' \
  -d '{"question": "Сколько лет декану ФИРТ?"}'
```

Клиент на TypeScript - `askQuestion()` в [`frontend/lib/api.ts`](../frontend/lib/api.ts).

## `POST /search`

Векторный поиск без LLM - для отладки качества базы знаний.

```json
{"really_questions": ["где взять справку об обучении"], "division": null}
```

`division` - необязательный slug подразделения (см. `backend/src/domain/division.py`, список -
`python -m src.domain.division`). Ответ - массив фрагментов `[{"id", "source", "content", "division"}]`.

## `POST /data`

Добавить фрагмент. LLM генерирует к нему поисковые вопросы, фрагмент сохраняется в
PostgreSQL, вопросы индексируются в Chroma (ADR 004). Кэш ответов очищается.

```json
{
  "source": "https://uust.ru/ospo/questions/",
  "content": "Справку об обучении выдаёт дирекция института, срок - 3 рабочих дня.",
  "division": null
}
```

- `source` - ссылка на первоисточник. Пустая строка - проверенный факт без ссылки: в ответах
  он используется без пометки об источнике (ADR 011).
- Ответ: `{"id": 42}`. `422`, если LLM не сгенерировала вопросов (фрагмент не сохранён).

## `GET /data/{id}`

`{"id", "source", "content", "division"}` или `404`.

## `DELETE /data/{id}`

Удаляет фрагмент из PostgreSQL и его векторы из Chroma, очищает кэш ответов. Ответ `{"ok": true}`.

## `GET /campus`

Данные для 3D-карты - массив кампусов:

```json
[{
  "id": "ugatu", "title": "Кампус УГАТУ", "address": "ул. Карла Маркса, 12", "scale": 0.4,
  "buildings": [{"id": "7", "name": "Корпус 7", "label": null, "floors": 5, "wings": [[795, 150, 1035, 205]]}],
  "bridges":   [{"from": "6", "to": "7", "floors": [1], "rect": [700, 210, 795, 230], "underground": true}],
  "stairs":    [{"building": "7", "at": [805, 178]}],
  "places":    [{"id": "library", "kind": "place", "building": "7", "floor": 1, "label": "Библиотека", "at": [843, 232]}],
  "entrances": [{"building": "7", "at": [825, 245], "dir": "up"}],
  "streets":   [{"name": "ул. Карла Маркса", "rect": [20, 30, 1280, 72]}],
  "rooms":     {"7": [["101", 1, 795.0, 150.0, 810.0, 175.0, null]]}
}]
```

Координаты - пиксели схемы кампуса, `scale` - метров в пикселе. `rooms` - компактно:
`[номер, этаж, x1, y1, x2, y2, подпись|null]`. Формат исходных данных - [campus-map.md](campus-map.md).

## `POST /route`

```json
{"source": "3-201", "target": "8-305"}
```

`source` необязателен (по умолчанию - КПП). Форматы места:

| Пример | Что это |
|---|---|
| `kpp` | КПП (главный вход с ул. Карла Маркса) |
| `7-404` | кабинет 404 в корпусе 7 |
| `7` | корпус 7 |
| `7@3` | 3 этаж корпуса 7 |
| `sport` | корпус без номера (по его `id`) |
| `place:library`, `place:cafe` | отмеченное место; `place:cafe` - ближайший буфет |

**Ответ**

```json
{
  "campus": "ugatu",
  "from_label": "корпус 6, 1 этаж",
  "to_label": "корпус 7, 1 этаж",
  "steps": ["Старт: корпус 6, 1 этаж.", "Спуститесь в подземный переход и пройдите под КПП в корпус 7 (~40 м).", "Вы на месте: корпус 7, 1 этаж (~40 м)."],
  "text": "Маршрут: … По улице: около 100 м, примерно 1 мин (на карте - пунктиром).",
  "distance_m": 72.4,
  "minutes": 1,
  "points": [{"x": 665.0, "y": 225.0, "floor": 1, "building": "6"}, {"x": 747.5, "y": 220.0, "floor": -1, "building": "6"}],
  "alternative": {"distance_m": 101.2, "minutes": 1, "points": [ … ]}
}
```

- `points[].floor`: `0` - улица, `-1` - подземный переход, иначе этаж.
- `alternative` - тот же путь по улице, если основной целиком под крышей; иначе `null`.
- `404`, если место не найдено.

## `POST /news/import`

`POST /news/import?limit=14` - проверить `limit` (1-100) свежих новостей и загрузить новые.
Ответ: `{"imported": 2, "skipped": 12, "failed": 0}`. Фоном это происходит и так (см.
[configuration.md](configuration.md)).
