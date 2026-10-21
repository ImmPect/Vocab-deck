/**
 * Данные, которые раунд передаёт наружу через свои actions. Фича не импортирует
 * соседние фичи (правило FSD), поэтому описывает форму событий сама,
 * а слой app в listener middleware превращает их в guestProgress/eventRecorded
 * и outbox/enqueued.
 */
import type { BatchAnswer, Direction } from '@/entities/progress';

export interface WordInfoLike {
  en: string;
  ru: string;
  ipa?: string | null;
  deck_id?: number;
  deck_title?: string;
}

export interface GuestEventLike {
  client_event_id: string;
  word_id: number;
  direction: Direction;
  mode: 'deadline';
  is_correct: boolean;
  answered_at: string;
  combo: number;
  round_id: string;
  question_id: number;
  receipt: string;
  xp_awarded: number;
  new_box: number;
  next_review_at: string | null;
  learned: boolean;
  word: WordInfoLike;
}

export interface OutboxItemLike {
  answer: BatchAnswer;
  word?: WordInfoLike;
}
