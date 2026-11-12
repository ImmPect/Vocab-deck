/** Конфигурация клиента: адрес API, пути маршрутов, константы (слой shared/config). */

export const API_URL: string = import.meta.env.VITE_API_URL ?? '/api/v1';

export const ROUTES = {
  welcome: '/',
  home: '/home',
  cards: (deckId: number | string) => `/decks/${deckId}/cards`,
  deadline: (deckId: number | string) => `/decks/${deckId}/deadline`,
  result: (roundId: string) => `/rounds/${roundId}/result`,
  inbox: '/inbox',
  profile: '/profile',
  list: (deckId: number | string) => `/lists/${deckId}`,
  login: '/login',
  register: '/register',
  adminWords: '/admin/words',
  adminWordNew: '/admin/words/new',
  adminWord: (wordId: number | string) => `/admin/words/${wordId}`,
} as const;

/** Ограничения раунда «Дедлайн» (п. 3.5 ТЗ). */
export const ROUND = {
  questions: 5,
  minWords: 4,
  nextQuestionDelayMs: 900,
  lowTimeS: 10,
} as const;

/** Ключи localStorage (табл. 4.6 ПР3). */
export const STORAGE_KEYS = {
  guest: 'vocabdeck:guest',
  outbox: 'vocabdeck:outbox',
  prefs: 'vocabdeck:prefs',
} as const;

export const OUTBOX = {
  batchSize: 50,
  /** Паузы перед повторной отправкой: 5 с, 15 с, 1 мин, далее 5 мин (поток 4.7.3). */
  backoffMs: [5_000, 15_000, 60_000, 300_000],
} as const;

export const TOAST_MS = 2_000;
export const SKELETON_DELAY_MS = 200;
export { registerPrefetch, prefetch } from './prefetch';
