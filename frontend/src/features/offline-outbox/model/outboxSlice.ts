/**
 * Slice outbox (раздел 4.6.2 ПР3): очередь ответов, которые не удалось отправить
 * (нет сети, 5xx). Ответы идемпотентны по client_event_id, поэтому повтор безопасен:
 * сервер вернёт duplicate и не начислит опыт второй раз (NFR-R-02).
 */
import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { BatchAnswer, BatchItemResult } from '@/entities/progress';

export const OUTBOX_FORMAT_VERSION = 1;

/** Слово для журнала гостя, если квитанция придёт после отправки очереди. */
export interface OutboxWordInfo {
  en: string;
  ru: string;
  ipa?: string | null;
  example?: string | null;
  deck_id?: number;
  deck_title?: string;
}

export interface OutboxItem {
  answer: BatchAnswer;
  word?: OutboxWordInfo;
}

export interface OutboxState {
  format_version: number;
  items: OutboxItem[];
  flushing: boolean;
  attempt: number;
  nextAttemptAt: number | null;
}

export const emptyOutbox = (): OutboxState => ({
  format_version: OUTBOX_FORMAT_VERSION,
  items: [],
  flushing: false,
  attempt: 0,
  nextAttemptAt: null,
});

export interface AckPayload {
  items: OutboxItem[];
  results: BatchItemResult[];
}

export const outboxSlice = createSlice({
  name: 'outbox',
  initialState: emptyOutbox,
  reducers: {
    enqueued(state, action: PayloadAction<OutboxItem | OutboxItem[]>) {
      const add = Array.isArray(action.payload) ? action.payload : [action.payload];
      const known = new Set(state.items.map((i) => i.answer.client_event_id));
      for (const item of add) if (!known.has(item.answer.client_event_id)) state.items.push(item);
    },
    flushStarted(state) {
      state.flushing = true;
    },
    /** Сервер обработал пакет: applied, duplicate и rejected удаляются из очереди. */
    itemsAcked(state, action: PayloadAction<AckPayload>) {
      const done = new Set(action.payload.results.map((r) => r.client_event_id));
      state.items = state.items.filter((i) => !done.has(i.answer.client_event_id));
      state.flushing = false;
      state.attempt = 0;
      state.nextAttemptAt = null;
    },
    flushFailed(state, action: PayloadAction<{ nextAttemptAt: number }>) {
      state.flushing = false;
      state.attempt += 1;
      state.nextAttemptAt = action.payload.nextAttemptAt;
    },
    flushSkipped(state) {
      state.flushing = false;
    },
    restored(state, action: PayloadAction<OutboxItem[]>) {
      state.items = action.payload;
    },
  },
});

export const outbox = outboxSlice.actions;

type WithOutbox = { outbox: OutboxState };
export const selectOutbox = (s: WithOutbox) => s.outbox;
export const selectOutboxCount = (s: WithOutbox) => s.outbox.items.length;
