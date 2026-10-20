/** Блок «Входящие на сегодня» в кабинете (табл. 4.2 ПР3, UC-01). */
import { useLearner } from '@/features/guest-progress-sync';
import { ROUTES } from '@/shared/config';
import { WORD_FORMS, countOf } from '@/shared/lib';
import { ButtonLink, Paper, Skeleton } from '@/shared/ui';
import s from './InboxCard.module.css';

export function InboxCard() {
  const l = useLearner();
  if (l.kind === 'loading') return <Skeleton height={130} />;
  const n = l.inboxCount;
  const minutes = Math.max(1, Math.round((n * 12) / 60)); // ~12 с на карточку
  return (
    <Paper as="section" plain className={s.inbox} aria-labelledby="inbox-title">
      <h2 id="inbox-title" className={s.title}>
        📥 Входящие на сегодня
      </h2>
      {n > 0 ? (
        <>
          <p className={s.text}>
            {countOf(n, WORD_FORMS)} пора повторить — около {minutes} мин. Неразобранные слова останутся во входящих.
          </p>
          <ButtonLink to={ROUTES.inbox} variant="primary" block>
            Разобрать входящие
          </ButtonLink>
        </>
      ) : (
        <p className={s.text}>Входящие разобраны. Новые слова придут завтра — а пока сыграйте раунд в любом отделе.</p>
      )}
    </Paper>
  );
}
