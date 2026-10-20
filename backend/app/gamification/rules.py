"""Правила игры из ТЗ (ЛР2) в виде чистых функций без БД и HTTP.

- табл. 4  — карьерная лестница (должности и пороги опыта);
- табл. 15 — система Лейтнера: 5 ящиков и интервалы повторения;
- табл. 16 — начисление опыта;
- п. 3.8   — серия дней и заморозки.

Все модули (learning, auth при переносе гостевого прогресса, users) применяют
правила только через этот файл, поэтому они одинаковы для любого сценария.
"""
from dataclasses import dataclass, field
from datetime import date, timedelta

# ---------- табл. 4: карьерная лестница ----------

LEVELS: list[dict] = [
    {"code": "intern", "title": "Стажёр", "min_xp": 0, "unlocks": ["Отделы «Офис» и «Переговоры»"]},
    {"code": "junior", "title": "Младший специалист", "min_xp": 300,
     "unlocks": ["Мини-игра «Звонок клиента» (диктант)"]},
    {"code": "specialist", "title": "Специалист", "min_xp": 800, "unlocks": ["Отдел «Командировка»"]},
    {"code": "senior", "title": "Старший специалист", "min_xp": 1600, "unlocks": ["Режим RU→EN во всех отделах"]},
    {"code": "head", "title": "Руководитель отдела", "min_xp": 3000,
     "unlocks": ["Личные списки без ограничения размера"]},
    {"code": "director", "title": "Директор", "min_xp": 5000, "unlocks": ["Итоговое достижение"]},
]

# Пороги открытия функций (табл. 4)
DICTATION_MIN_XP = 300
RU_EN_MIN_XP = 1600
UNLIMITED_LISTS_MIN_XP = 3000
PERSONAL_LIST_LIMIT = 100  # слов в личном списке до должности «Руководитель отдела»


def _short(level: dict) -> dict:
    return {"code": level["code"], "title": level["title"], "min_xp": level["min_xp"]}


def level_for(xp: int) -> dict:
    """Текущая должность по опыту: {"code", "title", "min_xp"}."""
    current = LEVELS[0]
    for lvl in LEVELS:
        if xp >= lvl["min_xp"]:
            current = lvl
    return _short(current)


def next_level_for(xp: int) -> dict | None:
    """Следующая должность и сколько опыта до неё; None для «Директора»."""
    for lvl in LEVELS:
        if lvl["min_xp"] > xp:
            return {**_short(lvl), "xp_left": lvl["min_xp"] - xp}
    return None


def level_up(xp_before: int, xp_after: int) -> dict | None:
    """Объект повышения для итогов раунда или None, если порог не пройден."""
    before, after = level_for(xp_before), level_for(xp_after)
    if before["code"] == after["code"]:
        return None
    unlocked = [u for lvl in LEVELS if xp_before < lvl["min_xp"] <= xp_after for u in lvl["unlocks"]]
    return {"from": before, "to": after, "unlocked": unlocked}


def features_for(xp: int) -> dict:
    """Функции, открытые по должности (поле features в GET /me)."""
    return {
        "dictation": xp >= DICTATION_MIN_XP,
        "ru_en": xp >= RU_EN_MIN_XP,
        "unlimited_lists": xp >= UNLIMITED_LISTS_MIN_XP,
    }


# ---------- табл. 15: система Лейтнера ----------

BOX_INTERVAL_DAYS = {1: 1, 2: 3, 3: 7, 4: 14, 5: 30}
MAX_BOX = 5


def next_review_date(box: int, today: date) -> date:
    return today + timedelta(days=BOX_INTERVAL_DAYS[box])


# ---------- табл. 16: опыт ----------

XP_CORRECT = 10
XP_COMBO = 5          # за каждый ответ серии, начиная с третьего подряд
COMBO_FROM = 3
XP_LEARNED = 20       # верный ответ на слово в ящике 5

GAME_MODES = {"deadline", "dictation"}           # дают опыт
CHECKED_MODES = {"deadline", "dictation", "review"}  # засчитываются в серию дней


@dataclass
class AnswerOutcome:
    """Результат применения правил к одному ответу."""

    xp: int = 0
    breakdown: list[dict] = field(default_factory=list)
    new_box: int = 1
    next_review_at: date | None = None
    learned: bool = False
    box_changed: bool = False


def apply_answer(*, mode: str, is_correct: bool, combo: int, box: int | None, learned: bool,
                 due: bool, repeat_same_day: bool, today: date) -> AnswerOutcome:
    """Применяет табл. 15 и 16 к одному ответу.

    mode            — deadline | dictation | review | self_check;
    combo           — число верных ответов подряд в раунде, включая этот ответ;
    box             — текущий ящик слова или None, если слово новое;
    learned         — слово уже выучено ранее;
    due             — срок повтора наступил (ящик меняется только у новых и «созревших» слов);
    repeat_same_day — на это слово сегодня уже был верный ответ (тогда опыт 0).
    """
    is_new = box is None
    current_box = box or 1
    out = AnswerOutcome(new_box=current_box, learned=learned)

    # Ящик Лейтнера
    if is_new or due:
        # Верный ответ — следующий ящик (новое слово попадает в ящик 2), ошибка — ящик 1
        out.new_box = min(current_box + 1, MAX_BOX) if is_correct else 1
        out.box_changed = True
        out.next_review_at = next_review_date(out.new_box, today)
    # Слово выучено: верный ответ, когда оно уже в ящике 5 и срок повтора наступил
    newly_learned = is_correct and not is_new and due and current_box == MAX_BOX and not learned
    if newly_learned:
        out.learned = True

    # Опыт — только в мини-играх
    if mode not in GAME_MODES or not is_correct:
        return out
    if repeat_same_day:
        out.breakdown = [{"rule": "repeat_same_day", "xp": 0}]
        return out
    out.breakdown.append({"rule": "correct_answer", "xp": XP_CORRECT})
    if combo >= COMBO_FROM:
        out.breakdown.append({"rule": "combo", "xp": XP_COMBO})
    if newly_learned:
        out.breakdown.append({"rule": "learned", "xp": XP_LEARNED})
    out.xp = sum(b["xp"] for b in out.breakdown)
    return out


# ---------- п. 3.8 ТЗ: серия дней и заморозки ----------

MAX_FREEZES = 2
FREEZE_EVERY_DAYS = 7


@dataclass
class StreakState:
    streak_days: int
    streak_freezes: int
    last_active_date: date | None


def update_streak(state: StreakState, today: date) -> StreakState:
    """Учитывает проверяемый ответ, данный в день today (по часовому поясу пользователя).

    Серия растёт, если в календарный день дан хотя бы один проверяемый ответ.
    Пропущенные дни покрываются заморозками; если их не хватает — серия начинается заново.
    За каждые 7 дней серии начисляется заморозка, в запасе не больше двух.
    """
    last = state.last_active_date
    streak, freezes = state.streak_days, state.streak_freezes
    if last == today:
        return state
    if last is None or last > today:
        streak = 1
    else:
        missed = (today - last).days - 1
        if missed == 0:
            streak += 1
        elif missed <= freezes:
            freezes -= missed
            streak += 1
        else:
            streak = 1
    if streak % FREEZE_EVERY_DAYS == 0:
        freezes = min(MAX_FREEZES, freezes + 1)
    return StreakState(streak, freezes, today)


def current_streak(state: StreakState, today: date) -> int:
    """Серия для показа: если пропуск уже не покрыть заморозками — 0."""
    if state.last_active_date is None:
        return 0
    missed = (today - state.last_active_date).days - 1
    return state.streak_days if missed <= state.streak_freezes else 0
