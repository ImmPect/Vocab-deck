/**
 * Отправка очереди (поток 4.7.3 ПР3): пакеты до 50 ответов в порядке answered_at
 * одним запросом POST /answers/batch; при сбое — повтор с растущей паузой.
 * Очередь в каждый момент отправляет одна вкладка (Web Locks API, где он есть).
 */
import { progressApi } from '@/entities/progress';
import { selectIsGuest } from '@/entities/user';
import { asApiError } from '@/shared/api';
import { OUTBOX } from '@/shared/config';
import { ANSWER_FORMS, countOf } from '@/shared/lib';
import { ui, type AppThunk } from '@/shared/model';
import { outbox } from './outboxSlice';

let retryTimer: ReturnType<typeof setTimeout> | undefined;

export const flushOutbox =
  (): AppThunk<Promise<void>> =>
  async (dispatch, getState) => {
    const state = getState();
    if (state.outbox.flushing || !state.outbox.items.length || !state.ui.online) return;

    const run = async () => {
      let sent = 0;
      let xp = 0;
      let rejected = 0;
      const asGuest = selectIsGuest(getState());
      while (getState().outbox.items.length) {
        const batch = [...getState().outbox.items]
          .sort((a, b) => a.answer.answered_at.localeCompare(b.answer.answered_at))
          .slice(0, OUTBOX.batchSize);
        dispatch(outbox.flushStarted());
        try {
          const res = await dispatch(
            progressApi.endpoints.sendAnswers.initiate({ answers: batch.map((i) => i.answer), asGuest }),
          ).unwrap();
          dispatch(outbox.itemsAcked({ items: batch, results: res.results }));
          sent += res.summary.applied + res.summary.duplicate;
          rejected += res.summary.rejected;
          xp += res.results.reduce((sum, r) => sum + (r.status === 'applied' && !asGuest ? (r.xp_awarded ?? 0) : 0), 0);
        } catch (e) {
          const err = asApiError(e);
          const attempt = getState().outbox.attempt;
          const delay = OUTBOX.backoffMs[Math.min(attempt, OUTBOX.backoffMs.length - 1)];
          dispatch(outbox.flushFailed({ nextAttemptAt: Date.now() + delay }));
          if (err?.status !== 401) {
            clearTimeout(retryTimer);
            retryTimer = setTimeout(() => void dispatch(flushOutbox()), delay);
          }
          break;
        }
      }
      if (sent) {
        const tail = xp ? `, начислено ${xp} опыта` : '';
        dispatch(ui.toastShown(`Отправлено ${countOf(sent, ANSWER_FORMS)}${tail}`));
      }
      if (rejected) {
        dispatch(ui.toastShown(`${countOf(rejected, ANSWER_FORMS)} не засчитано: слово больше недоступно`, 'info'));
      }
    };

    const locks = typeof navigator !== 'undefined' ? navigator.locks : undefined;
    if (locks) {
      await locks.request('vocabdeck-outbox', { ifAvailable: true }, async (lock) => {
        if (lock) await run(); // null — очередь уже отправляет другая вкладка
      });
    } else {
      await run();
    }
  };
