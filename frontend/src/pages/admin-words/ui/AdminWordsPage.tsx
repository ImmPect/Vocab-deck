/**
 * Управление словами общей колоды (E7). Загружается отдельным чанком только для роли admin.
 * «Добавить» и «Изменить» открывают окно по вложенному маршруту — «Назад» в браузере его закрывает.
 */
import { Outlet, useLocation, useNavigate, useParams } from 'react-router-dom';
import { useGetDecksQuery } from '@/entities/deck';
import { useGetAdminWordsQuery } from '@/entities/word';
import { WordEditModal } from '@/features/edit-word';
import { WordFilters, useWordFilter } from '@/features/filter-words';
import { ROUTES } from '@/shared/config';
import { ui, useAppDispatch } from '@/shared/model';
import { ButtonLink, Modal, Button, PageHeader } from '@/shared/ui';
import { AdminWordTable } from '@/widgets/admin-word-table';
import s from './AdminWordsPage.module.css';

export default function AdminWordsPage() {
  const { data: decks = [] } = useGetDecksQuery();
  const { search } = useLocation();
  return (
    <>
      <PageHeader title="Слова" lead="Общая колода: черновики видны только администраторам, опубликованные — всем.">
        <div className={s.head}>
          <ButtonLink to={{ pathname: ROUTES.adminWordNew, search }} variant="primary" size="small">
            + Добавить слово
          </ButtonLink>
        </div>
      </PageHeader>
      <WordFilters decks={decks} />
      <AdminWordTable />
      <Outlet />
    </>
  );
}

/** Вложенный маршрут /admin/words/new и /admin/words/:wordId — окно поверх списка. */
export function AdminWordModalRoute() {
  const { wordId } = useParams();
  const { search } = useLocation();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const filter = useWordFilter();
  const { data: decks = [] } = useGetDecksQuery();
  const { data, isFetching } = useGetAdminWordsQuery(filter, { skip: !wordId });
  const close = () => navigate({ pathname: ROUTES.adminWords, search });
  const word = wordId ? data?.items.find((w) => w.id === Number(wordId)) : undefined;

  if (wordId && !word) {
    if (isFetching) return null;
    return (
      <Modal title="Слово не найдено" onClose={close} actions={<Button onClick={close}>Закрыть</Button>}>
        <p>Слова нет в текущей выборке. Измените поиск или фильтры.</p>
      </Modal>
    );
  }
  return (
    <WordEditModal
      key={wordId ?? 'new'}
      word={word}
      decks={decks}
      onClose={close}
      onSaved={(text) => {
        dispatch(ui.toastShown(text));
        close();
      }}
      // UC-04 4в: слово уже есть — открыть существующую запись; поиск по слову гарантирует, что она в выборке
      onOpenExisting={(id, en) => navigate({ pathname: ROUTES.adminWord(id), search: `?${new URLSearchParams({ q: en })}` })}
    />
  );
}
