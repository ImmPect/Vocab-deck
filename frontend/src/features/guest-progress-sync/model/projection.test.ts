import { describe, expect, it } from 'vitest';
import { guestProgress, guestProgressSlice, type GuestEvent } from './guestSlice';
import { project, toGuestProgressPayload } from './projection';

const ev = (over: Partial<GuestEvent>): GuestEvent => ({
  client_event_id: crypto.randomUUID(),
  word_id: 1,
  direction: 'en_ru',
  mode: 'deadline',
  is_correct: true,
  answered_at: '2026-10-20T10:00:00Z',
  combo: 1,
  round_id: '11111111-1111-4111-8111-111111111111',
  question_id: 1,
  receipt: 'sig',
  xp_awarded: 10,
  new_box: 2,
  next_review_at: '2026-10-23',
  learned: false,
  word: { en: 'deadline', ru: 'крайний срок', deck_id: 1, deck_title: 'Офис' },
  ...over,
});

describe('проекция журнала гостя', () => {
  it('опыт — сумма значений сервера, ящик — последний по времени', () => {
    const p = project(
      [
        ev({ answered_at: '2026-10-20T10:00:00Z', xp_awarded: 10, new_box: 2 }),
        ev({ answered_at: '2026-10-20T10:00:05Z', xp_awarded: 15, new_box: 3, combo: 3 }),
      ],
      '2026-10-20',
    );
    expect(p.xp).toBe(25);
    expect(p.words).toHaveLength(1);
    expect(p.words[0].box).toBe(3);
  });

  it('во входящие попадают слова со сроком повтора не позже сегодняшнего', () => {
    const p = project(
      [
        ev({ word_id: 1, next_review_at: '2026-10-20' }),
        ev({ word_id: 2, next_review_at: '2026-10-25', word: { en: 'invoice', ru: 'счёт' } }),
      ],
      '2026-10-20',
    );
    expect(p.inbox.map((i) => i.word_id)).toEqual([1]);
  });

  it('серия — подряд идущие дни с ответами', () => {
    const days = ['2026-10-18', '2026-10-19', '2026-10-20'].map((d) => ev({ answered_at: `${d}T09:00:00` }));
    expect(project(days, '2026-10-20').streakDays).toBe(3);
    expect(project(days, '2026-10-22').streakDays).toBe(0);
  });
});

describe('slice guestProgress', () => {
  it('повторная квитанция того же события не дублируется', () => {
    const e = ev({});
    let s = guestProgressSlice.reducer(undefined, guestProgress.eventRecorded(e));
    s = guestProgressSlice.reducer(s, guestProgress.eventRecorded(e));
    expect(s.events).toHaveLength(1);
    expect(guestProgressSlice.reducer(s, guestProgress.cleared()).events).toHaveLength(0);
  });
});

describe('поле guest_progress для регистрации', () => {
  it('передаёт только подписанные поля и только события с квитанцией', () => {
    const payload = toGuestProgressPayload([ev({}), ev({ receipt: '' })])!;
    expect(payload.format_version).toBe(1);
    expect(payload.events).toHaveLength(1);
    expect(Object.keys(payload.events[0]).sort()).toEqual(
      ['answered_at', 'client_event_id', 'combo', 'direction', 'is_correct', 'mode', 'question_id', 'receipt', 'round_id', 'word_id'].sort(),
    );
  });

  it('пустой журнал — поле не передаётся', () => {
    expect(toGuestProgressPayload([])).toBeUndefined();
  });
});
