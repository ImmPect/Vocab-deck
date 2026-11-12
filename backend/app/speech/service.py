"""Озвучка слов: доступ к слову, кэш MP3 на диске, генерация при первом запросе.

Файл кэша называется по хэшу «голос | текст», поэтому после правки слова
администратором озвучка автоматически генерируется заново, а одинаковые слова
из разных колод используют один файл.
"""
import hashlib
import logging
import os
import tempfile
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, NotFound
from app.speech import tts
from app.users.models import User
from app.words.models import Word

log = logging.getLogger("vocabdeck.speech")


class SpeechUnavailable(AppError):
    status_code, code, message = 503, "tts_unavailable", "Озвучка временно недоступна"


def _readable_word(db: Session, user: User | None, word_id: int) -> Word:
    """Опубликованное слово общей колоды, своё слово личного списка или любое слово для администратора."""
    word = db.get(Word, word_id)
    if word is None:
        raise NotFound("Слово не найдено")
    owner_id = word.deck.owner_id
    if owner_id is not None:
        if user is None or user.id != owner_id:
            raise NotFound("Слово не найдено")
    elif word.status != "published" and (user is None or user.role != "admin"):
        raise NotFound("Слово не найдено")
    return word


def cache_path(voice: str, text: str) -> Path:
    digest = hashlib.sha256(f"{voice}|{text}".encode()).hexdigest()[:40]
    return settings.media_dir / "tts" / f"{digest}.mp3"


def ensure_audio(voice: str, text: str) -> Path:
    """Путь к готовому MP3; при отсутствии в кэше — генерация и атомарная запись файла."""
    path = cache_path(voice, text)
    if path.exists():
        return path
    try:
        data = tts.synthesize(text, voice)
    except tts.SynthesisError as exc:
        log.warning("tts failed: %s", exc)
        raise SpeechUnavailable() from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    # Запись во временный файл и переименование: параллельный запрос не прочитает половину файла
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".part")
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    os.replace(tmp, path)
    return path


def word_audio(db: Session, user: User | None, word_id: int, part: str, accent: str) -> Path:
    word = _readable_word(db, user, word_id)
    text = word.en if part == "word" else word.example
    if not text:
        raise NotFound("У слова нет примера")
    return ensure_audio(tts.VOICES[accent], text)
