"""Демонстрационный сценарий тестового запуска (раздел 3.10 ПР3) на работающем сервере.

Гость играет раунд «Дедлайн», регистрируется с переносом прогресса, затем
проверяются профиль, колоды, админ-эндпоинт и типовые ошибки.

Запуск (сервер должен работать на :8000):  python scripts/demo_scenario.py
"""
import json
import os
import sys
import uuid
from datetime import UTC, datetime

import httpx

BASE = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")
H = {"X-Requested-With": "VocabDeck"}


def show(step: str, r: httpx.Response, keys: list[str] | None = None) -> dict:
    body = r.json() if r.content else {}
    data = body.get("data", body)
    if keys and isinstance(data, dict):
        data = {k: data.get(k) for k in keys}
    print(f"\n### {step}\n{r.request.method} {r.request.url.path} -> {r.status_code}")
    print(json.dumps(data if "error" not in body else body, ensure_ascii=False, indent=2)[:900])
    return body


def now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def main() -> None:
    guest = httpx.Client(base_url=BASE, headers=H)
    show("1. Профиль без входа", guest.get("/me"))
    decks = show("2. Отделы (гость)", guest.get("/decks"))
    office = next(d for d in decks["data"] if d["title"] == "Офис")
    print("Отделы:", [(d["title"], "закрыт" if d.get("locked") else "открыт") for d in decks["data"]])

    r = guest.post("/rounds", json={"deck_id": office["id"], "mode": "deadline"})
    show("3. Начало раунда «Дедлайн»", r, ["round_id", "mode", "direction", "time_limit_s"])
    rnd = r.json()["data"]
    print("Первый вопрос:", json.dumps(rnd["questions"][0], ensure_ascii=False))
    round_id = rnd["round_id"]
    round_questions = rnd["questions"]

    # Правильный перевод знаем из справочника слов отдела: ищем вариант, совпадающий с ru слова
    words = {w["id"]: w for w in guest.get(f"/decks/{office['id']}/words", params={"limit": 100}).json()["data"]}
    events = []
    plan = [True, True, True, False, True]  # как в сценарии 3.10: 3 верных, ошибка, верный
    for q, correct in zip(round_questions, plan):
        right = q["options"].index(words[q["word_id"]]["ru"])
        choice = right if correct else (right + 1) % 4
        cid = str(uuid.uuid4())
        payload = {"question_id": q["question_id"], "choice_index": choice, "client_event_id": cid,
                   "answered_at": now(), "response_ms": 2500}
        res = show(f"4.{q['question_id']} Ответ на вопрос «{q['prompt']}» ({'верно' if correct else 'ошибка'})",
                   guest.post(f"/rounds/{round_id}/answers", json=payload),
                   ["is_correct", "xp_awarded", "combo", "new_box", "xp_provisional"])["data"]
        events.append({"client_event_id": cid, "word_id": q["word_id"], "direction": "en_ru", "mode": "deadline",
                       "is_correct": res["is_correct"], "answered_at": res.get("answered_at", payload["answered_at"]),
                       "combo": res["combo"], "round_id": round_id, "question_id": q["question_id"],
                       "receipt": res["receipt"]})
        if q["question_id"] == 4:
            show("4.4-повтор. Повторная отправка того же ответа (обрыв связи)",
                 guest.post(f"/rounds/{round_id}/answers", json=payload), ["is_correct", "xp_awarded", "combo"])

    show("5. Итоги раунда (гость)", guest.post(f"/rounds/{round_id}/finish"),
         ["answered", "correct", "xp_earned", "xp_provisional", "suggest_registration"])

    # Подделка: гость меняет результат ошибочного ответа на «верно» — подпись не совпадёт
    events[3] = {**events[3], "is_correct": True}
    email = f"demo-{uuid.uuid4().hex[:6]}@example.ru"
    reg = {"name": "Анна", "email": email, "password": "Str0ngPass!", "consent": True,
           "guest_progress": {"format_version": 1, "events": events}}
    user = httpx.Client(base_url=BASE, headers=H)
    show("6. Регистрация с переносом гостевого прогресса", user.post("/auth/register", json=reg), ["user", "imported"])
    print("Cookie session_id установлена:", "session_id" in user.cookies)
    show("7. Повторная регистрация с той же почтой", user.post("/auth/register", json=reg))
    show("8. Профиль пользователя", user.get("/me"),
         ["name", "xp", "level", "next_level", "streak_days", "inbox_count", "features"])
    show("9. Начало раунда в закрытом отделе «Командировка»",
         user.post("/rounds", json={"deck_id": next(d["id"] for d in decks["data"] if d["title"] == "Командировка"),
                                    "mode": "deadline"}))
    show("10. Админ-эндпоинт с ролью user", user.get("/admin/words"))
    show("11. Изменяющий запрос без заголовка X-Requested-With",
         httpx.post(f"{BASE}/decks", json={"title": "Мой список"}, cookies=user.cookies))
    my = show("12. Создание личного списка", user.post("/decks", json={"title": "Мой список"}), ["id", "title"])
    my_id = my["data"]["id"]
    show("13. Добавление слова в личный список",
         user.post(f"/decks/{my_id}/words", json={"en": "budget", "ru": "бюджет"}), ["id", "en", "ru", "status"])
    show("13а. Дубликат слова (без учёта регистра)",
         user.post(f"/decks/{my_id}/words", json={"en": "Budget", "ru": "бюджет"}))
    show("13б. Ошибка валидации: кириллица в поле en",
         user.post(f"/decks/{my_id}/words", json={"en": "срок", "ru": "срок"}))
    show("14. Выход", user.post("/auth/logout"))
    show("15. Профиль после выхода", user.get("/me"))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
