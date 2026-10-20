"""Сервис модуля learning: входящие, раунды мини-игр, ответы, пакет ответов, перенос гостя.

Все ответы пользователя (в раунде, в пакете, при переносе гостевого журнала)
проходят через одну функцию record_answer, поэтому правила табл. 15 и 16
применяются одинаково. Сервис не знает об HTTP и бросает исключения из app.core.errors.
"""
import random
import uuid
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import settings
from app.core.db import utcnow
from app.core.errors import AppError, Conflict, Forbidden, NotFound, ValidationFailed
from app.core.security import sign_receipt, verify_receipt
from app.decks.models import Deck
from app.gamification import rules
from app.gamification import service as gservice
from app.learning import repository as repo
from app.learning import stats
from app.learning.models import AnswerEvent, Round, UserWordProgress
from app.learning.schemas import AnswerCreate, BatchAnswer, RoundCreate
from app.users.models import User
from app.words.models import Word

CLOCK_SKEW = timedelta(minutes=5)   # допустимое расхождение часов клиента (3.1.9)
BATCH_MAX_AGE = timedelta(days=30)  # ответы старше не принимаются (3.7.7)
MIN_DECK_WORDS = 4

_rng = random.SystemRandom()


# ---------- время ----------

def to_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def fmt_ts(dt: datetime) -> str:
    """Каноническая запись времени для квитанции и ответа: 2026-10-20T09:15:42Z."""
    return to_utc(dt).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clamp(answered_at: datetime, now: datetime) -> datetime:
    """Время клиента принимается, если отличается от серверного не более чем на 5 минут."""
    at = to_utc(answered_at)
    return at if abs(at - now) <= CLOCK_SKEW else now


def _day_bounds(user: User, day: date) -> tuple[datetime, datetime]:
    """Границы календарного дня пользователя в UTC."""
    tz = ZoneInfo(user.timezone)
    start = datetime.combine(day, time.min, tz)
    return start.astimezone(UTC), (start + timedelta(days=1)).astimezone(UTC)


# ---------- квитанции гостя ----------

def make_receipt(*, word_id: int, direction: str, mode: str, is_correct: bool, answered_at: datetime,
                 client_event_id: uuid.UUID | str, combo: int) -> str:
    return sign_receipt(word_id=word_id, direction=direction, mode=mode, is_correct=is_correct,
                        answered_at=fmt_ts(answered_at), client_event_id=str(client_event_id), combo=combo)


def check_receipt(receipt: str, *, word_id: int, direction: str, mode: str, is_correct: bool,
                  answered_at: datetime, client_event_id: uuid.UUID | str, combo: int) -> bool:
    return verify_receipt(receipt, word_id=word_id, direction=direction, mode=mode, is_correct=is_correct,
                          answered_at=fmt_ts(answered_at), client_event_id=str(client_event_id), combo=combo)


# ---------- единое применение правил к ответу ----------

def record_answer(db: Session, user: User, *, word_id: int, direction: str, mode: str, is_correct: bool,
                  combo: int, answered_at: datetime, client_event_id: uuid.UUID,
                  round_id: uuid.UUID | None = None, response_ms: int | None = None) -> dict:
    """Применяет табл. 15 и 16 к ответу пользователя и сохраняет результат в текущей транзакции.

    Обновляет user_word_progress, пишет answer_events, начисляет опыт и учитывает серию дней.
    «Сегодня» — день ответа по часовому поясу пользователя.
    """
    answered_at = to_utc(answered_at)
    day = gservice.user_today(user, answered_at)
    prog = repo.get_progress(db, user.id, word_id, direction)
    repeat = (is_correct and mode in rules.GAME_MODES
              and repo.has_correct_game_answer(db, user.id, word_id, *_day_bounds(user, day)))
    out = rules.apply_answer(
        mode=mode, is_correct=is_correct, combo=combo,
        box=prog.box if prog else None, learned=prog.learned if prog else False,
        due=prog is not None and prog.next_review_at <= day, repeat_same_day=repeat, today=day)

    if prog is None:
        prog = repo.add(db, UserWordProgress(user_id=user.id, word_id=word_id, direction=direction,
                                             box=out.new_box, next_review_at=out.next_review_at,
                                             learned=out.learned))
    else:
        if out.box_changed:
            prog.box, prog.next_review_at = out.new_box, out.next_review_at
        prog.learned = out.learned

    repo.add(db, AnswerEvent(client_event_id=client_event_id, user_id=user.id, word_id=word_id,
                             round_id=round_id, direction=direction, mode=mode, is_correct=is_correct,
                             response_ms=response_ms, xp_awarded=out.xp, answered_at=answered_at))
    gservice.award(user, out.xp)
    if mode in rules.CHECKED_MODES:
        gservice.register_activity(user, day)
    db.flush()
    return {
        "is_correct": is_correct,
        "xp_awarded": out.xp,
        "xp_breakdown": out.breakdown,
        "new_box": prog.box,
        "next_review_at": prog.next_review_at.isoformat(),
        "learned": prog.learned,
    }


