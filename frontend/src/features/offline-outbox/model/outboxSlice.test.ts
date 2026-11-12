import { describe, expect, it } from 'vitest';
import { outbox, outboxSlice, type OutboxItem } from './outboxSlice';

const item = (id: string): OutboxItem => ({
  answer: { client_event_id: id, mode: 'review', word_id: 1, direction: 'en_ru', is_correct: true, answered_at: '2026-10-20T10:00:00Z' },
});

describe('slice outbox (поток 4.7.3)', () => {
  it('один и тот же ответ не попадает в очередь дважды', () => {
    let s = outboxSlice.reducer(undefined, outbox.enqueued([item('a'), item('b')]));
    s = outboxSlice.reducer(s, outbox.enqueued(item('a')));
    expect(s.items.map((i) => i.answer.client_event_id)).toEqual(['a', 'b']);
  });

  it('applied, duplicate и rejected удаляются, остальные остаются', () => {
    let s = outboxSlice.reducer(undefined, outbox.enqueued([item('a'), item('b'), item('c')]));
    s = outboxSlice.reducer(s, outbox.flushStarted());
    s = outboxSlice.reducer(
      s,
      outbox.itemsAcked({
        items: [item('a'), item('b')],
        results: [
          { client_event_id: 'a', status: 'applied' },
          { client_event_id: 'b', status: 'duplicate' },
        ],
      }),
    );
    expect(s.items.map((i) => i.answer.client_event_id)).toEqual(['c']);
    expect(s.flushing).toBe(false);
  });

  it('сбой отправки увеличивает счётчик попыток и не теряет элементы', () => {
    let s = outboxSlice.reducer(undefined, outbox.enqueued(item('a')));
    s = outboxSlice.reducer(s, outbox.flushFailed({ nextAttemptAt: 5000 }));
    expect(s.attempt).toBe(1);
    expect(s.items).toHaveLength(1);
  });
});
