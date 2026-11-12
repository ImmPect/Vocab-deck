/** Формат ответов API (раздел 3.1.5 ПР3): {"data": ..., "meta": ...} или {"error": {...}}. */

export interface PageMeta {
  page?: number;
  limit?: number;
  total_items: number;
}

export interface Envelope<T> {
  data: T;
  meta?: PageMeta;
}

export interface Paged<T> {
  items: T[];
  meta: PageMeta;
}

export interface ErrorDetail {
  field?: string;
  message: string;
  existing_word_id?: number;
  [key: string]: unknown;
}

/** Ошибка, приведённая к одному виду единым обработчиком (раздел 4.8.1 ПР3). */
export interface ApiError {
  /** HTTP-код или 'network' при сбое сети. */
  status: number | 'network';
  code: string;
  message: string;
  details?: ErrorDetail[];
  /** Секунды из заголовка Retry-After (ответ 429). */
  retryAfter?: number;
}

export const unwrap = <T>(r: Envelope<T>): T => r.data;

export const unwrapPage = <T>(r: Envelope<T[]>): Paged<T> => ({
  items: r.data,
  meta: r.meta ?? { total_items: r.data.length },
});
