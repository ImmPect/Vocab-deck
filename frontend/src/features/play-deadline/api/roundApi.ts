/** Эндпоинты раунда мини-игры (раздел 3.7 ПР3). Мутации не кэшируются. */
import type { AnswerResult, Direction } from '@/entities/progress';
import { baseApi, PROGRESS_TAGS, unwrap } from '@/shared/api';

export interface RoundQuestion {
  question_id: number;
  word_id: number;
  prompt: string;
  ipa: string | null;
  options: string[];
}

export interface Round {
  round_id: string;
  deck: { id: number; title: string };
  mode: 'deadline' | 'dictation';
  direction: Direction;
  time_limit_s: number;
  started_at: string;
  questions: RoundQuestion[];
}

export interface RoundAnswer extends AnswerResult {
  question_id: number;
  correct_answer: { index: number; text: string };
  combo: number;
}

export interface LevelUp {
  from: { code: string; title: string; min_xp: number };
  to: { code: string; title: string; min_xp: number };
  unlocked: string[];
}

export interface RoundSummary {
  round_id: string;
  answered: number;
  correct: number;
  xp_earned: number;
  /** null у гостя: его опыт — в локальном журнале. */
  xp_total: number | null;
  level_up: LevelUp | null;
  level: { code: string; title: string; min_xp: number } | null;
  next_level: { code: string; title: string; min_xp: number; xp_left: number } | null;
  streak_days: number | null;
  streak_freezes: number | null;
  achievements_earned: { code: string; title: string }[];
  xp_provisional: boolean;
  suggest_registration: boolean;
}

export interface AnswerBody {
  roundId: string;
  question_id: number;
  choice_index: number;
  client_event_id: string;
  answered_at: string;
  response_ms: number;
  current_box?: number;
}

export const roundApi = baseApi.injectEndpoints({
  endpoints: (b) => ({
    startRound: b.mutation<Round, { deck_id: number; mode: 'deadline'; direction: Direction }>({
      query: (body) => ({ url: '/rounds', method: 'POST', body }),
      transformResponse: unwrap<Round>,
    }),
    // Ответы внутри раунда теги не инвалидируют: опыт раунда показывается из ответов
    // сервера в slice game, а профиль обновляется один раз — после finish (раздел 4.6.1)
    answerQuestion: b.mutation<RoundAnswer, AnswerBody>({
      query: ({ roundId, ...body }) => ({ url: `/rounds/${roundId}/answers`, method: 'POST', body }),
      transformResponse: unwrap<RoundAnswer>,
    }),
    finishRound: b.mutation<RoundSummary, string>({
      query: (roundId) => ({ url: `/rounds/${roundId}/finish`, method: 'POST' }),
      transformResponse: unwrap<RoundSummary>,
      invalidatesTags: (r) => (r && r.xp_total !== null ? [...PROGRESS_TAGS] : []),
    }),
  }),
});
