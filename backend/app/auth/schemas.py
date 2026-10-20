"""Pydantic-схемы модуля auth: регистрация и вход (раздел 3.3 ПР3)."""
from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, ConfigDict, field_validator

from app.learning.guest import GuestProgress
from app.users.schemas import PASSWORD_MAX, check_name, check_new_password, check_timezone

EMAIL_MAX = 255
EMAIL_MESSAGE = "Укажите почту в формате name@example.ru"


def check_email(value: str) -> str:
    """Проверяет формат почты и приводит её к нижнему регистру."""
    value = value.strip().lower()
    if not value or len(value) > EMAIL_MAX:
        raise ValueError(EMAIL_MESSAGE)
    try:
        validate_email(value, check_deliverability=False)
    except EmailNotValidError:
        raise ValueError(EMAIL_MESSAGE) from None
    return value


class RegisterIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    email: str
    password: str
    consent: bool
    timezone: str = "Europe/Moscow"
    guest_progress: GuestProgress | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        return check_name(v)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return check_email(v)

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return check_new_password(v)

    @field_validator("timezone")
    @classmethod
    def _timezone(cls, v: str) -> str:
        return check_timezone(v)

    @field_validator("consent")
    @classmethod
    def _consent(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError("Нужно согласие на обработку персональных данных")
        return v


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str
    guest_progress: GuestProgress | None = None

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        # Формат не проверяется: неверная почта даёт общий ответ 401, а не подсказку
        v = v.strip().lower()
        if not v:
            raise ValueError("Введите почту")
        if len(v) > EMAIL_MAX:
            raise ValueError(f"Почта должна содержать не более {EMAIL_MAX} символов")
        return v

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        if not v:
            raise ValueError("Введите пароль")
        if len(v) > PASSWORD_MAX:
            raise ValueError(f"Пароль должен содержать не более {PASSWORD_MAX} символов")
        return v
