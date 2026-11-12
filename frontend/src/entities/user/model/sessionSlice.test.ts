import { describe, expect, it } from 'vitest';
import { sessionExpired } from '@/shared/api';
import { session, sessionSlice } from './sessionSlice';

describe('slice session', () => {
  it('стартует в статусе unknown — охранники ждут ответа GET /me', () => {
    expect(sessionSlice.reducer(undefined, { type: '@@init' }).status).toBe('unknown');
  });

  it('401 на защищённом запросе: пользователь становится гостем, показывается уведомление', () => {
    let s = sessionSlice.reducer(undefined, session.resolved({ status: 'authenticated', role: 'admin' }));
    s = sessionSlice.reducer(s, sessionExpired());
    expect(s).toEqual({ status: 'guest', role: null, expired: true });
  });

  it('у гостя 401 не вызывает уведомление «сессия завершена»', () => {
    let s = sessionSlice.reducer(undefined, session.resolved({ status: 'guest' }));
    s = sessionSlice.reducer(s, sessionExpired());
    expect(s.expired).toBe(false);
  });
});