def _provisional(*, mode: str, is_correct: bool, combo: int, current_box: int | None,
                 answered_at: datetime) -> dict:
    """Предварительный результат гостя: ящик из localStorage, без правила «тот же день»."""
    day = gservice.user_today(None, answered_at)
    out = rules.apply_answer(mode=mode, is_correct=is_correct, combo=combo, box=current_box, learned=False,
                             due=True, repeat_same_day=False, today=day)
    return {
        "is_correct": is_correct,
        "xp_awarded": out.xp,
        "xp_breakdown": out.breakdown,
        "new_box": out.new_box,
        "next_review_at": out.next_review_at.isoformat(),
        "learned": out.learned,
    }


# ---------- входящие ----------

def inbox(db: Session, user: User, direction: str | None, offset: int, limit: int) -> tuple[list[dict], int]:
    today = gservice.user_today(user)
    rows, total = repo.inbox_page(db, user.id, today, direction, offset, limit)
    items = [{
        "word_id": w.id, "en": w.en, "ipa": w.ipa, "ru": w.ru, "example": w.example,
        "deck": {"id": d.id, "title": d.title},
        "direction": p.direction, "box": p.box,
        "next_review_at": p.next_review_at.isoformat(),
        "overdue_days": (today - p.next_review_at).days,
    } for p, w, d in rows]
    return items, total


# ---------- начало раунда ----------

def _accessible_deck(db: Session, user: User | None, deck_id: int) -> Deck:
    """Колода существует и это общий отдел или собственный личный список (иначе 404)."""
    deck = repo.get_deck(db, deck_id)
    if deck is None or (deck.owner_id is not None and (user is None or deck.owner_id != user.id)):
        raise NotFound("Колода не найдена")
    return deck


def _check_unlock(db: Session, user: User, deck: Deck) -> None:
    rule = deck.unlock_rule or {}
    if "min_xp" in rule and user.xp < rule["min_xp"]:
        title = rules.level_for(rule["min_xp"])["title"]
        raise Forbidden(f"Отдел откроется на должности «{title}» ({rule['min_xp']} опыта)",
                        code="deck_locked")
    if "learned_in_deck" in rule:
        need = rule["learned_in_deck"]
        if stats.learned_in_deck(db, user.id, need["deck_id"]) < need["count"]:
            src = repo.get_deck(db, need["deck_id"])
            raise Forbidden(f"Отдел откроется, когда вы выучите {need['count']} слов в отделе "
                            f"«{src.title if src else need['deck_id']}»", code="deck_locked")


def _check_features(user: User, mode: str, direction: str) -> None:
    if mode == "dictation" and user.xp < rules.DICTATION_MIN_XP:
        raise Forbidden("Мини-игра «Звонок клиента» откроется на должности «Младший специалист» "
                        f"({rules.DICTATION_MIN_XP} опыта)", code="feature_locked")
    if direction == "ru_en" and user.xp < rules.RU_EN_MIN_XP:
        raise Forbidden("Режим RU→EN откроется на должности «Старший специалист» "
                        f"({rules.RU_EN_MIN_XP} опыта)", code="feature_locked")


