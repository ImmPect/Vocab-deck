"""Тесты модуля learning: раунды, ответы, итоги, входящие, пакет ответов (раздел 3.7 ПР3)."""
import uuid
from datetime import date, timedelta

from sqlalchemy import select

from app.core.db import utcnow
from app.decks.models import Deck
from app.learning.models import AnswerEvent, Round, UserWordProgress
from app.users.models import User
from app.words.models import Word

API = "/api/v1"


def deck_id(db, title: str) -> int:
    return db.scalar(select(Deck.id).where(Deck.title == title, Deck.owner_id.is_(None)))


def question(db, round_id: str, qid: int) -> dict:
    db.expire_all()
    return db.get(Round, uuid.UUID(round_id)).questions[qid - 1]


def start(c, deck: int, mode: str = "deadline", direction: str = "en_ru"):
    return c.post(f"{API}/rounds", json={"deck_id": deck, "mode": mode, "direction": direction})


def answer(c, db, round_id: str, qid: int, correct: bool = True, cid: str | None = None, **extra):
    q = question(db, round_id, qid)
    body = {"question_id": qid, "client_event_id": cid or str(uuid.uuid4()),
            "answered_at": utcnow().isoformat(), **extra}
    if q.get("options") is not None:
        body["choice_index"] = q["correct_index"] if correct else (q["correct_index"] + 1) % 4
    else:
        body["text"] = q["answer"] if correct else "wrong"
    return c.post(f"{API}/rounds/{round_id}/answers", json=body)


# ---------- сценарий 3.10, шаги 5–12: гость ----------

def test_guest_round_scenario(client, db):
    r = start(client, deck_id(db, "Офис"))
    assert r.status_code == 201
    data = r.json()["data"]
    rid = data["round_id"]
    assert r.headers["Location"] == f"/api/v1/rounds/{rid}"
    assert data["time_limit_s"] == 60 and len(data["questions"]) == 5
    q1 = data["questions"][0]
    assert len(q1["options"]) == 4 and "correct_index" not in q1 and "answer" not in q1
    assert db.get(Round, uuid.UUID(rid)).user_id is None

    xp = []
    for qid, ok in [(1, True), (2, True), (3, True)]:
        d = answer(client, db, rid, qid, ok).json()["data"]
        xp.append(d["xp_awarded"])
        assert d["xp_provisional"] is True and d["receipt"] and "xp_total" not in d
    assert xp == [10, 10, 15]
    assert d["combo"] == 3 and d["xp_breakdown"] == [{"rule": "correct_answer", "xp": 10},
                                                     {"rule": "combo", "xp": 5}]

    cid = str(uuid.uuid4())
    wrong = answer(client, db, rid, 4, False, cid=cid)
    assert wrong.status_code == 200
    w = wrong.json()["data"]
    assert (w["is_correct"], w["combo"], w["new_box"], w["xp_awarded"]) == (False, 0, 1, 0)
    assert w["correct_answer"]["text"] == question(db, rid, 4)["answer"]
    retry = answer(client, db, rid, 4, False, cid=cid)  # обрыв связи: тот же client_event_id
    assert retry.status_code == 200 and retry.json()["data"] == w

    d5 = answer(client, db, rid, 5, True).json()["data"]
    assert (d5["xp_awarded"], d5["combo"], d5["new_box"]) == (10, 1, 2)

    fin = client.post(f"{API}/rounds/{rid}/finish").json()["data"]
    assert (fin["answered"], fin["correct"], fin["xp_earned"]) == (5, 4, 45)
    assert fin["xp_provisional"] is True and fin["suggest_registration"] is True
    assert fin["level"] is None and fin["xp_total"] is None
    assert client.post(f"{API}/rounds/{rid}/finish").json()["data"] == fin
    assert db.scalar(select(AnswerEvent.id)) is None  # гость ничего не пишет в журнал


# ---------- раунд пользователя ----------

