"""Роутер модуля users: профиль и личная статистика (раздел 3.4 ПР3)."""
from datetime import date

from fastapi import APIRouter, Cookie, Depends, Query, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import SESSION_COOKIE, get_current_user
from app.auth.router import clear_session_cookie
from app.core.db import get_db
from app.core.responses import ok
from app.users import service
from app.users.models import User
from app.users.schemas import DeleteMe, UpdateMe

router = APIRouter(tags=["users"])


@router.get("/me", summary="Профиль текущего пользователя")
def get_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(service.profile(db, user))


@router.patch("/me", summary="Изменение имени, часового пояса или пароля")
def patch_me(body: UpdateMe, user: User = Depends(get_current_user), db: Session = Depends(get_db),
             session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE)):
    return ok(service.update_me(db, user, body, session_id))


@router.delete("/me", status_code=204, summary="Удаление аккаунта")
def delete_me(body: DeleteMe, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service.delete_me(db, user, body.password)
    response = Response(status_code=204)
    clear_session_cookie(response)
    return response


@router.get("/me/stats", summary="Статистика ответов по дням")
def get_stats(date_from: date | None = Query(None, alias="from"),
              date_to: date | None = Query(None, alias="to"),
              user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(service.stats_by_day(db, user, date_from, date_to))


@router.get("/me/achievements", summary="Достижения пользователя")
def get_achievements(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(service.achievements(db, user))
