"""Роутер модуля words: слова колод и личных списков (раздел 3.6 ПР3)."""
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_optional_user
from app.core.db import get_db
from app.core.responses import Page, ok, pagination
from app.users.models import User
from app.words import service
from app.words.schemas import WordCreate, WordUpdate

router = APIRouter(tags=["words"])


@router.get("/decks/{deck_id}/words", summary="Слова колоды")
def list_words(deck_id: int, q: str | None = Query(None, description="Поиск по en и ru, от 2 символов"),
               page: Page = Depends(pagination), user: User | None = Depends(get_optional_user),
               db: Session = Depends(get_db)):
    items, meta = service.list_deck_words(db, user, deck_id, q, page)
    return ok(items, meta)


@router.post("/decks/{deck_id}/words", status_code=201, summary="Слово в личный список")
def create_word(deck_id: int, body: WordCreate, response: Response, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    word = service.create_personal_word(db, user, deck_id, body.model_dump())
    response.headers["Location"] = f"/api/v1/words/{word['id']}"
    return ok(word)


@router.patch("/words/{word_id}", summary="Изменение слова личного списка")
def update_word(word_id: int, body: WordUpdate, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    return ok(service.update_personal_word(db, user, word_id, body.model_dump(exclude_unset=True)))


@router.delete("/words/{word_id}", status_code=204, response_class=Response,
               summary="Удаление слова личного списка")
def delete_word(word_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service.delete_personal_word(db, user, word_id)
    return Response(status_code=204)