def test_user_round_updates_progress_xp_streak(client, db, make_user, make_client):
    user = make_user(xp=290)
    c = make_client(user)
    rid = start(c, deck_id(db, "Офис")).json()["data"]["round_id"]
    totals = []
    for qid in range(1, 6):
        d = answer(c, db, rid, qid).json()["data"]
        assert "receipt" not in d and "xp_provisional" not in d
        totals.append((d["xp_awarded"], d["xp_total"]))
    assert totals == [(10, 300), (10, 310), (15, 325), (15, 340), (15, 355)]

    fin = c.post(f"{API}/rounds/{rid}/finish").json()["data"]
    assert (fin["correct"], fin["xp_earned"], fin["xp_total"]) == (5, 65, 355)
    assert fin["level_up"]["to"]["code"] == "junior" and fin["level"]["code"] == "junior"
    assert fin["next_level"]["xp_left"] == 445
    assert fin["streak_days"] == 1 and fin["suggest_registration"] is False
    assert {"code": "first_round", "title": "Первый рабочий день"} in fin["achievements_earned"]
    assert c.post(f"{API}/rounds/{rid}/finish").json()["data"] == fin  # идемпотентно

    db.expire_all()
    u = db.get(User, user.id)
    assert (u.xp, u.streak_days) == (355, 1)
    boxes = db.scalars(select(UserWordProgress.box).where(UserWordProgress.user_id == user.id)).all()
    assert sorted(boxes) == [2] * 5
    assert len(db.scalars(select(AnswerEvent).where(AnswerEvent.round_id == uuid.UUID(rid))).all()) == 5


def test_user_retry_same_event_no_double_xp(client, db, user_client):
    rid = start(user_client, deck_id(db, "Офис")).json()["data"]["round_id"]
    cid = str(uuid.uuid4())
    a = answer(user_client, db, rid, 1, cid=cid).json()["data"]
    b = answer(user_client, db, rid, 1, cid=cid).json()["data"]
    assert a == b and b["xp_total"] == 10
    other = answer(user_client, db, rid, 1, cid=str(uuid.uuid4()))
    assert other.status_code == 409 and other.json()["error"]["code"] == "question_already_answered"


def test_repeat_same_day_zero_xp(client, db, user_client):
    deck = deck_id(db, "Собеседование")
    # В отделе оставляем 6 опубликованных слов: второй раунд обязательно повторит слова первого
    for w in db.scalars(select(Word).where(Word.deck_id == deck).order_by(Word.id)).all()[6:]:
        w.status = "archived"
    db.commit()
    rid = start(user_client, deck).json()["data"]["round_id"]
    first_words = {question(db, rid, q)["word_id"] for q in range(1, 6)}
    for q in range(1, 6):
        answer(user_client, db, rid, q)
    rid2 = start(user_client, deck).json()["data"]["round_id"]
    seen_repeat = False
    for q in range(1, 6):
        d = answer(user_client, db, rid2, q).json()["data"]
        if question(db, rid2, q)["word_id"] in first_words:
            assert d["xp_awarded"] == 0 and d["xp_breakdown"] == [{"rule": "repeat_same_day", "xp": 0}]
            assert d["new_box"] == 2  # срок повтора не наступил — ящик не меняется
            seen_repeat = True
        else:
            assert d["xp_awarded"] > 0
    assert seen_repeat


def test_round_prefers_due_words(client, db, make_user, make_client):
    user = make_user()
    words = db.scalars(select(Word).where(Word.deck_id == deck_id(db, "Офис")).order_by(Word.id)).all()
    for w in words[8:]:  # в отделе остаются 8 слов: 5 не созрели, 1 созрело, 2 новых
        w.status = "archived"
    today = date.today()
    for w in words[:5]:  # 5 слов не созрели
        db.add(UserWordProgress(user_id=user.id, word_id=w.id, direction="en_ru", box=3,
                                next_review_at=today + timedelta(days=5)))
    db.add(UserWordProgress(user_id=user.id, word_id=words[7].id, direction="en_ru", box=2,
                            next_review_at=today - timedelta(days=2)))
    db.commit()
    qs = start(make_client(user), deck_id(db, "Офис")).json()["data"]["questions"]
    ids = [q["word_id"] for q in qs]
    assert ids[0] == words[7].id  # созревшее — первым
    assert set(ids[1:3]) == {words[5].id, words[6].id}  # затем новые