def _pick_words(db: Session, user: User | None, words: list[Word], direction: str) -> list[Word]:
    """Сначала слова со сроком повтора, затем новые, затем остальные."""
    if user is None:
        return _rng.sample(words, min(settings.round_questions, len(words)))
    today = gservice.user_today(user)
    progress = repo.progress_for_words(db, user.id, [w.id for w in words], direction)
    due = sorted((w for w in words if w.id in progress and progress[w.id].next_review_at <= today),
                 key=lambda w: (progress[w.id].next_review_at, progress[w.id].box))
    new = [w for w in words if w.id not in progress]
    rest = [w for w in words if w.id in progress and progress[w.id].next_review_at > today]
    _rng.shuffle(new)
    _rng.shuffle(rest)
    return (due + new + rest)[:settings.round_questions]


def _build_question(n: int, word: Word, words: list[Word], mode: str, direction: str) -> dict:
    """Вопрос с правильным ответом (correct_index, answer) — хранится только в rounds.questions."""
    q = {"question_id": n, "word_id": word.id, "result": None}
    if mode == "dictation":
        q.update(speak_text=word.en, hint_ru=word.ru, correct_index=None, answer=word.en)
        return q
    ru_en = direction == "ru_en"
    correct = word.en if ru_en else word.ru
    pool = list({(w.en if ru_en else w.ru) for w in words if w.id != word.id} - {correct})
    options = _rng.sample(pool, min(3, len(pool))) + [correct]
    _rng.shuffle(options)
    q.update(prompt=word.ru if ru_en else word.en, ipa=None if ru_en else word.ipa,
             options=options, correct_index=options.index(correct), answer=correct)
    return q


def _public_question(q: dict) -> dict:
    return {k: v for k, v in q.items() if k not in ("correct_index", "answer", "result")}


def start_round(db: Session, user: User | None, data: RoundCreate) -> dict:
    deck = _accessible_deck(db, user, data.deck_id)
    direction = "en_ru" if data.mode == "dictation" else data.direction
    # Для гостя условия открытия проверяет клиент: сервер не знает его опыта (3.7.4)
    if user is not None:
        _check_unlock(db, user, deck)
        _check_features(user, data.mode, direction)
    words = repo.published_words(db, deck.id)
    if len(words) < MIN_DECK_WORDS:
        raise ValidationFailed("В колоде меньше 4 слов — добавьте слова, чтобы начать раунд",
                               code="not_enough_words")
    picked = _pick_words(db, user, words, direction)
    questions = [_build_question(i, w, words, data.mode, direction) for i, w in enumerate(picked, 1)]
    rnd = repo.add(db, Round(user_id=user.id if user else None, deck_id=deck.id, mode=data.mode,
                             direction=direction, questions=questions, current_combo=0, started_at=utcnow()))
    return {
        "round_id": str(rnd.id),
        "deck": {"id": deck.id, "title": deck.title},
        "mode": rnd.mode,
        "direction": rnd.direction,
        "time_limit_s": settings.round_time_limit_s,
        "started_at": fmt_ts(rnd.started_at),
        "questions": [_public_question(q) for q in questions],
    }


# ---------- ответ на вопрос раунда ----------

def _load_round(db: Session, user: User | None, round_id: uuid.UUID) -> Round:
    """Раунд пользователя доступен только его владельцу, раунд гостя — любому по round_id."""
    rnd = repo.get_round(db, round_id, lock=True)
    if rnd is None or (rnd.user_id is not None and (user is None or user.id != rnd.user_id)):
        raise NotFound("Раунд не найден")
    return rnd


def _is_correct(q: dict, mode: str, choice_index: int | None, text: str | None) -> bool:
    if mode == "deadline":
        if choice_index is None:
            raise ValidationFailed(details=[{"field": "choice_index", "message": "Укажите индекс варианта"}])
        if choice_index >= len(q["options"]):
            raise ValidationFailed(details=[{"field": "choice_index", "message": "Нет такого варианта"}])
        return choice_index == q["correct_index"]
    if text is None:
        raise ValidationFailed(details=[{"field": "text", "message": "Введите слово"}])

    def norm(s: str) -> str:
        return " ".join(s.split()).casefold()

    return norm(text) == norm(q["answer"])


def _with_total(response: dict, owner: User | None) -> dict:
    return {**response, "xp_total": owner.xp} if owner is not None else dict(response)


