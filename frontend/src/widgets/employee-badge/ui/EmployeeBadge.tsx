/**
 * Пропуск сотрудника — главный элемент кабинета (табл. 4.2 ПР3): должность,
 * шкала опыта до следующей должности, серия дней и заморозки. Гостю — «пропуск временный».
 */
import { useLearner } from '@/features/guest-progress-sync';
import { initialOf } from '@/entities/user';
import { DAY_FORMS, countOf } from '@/shared/lib';
import { Paper, ProgressBar, Skeleton } from '@/shared/ui';
import s from './EmployeeBadge.module.css';

export function EmployeeBadge() {
  const l = useLearner();
  if (l.kind === 'loading') return <Skeleton height={196} />;

  const from = l.levelMinXp;
  const to = l.next ? l.next.min_xp : l.xp;
  return (
    <Paper as="section" className={s.badge} aria-label="Пропуск сотрудника">
      <span className={s.clip} aria-hidden="true" />
      <div className={s.who}>
        <span className={s.photo} aria-hidden="true">
          {l.kind === 'guest' ? '?' : initialOf(l.name)}
        </span>
        <div>
          <div className={s.role}>{l.levelTitle}</div>
          <div className={s.name}>{l.kind === 'guest' ? 'Гость · пропуск временный' : l.name}</div>
        </div>
      </div>
      <div className={s.xpRow}>
        <span>{l.xp} опыта</span>
        <span>{l.next ? `до «${l.next.title}» — ${l.next.xp_left}` : 'Высшая должность'}</span>
      </div>
      <ProgressBar value={l.xp - from} max={Math.max(1, to - from)} label="Опыт до следующей должности" />
      <div className={s.streak}>
        <span aria-hidden="true">🔥</span>
        <span>
          Серия: <b>{countOf(l.streakDays, DAY_FORMS)}</b>
        </span>
        {l.kind === 'user' && l.freezes > 0 && (
          <span className={s.freeze} title="Заморозка сохраняет серию за пропущенный день">
            ❄ {l.freezes}
          </span>
        )}
      </div>
    </Paper>
  );
}
