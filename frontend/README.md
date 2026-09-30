# Фронтенд - УУНиТ База знаний

Next.js 15 + React 19 + TypeScript: главная с поиском, чат `/ask` с потоковыми статусами и
Markdown-ответами, 3D-карта кампуса `/map` (react-three-fiber), адаптив под телефоны.

## Запуск

```bash
npm install
npm run dev          # http://localhost:3000, бэкенд ожидается на том же хосте, порт 8000
npx tsc --noEmit     # проверка типов
npm run build        # production-сборка (standalone)
```

| Переменная (сборка) | Смысл |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Адрес бэкенда; пусто - тот же хост, порт 8000 |
| `BASE_PATH` | Префикс пути, если сайт не в корне домена (прод - `/uunit`) |

## Устройство

```
app/          страницы: page.tsx (/), ask/, map/, layout.tsx, globals.css
components/   чат (Typewriter, Markdown, ThinkingIndicator, SourcesList, ClarificationPrompt…),
              навигация (Sidebar, MobileNav), карта (VenueMap, campus/CampusScene)
lib/          api.ts (HTTP + SSE), campus-data.ts, chatStorage.ts, useStudentFacts.ts
```

Подробно - [docs/frontend.md](../docs/frontend.md), API бэкенда - [docs/api.md](../docs/api.md).
