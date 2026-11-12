/** Создание и изменение слов общей колоды администратором (раздел 3.8 ПР3). */
import type { AdminWord, WordFields, WordStatus } from '@/entities/word';
import { baseApi, unwrap } from '@/shared/api';

type Body = WordFields & { deck_id: number; status: WordStatus };

export const adminWordApi = baseApi.injectEndpoints({
  endpoints: (b) => ({
    createAdminWord: b.mutation<AdminWord, Body>({
      query: (body) => ({ url: '/admin/words', method: 'POST', body }),
      transformResponse: unwrap<AdminWord>,
      invalidatesTags: (_r, _e, { deck_id }) => [{ type: 'AdminWords', id: 'LIST' }, 'Decks', { type: 'Words', id: deck_id }],
    }),
    updateAdminWord: b.mutation<AdminWord, { id: number } & Partial<Body>>({
      query: ({ id, ...body }) => ({ url: `/admin/words/${id}`, method: 'PATCH', body }),
      transformResponse: unwrap<AdminWord>,
      invalidatesTags: (r, _e, { id }) => [
        { type: 'AdminWords', id: 'LIST' },
        { type: 'AdminWords', id },
        'Decks',
        ...(r ? [{ type: 'Words' as const, id: r.deck.id }] : []),
      ],
    }),
  }),
});

export const { useCreateAdminWordMutation, useUpdateAdminWordMutation } = adminWordApi;
