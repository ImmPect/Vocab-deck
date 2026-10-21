/**
 * Slice guestProgress (раздел 4.6.2 ПР3): журнал событий гостя с подписанными
 * сервером квитанциями receipt. Опыт гостя не вычисляется «с нуля» на клиенте:
 * xp_awarded и new_box — значения, которые прислал сервер. При регистрации журнал
 * уходит на сервер, тот проверяет подписи и пересчитывает прогресс заново.
 */
import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { AnswerMode, Direction } from '@/entities/progress';

export const GUEST_FORMAT_VERSION = 1;

/** Поля, которые подписаны квитанцией и уходят на сервер (GuestEvent, learning/guest.py). */
export interface GuestEventSigned {
  client_event_id: string;
  word_id: number;
  direction: Direction;
  mode: AnswerMode;
  is_correct: boolean;
  answered_at: string;
  combo: number;
  round_id?: string;
  question_id?: number;
  receipt: string;
}

/** Слово для показа во входящих гостя (на сервер не отправляется). */
export interface GuestWordInfo {
  en: string;
  ru: string;
  ipa?: string | null;
  example?: string | null;
  deck_id?: number;
  deck_title?: string;
}

export interface GuestEvent extends GuestEventSigned {
  xp_awarded: number;
  new_box: number;
  next_review_at: string | null;
  learned: boolean;
  word?: GuestWordInfo;
}

export interface GuestProgressState {
  format_version: number;
  events: GuestEvent[];
}

export const emptyGuestProgress = (): GuestProgressState => ({ format_version: GUEST_FORMAT_VERSION, events: [] });

export const guestProgressSlice = createSlice({
  name: 'guestProgress',
  initialState: emptyGuestProgress,
  reducers: {
    eventRecorded(state, action: PayloadAction<GuestEvent>) {
      // Повторная квитанция того же события (duplicate из очереди) не дублируется
      if (state.events.some((e) => e.client_event_id === action.payload.client_event_id)) return;
      state.events.push(action.payload);
    },
    cleared: () => emptyGuestProgress(),
    restored: (_state, action: PayloadAction<GuestProgressState>) => action.payload,
  },
});

export const guestProgress = guestProgressSlice.actions;
