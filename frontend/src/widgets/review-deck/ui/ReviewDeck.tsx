/**
 * Сессия самооценки на карточках (экраны «Карточки» и «Входящие», табл. 4.2 ПР3).
 * Оценка «Помню» / «Ещё учить» ставится в очередь outbox и сразу показывается
 * следующая карточка (UC-01 6а); очередь отправляется пакетом POST /answers/batch.
 */
import { useEffect, type ReactNode } from 'react';
import type { Direction } from '@/entities/progress';
import { FlipCard } from '@/features/flip-card';
import { selectGuestBoxes } from '@/features/guest-progress-sync';
import { flushOutbox, outbox } from '@/features/offline-outbox';
import { ReviewControls, buildSelfAnswer, useReviewSession } from '@/features/review-inbox';
import { SpeakButton, preloadAudio } from '@/features/speak-word';
import { selectIsGuest } from '@/entities/user';
import { selectAccent, useAppDispatch, useAppSelector } from '@/shared/model';
import { ProgressBar } from '@/shared/ui';
import s from './ReviewDeck.module.css';

export interface ReviewCard {
  key: string;
  word_id: number;
  direction: Direction;
  en: string;
  ipa: string | null;
  ru: string;
  example: string | null;
  deck_id?: number;
  deck_title?: string;
}

export function ReviewDeck({
  cards,
  mode,
  note,
  renderDone,
}: {
  cards: ReviewCard[] | undefined;
  mode: 'review' | 'self_check';
  note?: string;
  renderDone: (stats: { remembered: number; again: number }, restart: () => void) => ReactNode;
}) {
  const dispatch = useAppDispatch();
  const boxOf = useAppSelector(selectGuestBoxes);
  const isGuest = useAppSelector(selectIsGuest);
  const session = useReviewSession(cards);
  const accent = useAppSelector(selectAccent);
  const currentId = session.current?.word_id;

  // Озвучка текущей карточки загружается заранее — по нажатию звук начинается сразу
  useEffect(() => {
    if (currentId) preloadAudio(currentId, 'word', accent);
  }, [currentId, accent]);

  if (!session.ready) return null;
  if (session.done) return <>{renderDone(session.stats, session.restart)}</>;
  const card = session.current!;

  const rate = (remembered: boolean) => {
    const answer = buildSelfAnswer(mode, card, remembered, isGuest ? boxOf(card.word_id, card.direction) : undefined);
    dispatch(
      outbox.enqueued({
        answer,
        word: { en: card.en, ru: card.ru, ipa: card.ipa, example: card.example, deck_id: card.deck_id, deck_title: card.deck_title },
      }),
    );
    void dispatch(flushOutbox());
    session.rate(remembered);
  };

  return (
    <div className={s.study}>
      <div className={s.head}>
        <span>
          Карточка {session.index + 1} из {session.total}
        </span>
        <span>
          помню {session.stats.remembered} · ещё учить {session.stats.again}
        </span>
      </div>
      <ProgressBar value={session.index} max={session.total} label="Пройдено карточек" onDesk thin className={s.track} />
      <FlipCard
        key={card.key}
        word={{ en: card.en, ipa: card.ipa, ru: card.ru, example: card.example, tag: card.deck_title }}
        speakSlot={<SpeakButton text={card.en} wordId={card.word_id} />}
        exampleSlot={card.example ? <SpeakButton text={card.example} wordId={card.word_id} part="example" /> : undefined}
      />
      <ReviewControls onRate={rate} />
      {note && <p className={s.note}>{note}</p>}
    </div>
  );
}
