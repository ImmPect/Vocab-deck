/**
 * Reducer — чистая функция: состояние + action → новое состояние. Раунд «Дедлайн»
 * воспроизводится по шагам без браузера и без сервера (раздел 4.2.3 ПР3).
 */
import { describe, expect, it } from 'vitest';
import type { Round, RoundAnswer } from '../api/roundApi';
import { game, gameSlice, type GameState } from './gameSlice';

const round: Round = {
  round_id: 'r1',
  deck: { id: 1, title: 'Офис' },
  mode: 'deadline',
  direction: 'en_ru',
  time_limit_s: 60,
  started_at: '2026-10-20T10:00:00Z',
  questions: [1, 2, 3, 4, 5].map((n) => ({ question_id: n, word_id: 10 + n, prompt: `w${n}`, ipa: null, options: ['a', 'b', 'c', 'd'] })),
};

const answer = (over: Partial<RoundAnswer>): RoundAnswer => ({
  question_id: 1,
  is_correct: true,
  correct_answer: { index: 0, text: 'a' },
  xp_awarded: 10,
  xp_breakdown: [{ rule: 'correct_answer', xp: 10 }],
  combo: 1,
  new_box: 2,
  next_review_at: '2026-10-23',
  learned: false,
  answered_at: '2026-10-20T10:00:03Z',
  ...over,
});

const run = (...actions: Parameters<typeof gameSlice.reducer>[1][]) =>
  actions.reduce<GameState>((s, a) => gameSlice.reducer(s, a), gameSlice.reducer(undefined, { type: '@@init' }));

describe('slice game', () => {
  it('roundStarted: вопросы, endsAt = сейчас + 60 с', () => {
    const s = run(game.roundRequested({ deckId: 1, requestId: 'q' }), game.roundStarted({ round, now: 1000, requestId: 'q' }));
    expect(s.status).toBe('playing');
    expect(s.endsAt).toBe(61_000);
    expect(s.questions).toHaveLength(5);
  });

  it('ответ устаревшего запроса раунда игнорируется', () => {
    const s = run(
      game.roundRequested({ deckId: 1, requestId: 'old' }),
      game.roundRequested({ deckId: 1, requestId: 'new' }),
      game.roundStarted({ round, now: 0, requestId: 'old' }),
    );
    expect(s.status).toBe('loading');
  });

  it('выбор блокирует варианты, опыт появляется только после ответа сервера', () => {
    let s = run(game.roundRequested({ deckId: 1, requestId: 'q' }), game.roundStarted({ round, now: 0, requestId: 'q' }), game.answerSubmitted({ choiceIndex: 0 }));
    expect(s.status).toBe('checking');
    expect(s.xp).toBe(0);
    s = gameSlice.reducer(s, game.answerChecked({ answer: answer({}), guestEvent: null }));
    expect(s.status).toBe('checked');
    expect(s.xp).toBe(10);
    expect(s.correct).toBe(1);
    expect(s.check?.isCorrect).toBe(true);
  });

  it('повторный выбор во время проверки не принимается', () => {
    const s = run(
      game.roundRequested({ deckId: 1, requestId: 'q' }),
      game.roundStarted({ round, now: 0, requestId: 'q' }),
      game.answerSubmitted({ choiceIndex: 0 }),
      game.answerSubmitted({ choiceIndex: 2 }),
    );
    expect(s.selected).toBe(0);
  });

  it('ответ без сети откладывается, комбо сбрасывается, раунд продолжается', () => {
    const s = run(
      game.roundRequested({ deckId: 1, requestId: 'q' }),
      game.roundStarted({ round, now: 0, requestId: 'q' }),
      game.answerSubmitted({ choiceIndex: 1 }),
      game.answerDeferred({
        questionId: 1,
        item: { answer: { client_event_id: 'e', mode: 'deadline', word_id: 11, direction: 'en_ru', answered_at: 'x' } },
      }),
      game.nextQuestion({ now: 5 }),
    );
    expect(s.index).toBe(1);
    expect(s.status).toBe('playing');
    expect(s.log[0].outcome).toBe('deferred');
  });

  it('время вышло — неотвеченные вопросы в итогах помечены «нет ответа»', () => {
    const s = run(
      game.roundRequested({ deckId: 1, requestId: 'q' }),
      game.roundStarted({ round, now: 0, requestId: 'q' }),
      game.timeExpired(),
      game.roundFinished(null),
    );
    expect(s.timeExpired).toBe(true);
    expect(s.status).toBe('finished');
    expect(s.log.filter((l) => l.outcome === 'skipped')).toHaveLength(5);
  });
});
