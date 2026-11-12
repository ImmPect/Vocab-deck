# Vocab Deck — серверная часть (ПР4)

REST API приложения Vocab Deck: FastAPI, SQLAlchemy 2, Alembic, Pydantic.
PostgreSQL в производственной среде, SQLite для разработки и тестов.
Реализует архитектуру из [docs/architecture](../docs/architecture/README.md) (ПР3).

## Быстрый старт (Windows)

```bat
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

Необязательно: заранее сгенерировать озвучку всех слов, чтобы первое нажатие не ждало синтеза
(иначе файл создаётся при первом запросе):

```bat
python -m app.speech.warm --accent all
```

Swagger UI: http://127.0.0.1:8000/docs. Учётная запись администратора для локального запуска указана в `.env.example`.
Изменяющие запросы требуют заголовок `X-Requested-With: VocabDeck`; страница `/docs` добавляет его сама.

С PostgreSQL в Docker: `docker compose up --build`.

## Тесты

```bat
pytest
```

134 теста, каждый на отдельной БД SQLite в памяти. В GitHub Actions те же тесты выполняются и на PostgreSQL 16.
Сквозной сценарий на работающем сервере: `python scripts/demo_scenario.py`.

## Структура

| Каталог | Назначение |
|---|---|
| `app/core` | Конфигурация, подключение к БД, ошибки, безопасность, middleware |
| `app/auth`, `app/users` | Регистрация, вход, сессии, профиль, статистика |
| `app/decks`, `app/words` | Отделы, личные списки, слова, импорт CSV |
| `app/learning` | Раунды мини-игр, проверка ответов, входящие, перенос прогресса гостя |
| `app/speech` | Озвучка слов и примеров: MP3 нейросетевыми голосами (edge-tts), кэш в `media/tts` |
| `app/gamification` | Правила игры: должности, система Лейтнера, опыт, серия дней, достижения |
| `app/admin` | Эндпоинты администратора |
| `app/system` | `/health`, `/levels` |
| `migrations` | Миграции Alembic |
| `tests` | Автоматические тесты (pytest) |

Каждый модуль: `router.py` (HTTP) → `service.py` (бизнес-логика) → `repository.py` (запросы к БД), модели — `models.py`.
