"""Тесты переноса гостевого прогресса (UC-03, разделы 3.1.9 и 3.3.1 ПР3)."""
import uuid
from datetime import date, timedelta

from sqlalchemy import select

from app.core.db import utcnow
from app.decks.models import Deck
from app.learning.guest import GuestProgress, import_guest_progress
from app.learning.models import AnswerEvent, Round, UserWordProgress
from app.words.models import Word

API = "/api/v1"


def office_id(db) -> int:
    return db.scalar(select(Deck.id).where(Deck.title == "Офис", Deck.owner_id.is_(None)))


def play_guest_round(client, db, pattern=(True, True, True, False, True)) -> list[dict]:
    """Гость играет раунд; возвращает события журнала в формате guest_progress."""
    rid = client.post(f"{API}/rounds", json={"deck_id": office_id(db), "mode": "deadline"}).json()["data"]["round_id"]
    events = []
    for qid, ok in enumerate(pattern, 1):
        db.expire_all()
        q = db.get(Round, uuid.UUID(rid)).questions[qid - 1]
        cid = str(uuid.uuid4())
        d = client.post(f"{API}/rounds/{rid}/answers", json={
            "question_id": qid, "choice_index": q["correct_index"] if ok else (q["correct_index"] + 1) % 4,
            "client_event_id": cid, "answered_at": utcnow().isoformat()}).json()["data"]
        events.append({"client_event_id": cid, "word_id": q["word_id"], "direction": "en_ru", "mode": "deadline",
                       "is_correct": d["is_correct"], "answered_at": d["answered_at"], "combo": d["combo"],
                       "round_id": rid, "question_id": qid, "receipt": d["receipt"]})
    return events


def self_check_event(client, word_id: int, is_correct: bool) -> dict:
    cid = str(uuid.uuid4())
    d = client.post(f"{API}/answers/batch", json={"answers": [{
        "client_event_id": cid, "mode": "self_check", "word_id": word_id, "direction": "en_ru",
        "is_correct": is_correct, "answered_at": utcnow().isoformat()}]}).json()["data"]["results"][0]
    return {"client_event_id": cid, "word_id": word_id, "direction": "en_ru", "mode": "self_check",
            "is_correct": is_correct, "answered_at": d["answered_at"], "combo": 0, "receipt": d["receipt"]}


def run_import(db, user, events):
    result = import_guest_progress(db, user, GuestProgress(format_version=1, events=events))
    db.commit()
    return result


def test_import_scenario_with_tampered_event(client, db, make_user):
    events = play_guest_round(client, db)
    first_word = db.scalar(select(Word.id).where(Word.deck_id == office_id(db)).order_by(Word.id))
    events.insert(0, self_check_event(client, first_word, False))
    tampered = {**events[4], "is_correct": True}  # вопрос 4 был неверным — гость «исправил» результат
    events[4] = tampered
    events.append({**events[1]})  # дубликат client_event_id
    events.append({**events[2], "client_event_id": str(uuid.uuid4()), "word_id": 99999})

    user = make_user()
    res = run_import(db, user, events)
    assert res["accepted"] == 5
    assert res["rejected"] == 3
    reasons = {e["reason"] for e in res["rejected_events"]}
    assert reasons == {"invalid_receipt", "duplicate"}  # неизвестное слово с чужой подписью — invalid_receipt
    assert any(e["client_event_id"] == tampered["client_event_id"] and e["reason"] == "invalid_receipt"
               for e in res["rejected_events"])
    # 10 + 10 + 15 + (ошибка отброшена) + 10 = 45
    assert res["xp_restored"] == 45 and user.xp == 45
    assert user.streak_days == 1
    stored = db.scalars(select(AnswerEvent).where(AnswerEvent.user_id == user.id)).all()
    assert len(stored) == 5 and all(e.round_id is not None for e in stored if e.mode == "deadline")


def test_import_full_log_and_reimport(client, db, make_user):
    events = play_guest_round(client, db)
    user = make_user()
    res = run_import(db, user, events)
    assert (res["accepted"], res["rejected"], res["xp_restored"], res["words_transferred"]) == (5, 0, 45, 5)
    boxes = sorted(db.scalars(select(UserWordProgress.box).where(UserWordProgress.user_id == user.id)))
    assert boxes == [1, 2, 2, 2, 2]
    # Повторный перенос того же журнала (вход на другом устройстве) — всё дубликаты
    again = run_import(db, user, events)
    assert again["accepted"] == 0 and again["rejected"] == 5 and user.xp == 45


def test_unknown_word_rejected(client, db, make_user):
    ev = self_check_event(client, db.scalar(select(Word.id)), True)
    word = db.get(Word, ev["word_id"])
    db.delete(word)
    db.commit()
    res = run_import(db, make_user(), [ev])
    assert res["rejected_events"] == [{"client_event_id": ev["client_event_id"], "reason": "unknown_word"}]


def test_merge_keeps_larger_box_and_same_day_rule(client, db, make_user):
    events = play_guest_round(client, db, pattern=(True, True, True, True, True))
    w_high, w_low, w_today = events[0]["word_id"], events[1]["word_id"], events[2]["word_id"]
    user = make_user()
    future = date.today() + timedelta(days=10)
    db.add(UserWordProgress(user_id=user.id, word_id=w_high, direction="en_ru", box=4, next_review_at=future))
    db.add(UserWordProgress(user_id=user.id, word_id=w_low, direction="en_ru", box=1, next_review_at=future))
    db.add(UserWordProgress(user_id=user.id, word_id=w_today, direction="en_ru", box=2, next_review_at=future))
    # В аккаунте сегодня уже был верный ответ на третье слово
    db.add(AnswerEvent(client_event_id=uuid.uuid4(), user_id=user.id, word_id=w_today, direction="en_ru",
                       mode="deadline", is_correct=True, xp_awarded=10, answered_at=utcnow()))
    db.commit()

    res = run_import(db, user, events)
    db.expire_all()

    def box(w):
        return db.get(UserWordProgress, (user.id, w, "en_ru")).box

    assert box(w_high) == 4  # в аккаунте больше — остаётся
    assert box(w_low) == 2   # в гостевом журнале больше — берётся он
    # 10 + 10 + 0 (повтор в тот же день) + 15 + 15
    assert res["xp_restored"] == 50