def test_round_expired_and_finished(client, db, user_client):
    rid = start(user_client, deck_id(db, "Офис")).json()["data"]["round_id"]
    rnd = db.get(Round, uuid.UUID(rid))
    rnd.started_at = utcnow() - timedelta(seconds=120)
    db.commit()
    r = answer(user_client, db, rid, 1)
    assert r.status_code == 409 and r.json()["error"]["code"] == "round_expired"

    rid = start(user_client, deck_id(db, "Офис")).json()["data"]["round_id"]
    user_client.post(f"{API}/rounds/{rid}/finish")
    r = answer(user_client, db, rid, 1)
    assert r.status_code == 409 and r.json()["error"]["code"] == "round_finished"


def test_foreign_round_404(client, db, make_user, make_client):
    a, b = make_client(make_user()), make_client(make_user())
    rid = start(a, deck_id(db, "Офис")).json()["data"]["round_id"]
    assert answer(b, db, rid, 1).status_code == 404
    assert b.post(f"{API}/rounds/{rid}/finish").status_code == 404
    assert answer(client, db, rid, 1).status_code == 404  # гость
    assert client.post(f"{API}/rounds/{uuid.uuid4()}/finish").status_code == 404


def test_answer_validation(client, db):
    rid = start(client, deck_id(db, "Офис")).json()["data"]["round_id"]
    r = client.post(f"{API}/rounds/{rid}/answers", json={
        "question_id": 1, "client_event_id": str(uuid.uuid4()), "answered_at": utcnow().isoformat()})
    assert r.status_code == 422 and r.json()["error"]["details"][0]["field"] == "choice_index"
    r = client.post(f"{API}/rounds/{rid}/answers", json={
        "question_id": 1, "choice_index": 4, "client_event_id": "x", "answered_at": utcnow().isoformat()})
    assert r.status_code == 422
    assert client.post(f"{API}/rounds/not-a-uuid/finish").status_code == 422


# ---------- доступ к раунду ----------

def test_feature_locked(client, db, make_user, make_client):
    office = deck_id(db, "Офис")
    c = make_client(make_user(xp=0))
    r = start(c, office, mode="dictation")
    assert r.status_code == 403 and r.json()["error"]["code"] == "feature_locked"
    c2 = make_client(make_user(xp=300))
    r = start(c2, office, direction="ru_en")
    assert r.status_code == 403 and r.json()["error"]["code"] == "feature_locked"
    # Диктант открыт с 300 опыта
    r = start(c2, office, mode="dictation")
    assert r.status_code == 201
    d = r.json()["data"]
    q = d["questions"][0]
    assert d["direction"] == "en_ru" and "options" not in q and q["speak_text"] and q["hint_ru"]
    rid = d["round_id"]
    res = c2.post(f"{API}/rounds/{rid}/answers", json={
        "question_id": 1, "text": "  " + q["speak_text"].upper() + " ", "client_event_id": str(uuid.uuid4()),
        "answered_at": utcnow().isoformat()}).json()["data"]
    assert res["is_correct"] is True and res["correct_answer"]["text"] == q["speak_text"]


def test_ru_en_round_swaps_prompt(client, db, make_user, make_client):
    c = make_client(make_user(xp=1600))
    q = start(c, deck_id(db, "Офис"), direction="ru_en").json()["data"]["questions"][0]
    word = db.get(Word, q["word_id"])
    assert q["prompt"] == word.ru and word.en in q["options"]


