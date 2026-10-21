"""Модуль speech: озвучка слов. Движок синтеза подменяется — тесты не ходят в сеть."""
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.decks.models import Deck
from app.speech import tts
from app.words.models import Word

API = "/api/v1"
FAKE_MP3 = b"ID3\x04fake-mp3"


@pytest.fixture(autouse=True)
def fake_tts(tmp_path, monkeypatch):
    """Кэш — во временном каталоге, синтез — заглушка, которая считает вызовы."""
    monkeypatch.setattr(settings, "media_dir", tmp_path)
    calls = []

    def _synth(text, voice, rate="-10%"):
        calls.append((text, voice))
        return FAKE_MP3

    monkeypatch.setattr(tts, "synthesize", _synth)
    return calls


def word(db, en="deadline") -> Word:
    return db.scalar(select(Word).join(Deck).where(Word.en == en, Deck.owner_id.is_(None)))


def test_guest_gets_word_audio_and_it_is_cached(db, client, fake_tts):
    w = word(db)
    r = client.get(f"{API}/words/{w.id}/audio")
    assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg"
    assert r.content == FAKE_MP3 and "max-age=86400" in r.headers["cache-control"]
    assert fake_tts == [("deadline", "en-GB-SoniaNeural")]
    # повторный запрос берётся из кэша на диске, синтез не вызывается
    assert client.get(f"{API}/words/{w.id}/audio").status_code == 200
    assert len(fake_tts) == 1


def test_example_and_american_accent(db, client, fake_tts):
    w = word(db)
    assert client.get(f"{API}/words/{w.id}/audio", params={"part": "example", "accent": "us"}).status_code == 200
    assert fake_tts == [(w.example, "en-US-AriaNeural")]


def test_invalid_params_and_unknown_word(db, client):
    w = word(db)
    assert client.get(f"{API}/words/{w.id}/audio", params={"part": "translation"}).status_code == 422
    assert client.get(f"{API}/words/{w.id}/audio", params={"accent": "au"}).status_code == 422
    assert client.get(f"{API}/words/999999/audio").status_code == 404


def test_personal_word_only_for_owner(db, client, user_client, make_user, make_client):
    deck = user_client.post(f"{API}/decks", json={"title": "Мой"}).json()["data"]["id"]
    wid = user_client.post(f"{API}/decks/{deck}/words", json={"en": "stand-up", "ru": "планёрка"}).json()["data"]["id"]
    assert user_client.get(f"{API}/words/{wid}/audio").status_code == 200
    assert client.get(f"{API}/words/{wid}/audio").status_code == 404
    assert make_client(make_user()).get(f"{API}/words/{wid}/audio").status_code == 404
    # примера нет — 404, а не пустой файл
    assert user_client.get(f"{API}/words/{wid}/audio", params={"part": "example"}).status_code == 404


def test_draft_audio_only_for_admin(db, client, admin_client):
    w = word(db)
    w.status = "draft"
    db.commit()
    assert client.get(f"{API}/words/{w.id}/audio").status_code == 404
    assert admin_client.get(f"{API}/words/{w.id}/audio").status_code == 200


def test_engine_failure_returns_503(db, client, monkeypatch):
    def _fail(text, voice, rate="-10%"):
        raise tts.SynthesisError("network down")

    monkeypatch.setattr(tts, "synthesize", _fail)
    r = client.get(f"{API}/words/{word(db).id}/audio")
    assert r.status_code == 503 and r.json()["error"]["code"] == "tts_unavailable"
