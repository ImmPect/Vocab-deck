/** Эндпоинты текущего пользователя и справочник должностей (табл. 4.5 ПР3). */
import { baseApi, unwrap, type Envelope } from '@/shared/api';
import type { Achievements, Level, Me, Stats, UpdateMeBody } from '../model/types';

export const userApi = baseApi.injectEndpoints({
  endpoints: (b) => ({
    getMe: b.query<Me, void>({
      query: () => '/me',
      transformResponse: unwrap<Me>,
      providesTags: ['Me'],
    }),
    getLevels: b.query<Level[], void>({
      query: () => '/levels',
      transformResponse: unwrap<Level[]>,
      providesTags: ['Levels'],
      keepUnusedDataFor: 24 * 3600, // справочник почти не меняется — весь сеанс
    }),
    getStats: b.query<Stats, { from: string; to: string }>({
      query: ({ from, to }) => ({ url: '/me/stats', params: { from, to } }),
      transformResponse: unwrap<Stats>,
      providesTags: ['Stats'],
    }),
    getAchievements: b.query<Achievements, void>({
      query: () => '/me/achievements',
      transformResponse: unwrap<Achievements>,
      providesTags: ['Achievements'],
    }),
    updateMe: b.mutation<Me, UpdateMeBody>({
      query: (body) => ({ url: '/me', method: 'PATCH', body }),
      transformResponse: (r: Envelope<Me>) => r.data,
      invalidatesTags: ['Me'],
    }),
    deleteMe: b.mutation<null, { password: string }>({
      query: (body) => ({ url: '/me', method: 'DELETE', body }),
    }),
  }),
});

export const {
  useGetMeQuery,
  useGetLevelsQuery,
  useGetStatsQuery,
  useGetAchievementsQuery,
  useUpdateMeMutation,
  useDeleteMeMutation,
} = userApi;
