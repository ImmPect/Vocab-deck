/**
 * Охранники маршрутов (табл. 4.4 ПР3). Пока статус сессии unknown (ответ GET /me
 * ещё не пришёл), показывается скелетон, а не редирект — иначе вошедший пользователь
 * на долю секунды увидел бы экран входа. Охранники — только удобство: права проверяет сервер.
 */
import { useEffect, type ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { selectSession } from '@/entities/user';
import { ROUTES } from '@/shared/config';
import { ui, useAppDispatch, useAppSelector } from '@/shared/model';
import { ShellSkeleton } from '../layout/ShellSkeleton';

const returnParam = (pathname: string, search: string) => `?${new URLSearchParams({ return: pathname + search })}`;

export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAppSelector(selectSession);
  const { pathname, search } = useLocation();
  if (status === 'unknown') return <ShellSkeleton />;
  if (status !== 'authenticated') return <Navigate to={ROUTES.register + returnParam(pathname, search)} replace />;
  return <>{children}</>;
}

export function RequireAdmin({ children }: { children: ReactNode }) {
  const { status, role } = useAppSelector(selectSession);
  const { pathname, search } = useLocation();
  const dispatch = useAppDispatch();
  const denied = status === 'authenticated' && role !== 'admin';
  useEffect(() => {
    if (denied) dispatch(ui.toastShown('Недостаточно прав', 'error'));
  }, [denied, dispatch]);
  if (status === 'unknown') return <ShellSkeleton />;
  if (status !== 'authenticated') return <Navigate to={ROUTES.login + returnParam(pathname, search)} replace />;
  if (denied) return <Navigate to={ROUTES.home} replace />;
  return <>{children}</>;
}

export function GuestOnly({ children }: { children: ReactNode }) {
  const { status } = useAppSelector(selectSession);
  if (status === 'unknown') return <ShellSkeleton bare />;
  if (status === 'authenticated') return <Navigate to={ROUTES.home} replace />;
  return <>{children}</>;
}
