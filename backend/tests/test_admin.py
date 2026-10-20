"""Модуль admin: слова и отделы общей колоды, поиск пользователей."""
from datetime import date

import pytest
from sqlalchemy import select

from app.decks.models import Deck
from app.learning.models import UserWordProgress
from app.words.models import Word

API = "/api/v1/admin"


def deck_id(db, title="Переговоры") -> int:
    return db.scalar(select(Deck.id).where(Deck.title == title))


def word_id(db, en="deadline") -> int:
    return db.scalar(select(Word.id).where(Word.en == en))


@pytest.mark.parametrize("method,path", [
    ("get", "/words"), ("post", "/words"), ("patch", "/words/1"),
    ("post", "/decks"), ("patch", "/decks/1"), ("get", "/users?email=adm"),
])
def test_admin_requires_role(client, user_client, method, path):
    assert getattr(client, method)(API + path).status_code == 401
    r = getattr(user_client, method)(API + path)
    assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden"


# ---------- GET /admin/words ----------

def test_search_words(db, admin_client, make_user):
    user = make_user()
    db.add(UserWordProgress(user_id=user.id, word_id=word_id(db, "negotiate"), direction="en_ru", box=2,
                            next_review_at=date(2030, 1, 1)))
    db.commit()
    r = admin_client.get(f"{API}/words", params={"q": "NEGO", "deck_id": deck_id(db)})
    body = r.json()
    assert r.status_code == 200 and body["meta"]["total_items"] == 1
    w = body["data"][0]
    assert w["deck"] == {"id": deck_id(db), "title": "Переговоры"}
    assert w["learners_count"] == 1 and w["status"] == "published"
    assert w["created_by"]["name"] == "Администратор" and w["created_at"].endswith("Z")
    assert admin_client.get(f"{API}/words").json()["meta"]["total_items"] == 26


def test_search_words_excludes_personal_and_validates(admin_client, user_client):
    personal = user_client.post("/api/v1/decks", json={"title": "Мой"}).json()["data"]["id"]
    user_client.post(f"/api/v1/decks/{personal}/words", json={"en": "deadline", "ru": "срок"})
    assert admin_client.get(f"{API}/words", params={"q": "deadline"}).json()["meta"]["total_items"] == 1
    assert admin_client.get(f"{API}/words", params={"q": "d"}).status_code == 422
    assert admin_client.get(f"{API}/words", params={"status": "deleted"}).status_code == 422
    assert admin_client.get(f"{API}/words", params={"status": "draft"}).json()["data"] == []


# ---------- POST /admin/words ----------

def test_create_word_draft_and_duplicate(db, admin_client, client):
    body = {"deck_id": deck_id(db), "en": "counteroffer", "ru": "встречное предложение",
            "ipa": "/ˈkaʊntərˌɒfə/"}
    r = admin_client.post(f"{API}/words", json=body)
    data = r.json()["data"]
    assert r.status_code == 201 and data["status"] == "draft" and data["updated_by"]["name"] == "Администратор"
    # Черновик не виден пользователям
    words = client.get(f"/api/v1/decks/{deck_id(db)}/words", params={"q": "counter"}).json()["data"]
    assert words == []

    r = admin_client.post(f"{API}/words", json={**body, "en": "COUNTEROFFER"})
    err = r.json()["error"]
    assert r.status_code == 409 and err["code"] == "word_duplicate"
    assert err["details"][0]["existing_word_id"] == data["id"]
    assert err["message"] == "Слово «COUNTEROFFER» уже есть в отделе «Переговоры»"


def test_create_word_errors(db, admin_client, make_user):
    base = {"deck_id": deck_id(db), "en": "bid", "ru": "заявка"}
    assert admin_client.post(f"{API}/words", json={**base, "deck_id": 99999}).status_code == 404
    assert admin_client.post(f"{API}/words", json={**base, "en": "ставка"}).status_code == 422
    assert admin_client.post(f"{API}/words", json={**base, "status": "archived"}).status_code == 422
    assert admin_client.post(f"{API}/words", json={"en": "bid", "ru": "x"}).status_code == 422
    owner = make_user()
    personal = Deck(owner_id=owner.id, title="Личный")
    db.add(personal)
    db.commit()
    r = admin_client.post(f"{API}/words", json={**base, "deck_id": personal.id})
    assert r.status_code == 422 and r.json()["error"]["details"][0]["field"] == "deck_id"
    r = admin_client.post(f"{API}/words", json={**base, "status": "published"})
    assert r.status_code == 201 and r.json()["data"]["status"] == "published"


# ---------- PATCH /admin/words/{id} ----------

