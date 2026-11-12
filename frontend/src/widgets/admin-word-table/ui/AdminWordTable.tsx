/**
 * Слова общей колоды: таблица на компьютере, карточки на телефоне (табл. 4.2, раздел 4.9 ПР3).
 * Фильтры и страница — в адресе; «Изменить» открывает окно по вложенному маршруту.
 */
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { STATUS_LABEL, useGetAdminWordsQuery } from '@/entities/word';
import { useWordFilter } from '@/features/filter-words';
import { asApiError } from '@/shared/api';
import { ROUTES } from '@/shared/config';
import { useDelayedFlag, useIsMobile } from '@/shared/lib';
import { Button, ButtonLink, Chip, EmptyState, ErrorBlock, Paper, Skeleton } from '@/shared/ui';
import s from './AdminWordTable.module.css';

export function AdminWordTable() {
  const filter = useWordFilter();
  const { data, isLoading, isFetching, error, refetch } = useGetAdminWordsQuery(filter);
  const isMobile = useIsMobile();
  const { search } = useLocation();
  const [, setParams] = useSearchParams();
  const showSkeleton = useDelayedFlag(isLoading);

  if (isLoading) return showSkeleton ? <Skeleton height={320} /> : null;
  if (error || !data) return <ErrorBlock message={asApiError(error)?.message ?? 'Не удалось загрузить слова'} onRetry={refetch} />;
  if (!data.items.length) {
    return (
      <EmptyState icon="🔍" actions={<ButtonLink to={{ pathname: ROUTES.adminWordNew, search }} variant="primary" size="small">Добавить слово</ButtonLink>}>
        Ничего не найдено. Измените запрос или добавьте слово
      </EmptyState>
    );
  }

  const page = filter.page ?? 1;
  const pages = Math.max(1, Math.ceil(data.meta.total_items / (filter.limit ?? 20)));
  const goPage = (p: number) =>
    setParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set('page', String(p));
      return next;
    });
  const editLink = (id: number) => ({ pathname: ROUTES.adminWord(id), search });

  return (
    <div aria-busy={isFetching}>
      {isMobile ? (
        <ul className={s.cards}>
          {data.items.map((w) => (
            <Paper as="li" plain key={w.id} className={s.card}>
              <div className={s.l1}>
                <span className={s.en} lang="en">{w.en}</span>
                <Chip tone={w.status}>{STATUS_LABEL[w.status]}</Chip>
              </div>
              <div className={s.ru}>{w.ru}</div>
              <div className={s.l2}>
                <span className={s.dept}>{w.deck.title}</span>
                <Link to={editLink(w.id)} className={s.link}>Изменить</Link>
              </div>
            </Paper>
          ))}
        </ul>
      ) : (
        <div className={s.wrap}>
          <table className={s.table}>
            <thead>
              <tr>
                <th scope="col">Слово</th>
                <th scope="col">Перевод</th>
                <th scope="col">Пример</th>
                <th scope="col">Отдел</th>
                <th scope="col">Статус</th>
                <th scope="col"><span className="sr-only">Действия</span></th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((w) => (
                <tr key={w.id}>
                  <td>
                    <b lang="en">{w.en}</b>
                    {w.ipa && <div className={s.ipa}>{w.ipa}</div>}
                  </td>
                  <td>{w.ru}</td>
                  <td className={s.ex} lang="en">{w.example}</td>
                  <td>{w.deck.title}</td>
                  <td><Chip tone={w.status}>{STATUS_LABEL[w.status]}</Chip></td>
                  <td><Link to={editLink(w.id)} className={s.link} aria-label={`Изменить «${w.en}»`}>Изменить</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <nav className={s.pager} aria-label="Страницы">
        <span>
          Всего: {data.meta.total_items} · страница {page} из {pages}
        </span>
        <Button variant="outline" size="small" disabled={page <= 1} onClick={() => goPage(page - 1)}>← Назад</Button>
        <Button variant="outline" size="small" disabled={page >= pages} onClick={() => goPage(page + 1)}>Вперёд →</Button>
      </nav>
    </div>
  );
}
