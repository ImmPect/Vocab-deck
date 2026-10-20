/** DTO модуля learning: результат ответа, пакет ответов, входящие (раздел 3.7 ПР3). */

export type Direction = 'en_ru' | 'ru_en';
export type AnswerMode = 'deadline' | 'dictation' | 'review' | 'self_check';

export interface XpPart {
  rule: string;
  xp: number;
}

/** Результат проверки ответа сервером. Гостю дополнительно приходит подписанная квитанция receipt. */
export interface AnswerResult {
  is_correct: boolean;
  xp_awarded: number;
  xp_breakdown: XpPart[];
  new_box: number;
  next_review_at: string | null;
  learned: boolean;
  xp_provisional?: boolean;
  answered_at: string;
  receipt?: string;
}

export interface BatchAnswer {
  client_event_id: string;
  mode: AnswerMode;
  word_id: number;
  direction: Direction;
  is_correct?: boolean;
  round_id?: string;
  question_id?: number;
  choice_index?: number;
  answered_at: string;
  response_ms?: number;
  /** Только для гостя: текущий ящик слова из локального журнала. */
  current_box?: number;
}

export type BatchStatus = 'applied' | 'duplicate' | 'rejected';

export interface BatchItemResult extends Partial<AnswerResult> {
  client_event_id: string;
  status: BatchStatus;
  combo?: number;
  error?: { code: string; message: string };
}

export interface BatchResponse {
  results: BatchItemResult[];
  summary: Record<BatchStatus, number>;
}

export interface InboxItem {
  word_id: number;
  en: string;
  ipa: string | null;
  ru: string;
  example: string | null;
  deck: { id: number; title: string };
  direction: Direction;
  box: number;
  next_review_at: string;
  overdue_days: number;
}

/** Подписи правил начисления опыта (табл. 16 ТЗ). */
export const XP_RULE_LABEL: Record<string, string> = {
  correct_answer: 'верный ответ',
  combo: 'серия',
  learned: 'слово выучено',
  repeat_same_day: 'повтор в тот же день',
};
