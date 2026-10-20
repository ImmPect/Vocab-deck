/**
 * Модальное окно (табл. 4.3): закрытие по Esc и щелчку по фону, фокус удерживается внутри,
 * после закрытия возвращается на элемент, который открыл окно (раздел 4.9 ПР3).
 */
import { useEffect, useId, useRef, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { Paper } from './components';
import s from './ui.module.css';

const FOCUSABLE = 'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

export function Modal({
  title,
  onClose,
  children,
  actions,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  actions?: ReactNode;
}) {
  const titleId = useId();
  const boxRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    const box = boxRef.current;
    (box?.querySelector<HTMLElement>(FOCUSABLE) ?? box)?.focus();

    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        closeRef.current();
        return;
      }
      if (e.key !== 'Tab' || !box) return;
      const items = [...box.querySelectorAll<HTMLElement>(FOCUSABLE)];
      if (!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
      opener?.focus?.();
    };
  }, []);

  return createPortal(
    <div className={s.backdrop} onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div ref={boxRef} role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1}>
        <Paper className={s.modal}>
          <h2 id={titleId} className={s.modalTitle}>
            {title}
          </h2>
          {children}
          {actions && <div className={s.modalActions}>{actions}</div>}
        </Paper>
      </div>
    </div>,
    document.body,
  );
}