def _answer_question(db: Session, user: User | None, rnd: Round, *, question_id: int,
                     choice_index: int | None, text: str | None, client_event_id: uuid.UUID,
                     answered_at: datetime, response_ms: int | None, current_box: int | None,
                     from_batch: bool) -> tuple[str, dict]:
    """Проверяет ответ на вопрос раунда. Возвращает ("applied" | "duplicate", результат).

    Все проверки выполняются до изменений в БД, поэтому отклонённый ответ ничего не записывает.
    В пакете (from_batch) время раунда проверяется по answered_at, завершённость раунда — нет.
    """
    owner = user if rnd.user_id is not None else None
    idx = next((i for i, q in enumerate(rnd.questions) if q["question_id"] == question_id), None)
    if idx is None:
        raise ValidationFailed(details=[{"field": "question_id", "message": "В раунде нет такого вопроса"}])
    q = rnd.questions[idx]
    stored = q.get("result")
    if stored and stored["client_event_id"] == str(client_event_id):
        return "duplicate", _with_total(stored["response"], owner)

    now = utcnow()
    if not from_batch and rnd.finished_at is not None:
        raise Conflict("Раунд уже завершён", code="round_finished")
    limit = timedelta(seconds=settings.round_time_limit_s + settings.round_grace_s)
    moment = to_utc(answered_at) if from_batch else now
    if moment > rnd.started_at + limit:
        raise Conflict("Время раунда истекло", code="round_expired")
    if stored:
        raise Conflict("На этот вопрос уже дан ответ", code="question_already_answered")
    if owner is not None and repo.get_event(db, client_event_id) is not None:
        raise Conflict("Ответ с этим client_event_id уже принят", code="duplicate_event")
    is_correct = _is_correct(q, rnd.mode, choice_index, text)

    combo = rnd.current_combo + 1 if is_correct else 0
    at = to_utc(answered_at) if from_batch else _clamp(answered_at, now)
    if owner is not None:
        base = record_answer(db, owner, word_id=q["word_id"], direction=rnd.direction, mode=rnd.mode,
                             is_correct=is_correct, combo=combo, answered_at=at,
                             client_event_id=client_event_id, round_id=rnd.id, response_ms=response_ms)
    else:
        base = _provisional(mode=rnd.mode, is_correct=is_correct, combo=combo, current_box=current_box,
                            answered_at=at)
    response = {
        "question_id": question_id,
        "is_correct": is_correct,
        "correct_answer": {"index": q["correct_index"], "text": q["answer"]},
        "xp_awarded": base["xp_awarded"],
        "xp_breakdown": base["xp_breakdown"],
        "combo": combo,
        "new_box": base["new_box"],
        "next_review_at": base["next_review_at"],
        "learned": base["learned"],
    }
    if owner is None:
        response.update(xp_provisional=True, answered_at=fmt_ts(at),
                        receipt=make_receipt(word_id=q["word_id"], direction=rnd.direction, mode=rnd.mode,
                                             is_correct=is_correct, answered_at=at,
                                             client_event_id=client_event_id, combo=combo))

    # JSON-столбец: присваиваем новый список, чтобы изменение сохранилось и в PostgreSQL, и в SQLite
    questions = [dict(x) for x in rnd.questions]
    questions[idx]["result"] = {"client_event_id": str(client_event_id), "response": response}
    rnd.questions = questions
    flag_modified(rnd, "questions")
    rnd.current_combo = combo
    db.flush()
    return "applied", _with_total(response, owner)


def answer_round(db: Session, user: User | None, round_id: uuid.UUID, data: AnswerCreate) -> dict:
    rnd = _load_round(db, user, round_id)
    _, result = _answer_question(
        db, user, rnd, question_id=data.question_id, choice_index=data.choice_index, text=data.text,
        client_event_id=data.client_event_id, answered_at=data.answered_at, response_ms=data.response_ms,
        current_box=data.current_box, from_batch=False)
    return result


# ---------- итоги раунда ----------

