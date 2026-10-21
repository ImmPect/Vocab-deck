"""Модуль words: слова колод и личных списков."""
from datetime import date

from sqlalchemy import select

from app.decks.models import Deck
from app.learning.models import UserWordProgress
from app.words.models import Word
from app.seed_data import WORDS

API = "/api/v1"


def office(db) -> int:
    return db.scalar(select(Deck.id).where(Deck.title == "Офис"))


def new_list(c) -> int:
    return c.post(f"{API}/decks", json={"title": "Список"}).json()["data"]["id"]


def add_word(c, deck_id, en="budget", ru="бюджет", **extra):
    return c.post(f"{API}/decks/{deck_id}/words", json={"en": en, "ru": ru, **extra})


# ---------- GET /decks/{id}/words ----------

def test_guest_lists_published_words_sorted(db, client):
    deck_id = office(db)
    db.add(Word(deck_id=deck_id, en="aaa draft", ru="черновик", status="draft"))
    db.commit()
    r = client.get(f"{API}/decks/{deck_id}/words", params={"limit": 3})
    body = r.json()
    assert r.status_code == 200
    expected = sorted((w[0] for w in WORDS["Офис"]), key=str.lower)
    assert body["meta"] == {"page": 1, "limit": 3, "total_items": len(expected)}
    assert [w["en"] for w in body["data"]] == expected[:3]
    assert "progress" not in body["data"][0]
    page3 = client.get(f"{API}/decks/{deck_id}/words", params={"limit": 3, "page": 3}).json()["data"]
    assert [w["en"] for w in page3] == expected[6:9]


def test_user_sees_word_progress(db, make_user, make_client):
    user = make_user()
    word = db.scalar(select(Word).where(Word.en == "deadline"))
    db.add(UserWordProgress(user_id=user.id, word_id=word.id, direction="en_ru", box=3,
                            next_review_at=date(2026, 10, 24), learned=False))
    db.commit()
    data = make_client(user).get(f"{API}/decks/{word.deck_id}/words", params={"q": "dead"}).json()["data"]
    assert len(data) == 1
    assert data[0]["progress"] == {"en_ru": {"box": 3, "next_review_at": "2026-10-24", "learned": False},
                                   "ru_en": None}


def test_words_search_and_errors(db, client, user_client, make_user, make_client):
    deck_id = office(db)
    assert [w["en"] for w in client.get(f"{API}/decks/{deck_id}/words",
                                        params={"q": "отч"}).json()["data"]] == ["report"]
    r = client.get(f"{API}/decks/{deck_id}/words", params={"q": "a"})
    assert r.status_code == 422 and r.json()["error"]["details"][0]["field"] == "q"
    assert client.get(f"{API}/decks/{deck_id}/words", params={"limit": 101}).status_code == 422
    assert client.get(f"{API}/decks/99999/words").status_code == 404
    personal = new_list(user_client)
    add_word(user_client, personal)
    assert user_client.get(f"{API}/decks/{personal}/words").json()["meta"]["total_items"] == 1
    assert make_client(make_user()).get(f"{API}/decks/{personal}/words").status_code == 404
    assert client.get(f"{API}/decks/{personal}/words").status_code == 404


# ---------- POST /decks/{id}/words ----------

def test_create_word(user_client):
    deck_id = new_list(user_client)
    r = add_word(user_client, deck_id, en="  stakeholder ", ru="заинтересованная сторона",
                 example="Inform all stakeholders.")
    data = r.json()["data"]
    assert r.status_code == 201
    assert r.headers["Location"] == f"/api/v1/words/{data['id']}"
    assert data["en"] == "stakeholder" and data["status"] == "published" and data["ipa"] is None


def test_create_word_duplicate_case_insensitive(user_client):
    deck_id = new_list(user_client)
    first = add_word(user_client, deck_id, en="Deadline").json()["data"]
    r = add_word(user_client, deck_id, en="deadline")
    err = r.json()["error"]
    assert r.status_code == 409 and err["code"] == "word_duplicate"
    assert err["details"][0]["existing_word_id"] == first["id"]


def test_create_word_validation(user_client):
    deck_id = new_list(user_client)
    for en in ("дедлайн", "<b>x</b>", "", "a" * 101, "1st"):
        r = add_word(user_client, deck_id, en=en)
        assert r.status_code == 422, en
        assert r.json()["error"]["details"][0]["field"] == "en"
    r = add_word(user_client, deck_id, en="dead-line")
    assert r.status_code == 201
    assert add_word(user_client, deck_id, en="o'clock", ru="").status_code == 422
    assert add_word(user_client, deck_id, en="ok", ru="ок", unknown=1).status_code == 422
    msg = add_word(user_client, deck_id, en="дедлайн").json()["error"]["details"][0]["message"]
    assert msg == "Допустимы латинские буквы, пробел, дефис и апостроф"


def test_create_word_access(db, client, user_client, make_user, make_client):
    deck_id = new_list(user_client)
    assert add_word(client, deck_id).status_code == 401
    assert add_word(make_client(make_user()), deck_id).status_code == 404
    r = add_word(user_client, office(db))
    assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden"


def test_personal_list_limit(db, make_user, make_client):
    user = make_user(xp=0)
    c = make_client(user)
    deck_id = new_list(c)
    db.add_all(Word(deck_id=deck_id, en=f"word{chr(97 + i // 26)}{chr(97 + i % 26)}", ru="с")
               for i in range(100))
    db.commit()
    r = add_word(c, deck_id)
    assert r.status_code == 403 and r.json()["error"]["code"] == "limit_reached"
    user.xp = 3000
    db.commit()
    assert add_word(c, deck_id).status_code == 201


# ---------- PATCH / DELETE /words/{id} ----------

def test_update_and_delete_word(db, user_client, make_user, make_client):
    deck_id = new_list(user_client)
    word = add_word(user_client, deck_id).json()["data"]
    other = add_word(user_client, deck_id, en="invoice", ru="счёт").json()["data"]

    r = user_client.patch(f"{API}/words/{word['id']}", json={"ru": "бюджет, смета", "ipa": "/ˈbʌdʒɪt/"})
    assert r.status_code == 200
    assert r.json()["data"]["ru"] == "бюджет, смета" and r.json()["data"]["en"] == "budget"

    r = user_client.patch(f"{API}/words/{word['id']}", json={"en": "INVOICE"})
    assert r.status_code == 409 and r.json()["error"]["details"][0]["existing_word_id"] == other["id"]
    assert user_client.patch(f"{API}/words/{word['id']}", json={"en": None}).status_code == 422
    assert user_client.patch(f"{API}/words/{word['id']}", json={"en": "Budget"}).status_code == 200

    stranger = make_client(make_user())
    assert stranger.patch(f"{API}/words/{word['id']}", json={"ru": "x"}).status_code == 404
    assert stranger.delete(f"{API}/words/{word['id']}").status_code == 404

    shared_word = db.scalar(select(Word.id).where(Word.en == "deadline"))
    r = user_client.patch(f"{API}/words/{shared_word}", json={"ru": "x"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden"
    assert user_client.delete(f"{API}/words/{shared_word}").status_code == 403

    assert user_client.delete(f"{API}/words/{word['id']}").status_code == 204
    assert user_client.delete(f"{API}/words/{word['id']}").status_code == 404
    assert user_client.patch(f"{API}/words/99999", json={"ru": "x"}).status_code == 404
