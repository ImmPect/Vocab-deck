"""Роутер модуля admin: слова и отделы общей колоды, поиск пользователей (раздел 3.8 ПР3).

Зависимость require_admin подключена ко всему роутеру: роль проверяется
по данным БД на каждом запросе (NFR-S-07).
"""
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.admin import service as admin_service
from app.admin.schemas import AdminDeckCreate, AdminDeckUpdate
from app.auth.dependencies import require_admin
from app.core.db import get_db
from app.core.responses import Page, ok, pagination
from app.decks import service as decks_service
from app.users.models import User
from app.words import service as words_service
from app.words.schemas import AdminWordCreate, AdminWordUpdate

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/words", summary="Поиск слов общей колоды")
def list_words(q: str | None = Query(None, description="Поиск по en и ru, от 2 символов"),
               deck_id: int | None = None,
               status: str | None = Query(None, description="draft, published или archived"),
               page: Page = Depends(pagination), db: Session = Depends(get_db)):
    items, meta = words_service.admin_list(db, q, deck_id, status, page)
    return ok(items, meta)


@router.post("/words", status_code=201, summary="Создание слова")
def create_word(body: AdminWordCreate, response: Response, admin: User = Depends(require_admin),
                db: Session = Depends(get_db)):
    word = words_service.admin_create(db, admin, body.model_dump())
    response.headers["Location"] = f"/api/v1/admin/words/{word['id']}"
    return ok(word)


@router.patch("/words/{word_id}", summary="Изменение, публикация, архивирование слова")
def update_word(word_id: int, body: AdminWordUpdate, admin: User = Depends(require_admin),
                db: Session = Depends(get_db)):
    return ok(words_service.admin_update(db, admin, word_id, body.model_dump(exclude_unset=True)))


@router.post("/decks", status_code=201, summary="Создание отдела")
def create_deck(body: AdminDeckCreate, response: Response, admin: User = Depends(require_admin),
                db: Session = Depends(get_db)):
    deck = decks_service.admin_create_deck(db, admin, body.model_dump())
    response.headers["Location"] = f"/api/v1/decks/{deck['id']}"
    return ok(deck)


@router.patch("/decks/{deck_id}", summary="Изменение отдела и условия открытия")
def update_deck(deck_id: int, body: AdminDeckUpdate, admin: User = Depends(require_admin),
                db: Session = Depends(get_db)):
    return ok(decks_service.admin_update_deck(db, admin, deck_id, body.model_dump(exclude_unset=True)))


@router.get("/users", summary="Поиск пользователя по почте")
def search_users(email: str | None = Query(None, description="Подстрока почты, от 3 символов"),
                 page: Page = Depends(pagination), db: Session = Depends(get_db)):
    items, meta = admin_service.search_users(db, email, page)
    return ok(items, meta)
