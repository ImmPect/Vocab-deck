"""Промежуточные слои: идентификатор запроса, журнал, защита от CSRF."""
import json
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.errors import error_body

log = logging.getLogger("vocabdeck.access")

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
CSRF_HEADER_VALUE = "VocabDeck"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Присваивает запросу X-Request-Id и пишет строку журнала в формате JSON.

    Пароли, тела запросов и cookie в журнал не попадают.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:16]
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        log.info(json.dumps({
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "ms": round((time.perf_counter() - started) * 1000, 1),
        }, ensure_ascii=False))
        return response


class CSRFMiddleware(BaseHTTPMiddleware):
    """Изменяющие запросы к API обязаны нести заголовок X-Requested-With: VocabDeck.

    Чужой сайт не может добавить этот заголовок без разрешения CORS,
    а CORS разрешён только для origin фронтенда (раздел 3.1.3).
    """

    async def dispatch(self, request: Request, call_next):
        if (request.method in UNSAFE_METHODS and request.url.path.startswith("/api/")
                and request.headers.get("X-Requested-With") != CSRF_HEADER_VALUE):
            return JSONResponse(
                error_body("csrf_check_failed", "Запрос отклонён: нет заголовка X-Requested-With"),
                status_code=403,
            )
        return await call_next(request)
