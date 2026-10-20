"""Импорт всех ORM-моделей: нужен Alembic (autogenerate) и тестам (create_all)."""
from app.decks.models import Deck  # noqa: F401
from app.gamification.models import Achievement, UserAchievement  # noqa: F401
from app.learning.models import AnswerEvent, Round, UserWordProgress  # noqa: F401
from app.users.models import User, UserSession  # noqa: F401
from app.words.models import Word  # noqa: F401
