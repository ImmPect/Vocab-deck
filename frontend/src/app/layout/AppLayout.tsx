/**
 * Оболочка экранов (табл. 4.2 ПР3): на компьютере — боковое меню 232 px,
 * на телефоне — верхняя панель и нижняя панель вкладок в зоне большого пальца.
 * Переключение — чистым CSS по медиа-запросам (отзывчивая вёрстка, mobile-first).
 */
import { Suspense } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { LogoutButton } from '@/features/auth';
import { useLearner } from '@/features/guest-progress-sync';
import { ROUTES } from '@/shared/config';
import { ButtonLink } from '@/shared/ui';
import { OfflineBanner } from '@/widgets/offline-banner';
import { PageErrorBoundary } from '../providers/ErrorBoundary';
import { PageSkeleton } from './ShellSkeleton';
import { ToastHost } from './ToastHost';
import s from './AppLayout.module.css';

interface NavItem {
  to: string;
  icon: string;
  label: string;
  badge?: number;
}

export function AppLayout() {
  const learner = useLearner();
  const { pathname } = useLocation();
  const isGuest = learner.kind === 'guest';
  const items: NavItem[] = [
    { to: ROUTES.home, icon: '🗂', label: 'Кабинет' },
    { to: ROUTES.inbox, icon: '📥', label: 'Входящие', badge: learner.inboxCount || undefined },
    { to: ROUTES.profile, icon: '🪪', label: 'Профиль' },
  ];
  if (learner.isAdmin) items.push({ to: ROUTES.adminWords, icon: '🛠', label: 'Слова' });

  const link = (it: NavItem, cls: string) => (
    <NavLink key={it.to} to={it.to} className={cls}>
      <span className={s.ico} aria-hidden="true">{it.icon}</span>
      <span>{it.label}</span>
      {it.badge ? (
        <span className={s.badge}>
          {it.badge}
          <span className="sr-only"> слов к повторению</span>
        </span>
      ) : null}
    </NavLink>
  );

  return (
    <div className={s.shell}>
      <a href="#main" className="skip-link">Перейти к содержимому</a>

      <nav className={s.side} aria-label="Основное меню">
        <div className={s.brand}>Vocab Deck</div>
        {items.map((it) => link(it, s.navBtn))}
        <div className={s.foot}>
          {isGuest ? (
            <>
              <p>Вы гость. Прогресс хранится только на этом устройстве.</p>
              <ButtonLink to={ROUTES.register} variant="primary" size="small" block>Сохранить прогресс</ButtonLink>
              <ButtonLink to={ROUTES.login} variant="linkLight" size="small">Войти</ButtonLink>
            </>
          ) : (
            learner.kind === 'user' && (
              <>
                <p>
                  {learner.name}
                  <br />
                  {learner.email}
                </p>
                <LogoutButton block />
              </>
            )
          )}
        </div>
      </nav>

      <header className={s.topbar}>
        <span className={s.brand}>Vocab Deck</span>
        {isGuest ? (
          <ButtonLink to={ROUTES.register} variant="primary" size="small">Сохранить</ButtonLink>
        ) : (
          learner.kind === 'user' && <span className={s.streak} aria-label={`Серия ${learner.streakDays} дней`}>🔥 {learner.streakDays}</span>
        )}
      </header>

      <main id="main" className={s.main} tabIndex={-1}>
        <div className={s.content}>
          <OfflineBanner isGuest={isGuest} />
          <PageErrorBoundary resetKey={pathname}>
            <Suspense fallback={<PageSkeleton />}>
              <Outlet />
            </Suspense>
          </PageErrorBoundary>
        </div>
      </main>

      <nav className={s.tabs} aria-label="Основное меню">
        {items.map((it) => link(it, s.tab))}
      </nav>
      <ToastHost />
    </div>
  );
}
