"""Точка входа: создание приложения FastAPI и подключение роутеров модулей.

Запуск для разработки:  uvicorn app.main:app --reload
Swagger UI:             http://127.0.0.1:8000/docs
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.admin.router import router as admin_router
from app.auth.router import router as auth_router
from app.core.config import settings
from app.core.errors import error_body, register_error_handlers
from app.core.middleware import CSRFMiddleware, RequestContextMiddleware
from app.core.ratelimit import limiter
from app.decks.router import router as decks_router
from app.learning.router import router as learning_router
from app.speech.router import router as speech_router
from app.system.router import router as system_router
from app.users.router import router as users_router
from app.words.router import router as words_router

API_PREFIX = "/api/v1"

logging.basicConfig(level=logging.INFO, format="%(message)s")


def create_app() -> FastAPI:
    settings.check_production()
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="Серверная часть Vocab Deck — деловая английская лексика A2–B1 "
                    "в формате карьерной лестницы. Изменяющие запросы требуют заголовок "
                    "`X-Requested-With: VocabDeck`.",
        docs_url=None,  # своя страница /docs, см. ниже
        openapi_url="/openapi.json",
    )

    # Порядок: последний добавленный middleware выполняется первым
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.cors_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-Requested-With"],
    )
    app.add_middleware(RequestContextMiddleware)

    register_error_handlers(app)

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limited(_, exc: RateLimitExceeded):
        return JSONResponse(error_body("too_many_requests", "Слишком много запросов. Попробуйте через минуту"),
                            status_code=429, headers={"Retry-After": "60"})

    for r in (system_router, auth_router, users_router, decks_router, words_router,
              learning_router, speech_router, admin_router):
        app.include_router(r, prefix=API_PREFIX)

    @app.get("/docs", include_in_schema=False)
    def swagger_ui() -> HTMLResponse:
        """Swagger UI, который сам добавляет заголовок X-Requested-With к запросам.

        Без него кнопка «Try it out» для POST/PATCH/DELETE получала бы 403 csrf_check_failed.
        Cookie сессии браузер передаёт сам: страница и API на одном origin.
        """
        page = get_swagger_ui_html(openapi_url=app.openapi_url, title=f"{settings.app_name} — документация")
        html = page.body.decode().replace(
            "SwaggerUIBundle({",
            "SwaggerUIBundle({ requestInterceptor: (req) => "
            "{ req.headers['X-Requested-With'] = 'VocabDeck'; return req; },",
            1)
        return HTMLResponse(html)

    @app.get("/", include_in_schema=False)
    def root():
        return {"data": {"name": settings.app_name, "version": settings.version, "docs": "/docs"}}

    return app


app = create_app()
