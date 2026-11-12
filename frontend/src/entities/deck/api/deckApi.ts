/** Эндпоинты отделов и личных списков (табл. 4.5 ПР3). */
import { baseApi, unwrap } from '@/shared/api';
import type { Deck, ImportReport } from '../model/types';

export const deckApi = baseApi.injectEndpoints({
  endpoints: (b) => ({
    getDecks: b.query<Deck[], void>({
      query: () => '/decks',
      transformResponse: unwrap<Deck[]>,
      providesTags: ['Decks'],
    }),
    getDeck: b.query<Deck, number>({
      query: (id) => `/decks/${id}`,
      transformResponse: unwrap<Deck>,
      providesTags: (_r, _e, id) => [{ type: 'Deck', id }],
    }),
    createList: b.mutation<Deck, { title: string }>({
      query: (body) => ({ url: '/decks', method: 'POST', body }),
      transformResponse: unwrap<Deck>,
      invalidatesTags: ['Decks'],
    }),
    renameList: b.mutation<Deck, { id: number; title: string }>({
      query: ({ id, title }) => ({ url: `/decks/${id}`, method: 'PATCH', body: { title } }),
      transformResponse: unwrap<Deck>,
      invalidatesTags: (_r, _e, { id }) => ['Decks', { type: 'Deck', id }],
    }),
    deleteList: b.mutation<null, number>({
      query: (id) => ({ url: `/decks/${id}`, method: 'DELETE' }),
      invalidatesTags: ['Decks', 'Inbox', 'Me'],
    }),
    importCsv: b.mutation<ImportReport, { deckId: number; file: File }>({
      query: ({ deckId, file }) => {
        const form = new FormData();
        form.append('file', file);
        return { url: `/decks/${deckId}/import`, method: 'POST', body: form };
      },
      transformResponse: unwrap<ImportReport>,
      invalidatesTags: (_r, _e, { deckId }) => ['Decks', { type: 'Deck', id: deckId }, { type: 'Words', id: deckId }],
    }),
  }),
});

export const {
  useGetDecksQuery,
  useGetDeckQuery,
  useCreateListMutation,
  useRenameListMutation,
  useDeleteListMutation,
  useImportCsvMutation,
} = deckApi;
