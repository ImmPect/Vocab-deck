"""Роутер модуля learning: входящие, раунды мини-игр, пакет ответов (раздел 3.7 ПР3)."""
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_optional_user
from app.core.db import get_db
from app.core.ratelimit import limiter
from app.core.responses import Page, ok, pagination
from app.learning import service
from app.learning.schemas import AnswerCreate, BatchCreate, RoundCreate
from app.users.models import User

router = APIRouter(tags=["learning"])


@router.get("/inbox", summary="Входящие: слова, срок повтора которых наступил")
def get_inbox(direction: Literal["en_ru", "ru_en"] | None = Query(default=None),
              page: Page = Depends(pagination), user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    items, total = service.inbox(db, user, direction, page.offset, page.limit)
    return ok(items, page.meta(total))


@router.post("/rounds", status_code=201, summary="Начать раунд мини-игры (гость или пользователь)")
def create_round(body: RoundCreate, response: Response, user: User | None = Depends(get_optional_user),
                 db: Session = Depends(get_db)):
    data = service.start_round(db, user, body)
    response.headers["Location"] = f"/api/v1/rounds/{data['round_id']}"
    return ok(data)


@router.post("/rounds/{round_id}/answers", summary="Ответ на вопрос раунда")
def answer_round(round_id: uuid.UUID, body: AnswerCreate, user: User | None = Depends(get_optional_user),
                 db: Session = Depends(get_db)):
    return ok(service.answer_round(db, user, round_id, body))


@router.post("/rounds/{round_id}/finish", summary="Итоги раунда")
def finish_round(round_id: uuid.UUID, user: User | None = Depends(get_optional_user),
                 db: Session = Depends(get_db)):
    return ok(service.finish_round(db, user, round_id))


@router.post("/answers/batch", summary="Пакет ответов: самооценка, входящие, отложенные ответы")
@limiter.limit("30/minute")
def answers_batch(request: Request, body: BatchCreate, user: User | None = Depends(get_optional_user),
                  db: Session = Depends(get_db)):
    return ok(service.answer_batch(db, user, body.answers))
