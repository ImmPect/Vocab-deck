/**
 * Входящие: разбор слов, которые пора повторить (UC-01). Пользователю — GET /inbox,
 * гостю — проекция локального журнала. Ответы уходят пакетами через outbox (mode = review).
 */
import { useMemo } from 'react';
import { useGetInboxQuery, type InboxItem } from '@/entities/progress';
import { selectGuestProjection, useLearner } from '@/features/guest-progress-sync';
import { asApiError } from '@/shared/api';
import { ROUTES } from '@/shared/config';
import { WORD_FORMS, countOf, useDelayedFlag } from '@/shared/lib';
import { useAppSelector } from '@/shared/model';
import { ButtonLink, EmptyState, ErrorBlock, PageHeader, Paper, Skeleton } from '@/shared/ui';
import { ReviewDeck, type ReviewCard } from '@/widgets/review-deck';
import s from './InboxPage.module.css';

const toCard = (i: InboxItem): ReviewCard => ({
  key: `${i.word_id}:${i.direction}`,
  word_id: i.word_id,
  direction: i.direction,
  en: i.en,
  ipa: i.ipa,
  ru: i.ru,
  example: i.example,
  deck_id: i.deck.id || undefined,
  deck_title: i.deck.title || undefined,
});

export default function InboxPage() {
  const learner = useLearner();
  const guest = useAppSelector(selectGuestProjection);
  const isUser = learner.kind === 'user';
  const inbox = useGetInboxQuery(undefined, { skip: !isUser, refetchOnMountOrArgChange: true });
  const skeleton = useDelayedFlag(inbox.isLoading);

  const items = isUser ? inbox.data?.items : learner.kind === 'guest' ? guest.inbox : undefined;
  const cards = useMemo(() => items?.map(toCard), [items]);

  return (
    <>
      <PageHeader
        title="Входящие"
        lead={
          cards?.length
            ? `${countOf(cards.length, WORD_FORMS)} пора повторить. Перевод открывается по нажатию на карточку.`
            : 'Слова, которые пора повторить по системе Лейтнера.'
        }
      />
      {isUser && inbox.isLoading && skeleton && <Skeleton height={400} width={330} style={{ margin: '0 auto' }} />}
      {inbox.error && <ErrorBlock message={asApiError(inbox.error)?.message ?? 'Не удалось загрузить входящие'} onRetry={inbox.refetch} />}
      {cards && cards.length === 0 && (
        <EmptyState icon="📭" actions={<ButtonLink to={ROUTES.home} variant="game" size="small">Сыграть раунд</ButtonLink>}>
          Входящие разобраны. Новые слова придут завтра
        </EmptyState>
      )}
      {cards && cards.length > 0 && (
        <ReviewDeck
          cards={cards}
          mode="review"
          renderDone={(st) => (
            <Paper className={s.done}>
              <h2 className={s.h}>Входящие разобраны</h2>
              <p>
                Помню: <b>{st.remembered}</b> · ещё учить: <b>{st.again}</b>. Слова «ещё учить» вернутся завтра.
              </p>
              <ButtonLink to={ROUTES.home} variant="primary" block>
                В кабинет
              </ButtonLink>
            </Paper>
          )}
        />
      )}
    </>
  );
}
