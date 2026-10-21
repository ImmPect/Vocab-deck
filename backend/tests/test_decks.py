"""Модуль decks: отделы, личные списки, условия открытия, импорт CSV."""
from datetime import date

from sqlalchemy import select

from app.decks.models import Deck
from app.learning.models import UserWordProgress
from app.words.models import Word
from app.seed_data import DECKS, WORDS

API = "/api/v1"


def shared_id(db, title: str) -> int:
    return db.scalar(select(Deck.id).where(Deck.title == title, Deck.owner_id.is_(None)))


def new_list(c, title="Мой список") -> int:
    r = c.post(f"{API}/decks", json={"title": title})
    assert r.status_code == 201, r.text
    return r.json()["data"]["id"]


def upload(c, deck_id, content: bytes | str, name="words.csv"):
    if isinstance(content, str):
        content = content.encode("utf-8")
    return c.post(f"{API}/decks/{deck_id}/import", files={"file": (name, content, "text/csv")})


# ---------- GET /decks ----------

def test_guest_sees_shared_decks_without_progress(client):
    r = client.get(f"{API}/decks")
    body = r.json()
    assert r.status_code == 200
    assert body["meta"]["total_items"] == len(DECKS)
    assert [d["title"] for d in body["data"]] == [t for t, _, _ in sorted(DECKS, key=lambda d: d[2])]
    office = body["data"][0]
    assert office["kind"] == "shared" and office["words_count"] == len(WORDS["Офис"]) and office["progress"] is None
    trip = body["data"][3]
    assert trip["locked"] is True and trip["unlock_rule"] == {"min_xp": 800}
    assert trip["unlock_condition"] == "Откроется на должности «Специалист» (800 опыта)"


def test_locked_deck_depends_on_user_xp(make_user, make_client):
    low = make_client(make_user(xp=100)).get(f"{API}/decks").json()["data"]
    high = make_client(make_user(xp=900)).get(f"{API}/decks").json()["data"]
    assert low[3]["locked"] is True
    assert high[3]["locked"] is False
    assert low[0]["progress"] == {"learned": 0, "in_progress": 0, "new": len(WORDS["Офис"])}


def test_learned_in_deck_rule_and_progress(db, make_user, make_client):
    office, talks = shared_id(db, "Офис"), shared_id(db, "Переговоры")
    db.get(Deck, talks).unlock_rule = {"learned_in_deck": {"deck_id": office, "count": 2}}
    user = make_user()
    words = db.scalars(select(Word.id).where(Word.deck_id == office).limit(3)).all()
    for i, wid in enumerate(words):
        db.add(UserWordProgress(user_id=user.id, word_id=wid, direction="en_ru", box=5,
                                next_review_at=date(2030, 1, 1), learned=i < 1))
    db.commit()
    c = make_client(user)
    data = {d["title"]: d for d in c.get(f"{API}/decks").json()["data"]}
    assert data["Офис"]["progress"] == {"learned": 1, "in_progress": 2, "new": len(WORDS["Офис"]) - 3}
    assert data["Переговоры"]["locked"] is True
    assert data["Переговоры"]["unlock_condition"] == "Откроется, когда вы выучите 2 слова в отделе «Офис»"

    db.get(UserWordProgress, (user.id, words[1], "en_ru")).learned = True
    db.commit()
    data = {d["title"]: d for d in c.get(f"{API}/decks").json()["data"]}
    assert data["Переговоры"]["locked"] is False


def test_kind_filter_and_personal_lists(user_client):
    new_list(user_client, "Слова из отчёта")
    all_decks = user_client.get(f"{API}/decks").json()
    assert all_decks["meta"]["total_items"] == len(DECKS) + 1
    assert all_decks["data"][-1]["kind"] == "personal"
    personal = user_client.get(f"{API}/decks", params={"kind": "personal"}).json()["data"]
    assert [d["title"] for d in personal] == ["Слова из отчёта"]
    assert len(user_client.get(f"{API}/decks", params={"kind": "shared"}).json()["data"]) == len(DECKS)
    r = user_client.get(f"{API}/decks", params={"kind": "other"})
    assert r.status_code == 422 and r.json()["error"]["details"][0]["field"] == "kind"


def test_get_deck_and_foreign_list(db, client, user_client, make_user, make_client):
    office = shared_id(db, "Офис")
    r = client.get(f"{API}/decks/{office}")
    assert r.status_code == 200 and r.json()["data"]["can_edit"] is False
    deck_id = new_list(user_client)
    assert user_client.get(f"{API}/decks/{deck_id}").json()["data"]["can_edit"] is True
    other = make_client(make_user())
    assert other.get(f"{API}/decks/{deck_id}").status_code == 404
    assert client.get(f"{API}/decks/{deck_id}").status_code == 404
    assert client.get(f"{API}/decks/99999").json()["error"]["code"] == "not_found"


# ---------- POST / PATCH / DELETE /decks ----------

def test_create_list(client, user_client):
    r = user_client.post(f"{API}/decks", json={"title": "  Слова из отчёта Q3 "})
    data = r.json()["data"]
    assert r.status_code == 201
    assert r.headers["Location"] == f"/api/v1/decks/{data['id']}"
    assert data["title"] == "Слова из отчёта Q3" and data["kind"] == "personal" and data["words_count"] == 0
    assert client.post(f"{API}/decks", json={"title": "x"}).status_code == 401
    r = user_client.post(f"{API}/decks", json={"title": "   "})
    assert r.status_code == 422 and r.json()["error"]["details"][0]["message"] == "Введите название"
    assert user_client.post(f"{API}/decks", json={"title": "x", "extra": 1}).status_code == 422


