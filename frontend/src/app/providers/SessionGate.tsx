/**
 * Старт приложения (поток 4.7.1, шаги 3–4): запрос GET /me с cookie сессии.
 * 200 — пользователь, 401 — гость (штатно, без сообщений). Если сессия завершилась
 * на сервере во время работы — переход на вход с возвратом на текущий адрес (табл. 4.8).
 */
import { useEffect, type ReactNode } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { selectSession, session, useGetMeQuery } from '@/entities/user';
import { ROUTES } from '@/shared/config';
import { ui, useAppDispatch, useAppSelector } from '@/shared/model';

export function SessionGate({ children }: { children: ReactNode }) {
  const { status, expired } = useAppSelector(selectSession);
  // Пока статус неизвестен или пользователь вошёл — подписка на GET /me держит профиль в кэше
  useGetMeQuery(undefined, { skip: status === 'guest' });
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { pathname, search } = useLocation();

  useEffect(() => {
    if (!expired) return;
    dispatch(session.expiredNoticeShown());
    dispatch(ui.toastShown('Сессия завершена, войдите снова', 'info'));
    navigate(`${ROUTES.login}?${new URLSearchParams({ return: pathname + search })}`, { replace: true });
  }, [expired, dispatch, navigate, pathname, search]);

  return <>{children}</>;
}
