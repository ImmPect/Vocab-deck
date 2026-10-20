"""Модуль users: профиль, изменение и удаление аккаунта, статистика, достижения."""
import uuid
from datetime import timedelta

from sqlalchemy import select

from app.core.db import utcnow
from app.gamification.models import Achievement, UserAchievement
from app.gamification.service import user_today
from app.learning.models import AnswerEvent
from app.users.models import User, UserSession
from app.words.models import Word
from tests.conftest import PASSWORD

ME = "/api/v1/me"


def test_me_requires_session(client):
    r = client.get(ME)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_me_profile(make_user, make_client):
    u = make_user("anna@example.ru", name="Анна", xp=1240)
    r = make_client(u).get(ME)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["id"] == u.id and data["email"] == "anna@example.ru" and data["role"] == "user"
    assert data["level"]["code"] == "specialist"
    assert data["next_level"] == {"code": "senior", "title": "Старший специалист", "min_xp": 1600, "xp_left": 360}
    assert data["features"] == {"dictation": True, "ru_en": False, "unlimited_lists": False}
    assert data["inbox_count"] == 0 and data["timezone"] == "Europe/Moscow"
    assert data["created_at"].endswith("Z")
    for secret in ("password_hash", "failed_logins", "locked_until"):
        assert secret not in data


def test_patch_name_and_timezone(user_client):
    r = user_client.patch(ME, json={"name": "  Пётр ", "timezone": "Asia/Yekaterinburg"})
    assert r.status_code == 200
    assert r.json()["data"]["name"] == "Пётр"
    assert r.json()["data"]["timezone"] == "Asia/Yekaterinburg"


def test_patch_validation(user_client):
    assert user_client.patch(ME, json={"name": ""}).status_code == 422
    assert user_client.patch(ME, json={"timezone": "Nowhere/City"}).status_code == 422
    assert user_client.patch(ME, json={"email": "x@example.ru"}).status_code == 422
    r = user_client.patch(ME, json={"new_password": "N3wPassw0rd"})
    assert r.status_code == 422 and r.json()["error"]["details"][0]["field"] == "current_password"
    assert user_client.patch(ME, json={"current_password": PASSWORD, "new_password": "short"}).status_code == 422


def test_patch_password(db, client, make_user, make_client):
    u = make_user("anna@example.ru")
    current, other = make_client(u), make_client(u)

    r = current.patch(ME, json={"current_password": "WrongPass1", "new_password": "N3wPassw0rd"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_credentials"

    r = current.patch(ME, json={"current_password": PASSWORD, "new_password": "N3wPassw0rd"})
    assert r.status_code == 200
    # Текущая сессия сохраняется, остальные удалены
    assert current.get(ME).status_code == 200
    assert other.get(ME).status_code == 401
    assert len(db.scalars(select(UserSession).where(UserSession.user_id == u.id)).all()) == 1
    # Вход — только с новым паролем
    login = "/api/v1/auth/login"
    assert client.post(login, json={"email": "anna@example.ru", "password": PASSWORD}).status_code == 401
    assert client.post(login, json={"email": "anna@example.ru", "password": "N3wPassw0rd"}).status_code == 200


def test_delete_me(db, make_user, make_client):
    u = make_user("anna@example.ru")
    c = make_client(u)
    uid = u.id

    r = c.request("DELETE", ME, json={"password": "WrongPass1"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_credentials"

    r = c.request("DELETE", ME, json={"password": PASSWORD})
    assert r.status_code == 204
    assert "Max-Age=0" in r.headers["set-cookie"]
    db.expire_all()
    assert db.get(User, uid) is None
    assert db.scalars(select(UserSession).where(UserSession.user_id == uid)).all() == []
    assert c.get(ME).status_code == 401


def test_delete_last_admin(admin_client):
    r = admin_client.request("DELETE", ME, json={"password": "AdminPass123"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "last_admin"


def test_stats_default_period(db, make_user, make_client):
    u = make_user()
    word = db.scalar(select(Word).limit(1))
    for correct in (True, False):
        db.add(AnswerEvent(client_event_id=uuid.uuid4(), user_id=u.id, word_id=word.id, direction="en_ru",
                           mode="deadline", is_correct=correct, xp_awarded=10 if correct else 0,
                           answered_at=utcnow()))
    db.commit()

    r = make_client(u).get(f"{ME}/stats")
    assert r.status_code == 200
    data = r.json()["data"]
    today = user_today(u)
    assert data["to"] == today.isoformat()
    assert data["from"] == (today - timedelta(days=6)).isoformat()
    assert len(data["days"]) == 7
    assert data["days"][-1] == {"date": today.isoformat(), "answers": 2, "correct": 1, "xp": 10}
    assert data["totals"] == {"answers": 2, "correct": 1, "xp": 10, "active_days": 1, "learned_words": 0}


def test_stats_validation(user_client):
    assert user_client.get(f"{ME}/stats?from=2026-10-20&to=2026-10-14").status_code == 422
    assert user_client.get(f"{ME}/stats?from=2025-01-01&to=2026-10-14").status_code == 422
    assert user_client.get(f"{ME}/stats?from=not-a-date").status_code == 422
    r = user_client.get(f"{ME}/stats?from=2026-10-14&to=2026-10-20")
    assert r.status_code == 200 and len(r.json()["data"]["days"]) == 7


def test_achievements(db, make_user, make_client):
    u = make_user(xp=1240)
    first = db.scalar(select(Achievement).where(Achievement.code == "first_round"))
    db.add(UserAchievement(user_id=u.id, achievement_id=first.id))
    db.commit()

    r = make_client(u).get(f"{ME}/achievements")
    assert r.status_code == 200
    data = r.json()["data"]
    assert [a["code"] for a in data["earned"]] == ["first_round"]
    assert data["earned"][0]["earned_at"].endswith("Z")
    director = next(a for a in data["available"] if a["code"] == "director")
    assert director["progress"] == {"current": 1240, "target": 5000}


def test_achievements_requires_session(client):
    assert client.get(f"{ME}/achievements").status_code == 401