def test_rename_and_delete_list(db, user_client, make_user, make_client):
    deck_id = new_list(user_client)
    r = user_client.patch(f"{API}/decks/{deck_id}", json={"title": "Новое"})
    assert r.status_code == 200 and r.json()["data"]["title"] == "Новое"
    user_client.post(f"{API}/decks/{deck_id}/words", json={"en": "budget", "ru": "бюджет"})

    other = make_client(make_user())
    assert other.patch(f"{API}/decks/{deck_id}", json={"title": "x"}).status_code == 404
    assert other.delete(f"{API}/decks/{deck_id}").status_code == 404

    office = shared_id(db, "Офис")
    r = user_client.patch(f"{API}/decks/{office}", json={"title": "x"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden"
    assert user_client.delete(f"{API}/decks/{office}").status_code == 403

    r = user_client.delete(f"{API}/decks/{deck_id}")
    assert r.status_code == 204 and r.content == b""
    assert user_client.get(f"{API}/decks/{deck_id}").status_code == 404
    db.expire_all()
    assert db.scalar(select(Word.id).where(Word.deck_id == deck_id)) is None


# ---------- POST /decks/{id}/import ----------

SAMPLE = (
    "en,ru,example\n"
    'deadline,"срок, крайний срок",We must meet the deadline by Friday.\n'
    "stakeholder,заинтересованная сторона,Inform all stakeholders about the delay.\n"
    "negotiate,вести переговоры,\n"
    "<b>invoice</b>,счёт-фактура,\n"
    ",отчёт,The report is ready.\n"
    "Deadline,срок,\n"
)


def test_import_report(user_client):
    deck_id = new_list(user_client)
    user_client.post(f"{API}/decks/{deck_id}/words", json={"en": "deadline", "ru": "срок"})
    r = upload(user_client, deck_id, "﻿" + SAMPLE)
    assert r.status_code == 200, r.text
    report = r.json()["data"]
    assert report["total_rows"] == 6 and report["added"] == 2
    assert [(s["line"], s["reason_code"]) for s in report["skipped"]] == [
        (2, "duplicate"), (5, "invalid_en"), (6, "missing_field"), (7, "duplicate")]
    assert report["skipped"][1]["reason"] == "Допустимы латинские буквы, пробел, дефис и апостроф"
    assert report["skipped"][2]["reason"] == "Не заполнен столбец en"
    words = user_client.get(f"{API}/decks/{deck_id}/words").json()
    assert sorted(w["en"] for w in words["data"]) == ["deadline", "negotiate", "stakeholder"]


def test_import_duplicates_inside_file_and_column_order(user_client):
    deck_id = new_list(user_client)
    r = upload(user_client, deck_id, "ru,example\nсрок,x\n")
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_file"
    r = upload(user_client, deck_id, "ipa,ru,EN\n/bʌdʒɪt/,бюджет,Budget\n,бюджет,budget\n")
    report = r.json()["data"]
    assert report["added"] == 1 and report["skipped"][0]["reason_code"] == "duplicate"


def test_import_errors(db, client, user_client, make_user, make_client):
    deck_id = new_list(user_client)
    assert upload(client, deck_id, SAMPLE).status_code == 401
    assert upload(make_client(make_user()), deck_id, SAMPLE).status_code == 404
    r = upload(user_client, shared_id(db, "Офис"), SAMPLE)
    assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden"
    r = upload(user_client, deck_id, "en,ru\nдедлайн,срок\n".encode("cp1251"))
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_file"
    assert upload(user_client, deck_id, b"").status_code == 400
    big = "en,ru\n" + "word,слово\n" * 100_000
    r = upload(user_client, deck_id, big)
    assert r.status_code == 413 and r.json()["error"]["code"] == "file_too_large"
    many = "en,ru\n" + "".join(f"w{chr(97 + i % 26)}{chr(97 + i // 26 % 26)}{chr(97 + i // 676)},с\n"
                               for i in range(5001))
    r = upload(user_client, deck_id, many)
    assert r.status_code == 413
    # Ни одна строка не добавлена: импорт выполняется одной транзакцией
    assert user_client.get(f"{API}/decks/{deck_id}").json()["data"]["words_count"] == 0


def test_import_personal_list_limit(make_user, make_client):
    c = make_client(make_user(xp=100))
    deck_id = new_list(c)
    rows = "".join(f"word{chr(97 + i // 26)}{chr(97 + i % 26)},слово\n" for i in range(105))
    report = upload(c, deck_id, "en,ru\n" + rows).json()["data"]
    assert report["added"] == 100
    assert len(report["skipped"]) == 5 and report["skipped"][0]["reason_code"] == "limit_reached"
    r = upload(c, deck_id, "en,ru\nextra,ещё\n")
    assert r.status_code == 403 and r.json()["error"]["code"] == "limit_reached"

    head = make_client(make_user(xp=3000))
    deck_id = new_list(head)
    assert upload(head, deck_id, "en,ru\n" + rows).json()["data"]["added"] == 105
