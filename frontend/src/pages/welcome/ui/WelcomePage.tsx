/**
 * Приветствие: польза одной фразой и старт без регистрации — одно действие до кабинета
 * (NFR-O-01). API не вызывает. Активная сессия или прогресс гостя — сразу в кабинет.
 */
import { useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import { selectSession } from '@/entities/user';
import { selectHasGuestProgress } from '@/features/guest-progress-sync';
import { ROUTES } from '@/shared/config';
import { useAppSelector } from '@/shared/model';
import { ButtonLink, Paper } from '@/shared/ui';
import s from './WelcomePage.module.css';

export default function WelcomePage() {
  const session = useAppSelector(selectSession);
  const hasGuest = useAppSelector(selectHasGuestProgress);
  useEffect(() => {
    document.title = 'Vocab Deck — деловой английский по карьерной лестнице';
  }, []);

  if (session.status === 'authenticated' || hasGuest) return <Navigate to={ROUTES.home} replace />;

  return (
    <main className={s.welcome} id="main">
      <div className={s.stack} aria-hidden="true">
        <Paper className={s.card} />
        <Paper className={s.card} />
        <Paper className={s.card}>
          <span className={s.word}>deadline</span>
          <span className={s.ru}>крайний срок</span>
        </Paper>
      </div>
      <h1 className={s.h}>Vocab Deck</h1>
      <p className={s.p}>
        Деловой английский A2–B1 за 5 минут в день. Учите слова офиса и переговоров, играйте раунды на время и
        поднимайтесь по карьерной лестнице — от стажёра до директора.
      </p>
      <div className={s.actions}>
        <ButtonLink to={ROUTES.home} variant="primary" block>
          Начать без регистрации
        </ButtonLink>
        <ButtonLink to={ROUTES.login} variant="outline" block>
          У меня есть аккаунт
        </ButtonLink>
      </div>
    </main>
  );
}
