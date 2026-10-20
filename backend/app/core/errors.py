"""Доменные ошибки и единый формат ответа об ошибке (раздел 3.1.5 ПР3).

Сервисы бросают исключения из этого модуля и ничего не знают об HTTP.
Обработчики ниже превращают их в JSON вида {"error": {"code", "message", "details"}}.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("vocabdeck")


class AppError(Exception):
    status_code = 400
    code = "bad_request"
    message = "Некорректный запрос"

    def __init__(self, message: str | None = None, *, code: str | None = None,
                 details: list | dict | None = None, headers: dict | None = None):
        super().__init__(message or self.message)
        self.message = message or self.message
        if code:
            self.code = code
        self.details = details
        self.headers = headers


class Unauthorized(AppError):
    status_code, code, message = 401, "unauthorized", "Войдите в аккаунт"


class Forbidden(AppError):
    status_code, code, message = 403, "forbidden", "Недостаточно прав"


class NotFound(AppError):
    status_code, code, message = 404, "not_found", "Не найдено"


class Conflict(AppError):
    status_code, code, message = 409, "conflict", "Конфликт с текущим состоянием"


class PayloadTooLarge(AppError):
    status_code, code, message = 413, "file_too_large", "Файл больше 1 МБ"


class ValidationFailed(AppError):
    status_code, code, message = 422, "validation_failed", "Проверьте введённые данные"


class Locked(AppError):
    status_code, code, message = 423, "account_locked", "Вход временно заблокирован"


def error_body(code: str, message: str, details=None) -> dict:
    err = {"code": code, "message": message}
    if details is not None:
        err["details"] = details
    return {"error": err}


def _field_path(loc) -> str:
    parts = [p for p in loc if p not in ("body", "query", "path", "header", "cookie")]
    out = ""
    for p in parts:
        out += f"[{p}]" if isinstance(p, int) else (f".{p}" if out else str(p))
    return out


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(error_body(exc.code, exc.message, exc.details),
                            status_code=exc.status_code, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        details = []
        for e in exc.errors():
            if e.get("type") == "json_invalid":
                return JSONResponse(error_body("bad_request", "Тело запроса не является корректным JSON"),
                                    status_code=400)
            msg = str(e.get("msg", "")).removeprefix("Value error, ")
            details.append({"field": _field_path(e.get("loc", ())), "message": msg})
        return JSONResponse(error_body("validation_failed", "Проверьте введённые данные", details),
                            status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        codes = {404: ("not_found", "Не найдено"), 405: ("method_not_allowed", "Метод не поддерживается")}
        code, msg = codes.get(exc.status_code, ("http_error", str(exc.detail)))
        return JSONResponse(error_body(code, msg), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        log.exception("unhandled error, request_id=%s", getattr(request.state, "request_id", "-"))
        return JSONResponse(error_body("internal_error", "Что-то пошло не так. Попробуйте ещё раз"),
                            status_code=500)
