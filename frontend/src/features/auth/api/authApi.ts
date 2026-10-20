/** Регистрация, вход и выход (раздел 3.3 ПР3, поток 4.7.4). */
import { session, type Role } from '@/entities/user';
import { baseApi, PROGRESS_TAGS, unwrap } from '@/shared/api';

export interface GuestProgressPayload {
  format_version: number;
  events: object[];
}

export interface ImportSummary {
  accepted: number;
  rejected: number;
  rejected_events: { client_event_id: string; reason: string }[];
  xp_restored: number;
  words_transferred: number;
}

export interface AuthResult {
  user: { id: number; name: string; email: string; role: Role; xp: number };
  imported: ImportSummary | null;
}

export interface RegisterBody {
  name: string;
  email: string;
  password: string;
  consent: boolean;
  timezone?: string;
  guest_progress?: GuestProgressPayload;
}

export interface LoginBody {
  email: string;
  password: string;
  guest_progress?: GuestProgressPayload;
}

/** После входа: статус сессии, затем все экраны получают данные уже с сервера (шаг 8 потока 4.7.4). */
async function afterAuth(
  queryFulfilled: Promise<{ data: AuthResult }>,
  dispatch: (a: unknown) => unknown,
) {
  try {
    const { data } = await queryFulfilled;
    dispatch(session.resolved({ status: 'authenticated', role: data.user.role }));
    dispatch(baseApi.util.invalidateTags([...PROGRESS_TAGS]));
  } catch {
    /* ошибку показывает форма */
  }
}

export const authApi = baseApi.injectEndpoints({
  endpoints: (b) => ({
    register: b.mutation<AuthResult, RegisterBody>({
      query: (body) => ({ url: '/auth/register', method: 'POST', body }),
      transformResponse: unwrap<AuthResult>,
      onQueryStarted: (_arg, { dispatch, queryFulfilled }) => afterAuth(queryFulfilled, dispatch),
    }),
    login: b.mutation<AuthResult, LoginBody>({
      query: (body) => ({ url: '/auth/login', method: 'POST', body }),
      transformResponse: unwrap<AuthResult>,
      onQueryStarted: (_arg, { dispatch, queryFulfilled }) => afterAuth(queryFulfilled, dispatch),
    }),
    logout: b.mutation<null, void>({
      query: () => ({ url: '/auth/logout', method: 'POST' }),
      // Кэш сбрасывается, чтобы данные одного пользователя не показались следующему (раздел 4.6.1)
      onQueryStarted: async (_arg, { dispatch, queryFulfilled }) => {
        await queryFulfilled.catch(() => undefined);
        dispatch(session.loggedOut());
        dispatch(baseApi.util.resetApiState());
      },
    }),
  }),
});

export const { useRegisterMutation, useLoginMutation, useLogoutMutation } = authApi;