def finish_round(db: Session, user: User | None, round_id: uuid.UUID) -> dict:
    """Идемпотентно: повторный вызов возвращает те же итоги (достижения — выданные при первом вызове)."""
    rnd = _load_round(db, user, round_id)
    owner = user if rnd.user_id is not None else None
    results = [q["result"]["response"] for q in rnd.questions if q.get("result")]
    xp_earned = sum(r["xp_awarded"] for r in results)
    first = rnd.finished_at is None
    if first:
        rnd.finished_at = utcnow()
        db.flush()
    summary = {
        "round_id": str(rnd.id),
        "answered": len(results),
        "correct": sum(1 for r in results if r["is_correct"]),
        "xp_earned": xp_earned,
    }
    if owner is None:
        return {**summary, "xp_total": None, "level_up": None, "level": None, "next_level": None,
                "streak_days": None, "streak_freezes": None, "achievements_earned": [],
                "xp_provisional": True, "suggest_registration": True}
    if first:
        earned = gservice.check_achievements(db, owner)
    else:
        earned = repo.achievements_earned_between(db, owner.id, rnd.finished_at,
                                                  rnd.finished_at + timedelta(seconds=5))
    xp_total = owner.xp
    return {**summary, "xp_total": xp_total,
            "level_up": rules.level_up(xp_total - xp_earned, xp_total),
            "level": rules.level_for(xp_total), "next_level": rules.next_level_for(xp_total),
            "streak_days": owner.streak_days, "streak_freezes": owner.streak_freezes,
            "achievements_earned": earned, "suggest_registration": False}


# ---------- пакет ответов ----------

class _Rejected(AppError):
    pass


def _reject(code: str, message: str) -> _Rejected:
    return _Rejected(message, code=code)


def _usable_word(db: Session, user: User | None, word_id: int) -> Word:
    """Опубликованное слово общего отдела или собственного личного списка."""
    word = repo.get_word(db, word_id)
    if word is None or word.status != "published" or (
            word.deck.owner_id is not None and (user is None or word.deck.owner_id != user.id)):
        raise _reject("word_not_found", "Слово не найдено или выведено из оборота")
    return word


def _batch_item(db: Session, user: User | None, item: BatchAnswer, now: datetime) -> tuple[str, dict]:
    at = to_utc(item.answered_at)
    if at > now + CLOCK_SKEW or at < now - BATCH_MAX_AGE:
        raise _reject("invalid_answered_at", "Неверное время ответа: не позже текущего и не раньше 30 дней назад")

    if item.mode in ("deadline", "dictation"):
        rnd = repo.get_round(db, item.round_id, lock=True)
        if rnd is None or (rnd.user_id is not None and (user is None or user.id != rnd.user_id)):
            raise _reject("round_not_found", "Раунд не найден или устарел")
        if rnd.user_id is not None:
            ev = repo.get_event(db, item.client_event_id)
            if ev is not None:  # ключ уже принят — ищем сохранённый результат в раунде
                stored = next((q["result"]["response"] for q in rnd.questions if q.get("result")
                               and q["result"]["client_event_id"] == str(item.client_event_id)), None)
                return "duplicate", dict(stored) if stored else _event_result(db, user, ev)
        return _answer_question(db, user, rnd, question_id=item.question_id, choice_index=item.choice_index,
                                text=item.text, client_event_id=item.client_event_id, answered_at=at,
                                response_ms=item.response_ms, current_box=item.current_box, from_batch=True)

    if user is not None:
        ev = repo.get_event(db, item.client_event_id)
        if ev is not None:
            return "duplicate", _event_result(db, user, ev)
    _usable_word(db, user, item.word_id)
    if user is None:
        res = _provisional(mode=item.mode, is_correct=item.is_correct, combo=0, current_box=item.current_box,
                           answered_at=at)
        res.update(xp_provisional=True, answered_at=fmt_ts(at),
                   receipt=make_receipt(word_id=item.word_id, direction=item.direction, mode=item.mode,
                                        is_correct=item.is_correct, answered_at=at,
                                        client_event_id=item.client_event_id, combo=0))
        return "applied", res
    res = record_answer(db, user, word_id=item.word_id, direction=item.direction, mode=item.mode,
                        is_correct=item.is_correct, combo=0, answered_at=at,
                        client_event_id=item.client_event_id, response_ms=item.response_ms)
    return "applied", res


def _event_result(db: Session, user: User, ev: AnswerEvent) -> dict:
    """Прежний результат по журналу: ящик — текущий по слову."""
    prog = repo.get_progress(db, user.id, ev.word_id, ev.direction)
    return {"is_correct": ev.is_correct, "xp_awarded": ev.xp_awarded,
            "new_box": prog.box if prog else None,
            "next_review_at": prog.next_review_at.isoformat() if prog else None}


