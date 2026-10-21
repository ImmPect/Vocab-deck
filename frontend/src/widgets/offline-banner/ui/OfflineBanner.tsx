/**
 * Плашка «Нет соединения» с числом ответов в очереди (поток 4.7.3) и предупреждение,
 * если localStorage недоступен и прогресс живёт только до закрытия вкладки (NFR-R-01).
 */
import { selectOutboxCount } from '@/features/offline-outbox';
import { ANSWER_FORMS, countOf, storage } from '@/shared/lib';
import { selectOnline, useAppSelector } from '@/shared/model';
import s from './OfflineBanner.module.css';

export function OfflineBanner({ isGuest }: { isGuest: boolean }) {
  const online = useAppSelector(selectOnline);
  const queued = useAppSelector(selectOutboxCount);

  if (!online) {
    return (
      <div className={`${s.banner} ${s.offline}`} role="status">
        Нет соединения. Ответы сохраняются на устройстве
        {queued > 0 && <> · в очереди {countOf(queued, ANSWER_FORMS)}</>}
      </div>
    );
  }
  if (queued > 0) {
    return (
      <div className={s.banner} role="status">
        Отправляем сохранённые ответы: {queued}
      </div>
    );
  }
  if (isGuest && !storage.persistent) {
    return (
      <div className={s.banner} role="note">
        Прогресс сохранится только до закрытия вкладки — зарегистрируйтесь, чтобы не потерять его
      </div>
    );
  }
  return null;
}
