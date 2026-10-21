/**
 * Listener middleware — побочные эффекты, которые связывают слайсы разных фич
 * (раздел 4.2.5 ПР3). Фичи не импортируют друг друга, поэтому «склейка» живёт в слое app:
 *
 *   game/answerChecked (+receipt)  → guestProgress/eventRecorded
 *   game/answerDeferred            → outbox/enqueued
 *   outbox/itemsAcked (+receipt)   → guestProgress/eventRecorded
 *   изменения журнала и очереди    → запись в localStorage (с задержкой до 500 мс)
 *   api/sessionExpired             → сброс кэша API
 *   ui/onboarding*, ui/accentChanged → vocabdeck:prefs
 */
import { createListenerMiddleware, isAnyOf, type TypedStartListening } from '@reduxjs/toolkit';
import { guestProgress, saveGuestProgress, type GuestEvent } from '@/features/guest-progress-sync';
import { flushOutbox, outbox, saveOutbox } from '@/features/offline-outbox';
import { game } from '@/features/play-deadline';
import { selectIsGuest } from '@/entities/user';
import { baseApi, sessionExpired } from '@/shared/api';
import { STORAGE_KEYS } from '@/shared/config';
import { storage } from '@/shared/lib';
import { ui, type AppDispatch, type RootState } from '@/shared/model';

export const listener = createListenerMiddleware();
const startListening = listener.startListening as TypedStartListening<RootState, AppDispatch>;

// Ответ раунда гостю пришёл с квитанцией — событие в журнал
startListening({
  actionCreator: game.answerChecked,
  effect: ({ payload }, api) => {
    if (payload.guestEvent && selectIsGuest(api.getState())) api.dispatch(guestProgress.eventRecorded(payload.guestEvent));
  },
});

// Нет сети: ответ раунда — в очередь
startListening({
  actionCreator: game.answerDeferred,
  effect: ({ payload }, api) => {
    api.dispatch(outbox.enqueued(payload.item));
  },
});

// Сервер подтвердил пакет: гостю — квитанции applied/duplicate в журнал (поток 4.7.3, п. 7)
startListening({
  actionCreator: outbox.itemsAcked,
  effect: ({ payload }, api) => {
    if (!selectIsGuest(api.getState())) return;
    const byId = new Map(payload.items.map((i) => [i.answer.client_event_id, i]));
    for (const r of payload.results) {
      const item = byId.get(r.client_event_id);
      if (!item || !r.receipt || r.status === 'rejected' || r.is_correct === undefined || !r.answered_at) continue;
      const a = item.answer;
      const event: GuestEvent = {
        client_event_id: a.client_event_id,
        word_id: a.word_id,
        direction: a.direction,
        mode: a.mode,
        is_correct: r.is_correct,
        answered_at: r.answered_at,
        combo: r.combo ?? 0,
        ...(a.round_id ? { round_id: a.round_id, question_id: a.question_id } : {}),
        receipt: r.receipt,
        xp_awarded: r.xp_awarded ?? 0,
        new_box: r.new_box ?? 1,
        next_review_at: r.next_review_at ?? null,
        learned: r.learned ?? false,
        word: item.word,
      };
      api.dispatch(guestProgress.eventRecorded(event));
    }
  },
});

// Журнал гостя → localStorage, с задержкой до 500 мс (табл. 4.6)
startListening({
  matcher: isAnyOf(guestProgress.eventRecorded, guestProgress.cleared),
  effect: async (_action, api) => {
    api.cancelActiveListeners();
    await api.delay(500);
    saveGuestProgress(storage, api.getState().guestProgress);
  },
});

// Очередь → localStorage при каждом изменении
startListening({
  matcher: isAnyOf(outbox.enqueued, outbox.itemsAcked, outbox.restored),
  effect: (_action, api) => {
    saveOutbox(storage, api.getState().outbox.items);
  },
});

// Сеть восстановилась — отправить очередь
startListening({
  actionCreator: ui.networkChanged,
  effect: ({ payload: online }, api) => {
    if (online) void api.dispatch(flushOutbox());
  },
});

// Сессия завершилась на сервере: кэш одного пользователя не должен достаться следующему
startListening({
  actionCreator: sessionExpired,
  effect: (_action, api) => {
    api.dispatch(baseApi.util.resetApiState());
  },
});

// Настройки устройства: подсказки онбординга пройдены, выбранное произношение озвучки
startListening({
  matcher: isAnyOf(ui.onboardingSkipped, ui.onboardingStepChanged, ui.accentChanged),
  effect: (_action, api) => {
    const { onboardingDone, accent } = api.getState().ui;
    storage.set(STORAGE_KEYS.prefs, JSON.stringify({ format_version: 1, onboarding_done: onboardingDone, accent }));
  },
});
