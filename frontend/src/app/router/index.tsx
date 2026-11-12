/**
 * Дерево маршрутов (табл. 4.4 ПР3). Каждая страница — отдельный чанк (React.lazy);
 * страница администратора скачивается только при роли admin (раздел 4.1.3).
 */
import { lazy, Suspense, type ReactNode } from 'react';
import { createBrowserRouter, Outlet } from 'react-router-dom';
import { registerPrefetch } from '@/shared/config';
import { AppLayout } from '../layout/AppLayout';
import { ShellSkeleton } from '../layout/ShellSkeleton';
import { PageErrorBoundary } from '../providers/ErrorBoundary';
import { SessionGate } from '../providers/SessionGate';
import { GuestOnly, RequireAdmin, RequireAuth } from './guards';

const load = {
  welcome: () => import('@/pages/welcome'),
  home: () => import('@/pages/home'),
  cards: () => import('@/pages/cards'),
  deadline: () => import('@/pages/deadline'),
  result: () => import('@/pages/round-result'),
  inbox: () => import('@/pages/inbox'),
  profile: () => import('@/pages/profile'),
  list: () => import('@/pages/my-list'),
  auth: () => import('@/pages/auth'),
  admin: () => import('@/pages/admin-words'),
  notFound: () => import('@/pages/not-found'),
};
// Предзагрузка вероятного следующего экрана — по наведению на «Дедлайн»
registerPrefetch('deadline', load.deadline);

const WelcomePage = lazy(load.welcome);
const HomePage = lazy(load.home);
const CardsPage = lazy(load.cards);
const DeadlinePage = lazy(load.deadline);
const RoundResultPage = lazy(load.result);
const InboxPage = lazy(load.inbox);
const ProfilePage = lazy(load.profile);
const MyListPage = lazy(load.list);
const AuthPage = lazy(load.auth);
const AdminWordsPage = lazy(load.admin);
const AdminWordModalRoute = lazy(() => load.admin().then((m) => ({ default: m.AdminWordModalRoute })));
const NotFoundPage = lazy(load.notFound);

/** Экраны без оболочки (приветствие, вход): своя граница ошибок и скелетон. */
const bare = (node: ReactNode) => (
  <PageErrorBoundary>
    <Suspense fallback={<ShellSkeleton bare />}>{node}</Suspense>
  </PageErrorBoundary>
);

export const router = createBrowserRouter(
  [
    {
      element: (
        <SessionGate>
          <Outlet />
        </SessionGate>
      ),
      children: [
        { path: '/', element: bare(<WelcomePage />) },
        { path: '/login', element: bare(<GuestOnly><AuthPage tab="login" /></GuestOnly>) },
        { path: '/register', element: bare(<GuestOnly><AuthPage tab="register" /></GuestOnly>) },
        {
          element: <AppLayout />,
          children: [
            { path: '/home', element: <HomePage /> },
            { path: '/decks/:deckId/cards', element: <CardsPage /> },
            { path: '/decks/:deckId/deadline', element: <DeadlinePage /> },
            { path: '/rounds/:roundId/result', element: <RoundResultPage /> },
            { path: '/inbox', element: <InboxPage /> },
            { path: '/profile', element: <ProfilePage /> },
            { path: '/lists/:deckId', element: <RequireAuth><MyListPage /></RequireAuth> },
            {
              path: '/admin/words',
              element: <RequireAdmin><AdminWordsPage /></RequireAdmin>,
              children: [
                { path: 'new', element: <AdminWordModalRoute /> },
                { path: ':wordId', element: <AdminWordModalRoute /> },
              ],
            },
            { path: '*', element: <NotFoundPage /> },
          ],
        },
      ],
    },
  ],
  { basename: import.meta.env.BASE_URL.replace(/\/$/, '') || '/' },
);
