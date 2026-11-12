/** Полученные и доступные достижения с прогрессом (US-11). */
import { useGetAchievementsQuery } from '@/entities/user';
import { ErrorBlock, Paper, ProgressBar, Skeleton } from '@/shared/ui';
import s from './AchievementsList.module.css';

const ICON: Record<string, string> = { first_round: '💼', streak_7: '📅', words_10: '📁', words_100: '🗄', director: '🏆' };

export function AchievementsList() {
  const { data, isLoading, error, refetch } = useGetAchievementsQuery();
  return (
    <Paper as="section" plain className={s.panel} aria-labelledby="ach-title">
      <h2 id="ach-title" className={s.h}>
        Достижения
      </h2>
      {isLoading && <Skeleton height={120} />}
      {error && <ErrorBlock message="Не удалось загрузить достижения" onRetry={refetch} />}
      {data && (
        <ul className={s.ach}>
          {data.earned.map((a) => (
            <li key={a.code}>
              <b aria-hidden="true">{ICON[a.code] ?? '🏅'}</b>
              {a.title}
              <span className="sr-only"> — получено</span>
            </li>
          ))}
          {data.available.map((a) => (
            <li key={a.code} className={s.off}>
              <b aria-hidden="true">{ICON[a.code] ?? '🏅'}</b>
              {a.title}
              {a.progress && (
                <ProgressBar
                  value={a.progress.current}
                  max={a.progress.target}
                  label={`${a.title}: ${a.progress.current} из ${a.progress.target}`}
                  tone="sage"
                  thin
                  className={s.bar}
                />
              )}
            </li>
          ))}
        </ul>
      )}
    </Paper>
  );
}
