"""Синтез речи нейросетевыми голосами Microsoft Edge (пакет edge-tts).

Отдельный модуль, чтобы сервис не зависел от конкретного движка: в тестах
функция synthesize подменяется, а при смене движка меняется только этот файл.
"""
import asyncio

# Голоса для произношения: британское (по умолчанию, как транскрипции в словаре) и американское
VOICES = {"uk": "en-GB-SoniaNeural", "us": "en-US-AriaNeural"}


class SynthesisError(Exception):
    """Движок синтеза недоступен или вернул пустой ответ."""


async def _synthesize(text: str, voice: str, rate: str) -> bytes:
    import edge_tts  # импорт здесь: модуль нужен только при первой генерации

    chunks = []
    async for chunk in edge_tts.Communicate(text, voice, rate=rate).stream():
        if chunk["type"] == "audio":
            chunks.append(chunk["data"])
    return b"".join(chunks)


def synthesize(text: str, voice: str, rate: str = "-10%") -> bytes:
    """MP3 с произношением text. Темп чуть ниже обычного — слова учат, а не слушают новости."""
    try:
        data = asyncio.run(_synthesize(text, voice, rate))
    except Exception as exc:  # сеть, отказ сервиса, неизвестный голос
        raise SynthesisError(str(exc)) from exc
    if not data:
        raise SynthesisError("пустой ответ движка синтеза")
    return data
