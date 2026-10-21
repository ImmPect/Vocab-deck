"""Роутер озвучки: MP3 с произношением слова или примера (US-03)."""
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_optional_user
from app.core.db import get_db
from app.core.ratelimit import limiter
from app.speech import service
from app.users.models import User

router = APIRouter(tags=["speech"])


@router.get(
    "/words/{word_id}/audio",
    summary="Озвучка слова или примера (MP3)",
    response_class=FileResponse,
    responses={200: {"content": {"audio/mpeg": {}}}, 503: {"description": "Движок синтеза недоступен"}},
)
@limiter.limit("120/minute")
def word_audio(request: Request, word_id: int,
               part: Literal["word", "example"] = Query("word", description="word — слово, example — пример"),
               accent: Literal["uk", "us"] = Query("uk", description="Британское или американское произношение"),
               user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    path = service.word_audio(db, user, word_id, part, accent)
    # Браузер кэширует файл на сутки; после правки слова сменится текст, а с ним и ETag файла
    return FileResponse(path, media_type="audio/mpeg", headers={"Cache-Control": "private, max-age=86400"})
