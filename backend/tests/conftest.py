"""Общие фикстуры тестов.

Каждый тест получает свежую БД SQLite в памяти с начальными данными (app.seed)
и клиент TestClient, который по умолчанию отправляет заголовок X-Requested-With.
Фикстура make_client позволяет получить клиента, уже вошедшего под пользователем,
не завися от реализации /auth (сессия создаётся напрямую в БД).
"""
import os

os.environ["ENV"] = "test"  # до импорта приложения: отключает ограничение частоты
os.environ.setdefault("ADMIN_PASSWORD", "AdminPass123")

from datetime import timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402

import app.models  # noqa: E402,F401
from app.core.db import Base, get_db, utcnow  # noqa: E402
from app.core.security import hash_password, new_session_token  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402
from app.users.models import User, UserSession  # noqa: E402

CSRF = {"X-Requested-With": "VocabDeck"}
PASSWORD = "Secret123"


@pytest.fixture
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(eng, "connect")
    def _fk_on(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def SessionTest(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db(SessionTest):
    """Сессия БД для подготовки данных и проверок в самом тесте."""
    with SessionTest() as s:
        seed(s)
        yield s


@pytest.fixture
def client(db, SessionTest):
    def _get_db():
        s = SessionTest()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app, headers=CSRF) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(db):
    """Создаёт пользователя напрямую в БД: make_user(email=..., xp=..., role=...)."""
    counter = {"n": 0}

    def _make(email: str | None = None, *, name: str = "Тест", role: str = "user", xp: int = 0,
              password: str = PASSWORD, **fields) -> User:
        counter["n"] += 1
        u = User(email=email or f"user{counter['n']}@example.ru", name=name, role=role, xp=xp,
                 password_hash=hash_password(password), consent_at=utcnow(), **fields)
        db.add(u)
        db.commit()
        return u

    return _make


@pytest.fixture
def make_client(db, client):
    """Возвращает нового TestClient с cookie сессии указанного пользователя."""
    clients = []

    def _make(user: User) -> TestClient:
        token = new_session_token()
        db.add(UserSession(id=token, user_id=user.id, expires_at=utcnow() + timedelta(days=30)))
        db.commit()
        c = TestClient(app, headers=CSRF, cookies={"session_id": token})
        clients.append(c)
        return c

    yield _make
    for c in clients:
        c.close()


@pytest.fixture
def user_client(make_user, make_client):
    return make_client(make_user())


@pytest.fixture
def admin_client(db, make_client):
    from sqlalchemy import select
    admin = db.scalar(select(User).where(User.role == "admin"))
    return make_client(admin)
