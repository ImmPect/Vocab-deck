"""Начальные данные: отделы общей колоды, слова, достижения, администратор.

Запуск:  python -m app.seed
Повторный запуск безопасен: существующие записи не дублируются.
"""
import os

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.core.db import SessionLocal, utcnow
from app.core.security import hash_password
from app.decks.models import Deck
from app.gamification.models import Achievement
from app.users.models import User
from app.words.models import Word

# (название отдела, условие открытия, порядок) — табл. 4 ТЗ
DECKS = [
    ("Офис", None, 1),
    ("Переговоры", None, 2),
    ("Собеседование", None, 3),
    ("Командировка", {"min_xp": 800}, 4),
]

# en, ipa, ru, example — деловая лексика A2–B1 (слова из прототипа ЛР2 + дополнение)
WORDS = {
    "Офис": [
        ("deadline", "/ˈdedlaɪn/", "крайний срок", "We need to meet the deadline on Friday."),
        ("colleague", "/ˈkɒliːɡ/", "коллега", "My colleague helped me with the report."),
        ("schedule", "/ˈʃedjuːl/", "расписание", "Can you check my schedule for tomorrow?"),
        ("meeting", "/ˈmiːtɪŋ/", "совещание", "The meeting starts at ten."),
        ("report", "/rɪˈpɔːt/", "отчёт", "Please send me the report by noon."),
        ("invoice", "/ˈɪnvɔɪs/", "счёт-фактура", "The invoice was paid yesterday."),
        ("agenda", "/əˈdʒendə/", "повестка дня", "What is on the agenda today?"),
        ("department", "/dɪˈpɑːtmənt/", "отдел", "She works in the sales department."),
    ],
    "Переговоры": [
        ("negotiate", "/nɪˈɡəʊʃieɪt/", "вести переговоры", "We need to negotiate a better price."),
        ("contract", "/ˈkɒntrækt/", "контракт", "They signed the contract yesterday."),
        ("offer", "/ˈɒfə/", "предложение", "We accepted their offer."),
        ("discount", "/ˈdɪskaʊnt/", "скидка", "Can you give us a discount?"),
        ("agreement", "/əˈɡriːmənt/", "соглашение", "We reached an agreement after two hours."),
        ("stakeholder", "/ˈsteɪkhəʊldə/", "заинтересованная сторона", "All stakeholders agreed with the plan."),
        ("compromise", "/ˈkɒmprəmaɪz/", "компромисс", "Both sides made a compromise."),
    ],
    "Собеседование": [
        ("interview", "/ˈɪntəvjuː/", "собеседование", "The interview went really well."),
        ("salary", "/ˈsæləri/", "зарплата", "The salary is paid monthly."),
        ("experience", "/ɪkˈspɪəriəns/", "опыт", "She has five years of experience."),
        ("skill", "/skɪl/", "навык", "Communication is an important skill."),
        ("resume", "/ˈrezjuːmeɪ/", "резюме", "Please attach your resume."),
        ("candidate", "/ˈkændɪdət/", "кандидат", "We interviewed three candidates."),
    ],
    "Командировка": [
        ("luggage", "/ˈlʌɡɪdʒ/", "багаж", "I lost my luggage at the airport."),
        ("flight", "/flaɪt/", "рейс", "My flight was delayed."),
        ("booking", "/ˈbʊkɪŋ/", "бронирование", "I made a hotel booking for two nights."),
        ("receipt", "/rɪˈsiːt/", "чек, квитанция", "Keep the receipt for your expenses."),
        ("expenses", "/ɪkˈspensɪz/", "расходы", "The company covers travel expenses."),
    ],
}

ACHIEVEMENTS = [
    ("first_round", "Первый рабочий день", {"rounds_finished": 1}),
    ("streak_7", "Неделя без прогулов", {"streak_days": 7}),
    ("words_10", "Десять слов в портфеле", {"learned_words": 10}),
    ("words_100", "Сотня слов", {"learned_words": 100}),
    ("director", "Директор", {"xp": 5000}),
]


def seed(db: Session) -> dict:
    created = {"decks": 0, "words": 0, "achievements": 0, "admin": 0}
    admin_email = os.getenv("ADMIN_EMAIL", "admin@vocabdeck.local")
    admin = db.scalar(select(User).where(User.email == admin_email))
    if admin is None:
        password = os.getenv("ADMIN_PASSWORD")
        if not password:
            raise SystemExit("Задайте ADMIN_PASSWORD (см. .env.example)")
        admin = User(email=admin_email, name="Администратор", role="admin",
                     password_hash=hash_password(password), consent_at=utcnow())
        db.add(admin)
        db.flush()
        created["admin"] = 1

    for title, rule, order in DECKS:
        deck = db.scalar(select(Deck).where(Deck.title == title, Deck.owner_id.is_(None)))
        if deck is None:
            deck = Deck(title=title, unlock_rule=rule, sort_order=order)
            db.add(deck)
            db.flush()
            created["decks"] += 1
        for en, ipa, ru, example in WORDS[title]:
            exists = db.scalar(select(Word.id).where(Word.deck_id == deck.id, func.lower(Word.en) == en.lower()))
            if exists is None:
                db.add(Word(deck_id=deck.id, en=en, ipa=ipa, ru=ru, example=example, status="published",
                            created_by=admin.id, updated_by=admin.id))
                created["words"] += 1

    for code, title, condition in ACHIEVEMENTS:
        if db.scalar(select(Achievement.id).where(Achievement.code == code)) is None:
            db.add(Achievement(code=code, title=title, condition=condition))
            created["achievements"] += 1
    db.commit()
    return created


if __name__ == "__main__":
    from dotenv import load_dotenv  # type: ignore[import-not-found]

    load_dotenv()
    with SessionLocal() as session:
        print("Добавлено:", seed(session))
