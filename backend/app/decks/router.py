"""Роутер модуля decks: отделы, личные списки и импорт CSV (раздел 3.5 ПР3)."""
from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_optional_user
from app.core.db import get_db
from app.core.responses import ok
from app.decks import service
from app.decks.csv_import import MAX_FILE_BYTES
from app.decks.schemas import DeckIn
from app.users.models import User

router = APIRouter(prefix="/decks", tags=["decks"])


@router.get("", summary="Отделы и личные списки")
def list_decks(kind: str | None = Query(None, description="shared или personal"),
               user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    items = service.list_decks(db, user, kind)
    return ok(items, {"total_items": len(items)})


@router.get("/{deck_id}", summary="Колода")
def get_deck(deck_id: int, user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    return ok(service.get_deck(db, user, deck_id))


@router.post("", status_code=201, summary="Создание личного списка")
def create_deck(body: DeckIn, response: Response, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    deck = service.create_list(db, user, body.title)
    response.headers["Location"] = f"/api/v1/decks/{deck['id']}"
    return ok(deck)


@router.patch("/{deck_id}", summary="Переименование личного списка")
def rename_deck(deck_id: int, body: DeckIn, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    return ok(service.rename_list(db, user, deck_id, body.title))


@router.delete("/{deck_id}", status_code=204, response_class=Response, summary="Удаление личного списка")
def delete_deck(deck_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service.delete_list(db, user, deck_id)
    return Response(status_code=204)


@router.post("/{deck_id}/import", summary="Импорт слов из CSV")
def import_csv(deck_id: int, file: UploadFile = File(...), user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    # Читаем не больше лимита + 1 байт: этого достаточно, чтобы отличить слишком большой файл.
    # Обработчик синхронный: FastAPI выполнит его в пуле потоков и не заблокирует цикл событий
    raw = file.file.read(MAX_FILE_BYTES + 1)
    return ok(service.import_csv(db, user, deck_id, raw))
