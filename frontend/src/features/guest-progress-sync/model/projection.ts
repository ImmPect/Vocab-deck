/**
 * Проекция журнала гостя для интерфейса (раздел 4.6.2 ПР3): опыт, ящики слов,
 * входящие, серия дней. Только для показа — на сервере прогресс пересчитывается заново.
 */
import { createSelector } from '@reduxjs/toolkit';
import type { Direction, InboxItem } from '@/entities/progress';
import { addDays, localIsoDate } from '@/shared/lib';
import type { GuestEvent, GuestEventSigned, GuestProgressState, GuestWordInfo } from './guestSlice';
import { GUEST_FORMAT_VERSION } from './guestSlice';

export interface GuestWordState {
  word_id: number;
  direction: Direction;
  box: number;
  next_review_at: string | null;
  learned: boolean;
  word?: GuestWordInfo;
}

export interface GuestProjection {
  xp: number;
  words: GuestWordState[];
  wordsCount: number;
  learnedCount: number;
  streakDays: number;
  inbox: InboxItem[];
  answers: number;
}

const key = (wordId: number, direction: string) => `${wordId}:${direction}`;

/** Чистая функция: журнал → проекция на дату today (YYYY-MM-DD). */
export function project(events: GuestEvent[], today: string = localIsoDate()): GuestProjection {
  const sorted = [...events].sort((a, b) => a.answered_at.localeCompare(b.answered_at));
  const words = new Map<string, GuestWordState>();
  const days = new Set<string>();
  let xp = 0;
  for (const e of sorted) {
    xp += e.xp_awarded;
    days.add(localIsoDate(new Date(e.answered_at)));
    const k = key(e.word_id, e.direction);
    const prev = words.get(k);
    words.set(k, {
      word_id: e.word_id,
      direction: e.direction,
      box: e.new_box,
      next_review_at: e.next_review_at,
      learned: (prev?.learned ?? false) || e.learned,
      word: e.word ?? prev?.word,
    });
  }

  // Серия: подряд идущие дни с ответами, заканчивая сегодня или вчера
  let streakDays = 0;
  let day = days.has(today) ? today : addDays(today, -1);
  while (days.has(day)) {
    streakDays += 1;
    day = addDays(day, -1);
  }

  const list = [...words.values()];
  const inbox: InboxItem[] = list
    .filter((w) => w.word && w.next_review_at && w.next_review_at <= today)
    .map((w) => ({
      word_id: w.word_id,
      en: w.word!.en,
      ru: w.word!.ru,
      ipa: w.word!.ipa ?? null,
      example: w.word!.example ?? null,
      deck: { id: w.word!.deck_id ?? 0, title: w.word!.deck_title ?? '' },
      direction: w.direction,
      box: w.box,
      next_review_at: w.next_review_at!,
      overdue_days: 0,
    }));

  return {
    xp,
    words: list,
    wordsCount: new Set(list.map((w) => w.word_id)).size,
    learnedCount: list.filter((w) => w.learned).length,
    streakDays,
    inbox,
    answers: events.length,
  };
}

type WithGuest = { guestProgress: GuestProgressState };

export const selectGuestEvents = (s: WithGuest) => s.guestProgress.events;
export const selectGuestProjection = createSelector([selectGuestEvents], (events) => project(events));
export const selectHasGuestProgress = (s: WithGuest) => s.guestProgress.events.length > 0;

/** Текущий ящик слова для поля current_box запроса гостя. */
export const selectGuestBoxes = createSelector([selectGuestProjection], (p) => {
  const map = new Map(p.words.map((w) => [key(w.word_id, w.direction), w.box]));
  return (wordId: number, direction: Direction) => map.get(key(wordId, direction));
});

/** Выученные гостем слова по отделам — для условия открытия learned_in_deck. */
export const selectGuestLearnedByDeck = createSelector([selectGuestProjection], (p) => {
  const counts = new Map<number, number>();
  for (const w of p.words) if (w.learned && w.word?.deck_id) counts.set(w.word.deck_id, (counts.get(w.word.deck_id) ?? 0) + 1);
  return (deckId: number) => counts.get(deckId) ?? 0;
});

/**
 * Поле guest_progress для POST /auth/register и /auth/login (поток 4.7.4, шаг 5):
 * только события с квитанцией и только подписанные поля — сервер запрещает лишние.
 */
export function toGuestProgressPayload(events: GuestEvent[]) {
  const signed: GuestEventSigned[] = events
    .filter((e) => e.receipt)
    .map(({ client_event_id, word_id, direction, mode, is_correct, answered_at, combo, round_id, question_id, receipt }) => ({
      client_event_id,
      word_id,
      direction,
      mode,
      is_correct,
      answered_at,
      combo,
      ...(round_id ? { round_id } : {}),
      ...(question_id ? { question_id } : {}),
      receipt,
    }));
  return signed.length ? { format_version: GUEST_FORMAT_VERSION, events: signed } : undefined;
}
