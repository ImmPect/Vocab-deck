"""Модульные тесты чистых правил игры (app.gamification.rules): табл. 4, 15, 16 и п. 3.8 ТЗ."""
from datetime import date, timedelta

import pytest

from app.gamification import rules
from app.gamification.rules import StreakState, apply_answer, update_streak

TODAY = date(2026, 10, 20)


def answer(**kw):
    params = dict(mode="deadline", is_correct=True, combo=1, box=None, learned=False, due=True,
                  repeat_same_day=False, today=TODAY)
    params.update(kw)
    return apply_answer(**params)


# ---------- табл. 15: Лейтнер ----------

@pytest.mark.parametrize("box,days", [(1, 1), (2, 3), (3, 7), (4, 14), (5, 30)])
def test_intervals(box, days):
    assert rules.next_review_date(box, TODAY) == TODAY + timedelta(days=days)


def test_new_word_correct_goes_to_box_2():
    out = answer(box=None)
    assert (out.new_box, out.next_review_at, out.box_changed) == (2, TODAY + timedelta(days=3), True)


def test_due_word_moves_up_and_caps_at_5():
    assert answer(box=3).new_box == 4
    assert answer(box=5, learned=True).new_box == 5


def test_wrong_answer_goes_to_box_1_tomorrow():
    out = answer(box=4, is_correct=False, combo=0)
    assert (out.new_box, out.next_review_at, out.xp, out.breakdown) == (1, TODAY + timedelta(days=1), 0, [])


def test_not_due_word_keeps_box():
    out = answer(box=3, due=False)
    assert out.new_box == 3 and not out.box_changed and out.next_review_at is None
    assert out.xp == 10  # опыт начисляется, ящик — нет


# ---------- табл. 16: опыт ----------

def test_correct_answer_10_xp():
    out = answer()
    assert out.xp == 10 and out.breakdown == [{"rule": "correct_answer", "xp": 10}]


@pytest.mark.parametrize("combo,xp", [(1, 10), (2, 10), (3, 15), (7, 15)])
def test_combo_bonus_from_third(combo, xp):
    assert answer(combo=combo).xp == xp


def test_learned_bonus_in_box_5():
    out = answer(box=5, combo=1)
    assert out.learned and out.xp == 30
    assert {"rule": "learned", "xp": 20} in out.breakdown


def test_learned_bonus_only_once():
    assert answer(box=5, learned=True).xp == 10


def test_repeat_same_day_zero_xp():
    out = answer(combo=4, repeat_same_day=True)
    assert out.xp == 0 and out.breakdown == [{"rule": "repeat_same_day", "xp": 0}]


@pytest.mark.parametrize("mode", ["self_check", "review"])
def test_self_check_and_review_no_xp_but_box_changes(mode):
    out = answer(mode=mode, box=2)
    assert out.xp == 0 and out.new_box == 3
    out = answer(mode=mode, box=2, is_correct=False)
    assert out.new_box == 1


# ---------- п. 3.8: серия и заморозки ----------

def test_streak_first_day_and_same_day():
    s = update_streak(StreakState(0, 0, None), TODAY)
    assert (s.streak_days, s.last_active_date) == (1, TODAY)
    assert update_streak(s, TODAY) == s


def test_streak_next_day_grows():
    s = update_streak(StreakState(3, 0, TODAY - timedelta(days=1)), TODAY)
    assert s.streak_days == 4


def test_streak_gap_without_freezes_resets():
    s = update_streak(StreakState(5, 0, TODAY - timedelta(days=2)), TODAY)
    assert s.streak_days == 1


def test_streak_gap_covered_by_freeze():
    s = update_streak(StreakState(5, 1, TODAY - timedelta(days=2)), TODAY)
    assert (s.streak_days, s.streak_freezes) == (6, 0)


def test_freeze_every_7_days_max_2():
    s = update_streak(StreakState(6, 0, TODAY - timedelta(days=1)), TODAY)
    assert (s.streak_days, s.streak_freezes) == (7, 1)
    s = update_streak(StreakState(13, 2, TODAY - timedelta(days=1)), TODAY)
    assert (s.streak_days, s.streak_freezes) == (14, 2)


def test_late_answer_for_past_day_keeps_streak():
    state = StreakState(4, 0, TODAY)
    assert update_streak(state, TODAY - timedelta(days=1)) == state


def test_current_streak_broken_shows_zero():
    assert rules.current_streak(StreakState(5, 0, TODAY - timedelta(days=3)), TODAY) == 0
    assert rules.current_streak(StreakState(5, 2, TODAY - timedelta(days=3)), TODAY) == 5


# ---------- табл. 4: должности ----------

def test_levels():
    assert rules.level_for(0)["code"] == "intern"
    assert rules.level_for(300)["code"] == "junior"
    assert rules.next_level_for(290) == {"code": "junior", "title": "Младший специалист", "min_xp": 300,
                                         "xp_left": 10}
    assert rules.next_level_for(5000) is None


def test_level_up():
    up = rules.level_up(290, 335)
    assert up["from"]["code"] == "intern" and up["to"]["code"] == "junior"
    assert up["unlocked"] == ["Мини-игра «Звонок клиента» (диктант)"]
    assert rules.level_up(300, 340) is None


def test_features():
    assert rules.features_for(299) == {"dictation": False, "ru_en": False, "unlimited_lists": False}
    assert rules.features_for(1600) == {"dictation": True, "ru_en": True, "unlimited_lists": False}
