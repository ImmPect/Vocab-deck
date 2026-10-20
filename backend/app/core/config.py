"""Конфигурация из переменных окружения (принцип 12-factor).

Значения по умолчанию подходят для локальной разработки: SQLite-файл рядом
с проектом и cookie без флага Secure (локально нет HTTPS). В производственной
среде все параметры задаются переменными окружения или файлом .env.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]  # каталог backend/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Vocab Deck API"
    version: str = "1.0.0"
    env: str = "dev"  # dev | test | prod

    # PostgreSQL в производственной среде: postgresql+psycopg://user:pass@host:5432/vocabdeck
    database_url: str = f"sqlite:///{(BASE_DIR / 'vocabdeck.db').as_posix()}"

    # Секрет для HMAC-квитанций гостя. В prod обязательно задать длинное случайное значение.
    secret_key: str = "dev-secret-change-me"

    cors_origin: str = "http://localhost:5173"
    session_ttl_days: int = 30
    cookie_secure: bool = False

    # Защита от подбора пароля (NFR-S-04)
    max_failed_logins: int = 5
    lock_minutes: int = 15
    rate_limit_login: str = "20/minute"
    rate_limit_default: str = "60/minute"

    # Раунд мини-игры
    round_time_limit_s: int = 60
    round_grace_s: int = 10
    round_questions: int = 5

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
