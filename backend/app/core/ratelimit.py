"""Ограничение частоты запросов по IP (slowapi). Лимиты задаются в config."""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit_default],
                  enabled=settings.env != "test")