def answer_batch(db: Session, user: User | None, items: list[BatchAnswer]) -> dict:
    """Каждый элемент обрабатывается независимо: отклонение одного не отменяет остальные."""
    now = utcnow()
    results, summary = [], {"applied": 0, "duplicate": 0, "rejected": 0}
    for item in items:
        cid = str(item.client_event_id)
        try:
            status, res = _batch_item(db, user, item, now)
        except AppError as exc:  # проверки выполняются до записи, поэтому откат не нужен
            results.append({"client_event_id": cid, "status": "rejected",
                            "reason_code": exc.code, "reason": exc.message})
            summary["rejected"] += 1
            continue
        res.pop("xp_total", None)
        results.append({"client_event_id": cid, "status": status, **res})
        summary[status] += 1
    data = {"results": results, "summary": summary}
    if user is not None:
        db.flush()
        data["achievements_earned"] = gservice.check_achievements(db, user) if summary["applied"] else []
        data["xp_total"] = user.xp
        data["inbox_count"] = stats.inbox_count(db, user.id, gservice.user_today(user))
    return data


# ---------- перенос гостевого прогресса ----------

def import_guest_events(db: Session, user: User, events: list) -> dict:
    """Проверяет квитанции и проигрывает события гостя через record_answer (UC-03).

    Ящик по слову и направлению после объединения — больший из ящика аккаунта
    и ящика, полученного из одного гостевого журнала.
    """
    accepted, rejected, seen = [], [], set()
    for ev in events:
        cid = str(ev.client_event_id)
        reason = None
        if not check_receipt(ev.receipt, word_id=ev.word_id, direction=ev.direction, mode=ev.mode,
                             is_correct=ev.is_correct, answered_at=ev.answered_at,
                             client_event_id=cid, combo=ev.combo):
            reason = "invalid_receipt"
        elif (word := repo.get_word(db, ev.word_id)) is None or word.deck.owner_id is not None:
            reason = "unknown_word"
        elif cid in seen or repo.get_event(db, ev.client_event_id) is not None:
            reason = "duplicate"
        if reason:
            rejected.append({"client_event_id": cid, "reason": reason})
            continue
        seen.add(cid)
        accepted.append(ev)

    accepted.sort(key=lambda e: to_utc(e.answered_at))
    xp_restored, words, guest_boxes = 0, set(), {}
    for ev in accepted:
        round_id = ev.round_id if ev.round_id and repo.round_exists(db, ev.round_id) else None
        res = record_answer(db, user, word_id=ev.word_id, direction=ev.direction, mode=ev.mode,
                            is_correct=ev.is_correct, combo=ev.combo, answered_at=ev.answered_at,
                            client_event_id=ev.client_event_id, round_id=round_id)
        xp_restored += res["xp_awarded"]
        words.add(ev.word_id)
        _simulate_guest_box(guest_boxes, user, ev)

    for (word_id, direction), (box, next_review_at, learned) in guest_boxes.items():
        prog = repo.get_progress(db, user.id, word_id, direction)
        if prog is not None and box > prog.box:
            prog.box, prog.next_review_at = box, next_review_at
            prog.learned = prog.learned or learned
    if accepted:
        db.flush()
        gservice.check_achievements(db, user)
    return {"accepted": len(accepted), "rejected": len(rejected), "rejected_events": rejected,
            "xp_restored": xp_restored, "words_transferred": len(words)}


def _simulate_guest_box(state: dict, user: User, ev) -> None:
    """Ящик слова по одному гостевому журналу (без учёта прогресса аккаунта)."""
    key = (ev.word_id, ev.direction)
    day = gservice.user_today(user, to_utc(ev.answered_at))
    box, next_review_at, learned = state.get(key, (None, None, False))
    out = rules.apply_answer(mode=ev.mode, is_correct=ev.is_correct, combo=ev.combo, box=box, learned=learned,
                             due=box is None or next_review_at <= day, repeat_same_day=False, today=day)
    if out.box_changed:
        box, next_review_at = out.new_box, out.next_review_at
    state[key] = (box, next_review_at, out.learned)
