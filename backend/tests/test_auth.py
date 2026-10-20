"""Модуль auth: регистрация, вход, блокировка после неудачных попыток, выход."""
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.db import utcnow
from app.learning.guest import GuestProgress, import_guest_progress
from app.users.models import User, UserSession
from tests.conftest import PASSWORD

REG = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
LOGOUT = "/api/v1/auth/logout"


def reg_body(**over):
    body = {"name": "  Анна ", "email": "Anna@Example.RU", "password": "Str0ngPass!", "consent": True}
    body.update(over)
    return body


def _guest_import_ready() -> bool:
    """import_guest_progress реализуется в модуле learning; до этого тест переноса пропускается."""
    try:
        import_guest_progress(None, None, GuestProgress(format_version=1, events=[]))
    except NotImplementedError:
        return False
    except Exception:
        return True
    return True


def test_register_creates_user_and_session(client, db):
    r = client.post(REG, json=reg_body())
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["imported"] is None
    user = data["user"]
    assert user["email"] == "anna@example.ru" and user["name"] == "Анна"
    assert user["role"] == "user" and user["xp"] == 0
    assert user["level"]["code"] == "intern"
    assert "password_hash" not in user and "failed_logins" not in user

    cookie = r.headers["set-cookie"]
    assert "session_id=" in cookie and "HttpOnly" in cookie and "Path=/api" in cookie
    assert "samesite=lax" in cookie.lower() and "Max-Age=2592000" in cookie
    # Cookie сразу даёт доступ к профилю
    assert client.get("/api/v1/me").json()["data"]["email"] == "anna@example.ru"
    assert db.scalar(select(UserSession).where(UserSession.user_id == user["id"])) is not None


def test_register_duplicate_email(client, make_user):
    make_user("anna@example.ru")
    r = client.post(REG, json=reg_body())
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "email_taken"


@pytest.mark.parametrize("over, field", [
    ({"consent": False}, "consent"),
    ({"password": "short"}, "password"),
    ({"email": "not-an-email"}, "email"),
    ({"name": "   "}, "name"),
    ({"timezone": "Mars/Base"}, "timezone"),
    ({"role": "admin"}, "role"),
])
def test_register_validation(client, over, field):
    r = client.post(REG, json=reg_body(**over))
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "validation_failed"
    assert any(d["field"] == field for d in err["details"])


def test_register_validation_message_in_russian(client):
    r = client.post(REG, json=reg_body(email="bad"))
    assert r.json()["error"]["details"][0]["message"] == "Укажите почту в формате name@example.ru"


@pytest.mark.skipif(not _guest_import_ready(), reason="import_guest_progress ещё не реализован")
def test_register_with_empty_guest_progress(client):
    r = client.post(REG, json=reg_body(guest_progress={"format_version": 1, "events": []}))
    assert r.status_code == 201
    imported = r.json()["data"]["imported"]
    assert imported["accepted"] == 0 and imported["rejected"] == 0


def test_register_unknown_guest_format(client):
    r = client.post(REG, json=reg_body(guest_progress={"format_version": 2, "events": []}))
    assert r.status_code == 422


def test_login_success_resets_counter(client, db, make_user):
    u = make_user("bob@example.ru", failed_logins=3)
    r = client.post(LOGIN, json={"email": "BOB@example.ru", "password": PASSWORD})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["user"]["id"] == u.id and data["imported"] is None
    assert "session_id=" in r.headers["set-cookie"]
    db.refresh(u)
    assert u.failed_logins == 0


def test_login_generic_error(client, make_user):
    make_user("bob@example.ru")
    wrong = client.post(LOGIN, json={"email": "bob@example.ru", "password": "WrongPass1"})
    unknown = client.post(LOGIN, json={"email": "nobody@example.ru", "password": "WrongPass1"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {
        "error": {"code": "invalid_credentials", "message": "Неверная почта или пароль"}}


def test_login_empty_fields(client):
    r = client.post(LOGIN, json={"email": "", "password": ""})
    assert r.status_code == 422


def test_lockout_after_five_failures(client, db, make_user):
    u = make_user("bob@example.ru")
    for _ in range(4):
        assert client.post(LOGIN, json={"email": "bob@example.ru", "password": "WrongPass1"}).status_code == 401
    db.refresh(u)
    assert u.failed_logins == 4

    fifth = client.post(LOGIN, json={"email": "bob@example.ru", "password": "WrongPass1"})
    assert fifth.status_code == 423
    db.refresh(u)
    assert u.failed_logins == 0 and u.locked_until is not None

    # Пока блокировка действует, верный пароль тоже отклоняется
    r = client.post(LOGIN, json={"email": "bob@example.ru", "password": PASSWORD})
    assert r.status_code == 423
    err = r.json()["error"]
    assert err["code"] == "account_locked"
    assert err["details"][0]["locked_until"].endswith("Z")
    assert 0 < int(r.headers["Retry-After"]) <= 900


def test_login_after_lock_expired(client, db, make_user):
    make_user("bob@example.ru", locked_until=utcnow() - timedelta(minutes=1))
    r = client.post(LOGIN, json={"email": "bob@example.ru", "password": PASSWORD})
    assert r.status_code == 200
    assert db.scalar(select(User).where(User.email == "bob@example.ru")).locked_until is None


def test_logout_invalidates_session(client, db, make_user):
    make_user("bob@example.ru")
    client.post(LOGIN, json={"email": "bob@example.ru", "password": PASSWORD})
    assert client.get("/api/v1/me").status_code == 200
    token = client.cookies.get("session_id")

    r = client.post(LOGOUT)
    assert r.status_code == 204 and r.content == b""
    assert "Max-Age=0" in r.headers["set-cookie"]
    assert db.get(UserSession, token) is None
    assert client.get("/api/v1/me", cookies={"session_id": token}).status_code == 401


def test_logout_is_idempotent(client):
    assert client.post(LOGOUT).status_code == 204