def test_deck_locked(client, db, make_user, make_client):
    trip = deck_id(db, "Командировка")
    r = start(make_client(make_user(xp=0)), trip)
    assert r.status_code == 403 and r.json()["error"]["code"] == "deck_locked"
    assert "800" in r.json()["error"]["message"]
    assert start(make_client(make_user(xp=800)), trip).status_code == 201
    assert start(client, trip).status_code == 201  # гостю условия проверяет клиент

    office = deck_id(db, "Офис")
    locked = Deck(title="Секретный", unlock_rule={"learned_in_deck": {"deck_id": office, "count": 1}})
    db.add(locked)
    db.flush()
    for en, ru in [("aa", "аа"), ("bb", "бб"), ("cc", "вв"), ("dd", "гг")]:
        db.add(Word(deck_id=locked.id, en=en, ru=ru))
    db.commit()
    r = start(make_client(make_user()), locked.id)
    assert r.status_code == 403 and "Офис" in r.json()["error"]["message"]


def test_not_enough_words_and_personal_lists(client, db, make_user, make_client):
    owner = make_user()
    deck = Deck(title="Мой список", owner_id=owner.id)
    db.add(deck)
    db.flush()
    for en, ru in [("one", "один"), ("two", "два"), ("three", "три")]:
        db.add(Word(deck_id=deck.id, en=en, ru=ru))
    db.commit()
    r = start(make_client(owner), deck.id)
    assert r.status_code == 422 and r.json()["error"]["code"] == "not_enough_words"
    assert start(make_client(make_user()), deck.id).status_code == 404  # чужой список
    assert start(client, deck.id).status_code == 404
    assert start(client, 9999).status_code == 404
    assert client.post(f"{API}/rounds", json={"deck_id": 1, "mode": "chess"}).status_code == 422
    assert client.post(f"{API}/rounds", json={"deck_id": 1, "mode": "deadline", "x": 1}).status_code == 422


# ---------- входящие ----------

def test_inbox(client, db, make_user, make_client):
    user = make_user()
    words = db.scalars(select(Word).order_by(Word.id)).all()
    today = date.today()
    rows = [(words[0], "en_ru", 3, today), (words[1], "en_ru", 1, today - timedelta(days=4)),
            (words[2], "ru_en", 2, today - timedelta(days=1)), (words[3], "en_ru", 1, today),
            (words[4], "en_ru", 2, today + timedelta(days=2))]
    for w, d, box, nra in rows:
        db.add(UserWordProgress(user_id=user.id, word_id=w.id, direction=d, box=box, next_review_at=nra))
    words[3].status = "archived"
    db.commit()
    c = make_client(user)
    r = c.get(f"{API}/inbox")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"] == {"page": 1, "limit": 20, "total_items": 3}
    assert [i["word_id"] for i in body["data"]] == [words[1].id, words[2].id, words[0].id]
    first = body["data"][0]
    assert first["overdue_days"] == 4 and first["deck"]["title"] and first["en"] == words[1].en
    assert c.get(f"{API}/inbox?direction=ru_en").json()["meta"]["total_items"] == 1
    assert c.get(f"{API}/inbox?limit=1&page=2").json()["data"][0]["word_id"] == words[2].id
    assert c.get(f"{API}/inbox?direction=xx").status_code == 422
    assert client.get(f"{API}/inbox").status_code == 401


# ---------- пакет ответов ----------

