"""Конверт успешного ответа {"data": ..., "meta": ...} и параметры пагинации."""
from dataclasses import dataclass
from typing import Any

from fastapi import Query


def ok(data: Any, meta: dict | None = None) -> dict:
    body = {"data": data}
    if meta is not None:
        body["meta"] = meta
    return body


@dataclass
class Page:
    page: int
    limit: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit

    def meta(self, total_items: int) -> dict:
        return {"page": self.page, "limit": self.limit, "total_items": total_items}


def pagination(page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)) -> Page:
    """Зависимость FastAPI: ?page=&limit= (limit ≤ 100, раздел 3.1.7)."""
    return Page(page, limit)
