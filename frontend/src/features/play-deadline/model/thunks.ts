/**
 * Побочные эффекты раунда (поток 4.7.2 ПР3): запросы к API и паузы между вопросами.
 * Reducers остаются чистыми функциями, всё асинхронное — здесь.
 */
import type { Direction } from '@/entities/progress';
import { asApiError, type ApiError } from '@/shared/api';
import { ROUND } from '@/shared/config';
import { nowIso, uuid } from '@/shared/lib';
import { ui, type AppThunk } from '@/shared/model';
import { roundApi } from '../api/roundApi';
import { game } from './gameSlice';

/** Ответ, на который сервер ещё не ответил: finish дожидается его (п. 11 потока 4.7.2). */
let inflight: Promise<unknown> | null = null;
let advanceTimer: ReturnType<typeof setTimeout> | undefined;

const isTransient = (e: ApiError | null) =>
  !e || e.status === 'network' || e.status === 429 || (typeof e.status === 'number' && e.status >= 500);

export const startRound =
  (deckId: number, direction: Direction = 'en_ru'): AppThunk<Promise<void>> =>
  async (dispatch, getState) => {
    clearTimeout(advanceTimer);
    const requestId = uuid();
    dispatch(game.roundRequested({ deckId, requestId }));
    try {
      const round = await dispatch(roundApi.endpoints.startRound.initiate({ deck_id: deckId, mode: 'deadline', direction })).unwrap();
      dispatch(game.roundStarted({ round, now: Date.now(), requestId }));
    } catch (e) {
      if (getState().game.requestId === requestId) dispatch(game.roundFailed(asApiError(e)));
    }
  };

export const finishRound =
  (): AppThunk<Promise<void>> =>
  async (dispatch, getState) => {
    clearTimeout(advanceTimer);
    const { roundId, status } = getState().game;
    if (!roundId || status === 'finished' || status === 'error') return;
    dispatch(game.finishRequested());
    if (inflight) await inflight.catch(() => undefined);
    try {
      const summary = await dispatch(roundApi.endpoints.finishRound.initiate(roundId)).unwrap();
      dispatch(game.roundFinished(summary));
    } catch {
      // Без сети итоги считаются по ответам, которые уже проверены; остальные — «ожидают проверки»
      dispatch(game.roundFinished(null));
    }
  };

/** Пауза 0,9 с после проверки, затем следующий вопрос или итоги. Таймер раунда при этом идёт. */
const scheduleAdvance = (): AppThunk => (dispatch, getState) => {
  clearTimeout(advanceTimer);
  advanceTimer = setTimeout(() => {
    const g = getState().game;
    if (g.status !== 'checked') return;
    if (g.index + 1 < g.questions.length) dispatch(game.nextQuestion({ now: Date.now() }));
    else void dispatch(finishRound());
  }, ROUND.nextQuestionDelayMs);
};

/**
 * Выбор варианта (клик или клавиша 1–4). currentBox — ящик слова из журнала гостя:
 * его подставляет страница, потому что фича не читает соседнюю фичу guest-progress-sync.
 */
export const submitAnswer =
  (choiceIndex: number, currentBox?: (wordId: number) => number | undefined): AppThunk =>
  (dispatch, getState) => {
    const g = getState().game;
    const q = g.questions[g.index];
    if (g.status !== 'playing' || !g.roundId || !q) return;

    const body = {
      roundId: g.roundId,
      question_id: q.question_id,
      choice_index: choiceIndex,
      client_event_id: uuid(),
      answered_at: nowIso(),
      response_ms: Math.min(Date.now() - g.shownAt, 60_000),
      current_box: currentBox?.(q.word_id),
    };
    const word = { en: q.prompt, ru: '', ipa: q.ipa, deck_id: g.deckId ?? undefined, deck_title: g.deckTitle };
    dispatch(game.answerSubmitted({ choiceIndex }));

    const request = dispatch(roundApi.endpoints.answerQuestion.initiate(body))
      .unwrap()
      .then((answer) => {
        const guestEvent = answer.receipt
          ? {
              client_event_id: body.client_event_id,
              word_id: q.word_id,
              direction: g.direction,
              mode: 'deadline' as const,
              is_correct: answer.is_correct,
              answered_at: answer.answered_at, // время в том виде, в каком его подписал сервер
              combo: answer.combo,
              round_id: body.roundId,
              question_id: q.question_id,
              receipt: answer.receipt,
              xp_awarded: answer.xp_awarded,
              new_box: answer.new_box,
              next_review_at: answer.next_review_at,
              learned: answer.learned,
              word: { ...word, ru: answer.correct_answer.text },
            }
          : null;
        dispatch(game.answerChecked({ answer, guestEvent }));
      })
      .catch((e: unknown) => {
        const err = asApiError(e);
        if (isTransient(err)) {
          if (err?.status === 429) dispatch(ui.toastShown('Слишком много запросов, подождите немного', 'info'));
          const { roundId, ...rest } = body;
          dispatch(
            game.answerDeferred({
              questionId: q.question_id,
              item: {
                answer: { ...rest, mode: 'deadline', word_id: q.word_id, direction: g.direction, round_id: roundId },
                word,
              },
            }),
          );
        } else {
          // 404 / 409: раунд устарел или уже завершён — «Начать заново»
          dispatch(game.roundFailed(err));
        }
      })
      .finally(() => {
        inflight = null;
        if (getState().game.status === 'checked') dispatch(scheduleAdvance());
      });
    inflight = request;
  };

/** Таймер дошёл до нуля: раунд завершается, даже если ответ ещё проверяется. */
export const expireRound = (): AppThunk => (dispatch, getState) => {
  if (!['playing', 'checking', 'checked'].includes(getState().game.status)) return;
  dispatch(game.timeExpired());
  void dispatch(finishRound());
};

/** Уход со страницы игры: раунд сбрасывается (UC-02). */
export const abandonRound = (): AppThunk => (dispatch, getState) => {
  clearTimeout(advanceTimer);
  if (getState().game.status !== 'finished') dispatch(game.roundAbandoned());
};
