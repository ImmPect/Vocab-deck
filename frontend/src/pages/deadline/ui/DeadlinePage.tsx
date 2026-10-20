/**
 * Мини-игра «Дедлайн» (UC-02): 5 вопросов по 4 варианта, 60 секунд.
 * При открытии — POST /rounds, при уходе со страницы раунд сбрасывается.
 */
import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { selectGuestBoxes } from '@/features/guest-progress-sync';
import { AnswerOptions, abandonRound, selectCurrentQuestion, selectGame, startRound, submitAnswer } from '@/features/play-deadline';
import { SpeakButton } from '@/features/speak-word';
import { selectIsGuest } from '@/entities/user';
import { ROUTES } from '@/shared/config';
import { useDelayedFlag } from '@/shared/lib';
import { useAppDispatch, useAppSelector } from '@/shared/model';
import { Button, ButtonLink, EmptyState, PageHeader, Paper, Skeleton } from '@/shared/ui';
import { RoundTimer } from '@/widgets/round-timer';
import s from './DeadlinePage.module.css';

function errorText(code: string | undefined, message: string | undefined) {
  if (code === 'round_expired' || code === 'round_finished' || code === 'not_found') return 'Раунд устарел — начните заново';
  return message ?? 'Не удалось начать раунд';
}

export default function DeadlinePage() {
  const deckId = Number(useParams().deckId);
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const g = useAppSelector(selectGame);
  const q = useAppSelector(selectCurrentQuestion);
  const isGuest = useAppSelector(selectIsGuest);
  const boxOf = useAppSelector(selectGuestBoxes);
  const skeleton = useDelayedFlag(g.status === 'loading' || g.status === 'idle');

  useEffect(() => {
    void dispatch(startRound(deckId));
    return () => {
      dispatch(abandonRound());
    };
  }, [deckId, dispatch]);

  useEffect(() => {
    if (g.status === 'finished' && g.roundId) navigate(ROUTES.result(g.roundId), { replace: true });
  }, [g.status, g.roundId, navigate]);

  const pick = (i: number) => dispatch(submitAnswer(i, isGuest ? (wordId) => boxOf(wordId, g.direction) : undefined));

  if (g.status === 'error') {
    const tooFew = g.error?.code === 'not_enough_words';
    return (
      <>
        <PageHeader title="Дедлайн" />
        <EmptyState
          icon={tooFew ? '🗂' : '⚠'}
          actions={
            <>
              {tooFew ? (
                <ButtonLink to={ROUTES.cards(deckId)} variant="outline" size="small">Смотреть карточки</ButtonLink>
              ) : (
                <Button variant="game" size="small" onClick={() => dispatch(startRound(deckId))}>Начать заново</Button>
              )}
              <ButtonLink to={ROUTES.home} variant="outline" size="small">В кабинет</ButtonLink>
            </>
          }
        >
          {tooFew ? 'Для раунда нужно не меньше 4 слов в отделе' : errorText(g.error?.code, g.error?.message)}
        </EmptyState>
      </>
    );
  }

  return (
    <div className={s.game}>
      <PageHeader title={g.deckTitle ? `Дедлайн · ${g.deckTitle}` : 'Дедлайн'} />
      <div className={s.head}>
        <span>
          Вопрос <b>{Math.min(g.index + 1, g.questions.length || 5)}</b> из {g.questions.length || 5}
        </span>
        <span>
          Опыт раунда: <b>+{g.xp}</b>
          {isGuest && <span className={s.hint}> (предварительно)</span>}
        </span>
      </div>
      <RoundTimer />
      {!q ? (
        skeleton && (
          <>
            <Skeleton height={150} style={{ marginBottom: 18 }} />
            <Skeleton height={120} />
          </>
        )
      ) : (
        <>
          <Paper className={s.q}>
            <span className={s.lbl}>Как переводится</span>
            <span className={s.en} lang="en">
              {q.prompt}
            </span>
            <span className={s.ipa}>
              {q.ipa}
              <SpeakButton text={q.prompt} />
            </span>
          </Paper>
          <AnswerOptions onPick={pick} />
          {g.status === 'finishing' && <p className={s.finishing}>Подводим итоги…</p>}
        </>
      )}
      <p className={s.keys}>Клавиши 1–4 — выбор варианта</p>
    </div>
  );
}