def test_update_word_status_transitions(db, admin_client, client):
    wid = admin_client.post(f"{API}/words", json={"deck_id": deck_id(db), "en": "bid", "ru": "заявка"}
                            ).json()["data"]["id"]
    r = admin_client.patch(f"{API}/words/{wid}", json={"status": "published"})
    assert r.status_code == 200 and r.json()["data"]["status"] == "published"
    r = admin_client.patch(f"{API}/words/{wid}", json={"status": "draft"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "invalid_status_transition"
    assert admin_client.patch(f"{API}/words/{wid}", json={"status": "archived"}).status_code == 200
    words = client.get(f"/api/v1/decks/{deck_id(db)}/words", params={"q": "bid"}).json()["data"]
    assert words == []
    assert admin_client.patch(f"{API}/words/{wid}", json={"status": "published"}).status_code == 200


def test_update_word_fields_and_conflicts(db, admin_client, user_client):
    wid = word_id(db, "deadline")
    r = admin_client.patch(f"{API}/words/{wid}", json={"example": "Please send it before the deadline."})
    data = r.json()["data"]
    assert r.status_code == 200 and data["example"] == "Please send it before the deadline."
    assert data["updated_at"] >= data["created_at"]
    r = admin_client.patch(f"{API}/words/{wid}", json={"en": "Report"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "word_duplicate"
    # Перенос в другой отдел
    r = admin_client.patch(f"{API}/words/{wid}", json={"deck_id": deck_id(db, "Собеседование")})
    assert r.status_code == 200 and r.json()["data"]["deck"]["title"] == "Собеседование"
    assert admin_client.patch(f"{API}/words/{wid}", json={"en": "dead line!"}).status_code == 422
    assert admin_client.patch(f"{API}/words/99999", json={"ru": "x"}).status_code == 404
    personal = user_client.post("/api/v1/decks", json={"title": "Мой"}).json()["data"]["id"]
    pw = user_client.post(f"/api/v1/decks/{personal}/words", json={"en": "x", "ru": "y"}).json()["data"]["id"]
    assert admin_client.patch(f"{API}/words/{pw}", json={"ru": "z"}).status_code == 404


# ---------- POST / PATCH /admin/decks ----------

def test_create_deck(db, admin_client, client):
    office = deck_id(db, "Офис")
    body = {"title": "Конференция", "sort_order": 5,
            "unlock_rule": {"learned_in_deck": {"deck_id": office, "count": 20}}}
    r = admin_client.post(f"{API}/decks", json=body)
    data = r.json()["data"]
    assert r.status_code == 201 and data["kind"] == "shared"
    assert data["unlock_condition"] == "Откроется, когда вы выучите 20 слов в отделе «Офис»"
    assert data["locked"] is True
    assert client.get("/api/v1/decks").json()["meta"]["total_items"] == 5
    r = admin_client.post(f"{API}/decks", json={"title": "Конференция"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "deck_title_taken"


@pytest.mark.parametrize("rule", [
    {"max_xp": 10}, {"min_xp": -1}, {"min_xp": "800"}, {"min_xp": True},
    {"learned_in_deck": {"deck_id": 1}}, {"learned_in_deck": {"deck_id": 1, "count": 5, "x": 1}},
    {"min_xp": 1, "learned_in_deck": {"deck_id": 1, "count": 1}}, [],
])
def test_unlock_rule_validation(admin_client, rule):
    r = admin_client.post(f"{API}/decks", json={"title": "Новый", "unlock_rule": rule})
    assert r.status_code == 422
    assert r.json()["error"]["details"][0]["field"] == "unlock_rule"


def test_update_deck(db, admin_client, user_client):
    trip = deck_id(db, "Командировка")
    r = admin_client.patch(f"{API}/decks/{trip}", json={"unlock_rule": {"min_xp": 300}})
    assert r.status_code == 200
    assert r.json()["data"]["unlock_condition"] == "Откроется на должности «Младший специалист» (300 опыта)"
    r = admin_client.patch(f"{API}/decks/{trip}", json={"unlock_rule": None, "title": "Поездка"})
    assert r.json()["data"]["locked"] is False and r.json()["data"]["title"] == "Поездка"
    assert admin_client.patch(f"{API}/decks/{trip}", json={"title": "Офис"}).status_code == 409
    r = admin_client.patch(f"{API}/decks/{trip}",
                           json={"unlock_rule": {"learned_in_deck": {"deck_id": 99999, "count": 1}}})
    assert r.status_code == 404
    assert admin_client.patch(f"{API}/decks/99999", json={"title": "x"}).status_code == 404
    personal = user_client.post("/api/v1/decks", json={"title": "Мой"}).json()["data"]["id"]
    assert admin_client.patch(f"{API}/decks/{personal}", json={"title": "x"}).status_code == 404
    assert admin_client.patch(f"{API}/decks/{trip}", json={"sort_order": 40000}).status_code == 422


# ---------- GET /admin/users ----------

def test_search_users(admin_client, make_user):
    make_user("anna@example.ru", name="Анна", xp=1240)
    make_user("boris@example.ru")
    r = admin_client.get(f"{API}/users", params={"email": "ANNA@"})
    body = r.json()
    assert r.status_code == 200 and body["meta"]["total_items"] == 1
    u = body["data"][0]
    assert u["name"] == "Анна" and u["level"] == {"code": "specialist", "title": "Специалист"}
    assert "password_hash" not in u and "failed_logins" not in u
    assert admin_client.get(f"{API}/users", params={"email": "example.ru"}).json()["meta"]["total_items"] == 2
    assert admin_client.get(f"{API}/users", params={"email": "an"}).status_code == 422
    r = admin_client.get(f"{API}/users")
    assert r.status_code == 422 and r.json()["error"]["details"][0]["field"] == "email"
