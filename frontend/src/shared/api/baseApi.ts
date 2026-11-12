/**
 * Базовый RTK Query API (раздел 4.3.1 ПР3). Слайсы entities и features добавляют
 * к нему свои эндпоинты через injectEndpoints, поэтому кэш один на всё приложение.
 *
 * Единый обработчик ответов (раздел 4.8.1):
 * - адрес /api/v1, отправка cookie сессии (credentials: include);
 * - заголовок X-Requested-With: VocabDeck для изменяющих запросов (защита от CSRF);
 * - ошибки приводятся к виду ApiError {status, code, message, details};
 * - запросы на чтение при сбое сети и 5xx повторяются до 3 раз, мутации — нет.
 */
import { createAction } from '@reduxjs/toolkit';
import {
  createApi,
  fetchBaseQuery,
  retry,
  type BaseQueryFn,
  type FetchArgs,
  type FetchBaseQueryError,
} from '@reduxjs/toolkit/query/react';
import { API_URL } from '../config';
import type { ApiError } from './types';

/** Ответ 401 на любой запрос, кроме стартового GET /me: сессия истекла или отозвана. */
export const sessionExpired = createAction('api/sessionExpired');

const CSRF_HEADER = 'X-Requested-With';
const CSRF_VALUE = 'VocabDeck';
const NETWORK_MESSAGE = 'Нет соединения с сервером. Проверьте подключение';

const rawBaseQuery = fetchBaseQuery({
  baseUrl: API_URL,
  credentials: 'include',
  prepareHeaders: (headers, { type }) => {
    if (type === 'mutation') headers.set(CSRF_HEADER, CSRF_VALUE);
    return headers;
  },
});

export function toApiError(error: FetchBaseQueryError, response?: Response): ApiError {
  if (error.status === 'FETCH_ERROR' || error.status === 'TIMEOUT_ERROR') {
    return { status: 'network', code: 'network_error', message: NETWORK_MESSAGE };
  }
  if (error.status === 'PARSING_ERROR') {
    return { status: error.originalStatus, code: 'bad_response', message: 'Сервер вернул неожиданный ответ' };
  }
  if (typeof error.status !== 'number') {
    return { status: 'network', code: 'unknown_error', message: NETWORK_MESSAGE };
  }
  const body = (error.data ?? {}) as { error?: Partial<ApiError> };
  return {
    status: error.status,
    code: body.error?.code ?? 'http_error',
    message: body.error?.message ?? 'Что-то пошло не так. Повторите попытку',
    details: body.error?.details,
    retryAfter: Number(response?.headers.get('Retry-After')) || undefined,
  };
}

const isMeProbe = (args: string | FetchArgs) => (typeof args === 'string' ? args : args.url) === '/me';

const normalizedBaseQuery: BaseQueryFn<string | FetchArgs, unknown, ApiError> = async (args, api, extra) => {
  const result = await rawBaseQuery(args, api, extra as object);
  if (!result.error) return { data: result.data ?? null };
  const error = toApiError(result.error, result.meta?.response);
  // 401 на GET /me — штатный режим гостя; на остальных запросах — сессия завершилась
  if (error.status === 401 && !(api.type === 'query' && isMeProbe(args))) {
    api.dispatch(sessionExpired());
  }
  return { error };
};

const isTransient = (e: ApiError) => e.status === 'network' || (typeof e.status === 'number' && e.status >= 500);

const baseQueryWithRetry = retry(
  async (args: string | FetchArgs, api, extra: object) => {
    const result = await normalizedBaseQuery(args, api, extra);
    if (result.error && (api.type === 'mutation' || !isTransient(result.error))) retry.fail(result.error);
    return result;
  },
  { maxRetries: 3 },
) as BaseQueryFn<string | FetchArgs, unknown, ApiError>;

/** Теги, которые устаревают после ответов на вопросы (итоги раунда, пакет ответов, вход). */
export const PROGRESS_TAGS = ['Me', 'Decks', 'Inbox', 'Stats', 'Achievements'] as const;

export const baseApi = createApi({
  reducerPath: 'api',
  baseQuery: baseQueryWithRetry,
  tagTypes: ['Me', 'Levels', 'Decks', 'Deck', 'Words', 'Inbox', 'Stats', 'Achievements', 'AdminWords'],
  keepUnusedDataFor: 60,
  refetchOnFocus: true,
  refetchOnReconnect: true,
  endpoints: () => ({}),
});

/** Ошибка из результата хука RTK Query или из .unwrap() — к виду ApiError. */
export function asApiError(e: unknown): ApiError | null {
  if (!e) return null;
  if (typeof e === 'object' && 'code' in e && 'message' in e) return e as ApiError;
  return { status: 'network', code: 'unknown_error', message: NETWORK_MESSAGE };
}

/** Тексты ошибок полей формы из details ответа 422 (раздел 4.8.1). */
export function fieldErrors(e: ApiError | null): Record<string, string> {
  const out: Record<string, string> = {};
  for (const d of e?.details ?? []) if (d.field && !out[d.field]) out[d.field] = d.message;
  return out;
}
