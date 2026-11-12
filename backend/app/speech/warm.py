"""Заранее генерирует озвучку опубликованных слов общей колоды, чтобы первый показ не ждал синтеза.

Запуск:  python -m app.speech.warm [--accent uk|us|all] [--no-examples]
Уже готовые файлы пропускаются, поэтому повторный запуск дозаполняет кэш.
"""
import argparse

from sqlalchemy import select

import app.models  # noqa: F401
from app.core.db import SessionLocal
from app.decks.models import Deck
from app.speech import tts
from app.speech.service import SpeechUnavailable, cache_path, ensure_audio
from app.words.models import Word


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accent", choices=["uk", "us", "all"], default="uk")
    parser.add_argument("--no-examples", action="store_true", help="только слова, без примеров")
    args = parser.parse_args()
    voices = list(tts.VOICES.values()) if args.accent == "all" else [tts.VOICES[args.accent]]

    with SessionLocal() as db:
        words = db.scalars(select(Word).join(Deck).where(Deck.owner_id.is_(None), Word.status == "published")
                           .order_by(Word.id)).all()
        texts = [w.en for w in words] + ([] if args.no_examples else [w.example for w in words if w.example])

    done = made = failed = 0
    for voice in voices:
        for text in texts:
            if cache_path(voice, text).exists():
                done += 1
                continue
            try:
                ensure_audio(voice, text)
                made += 1
            except SpeechUnavailable:
                failed += 1
            print(f"\r{voice}: готово {done + made}, создано {made}, ошибок {failed}", end="", flush=True)
    print(f"\nВсего файлов: {done + made}; создано сейчас: {made}; ошибок: {failed}")


if __name__ == "__main__":
    main()
