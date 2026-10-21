/**
 * Slice game (раздел 4.6.2 ПР3): состояние текущего раунда «Дедлайн».
 * Источник истины — сервер: опыт, комбо и ящик не вычисляются на клиенте,
 * а приходят в action answerChecked (поток 4.7.2). Выбор при этом подсвечивается
 * мгновенно (answerSubmitted), а оставшееся время вычисляется из endsAt.
 */
import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { Direction, XpPart } from '@/entities/progress';
import type { ApiError } from '@/shared/api';
import type { OutboxItemLike, GuestEventLike } from './events';
import type { Round, RoundAnswer, RoundQuestion, RoundSummary } from '../api/roundApi';

export type GameStatus =
  | 'idle'
  | 'loading'
  | 'playing' // ждём выбора
  | 'checking' // выбор отправлен, ждём ответа сервера
  | 'checked' // результат показан, пауза 0,9 с до следующего вопроса
  | 'finishing'
  | 'finished'
  | 'error';

export type Outcome = 'correct' | 'wrong' | 'deferred' | 'skipped';

export interface QuestionLog {
  questionId: number;
  wordId: number;
  prompt: string;
  choiceText: string | null;
  correctText: string | null;
  outcome: Outcome;
}

export interface CheckResult {
  isCorrect: boolean;
  correctIndex: number;
  correctText: string;
  xp: number;
  breakdown: XpPart[];
  combo: number;
}

export interface GameState {
  status: GameStatus;
  /** Идентификатор запроса раунда: ответ устаревшего запроса игнорируется. */
  requestId: string | null;
  roundId: string | null;
  deckId: number | null;
  deckTitle: string;
  direction: Direction;
  questions: RoundQuestion[];
  index: number;
  /** Время окончания раунда по часам клиента, мс. */
  endsAt: number | null;
  timeLimitS: number;
  /** Время показа текущего вопроса — для response_ms. */
  shownAt: number;
  selected: number | null;
  check: CheckResult | null;
  /** Ответ на текущий вопрос не дошёл до сервера и ждёт в очереди. */
  deferred: boolean;
  combo: number;
  xp: number;
  correct: number;
  log: QuestionLog[];
  summary: RoundSummary | null;
  timeExpired: boolean;
  error: ApiError | null;
}

const initialState: GameState = {
  status: 'idle',
  requestId: null,
  roundId: null,
  deckId: null,
  deckTitle: '',
  direction: 'en_ru',
  questions: [],
  index: 0,
  endsAt: null,
  timeLimitS: 60,
  shownAt: 0,
  selected: null,
  check: null,
  deferred: false,
  combo: 0,
  xp: 0,
  correct: 0,
  log: [],
  summary: null,
  timeExpired: false,
  error: null,
};

export interface CheckedPayload {
  answer: RoundAnswer;
  /** Событие для журнала гостя — есть, только если сервер прислал receipt. */
  guestEvent: GuestEventLike | null;
}

export const gameSlice = createSlice({
  name: 'game',
  initialState,
  reducers: {
    roundRequested(_state, action: PayloadAction<{ deckId: number; requestId: string }>) {
      return { ...initialState, status: 'loading', deckId: action.payload.deckId, requestId: action.payload.requestId };
    },
    roundStarted(state, action: PayloadAction<{ round: Round; now: number; requestId: string }>) {
      const { round, now, requestId } = action.payload;
      if (requestId !== state.requestId) return;
      state.status = 'playing';
      state.roundId = round.round_id;
      state.deckId = round.deck.id;
      state.deckTitle = round.deck.title;
      state.direction = round.direction;
      state.questions = round.questions;
      state.index = 0;
      state.timeLimitS = round.time_limit_s;
      state.endsAt = now + round.time_limit_s * 1000;
      state.shownAt = now;
    },
    answerSubmitted(state, action: PayloadAction<{ choiceIndex: number }>) {
      if (state.status !== 'playing') return;
      state.status = 'checking';
      state.selected = action.payload.choiceIndex;
    },
    answerChecked(state, action: PayloadAction<CheckedPayload>) {
      const a = action.payload.answer;
      const q = state.questions.find((x) => x.question_id === a.question_id);
      if (!q) return;
      if (q.question_id === state.questions[state.index]?.question_id && state.status === 'checking') {
        state.status = 'checked';
        state.check = {
          isCorrect: a.is_correct,
          correctIndex: a.correct_answer.index,
          correctText: a.correct_answer.text,
          xp: a.xp_awarded,
          breakdown: a.xp_breakdown,
          combo: a.combo,
        };
      }
      state.xp += a.xp_awarded;
      state.combo = a.combo;
      if (a.is_correct) state.correct += 1;
      state.log.push({
        questionId: q.question_id,
        wordId: q.word_id,
        prompt: q.prompt,
        choiceText: state.selected !== null ? q.options[state.selected] ?? null : null,
        correctText: a.correct_answer.text,
        outcome: a.is_correct ? 'correct' : 'wrong',
      });
    },
    /** Нет сети или 5xx: ответ ушёл в очередь outbox, раунд продолжается (поток 4.7.2, п. 14). */
    answerDeferred(state, action: PayloadAction<{ questionId: number; item: OutboxItemLike }>) {
      const q = state.questions.find((x) => x.question_id === action.payload.questionId);
      if (!q) return;
      if (state.status === 'checking') {
        state.status = 'checked';
        state.deferred = true;
      }
      state.combo = 0;
      state.log.push({
        questionId: q.question_id,
        wordId: q.word_id,
        prompt: q.prompt,
        choiceText: state.selected !== null ? q.options[state.selected] ?? null : null,
        correctText: null,
        outcome: 'deferred',
      });
    },
    nextQuestion(state, action: PayloadAction<{ now: number }>) {
      if (state.status !== 'checked') return;
      state.index += 1;
      state.status = 'playing';
      state.selected = null;
      state.check = null;
      state.deferred = false;
      state.shownAt = action.payload.now;
    },
    timeExpired(state) {
      if (['playing', 'checking', 'checked'].includes(state.status)) {
        state.timeExpired = true;
        state.status = 'finishing';
      }
    },
    finishRequested(state) {
      state.status = 'finishing';
    },
    roundFinished(state, action: PayloadAction<RoundSummary | null>) {
      state.status = 'finished';
      state.summary = action.payload;
      const answered = new Set(state.log.map((l) => l.questionId));
      for (const q of state.questions) {
        if (!answered.has(q.question_id)) {
          state.log.push({ questionId: q.question_id, wordId: q.word_id, prompt: q.prompt, choiceText: null, correctText: null, outcome: 'skipped' });
        }
      }
    },
    roundFailed(state, action: PayloadAction<ApiError | null>) {
      state.status = 'error';
      state.error = action.payload;
    },
    roundAbandoned: () => initialState,
  },
});

export const game = gameSlice.actions;

type WithGame = { game: GameState };
export const selectGame = (s: WithGame) => s.game;
export const selectCurrentQuestion = (s: WithGame) => s.game.questions[s.game.index] ?? null;
export const selectPendingAnswers = (s: WithGame) => s.game.log.filter((l) => l.outcome === 'deferred').length;
