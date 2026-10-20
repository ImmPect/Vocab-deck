"""Сервис модуля auth: регистрация, вход с защитой от подбора, выход (раздел 3.3 ПР3).

Ничего не знает об HTTP: возвращает данные и токен сессии, ошибки — исключения
из app.core.errors. Cookie выставляет роутер.
"""
import math
from datetime import timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import utcnow
from app.core.errors import Conflict, Locked, Unauthorized
from app.core.security import hash_password, new_session_token, verify_password
from app.learning.guest import GuestProgress, import_guest_progress
from app.users import repository as users_repo
from app.users.models import User
from app.users.service import iso_z, short_user

EMAIL_TAKEN_MESSAGE = "Аккаунт с этой почтой уже есть. Войдите, и прогресс будет объединён"
INVALID_CREDENTIALS_MESSAGE = "Неверная почта или пароль"

# Хэш-заглушка: для несуществующей почты тоже выполняется проверка Argon2,
# чтобы время ответа не выдавало, есть ли аккаунт (US-06)
_DUMMY_HASH = hash_password("dummy-password-for-timing")


def create_session(db: Session, user: User) -> str:
    """Создаёт запись в sessions и возвращает токен для cookie."""
    token = new_session_token()
    users_repo.add_session(db, token, user.id, utcnow() + timedelta(days=settings.session_ttl_days))
    return token


def _import(db: Session, user: User, progress: GuestProgress | None) -> dict | None:
    return import_guest_progress(db, user, progress) if progress is not None else None


def register(db: Session, *, name: str, email: str, password: str, timezone: str,
             guest_progress: GuestProgress | None) -> tuple[dict, str]:
    """Создаёт пользователя, сессию и переносит гостевой прогресс в одной транзакции."""
    if users_repo.email_exists(db, email):
        raise Conflict(EMAIL_TAKEN_MESSAGE, code="email_taken")
    user = User(name=name, email=email, password_hash=hash_password(password), timezone=timezone,
                consent_at=utcnow())
    try:
        users_repo.add_user(db, user)
    except IntegrityError:  # одновременная регистрация с той же почтой
        db.rollback()
        raise Conflict(EMAIL_TAKEN_MESSAGE, code="email_taken") from None
    imported = _import(db, user, guest_progress)
    token = create_session(db, user)
    return {"user": short_user(user), "imported": imported}, token


def _raise_locked(user: User) -> None:
    seconds = max(1, math.ceil((user.locked_until - utcnow()).total_seconds()))
    raise Locked(f"Слишком много неудачных попыток. Попробуйте войти через {settings.lock_minutes} минут",
                 details=[{"locked_until": iso_z(user.locked_until)}],
                 headers={"Retry-After": str(seconds)})


def login(db: Session, *, email: str, password: str,
          guest_progress: GuestProgress | None) -> tuple[dict, str]:
    """Проверяет почту и пароль, учитывает неудачные попытки (NFR-S-04), создаёт сессию."""
    user = users_repo.get_by_email(db, email)
    if user is None:
        verify_password(_DUMMY_HASH, password)
        raise Unauthorized(INVALID_CREDENTIALS_MESSAGE, code="invalid_credentials")

    if user.locked_until is not None and user.locked_until > utcnow():
        _raise_locked(user)

    if not verify_password(user.password_hash, password):
        user.failed_logins += 1
        locked = user.failed_logins >= settings.max_failed_logins
        if locked:
            user.locked_until = utcnow() + timedelta(minutes=settings.lock_minutes)
            user.failed_logins = 0
        # Счётчик фиксируется сразу: исключение ниже откатило бы транзакцию запроса
        db.commit()
        if locked:
            _raise_locked(user)
        raise Unauthorized(INVALID_CREDENTIALS_MESSAGE, code="invalid_credentials")

    user.failed_logins = 0
    user.locked_until = None
    imported = _import(db, user, guest_progress)
    token = create_session(db, user)
    return {"user": short_user(user), "imported": imported}, token


def logout(db: Session, token: str | None) -> None:
    """Удаляет сессию; без действующей сессии ничего не делает (идемпотентно)."""
    if token:
        users_repo.delete_session(db, token)
