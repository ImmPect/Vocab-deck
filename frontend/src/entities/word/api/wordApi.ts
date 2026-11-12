/** Эндпоинты слов: колода, личный список, поиск администратора (табл. 4.5 ПР3). */
import { baseApi, unwrap, unwrapPage, type Paged } from '@/shared/api';
import type { AdminWord, AdminWordsFilter, Word, WordFields } from '../model/types';

export const wordApi = baseApi.injectEndpoints({
  endpoints: (b) => ({
    getDeckWords: b.query<Paged<Word>, { deckId: number; page?: number; limit?: number; q?: string }>({
      query: ({ deckId, page = 1, limit = 100, q }) => ({
        url: `/decks/${deckId}/words`,
        params: { page, limit, ...(q ? { q } : {}) },
      }),
      transformResponse: unwrapPage<Word>,
      providesTags: (_r, _e, { deckId }) => [{ type: 'Words', id: deckId }],
    }),
    addWord: b.mutation<Word, { deckId: number } & WordFields>({
      query: ({ deckId, ...body }) => ({ url: `/decks/${deckId}/words`, method: 'POST', body }),
      transformResponse: unwrap<Word>,
      invalidatesTags: (_r, _e, { deckId }) => [{ type: 'Words', id: deckId }, 'Decks', { type: 'Deck', id: deckId }],
    }),
    updateWord: b.mutation<Word, { id: number; deckId: number } & Partial<WordFields>>({
      query: ({ id, deckId: _deckId, ...body }) => ({ url: `/words/${id}`, method: 'PATCH', body }),
      transformResponse: unwrap<Word>,
      invalidatesTags: (_r, _e, { deckId }) => [{ type: 'Words', id: deckId }],
    }),
    deleteWord: b.mutation<null, { id: number; deckId: number }>({
      query: ({ id }) => ({ url: `/words/${id}`, method: 'DELETE' }),
      invalidatesTags: (_r, _e, { deckId }) => [{ type: 'Words', id: deckId }, 'Decks', { type: 'Deck', id: deckId }, 'Inbox'],
    }),
    getAdminWords: b.query<Paged<AdminWord>, AdminWordsFilter>({
      query: ({ q, deck_id, status, page = 1, limit = 20 }) => ({
        url: '/admin/words',
        params: { page, limit, ...(q ? { q } : {}), ...(deck_id ? { deck_id } : {}), ...(status ? { status } : {}) },
      }),
      transformResponse: unwrapPage<AdminWord>,
      providesTags: (r) => [
        { type: 'AdminWords', id: 'LIST' },
        ...(r?.items.map((w) => ({ type: 'AdminWords' as const, id: w.id })) ?? []),
      ],
      keepUnusedDataFor: 30,
    }),
  }),
});

export const {
  useGetDeckWordsQuery,
  useAddWordMutation,
  useUpdateWordMutation,
  useDeleteWordMutation,
  useGetAdminWordsQuery,
} = wordApi;
