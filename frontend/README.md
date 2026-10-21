# Vocab Deck — клиентская часть (ПР5)

SPA на React 18 + TypeScript, сборщик Vite. Реализует архитектуру из
[docs/architecture/04-frontend.md](../docs/architecture/04-frontend.md) и работает с REST API из [backend](../backend/README.md).

| Что | Чем |
|---|---|
| Состояние (паттерн Flux) | Redux Toolkit: slices `session`, `game`, `guestProgress`, `outbox`, `ui` + listener middleware |
| Серверные данные | RTK Query: кэш, теги инвалидации, повтор чтения при сбое сети |
| Маршрутизация | React Router 6, ленивые страницы, охранники `RequireAuth`, `RequireAdmin`, `GuestOnly` |
| Структура кода | Feature-Sliced Design: `app → pages → widgets → features → entities → shared` |
| Стили | CSS Modules + CSS-переменные (токены дизайн-системы ЛР2), mobile-first |
| Озвучка | MP3 нейросетевого голоса с сервера (`GET /words/{id}/audio`), без сети — английский голос браузера; британское или американское произношение выбирается в профиле |
| Тесты | Vitest: reducers, проекция журнала гостя, хранилище и миграции формата, выбор голоса |

## Запуск

Нужны Node.js 20+ и работающий бэкенд на `http://127.0.0.1:8000` (см. [backend/README.md](../backend/README.md)).

```bash
cd frontend
npm install
npm run dev
```

Приложение откроется на http://localhost:5173. Dev-сервер проксирует `/api` на FastAPI, поэтому
страница и API работают на одном origin и cookie сессии передаётся без настройки CORS.

## Команды

| Команда | Что делает |
|---|---|
| `npm run dev` | Dev-сервер Vite с горячей заменой модулей (HMR) |
| `npm test` | Модульные тесты (Vitest) |
| `npm run lint:fsd` | Проверка правил импорта Feature-Sliced Design |
| `npm run build` | Проверка типов, продакшен-сборка, копия `404.html` для GitHub Pages, проверка бюджета 300 КБ |
| `npm run preview` | Локальный просмотр продакшен-сборки |

## Структура

```
src/
├── app/        store, listener middleware, маршруты и охранники, оболочка, стили и токены
├── pages/      экраны: welcome, home, cards, inbox, deadline, round-result, auth, profile, my-list, admin-words
├── widgets/    пропуск, сетка отделов, таймер, итоги, лестница, график, достижения, таблица слов
├── features/   auth, play-deadline, review-inbox, flip-card, speak-word, guest-progress-sync,
│               offline-outbox, import-csv, edit-word, filter-words, manage-list
├── entities/   user (session), deck, word, progress — типы DTO и эндпоинты RTK Query
└── shared/     базовый API-клиент, UI-kit, хранилище с миграциями, хуки, конфигурация
```

Каждый слайс открывает наружу только `index.ts`; слой импортирует только нижележащие слои.
