/**
 * Проверенные слова по дням недели (US-11). Свой компонент на CSS без библиотеки
 * графиков (бюджет NFR-P-04); у каждого столбца есть текст для экранного диктора.
 */
import { useGetStatsQuery } from '@/entities/user';
import { ROUTES } from '@/shared/config';
import { ANSWER_FORMS, addDays, countOf, localIsoDate, longDate, shortWeekday } from '@/shared/lib';
import { ButtonLink, EmptyState, ErrorBlock, Paper, Skeleton } from '@/shared/ui';
import s from './ActivityChart.module.css';

export function ActivityChart() {
  const to = localIsoDate();
  const from = addDays(to, -6);
  const { data, isLoading, error, refetch } = useGetStatsQuery({ from, to });

  return (
    <Paper as="section" plain className={s.panel} aria-labelledby="week-title">
      <h2 id="week-title" className={s.h}>
        Проверено слов за неделю
      </h2>
      {isLoading && <Skeleton height={150} />}
      {error && <ErrorBlock message="Не удалось загрузить статистику" onRetry={refetch} />}
      {data &&
        (data.totals.answers === 0 ? (
          <EmptyState actions={<ButtonLink to={ROUTES.home} variant="outlinePaper" size="small">В кабинет</ButtonLink>}>
            <span className={s.emptyText}>На этой неделе ответов пока нет. Сыграйте раунд, чтобы начать серию</span>
          </EmptyState>
        ) : (
          <>
            <ul className={s.week}>
              {data.days.map((d) => {
                const max = Math.max(...data.days.map((x) => x.answers), 1);
                return (
                  <li key={d.date} aria-label={`${longDate(d.date)}: ${countOf(d.answers, ANSWER_FORMS)}, верных ${d.correct}`}>
                    <span className={s.val} aria-hidden="true">{d.answers || ''}</span>
                    <i style={{ height: `${Math.max(3, (d.answers / max) * 100)}%` }} className={d.answers ? '' : s.zero} />
                    <span aria-hidden="true">{shortWeekday(d.date)}</span>
                  </li>
                );
              })}
            </ul>
            <p className={s.totals}>
              Ответов: <b>{data.totals.answers}</b> · верных: <b>{data.totals.correct}</b> · опыта: <b>{data.totals.xp}</b> · выучено
              слов: <b>{data.totals.learned_words}</b>
            </p>
          </>
        ))}
    </Paper>
  );
}
