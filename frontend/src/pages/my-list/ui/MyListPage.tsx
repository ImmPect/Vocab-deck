/**
 * Личный список слов: просмотр, добавление, изменение, удаление, импорт CSV (E6, US-10).
 * Чужой список — ответ 403/404 и сообщение «Нет доступа» (табл. 4.4).
 */
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useGetDeckQuery } from '@/entities/deck';
import { useGetDeckWordsQuery, type Word } from '@/entities/word';
import { ImportCsvForm } from '@/features/import-csv';
import { DeleteListModal, DeleteWordModal, PersonalWordModal, RenameListModal } from '@/features/manage-list';
import { SpeakButton } from '@/features/speak-word';
import { asApiError } from '@/shared/api';
import { ROUND, ROUTES } from '@/shared/config';
import { WORD_FORMS, countOf } from '@/shared/lib';
import { ui, useAppDispatch } from '@/shared/model';
import { Button, ButtonLink, EmptyState, ErrorBlock, PageHeader, Paper, Skeleton } from '@/shared/ui';
import s from './MyListPage.module.css';

type Dialog = { kind: 'add' } | { kind: 'edit'; word: Word } | { kind: 'delete'; word: Word } | { kind: 'rename' } | { kind: 'deleteList' } | null;

export default function MyListPage() {
  const deckId = Number(useParams().deckId);
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const deck = useGetDeckQuery(deckId);
  const words = useGetDeckWordsQuery({ deckId, limit: 100 }, { skip: !deck.data });
  const [dialog, setDialog] = useState<Dialog>(null);
  const close = () => setDialog(null);
  const done = (text: string) => {
    close();
    dispatch(ui.toastShown(text));
  };

  const err = asApiError(deck.error);
  if (err && (err.status === 403 || err.status === 404)) {
    return (
      <>
        <PageHeader title="Нет доступа" />
        <EmptyState icon="🔒" actions={<ButtonLink to={ROUTES.home} variant="outline" size="small">В кабинет</ButtonLink>}>
          Список не найден или принадлежит другому пользователю
        </EmptyState>
      </>
    );
  }
  if (deck.isLoading) return <Skeleton height={300} />;
  if (deck.error || !deck.data) return <ErrorBlock message={err?.message ?? 'Не удалось загрузить список'} onRetry={deck.refetch} />;

  const d = deck.data;
  const list = words.data?.items ?? [];
  return (
    <>
      <PageHeader title={d.title} lead={`Личный список · ${countOf(d.words_count, WORD_FORMS)}`}>
        <div className={s.head}>
          <ButtonLink to={ROUTES.cards(d.id)} variant="outline" size="small">Карточки</ButtonLink>
          {d.words_count >= ROUND.minWords && <ButtonLink to={ROUTES.deadline(d.id)} variant="game" size="small">Дедлайн</ButtonLink>}
          <Button variant="linkLight" size="small" onClick={() => setDialog({ kind: 'rename' })}>Переименовать</Button>
          <Button variant="linkLight" size="small" onClick={() => setDialog({ kind: 'deleteList' })}>Удалить список</Button>
        </div>
      </PageHeader>

      <div className={s.grid}>
        <section aria-labelledby="words-title">
          <div className={s.bar}>
            <h2 id="words-title" className={s.h}>Слова</h2>
            <Button size="small" onClick={() => setDialog({ kind: 'add' })}>+ Добавить слово</Button>
          </div>
          {words.isLoading && <Skeleton height={200} />}
          {words.error && <ErrorBlock message="Не удалось загрузить слова" onRetry={words.refetch} />}
          {words.data && !list.length && (
            <EmptyState icon="🗒" actions={<Button size="small" onClick={() => setDialog({ kind: 'add' })}>Добавить слово</Button>}>
              В списке пока нет слов. Добавьте их вручную или импортируйте CSV
            </EmptyState>
          )}
          {list.length > 0 && (
            <ul className={s.words}>
              {list.map((w) => (
                <Paper as="li" plain key={w.id} className={s.word}>
                  <div className={s.main}>
                    <span className={s.en} lang="en">{w.en}</span>
                    {w.ipa && <span className={s.ipa}>{w.ipa}</span>}
                    <span className={s.ru}>{w.ru}</span>
                    {w.example && <span className={s.ex} lang="en">{w.example}</span>}
                  </div>
                  <div className={s.acts}>
                    <SpeakButton text={w.en} />
                    <Button variant="link" size="small" onClick={() => setDialog({ kind: 'edit', word: w })} aria-label={`Изменить «${w.en}»`}>Изменить</Button>
                    <Button variant="link" size="small" className={s.del} onClick={() => setDialog({ kind: 'delete', word: w })} aria-label={`Удалить «${w.en}»`}>Удалить</Button>
                  </div>
                </Paper>
              ))}
            </ul>
          )}
        </section>
        <Paper as="section" plain className={s.import}>
          <ImportCsvForm deckId={d.id} onDone={(r) => r.added && dispatch(ui.toastShown(`Импортировано: ${countOf(r.added, WORD_FORMS)}`))} />
        </Paper>
      </div>

      {dialog?.kind === 'add' && <PersonalWordModal deckId={d.id} onClose={close} onSaved={done} />}
      {dialog?.kind === 'edit' && <PersonalWordModal deckId={d.id} word={dialog.word} onClose={close} onSaved={done} />}
      {dialog?.kind === 'delete' && <DeleteWordModal deckId={d.id} word={dialog.word} onClose={close} onDeleted={() => done('Слово удалено')} />}
      {dialog?.kind === 'rename' && <RenameListModal deck={d} onClose={close} onDone={() => done('Список переименован')} />}
      {dialog?.kind === 'deleteList' && (
        <DeleteListModal deck={d} onClose={close} onDeleted={() => { close(); dispatch(ui.toastShown('Список удалён')); navigate(ROUTES.home); }} />
      )}
    </>
  );
}
