"""Pydantic-схемы модуля users и общие проверки полей (используются и в auth)."""
from functools import lru_cache
from zoneinfo import available_timezones

from pydantic import BaseModel, ConfigDict, field_validator

NAME_MAX = 100
PASSWORD_MIN, PASSWORD_MAX = 8, 128


def check_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Укажите имя")
    if len(value) > NAME_MAX:
        raise ValueError(f"Имя должно содержать не более {NAME_MAX} символов")
    return value


def check_new_password(value: str) -> str:
    if len(value) < PASSWORD_MIN:
        raise ValueError(f"Пароль должен содержать не менее {PASSWORD_MIN} символов")
    if len(value) > PASSWORD_MAX:
        raise ValueError(f"Пароль должен содержать не более {PASSWORD_MAX} символов")
    return value


@lru_cache(maxsize=1)
def _known_timezones() -> frozenset[str]:
    return frozenset(available_timezones())


def check_timezone(value: str) -> str:
    """Имя часового пояса IANA, например Europe/Moscow."""
    if value not in _known_timezones():
        raise ValueError("Неизвестный часовой пояс. Укажите его в формате Europe/Moscow")
    return value


class UpdateMe(BaseModel):
    """PATCH /me: передаются только изменяемые поля."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    current_password: str | None = None
    new_password: str | None = None
    timezone: str | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: str | None) -> str | None:
        return None if v is None else check_name(v)

    @field_validator("new_password")
    @classmethod
    def _new_password(cls, v: str | None) -> str | None:
        return None if v is None else check_new_password(v)

    @field_validator("current_password")
    @classmethod
    def _current_password(cls, v: str | None) -> str | None:
        if v is not None and len(v) > PASSWORD_MAX:
            raise ValueError(f"Пароль должен содержать не более {PASSWORD_MAX} символов")
        return v

    @field_validator("timezone")
    @classmethod
    def _timezone(cls, v: str | None) -> str | None:
        return None if v is None else check_timezone(v)


class DeleteMe(BaseModel):
    """DELETE /me: подтверждение паролем."""

    model_config = ConfigDict(extra="forbid")

    password: str

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        if not v:
            raise ValueError("Введите пароль для подтверждения")
        if len(v) > PASSWORD_MAX:
            raise ValueError(f"Пароль должен содержать не более {PASSWORD_MAX} символов")
        return v
