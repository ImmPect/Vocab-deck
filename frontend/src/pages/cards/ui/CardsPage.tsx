/**
 * Карточки отдела — знакомство со словами без очков (табл. 4.2 ПР3).
 * Закрытая колода — в кабинет с уведомлением об условии открытия (табл. 4.4).
 */
import { useEffect, useMemo } from 'react';
import { Navigate, useParams } from 'react-router-dom';
import { isLockedFor, useGetDecksQuery } from '@/entities/deck';
import { useGetDeckWordsQuery } from '@/entities/word';
import { selectGuestLearnedByDeck, useLearner } from '@/features/guest-progress-sync';
import { asApiError } from '@/shared/api';
import { ROUND, ROUTES } from '@/shared/config';
import { useDelayedFlag } from '@/shared/lib';
import { ui, useAppDispatch, useAppSelector } from '@/shared/model';
import { ButtonLink, EmptyState, ErrorBlock, PageHeader, Paper, Skeleton } from '@/shared/ui';
import { ReviewDeck, type ReviewCard } from '@/widgets/review-deck';
import s from './CardsPage.module.css';

export default function CardsPage() {
  const deckId = Number(useParams().deckId);
  const dispatch = useAppDispatch();
  const learner = useLearner();
  const learnedByDeck = useAppSelector(selectGuestLearnedByDeck);
  const decks = useGetDecksQuery();
  const words = useGetDeckWordsQuery({ deckId, limit: 100 }, { skip: !deckId });
  const deck = decks.data?.find((d) => d.id === deckId);
  const locked = deck ? isLockedFor(deck, learner.kind === 'guest' ? { xp: learner.xp, learnedInDeck: learnedByDeck } : null) : false;
  const skeleton = useDelayedFlag(words.isLoading);

  useEffect(() => {
    if (locked && deck) dispatch(ui.toastShown(deck.unlock_condition ?? 'Отдел пока закрыт', 'info'));
  }, [locked, deck, dispatch]);

  const cards = useMemo<ReviewCard[] | undefined>(
    () =>
      words.data?.items.map((w) => ({
        key: `${w.id}`,
        word_id: w.id,
        direction: 'en_ru',
        en: w.en,
        ipa: w.ipa,
        ru: w.ru,
        example: w.example,
        deck_id: deckId,
        deck_title: deck?.title,
      })),
    [words.data, deckId, deck?.title],
  );

  if (locked) return <Navigate to={ROUTES.home} replace />;
  const title = deck ? `Карточки · ${deck.title}` : 'Карточки';

  return (
    <>
      <PageHeader title={title} lead="Нажмите на карточку, чтобы увидеть перевод, и честно оцените себя." />
      {words.isLoading && skeleton && <Skeleton height={400} width={330} style={{ margin: '0 auto' }} />}
      {words.error && <ErrorBlock message={asApiError(words.error)?.message ?? 'Не удалось загрузить слова'} onRetry={words.refetch} />}
      {cards && cards.length === 0 && (
        <EmptyState icon="🗂" actions={<ButtonLink to={ROUTES.home} variant="outline" size="small">В кабинет</ButtonLink>}>
          В отделе пока нет слов
        </EmptyState>
      )}
      {cards && cards.length > 0 && (
        <ReviewDeck
          cards={cards}
          mode="self_check"
          note="Опыт начисляется только в мини-играх; оценки помогают системе повторений"
          renderDone={(st, restart) => (
            <Paper className={s.done}>
              <h2 className={s.h}>Карточки пройдены</h2>
              <p>
                Помню: <b>{st.remembered}</b> · ещё учить: <b>{st.again}</b>
              </p>
              <div className={s.actions}>
                {cards.length >= ROUND.minWords && (
                  <ButtonLink to={ROUTES.deadline(deckId)} variant="game" block>
                    Сыграть «Дедлайн»
                  </ButtonLink>
                )}
                <button type="button" className={s.again} onClick={restart}>
                  Пройти ещё раз
                </button>
                <ButtonLink to={ROUTES.home} variant="outlinePaper" block>
                  В кабинет
                </ButtonLink>
              </div>
            </Paper>
          )}
        />
      )}
    </>
  );
}
