/** Уведомления: роль status, скрываются через 2 с, одновременно видно не больше одного (табл. 25 ТЗ). */
import { useEffect } from 'react';
import { TOAST_MS } from '@/shared/config';
import { selectToast, ui, useAppDispatch, useAppSelector } from '@/shared/model';
import s from './ToastHost.module.css';

export function ToastHost() {
  const toast = useAppSelector(selectToast);
  const dispatch = useAppDispatch();
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => dispatch(ui.toastHidden(toast.id)), toast.kind === 'error' ? TOAST_MS * 2 : TOAST_MS);
    return () => clearTimeout(t);
  }, [toast, dispatch]);

  return (
    <div className={s.host} role="status" aria-live="polite">
      {toast && (
        <div key={toast.id} className={`${s.toast} ${s[toast.kind]}`}>
          {toast.kind === 'success' && <span aria-hidden="true">✓ </span>}
          {toast.text}
        </div>
      )}
    </div>
  );
}