def test_batch_user(client, db, make_user, make_client):
    user = make_user()
    office = deck_id(db, "Офис")
    words = db.scalars(select(Word).where(Word.deck_id == office).order_by(Word.id)).all()
    db.add(UserWordProgress(user_id=user.id, word_id=words[0].id, direction="en_ru", box=2,
                            next_review_at=date.today()))
    db.commit()
    c = make_client(user)
    rid = start(c, office).json()["data"]["round_id"]
    q1 = question(db, rid, 1)
    now = utcnow().isoformat()
    review_id = str(uuid.uuid4())
    payload = {"answers": [
        {"client_event_id": review_id, "mode": "review", "word_id": words[0].id, "direction": "en_ru",
         "is_correct": True, "answered_at": now},
        {"client_event_id": str(uuid.uuid4()), "mode": "self_check", "word_id": words[1].id,
         "direction": "en_ru", "is_correct": False, "answered_at": now},
        {"client_event_id": str(uuid.uuid4()), "mode": "deadline", "word_id": q1["word_id"],
         "direction": "en_ru", "round_id": rid, "question_id": 1, "choice_index": q1["correct_index"],
         "is_correct": False, "answered_at": now},
        {"client_event_id": str(uuid.uuid4()), "mode": "review", "word_id": 9999, "direction": "en_ru",
         "is_correct": True, "answered_at": now},
        {"client_event_id": str(uuid.uuid4()), "mode": "review", "word_id": words[2].id, "direction": "en_ru",
         "is_correct": True, "answered_at": (utcnow() - timedelta(days=40)).isoformat()},
        {"client_event_id": str(uuid.uuid4()), "mode": "deadline", "word_id": 1, "direction": "en_ru",
         "round_id": str(uuid.uuid4()), "question_id": 1, "choice_index": 0, "answered_at": now},
    ]}
    r = c.post(f"{API}/answers/batch", json=payload)
    assert r.status_code == 200
    d = r.json()["data"]
    res = d["results"]
    assert [x["status"] for x in res] == ["applied", "applied", "applied", "rejected", "rejected", "rejected"]
    assert (res[0]["xp_awarded"], res[0]["new_box"]) == (0, 3)
    assert (res[1]["new_box"], res[1]["next_review_at"]) == (1, (date.today() + timedelta(days=1)).isoformat())
    assert res[2]["is_correct"] is True and res[2]["xp_awarded"] == 10  # клиентский is_correct игнорируется
    assert [x.get("reason_code") for x in res[3:]] == ["word_not_found", "invalid_answered_at", "round_not_found"]
    assert d["summary"] == {"applied": 3, "duplicate": 0, "rejected": 3}
    assert d["xp_total"] == 10 and d["inbox_count"] == 0

    # Повтор пакета: принятые — duplicate, опыт не удваивается
    d2 = c.post(f"{API}/answers/batch", json={"answers": payload["answers"][:3]}).json()["data"]
    assert [x["status"] for x in d2["results"]] == ["duplicate"] * 3
    assert d2["results"][0]["new_box"] == 3 and d2["results"][2]["xp_awarded"] == 10
    assert d2["xp_total"] == 10
    db.expire_all()
    assert db.get(User, user.id).streak_days == 1  # review засчитывается в серию


def test_batch_round_expired_by_answered_at(client, db, user_client):
    rid = start(user_client, deck_id(db, "Офис")).json()["data"]["round_id"]
    q1 = question(db, rid, 1)
    late = (utcnow() + timedelta(seconds=90)).isoformat()
    d = user_client.post(f"{API}/answers/batch", json={"answers": [
        {"client_event_id": str(uuid.uuid4()), "mode": "deadline", "word_id": q1["word_id"],
         "direction": "en_ru", "round_id": rid, "question_id": 1, "choice_index": 0, "answered_at": late}]})
    assert d.json()["data"]["results"][0]["reason_code"] == "round_expired"


def test_batch_guest_and_validation(client, db):
    word = db.scalar(select(Word.id))
    item = {"client_event_id": str(uuid.uuid4()), "mode": "self_check", "word_id": word, "direction": "en_ru",
            "is_correct": False, "answered_at": utcnow().isoformat()}
    d = client.post(f"{API}/answers/batch", json={"answers": [item]}).json()["data"]
    assert d["results"][0]["status"] == "applied" and d["results"][0]["receipt"]
    assert d["results"][0]["new_box"] == 1 and "xp_total" not in d
    again = client.post(f"{API}/answers/batch", json={"answers": [item]}).json()["data"]
    assert again["results"][0]["receipt"] == d["results"][0]["receipt"]  # подпись детерминирована

    assert client.post(f"{API}/answers/batch", json={"answers": []}).status_code == 422
    assert client.post(f"{API}/answers/batch", json={"answers": [item] * 201}).status_code == 422
    bad = {**item, "is_correct": None}
    assert client.post(f"{API}/answers/batch", json={"answers": [bad]}).status_code == 422
    no_round = {**item, "mode": "deadline"}
    assert client.post(f"{API}/answers/batch", json={"answers": [no_round]}).status_code == 422
