/**
 * Плитки отделов и личных списков (табл. 4.2 ПР3). Открытая плитка — прогресс и кнопки
 * «Карточки» / «Дедлайн»; закрытая — замок и условие открытия (NFR-O-04).
 * Для гостя признак locked вычисляется по unlock_rule и локальному опыту.
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { isLockedFor, useGetDecksQuery, type Deck } from '@/entities/deck';
import { selectGuestLearnedByDeck, useLearner } from '@/features/guest-progress-sync';
import { CreateListModal } from '@/features/manage-list';
import { asApiError } from '@/shared/api';
import { ROUND, ROUTES } from '@/shared/config';
import { WORD_FORMS, countOf, useDelayedFlag } from '@/shared/lib';
import { useAppSelector } from '@/shared/model';
import { Button, ButtonLink, EmptyState, ErrorBlock, Paper, ProgressBar, Skeleton } from '@/shared/ui';
import s from './DeptGrid.module.css';

function DeptTile({ deck, locked, onPrefetchGame }: { deck: Deck; locked: boolean; onPrefetchGame?: () => void }) {
  const learned = deck.progress?.learned ?? 0;
  const tooFew = deck.words_count < ROUND.minWords;
  if (locked) {
    return (
      <li className={`${s.dept} ${s.locked}`}>
        <div className={s.top}>
          <span className={s.title}>
            <span aria-hidden="true">🔒 </span>
            {deck.title}
          </span>
          <span className={s.count}>{countOf(deck.words_count, WORD_FORMS)}</span>
        </div>
        <p className={s.why}>{deck.unlock_condition ?? 'Отдел пока закрыт'}</p>
      </li>
    );
  }
  return (
    <Paper as="li" className={s.dept}>
      <div className={s.top}>
        <span className={s.title}>{deck.title}</span>
        <span className={s.count}>
          {deck.progress ? `изучено ${learned} из ${deck.words_count}` : countOf(deck.words_count, WORD_FORMS)}
        </span>
      </div>
      <ProgressBar value={learned} max={Math.max(1, deck.words_count)} label={`Изучено слов в отделе «${deck.title}»`} tone="sage" thin />
      <div className={s.row}>
        <ButtonLink to={ROUTES.cards(deck.id)} variant="outlinePaper" size="small">
          Карточки
        </ButtonLink>
        {tooFew ? (
          <Button variant="game" size="small" disabled title="Для раунда нужно не меньше 4 слов">
            Дедлайн
          </Button>
        ) : (
          <ButtonLink to={ROUTES.deadline(deck.id)} variant="game" size="small" onMouseEnter={onPrefetchGame} onFocus={onPrefetchGame}>
            Дедлайн
          </ButtonLink>
        )}
      </div>
      {tooFew && <p className={s.note}>Для раунда нужно не меньше 4 слов</p>}
      {deck.kind === 'personal' && (
        <ButtonLink to={ROUTES.list(deck.id)} variant="link" size="small" className={s.manage}>
          Слова списка
        </ButtonLink>
      )}
    </Paper>
  );
}

export function DeptGrid({ onPrefetchGame }: { onPrefetchGame?: () => void }) {
  const { data, isLoading, error, refetch } = useGetDecksQuery();
  const learner = useLearner();
  const learnedByDeck = useAppSelector(selectGuestLearnedByDeck);
  const showSkeleton = useDelayedFlag(isLoading);
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <section className={s.depts} aria-busy="true">
        <h2 className={s.h}>Отделы</h2>
        {showSkeleton && (
          <div className={s.list}>
            {[0, 1, 2, 3].map((i) => <Skeleton key={i} height={132} />)}
          </div>
        )}
      </section>
    );
  }
  if (error || !data) {
    return (
      <section className={s.depts}>
        <h2 className={s.h}>Отделы</h2>
        <ErrorBlock message={`Не удалось загрузить отделы. ${asApiError(error)?.message ?? ''}`} onRetry={refetch} />
      </section>
    );
  }

  const guestLocal = learner.kind === 'guest' ? { xp: learner.xp, learnedInDeck: learnedByDeck } : null;
  const shared = data.filter((d) => d.kind === 'shared');
  const personal = data.filter((d) => d.kind === 'personal');

  return (
    <>
      <section className={s.depts} aria-labelledby="depts-title">
        <h2 id="depts-title" className={s.h}>
          Отделы
        </h2>
        <ul className={s.list}>
          {shared.map((d) => (
            <DeptTile key={d.id} deck={d} locked={isLockedFor(d, guestLocal)} onPrefetchGame={onPrefetchGame} />
          ))}
        </ul>
      </section>

      {learner.kind === 'user' && (
        <section className={s.depts} aria-labelledby="lists-title">
          <div className={s.headRow}>
            <h2 id="lists-title" className={s.h}>
              Мои списки
            </h2>
            <Button variant="outline" size="small" onClick={() => setCreating(true)}>
              + Создать список
            </Button>
          </div>
          {personal.length ? (
            <ul className={s.list}>
              {personal.map((d) => (
                <DeptTile key={d.id} deck={d} locked={false} onPrefetchGame={onPrefetchGame} />
              ))}
            </ul>
          ) : (
            <EmptyState icon="🗒">У вас пока нет своих списков. Добавьте слова из рабочих документов</EmptyState>
          )}
        </section>
      )}
      {creating && (
        <CreateListModal onClose={() => setCreating(false)} onCreated={(deck) => navigate(ROUTES.list(deck.id))} />
      )}
    </>
  );
}
