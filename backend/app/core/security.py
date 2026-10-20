"""Хэширование паролей, токены сессий и подпись гостевых квитанций."""
import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import settings

_hasher = PasswordHasher()  # Argon2id с параметрами по умолчанию (NFR-S-02)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def new_session_token() -> str:
    """Случайный токен 256 бит для cookie session_id (NFR-S-03)."""
    return secrets.token_urlsafe(32)


def _canonical(word_id: int, direction: str, mode: str, is_correct: bool,
               answered_at: str, client_event_id: str, combo: int) -> str:
    return f"v1|{word_id}|{direction}|{mode}|{str(is_correct).lower()}|{answered_at}|{client_event_id}|{combo}"


def sign_receipt(**fields) -> str:
    """HMAC-SHA256 от канонической строки события гостя (раздел 3.1.9 ПР3)."""
    msg = _canonical(**fields).encode()
    return hmac.new(settings.secret_key.encode(), msg, hashlib.sha256).hexdigest()


def verify_receipt(receipt: str, **fields) -> bool:
    return hmac.compare_digest(receipt or "", sign_receipt(**fields))
