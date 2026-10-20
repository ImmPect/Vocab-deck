"""Справочники и служебные эндпоинты: GET /levels, GET /health (раздел 3.9 ПР3)."""
from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.errors import error_body
from app.core.responses import ok
from app.gamification.rules import LEVELS

router = APIRouter(tags=["system"])


@router.get("/levels", summary="Карьерная лестница")
def levels(response: Response):
    response.headers["Cache-Control"] = "public, max-age=3600"
    return ok(LEVELS, {"total_items": len(LEVELS)})


@router.get("/health", summary="Проверка доступности")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(error_body("db_unavailable", "База данных недоступна"), status_code=503)
    return ok({"status": "ok", "db": "ok", "version": settings.version})
