/**
 * Вход и регистрация — две вкладки одного экрана (табл. 4.2, поток 4.7.4 ПР3).
 * Страница соединяет фичи: формы (auth), журнал гостя (guest-progress-sync) и очередь (offline-outbox).
 * Журнал удаляется только ПОСЛЕ успешного ответа сервера — сбой не уничтожает прогресс.
 */
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { LoginForm, RegisterForm, type AuthResult, type GuestCarry } from '@/features/auth';
import { guestProgress, selectGuestEvents, selectGuestProjection, toGuestProgressPayload } from '@/features/guest-progress-sync';
import { flushOutbox } from '@/features/offline-outbox';
import { ROUTES } from '@/shared/config';
import { DAY_FORMS, WORD_FORMS, countOf } from '@/shared/lib';
import { ui, useAppDispatch, useAppSelector, type RootState } from '@/shared/model';
import { PageHeader, Paper } from '@/shared/ui';
import { useStore } from 'react-redux';
import s from './AuthPage.module.css';

/** Возврат только на внутренние пути приложения (защита от открытого редиректа). */
function safeReturn(value: string | null): string {
  return value && value.startsWith('/') && !value.startsWith('//') ? value : ROUTES.home;
}

export default function AuthPage({ tab }: { tab: 'login' | 'register' }) {
  const dispatch = useAppDispatch();
  const store = useStore<RootState>();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const events = useAppSelector(selectGuestEvents);
  const p = useAppSelector(selectGuestProjection);
  const returnTo = safeReturn(params.get('return'));

  const carry: GuestCarry | undefined = events.length
    ? {
        summary: `${countOf(p.wordsCount, WORD_FORMS)}, ${p.xp} опыта, серия ${countOf(p.streakDays, DAY_FORMS)}`,
        // Читается в момент отправки: после flushOutbox в журнале появятся новые квитанции
        payload: () => toGuestProgressPayload(selectGuestEvents(store.getState())),
      }
    : undefined;

  const beforeSubmit = () => dispatch(flushOutbox());

  function onSuccess(res: AuthResult, carried: boolean) {
    // Журнал очищается и при отказе от переноса: на устройстве не остаётся «ничейного» прогресса (UC-03 3а)
    dispatch(guestProgress.cleared());
    let text = tab === 'register' ? 'Аккаунт создан' : `С возвращением, ${res.user.name}`;
    if (carried && res.imported) {
      text += res.imported.accepted ? ', прогресс перенесён' : '';
      if (res.imported.rejected) text += `. Не перенесено событий: ${res.imported.rejected}`;
    }
    dispatch(ui.toastShown(text));
    navigate(returnTo, { replace: true });
  }

  const isLogin = tab === 'login';
  return (
    <main id="main" className={s.auth}>
      <Paper className={s.card}>
        <PageHeader
          title={isLogin ? 'Вход' : 'Регистрация'}
          lead={
            isLogin
              ? 'Войдите, чтобы продолжить с того места, где остановились, на любом устройстве.'
              : 'Аккаунт сохранит опыт и должность на сервере. Прогресс гостя можно перенести.'
          }
        />
        <div className={s.tabs} role="tablist" aria-label="Вход или регистрация">
          <Link role="tab" aria-selected={isLogin} className={isLogin ? s.on : ''} to={{ pathname: ROUTES.login, search: params.toString() }} replace>
            Вход
          </Link>
          <Link role="tab" aria-selected={!isLogin} className={!isLogin ? s.on : ''} to={{ pathname: ROUTES.register, search: params.toString() }} replace>
            Регистрация
          </Link>
        </div>
        {isLogin ? (
          <LoginForm key="login" carry={carry} beforeSubmit={beforeSubmit} onSuccess={onSuccess} initialEmail={params.get('email') ?? ''} />
        ) : (
          <RegisterForm
            key="register"
            carry={carry}
            beforeSubmit={beforeSubmit}
            onSuccess={onSuccess}
            onEmailTaken={(email) => navigate(`${ROUTES.login}?${new URLSearchParams({ ...Object.fromEntries(params), email })}`, { replace: true })}
          />
        )}
        <Link to={ROUTES.home} className={s.back}>
          ← Продолжить без входа
        </Link>
      </Paper>
    </main>
  );
}
