/** Карьерная лестница (табл. 4 ТЗ): пройденные должности, текущая и следующие. */
import { useGetLevelsQuery } from '@/entities/user';
import { useLearner } from '@/features/guest-progress-sync';
import { ErrorBlock, Paper, Skeleton } from '@/shared/ui';
import s from './CareerLadder.module.css';

export function CareerLadder() {
  const { data: levels, isLoading, refetch, error } = useGetLevelsQuery();
  const learner = useLearner();
  return (
    <Paper as="section" plain className={s.panel} aria-labelledby="ladder-title">
      <h2 id="ladder-title" className={s.h}>
        Карьерная лестница
      </h2>
      {isLoading && <Skeleton height={260} />}
      {error && <ErrorBlock message="Не удалось загрузить должности" onRetry={refetch} />}
      {levels && (
        <ol className={s.ladder}>
          {[...levels]
            .sort((a, b) => b.min_xp - a.min_xp)
            .map((l) => {
              const now = l.title === learner.levelTitle;
              const done = !now && learner.xp >= l.min_xp;
              return (
                <li key={l.code} className={`${s.rung} ${now ? s.now : done ? s.done : ''}`} aria-current={now ? 'step' : undefined}>
                  <div className={s.main}>
                    <span className={s.title}>
                      {done && <span aria-label="пройдено">✓ </span>}
                      {now && <span aria-hidden="true">● </span>}
                      {l.title}
                    </span>
                    <span className={s.pts}>{l.min_xp} опыта</span>
                  </div>
                  {l.unlocks.length > 0 && <div className={s.unlocks}>{l.unlocks.join('; ')}</div>}
                </li>
              );
            })}
        </ol>
      )}
    </Paper>
  );
}
