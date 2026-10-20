/**
 * Slice session (раздел 4.6.2 ПР3): статус сессии и роль. Данные профиля здесь
 * не дублируются — они в кэше GET /me. О сессии клиент узнаёт только по ответу
 * GET /me: cookie session_id HttpOnly и из JavaScript не читается.
 */
import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import { sessionExpired } from '@/shared/api';
import { userApi } from '../api/userApi';
import type { Role } from './types';

export type SessionStatus = 'unknown' | 'guest' | 'authenticated';

export interface SessionState {
  status: SessionStatus;
  role: Role | null;
  /** Сессия завершилась на сервере (401) — показать «Сессия завершена, войдите снова». */
  expired: boolean;
}

const initialState: SessionState = { status: 'unknown', role: null, expired: false };

export const sessionSlice = createSlice({
  name: 'session',
  initialState,
  reducers: {
    resolved(state, action: PayloadAction<{ status: Exclude<SessionStatus, 'unknown'>; role?: Role | null }>) {
      state.status = action.payload.status;
      state.role = action.payload.role ?? null;
      if (action.payload.status === 'authenticated') state.expired = false;
    },
    loggedOut(state) {
      state.status = 'guest';
      state.role = null;
    },
    expiredNoticeShown(state) {
      state.expired = false;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sessionExpired, (state) => {
        if (state.status === 'authenticated') state.expired = true;
        state.status = 'guest';
        state.role = null;
      })
      // Ответ GET /me при старте: 200 — пользователь, 401 — гость (штатно, без сообщений)
      .addMatcher(userApi.endpoints.getMe.matchFulfilled, (state, { payload }) => {
        state.status = 'authenticated';
        state.role = payload.role;
      })
      .addMatcher(userApi.endpoints.getMe.matchRejected, (state, { payload }) => {
        if (payload?.status === 401) {
          state.status = 'guest';
          state.role = null;
        } else if (state.status === 'unknown') {
          // Сервер недоступен: работаем как гость, прогресс копится локально
          state.status = 'guest';
        }
      });
  },
});

export const session = sessionSlice.actions;

type WithSession = { session: SessionState };
export const selectSession = (s: WithSession) => s.session;
export const selectIsGuest = (s: WithSession) => s.session.status === 'guest';
export const selectIsAdmin = (s: WithSession) => s.session.role === 'admin';
