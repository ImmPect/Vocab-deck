/** Входящие и пакет ответов (табл. 4.5 ПР3). */
import { baseApi, PROGRESS_TAGS, unwrap, unwrapPage, type Paged } from '@/shared/api';
import type { BatchAnswer, BatchResponse, Direction, InboxItem } from '../model/types';

export const progressApi = baseApi.injectEndpoints({
  endpoints: (b) => ({
    getInbox: b.query<Paged<InboxItem>, { direction?: Direction; limit?: number } | void>({
      query: (arg) => ({ url: '/inbox', params: { limit: arg?.limit ?? 100, ...(arg?.direction ? { direction: arg.direction } : {}) } }),
      transformResponse: unwrapPage<InboxItem>,
      providesTags: ['Inbox'],
      keepUnusedDataFor: 30,
    }),
    /**
     * POST /answers/batch: самооценка на карточках, разбор входящих, отложенные офлайн-ответы.
     * Идемпотентен по client_event_id, поэтому его можно безопасно повторять из очереди outbox.
     */
    sendAnswers: b.mutation<BatchResponse, { answers: BatchAnswer[]; asGuest: boolean }>({
      query: ({ answers }) => ({ url: '/answers/batch', method: 'POST', body: { answers } }),
      transformResponse: unwrap<BatchResponse>,
      invalidatesTags: (r, _e, { asGuest }) => (r && !asGuest && r.summary.applied > 0 ? [...PROGRESS_TAGS] : []),
    }),
  }),
});

export const { useGetInboxQuery, useSendAnswersMutation } = progressApi;
