"""Роутер модуля auth: регистрация, вход, выход (раздел 3.3 ПР3).

Здесь же — установка и сброс cookie session_id (HttpOnly, SameSite=Lax, Path=/api).
"""
from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy.orm import Session

from app.auth import service
from app.auth.dependencies import SESSION_COOKIE
from app.auth.schemas import LoginIn, RegisterIn
from app.core.config import settings
from app.core.db import get_db
from app.core.ratelimit import limiter
from app.core.responses import ok

router = APIRouter(tags=["auth"])

COOKIE_PATH = "/api"
RATE_LIMIT_REGISTER = "5/hour"  # раздел 3.3.1: не более 5 регистраций в час с одного IP


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(SESSION_COOKIE, token, max_age=settings.session_ttl_days * 86400, path=COOKIE_PATH,
                        httponly=True, secure=settings.cookie_secure, samesite="lax")


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path=COOKIE_PATH, httponly=True,
                           secure=settings.cookie_secure, samesite="lax")


@router.post("/auth/register", status_code=201, summary="Регистрация")
@limiter.limit(RATE_LIMIT_REGISTER)
def register(request: Request, response: Response, body: RegisterIn, db: Session = Depends(get_db)):
    data, token = service.register(db, name=body.name, email=body.email, password=body.password,
                                   timezone=body.timezone, guest_progress=body.guest_progress)
    set_session_cookie(response, token)
    return ok(data)


@router.post("/auth/login", summary="Вход")
@limiter.limit(settings.rate_limit_login)
def login(request: Request, response: Response, body: LoginIn, db: Session = Depends(get_db)):
    data, token = service.login(db, email=body.email, password=body.password,
                                guest_progress=body.guest_progress)
    set_session_cookie(response, token)
    return ok(data)


@router.post("/auth/logout", status_code=204, summary="Выход")
def logout(session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE),
           db: Session = Depends(get_db)):
    service.logout(db, session_id)
    response = Response(status_code=204)
    clear_session_cookie(response)
    return response
