/** Простые компоненты UI-kit: Paper, ProgressBar, Chip, Skeleton, EmptyState, ErrorBlock, PageHeader. */
import { useEffect, useRef, type CSSProperties, type HTMLAttributes, type ReactNode } from 'react';
import { Button } from './Button';
import s from './ui.module.css';

const join = (...c: (string | false | undefined)[]) => c.filter(Boolean).join(' ');

/** Лист бумаги в линейку — основная поверхность карточек и панелей (дизайн ЛР2). */
export function Paper({
  as: Tag = 'div',
  plain,
  className,
  ...rest
}: HTMLAttributes<HTMLElement> & { as?: 'div' | 'section' | 'article' | 'form' | 'li'; plain?: boolean }) {
  return <Tag className={join(s.paper, plain && s.plain, className)} {...rest} />;
}

export function ProgressBar({
  value,
  max,
  label,
  tone = 'gradient',
  thin,
  onDesk,
  className,
}: {
  value: number;
  max: number;
  label: string;
  tone?: 'gradient' | 'sage' | 'red';
  thin?: boolean;
  onDesk?: boolean;
  className?: string;
}) {
  const pct = max > 0 ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
  return (
    <div
      className={join(s.bar, thin && s.barThin, onDesk && s.barOnDesk, tone === 'sage' && s.barSage, tone === 'red' && s.barRed, className)}
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={Math.round(value)}
    >
      <i className={s.barFill} style={{ width: `${pct}%` }} />
    </div>
  );
}

export type ChipTone = 'neutral' | 'published' | 'draft' | 'archived' | 'amber';
const chipTone: Record<ChipTone, string | undefined> = {
  neutral: undefined,
  published: s.chipPublished,
  draft: s.chipDraft,
  archived: s.chipArchived,
  amber: s.chipAmber,
};

export function Chip({ tone = 'neutral', children, className }: { tone?: ChipTone; children: ReactNode; className?: string }) {
  return <span className={join(s.chip, chipTone[tone], className)}>{children}</span>;
}

export function Skeleton({ height, width = '100%', style, className }: { height: number; width?: number | string; style?: CSSProperties; className?: string }) {
  return <span className={join(s.skeleton, className)} style={{ height, width, ...style }} aria-hidden="true" />;
}

/** Пустое состояние со следующим шагом (п. 5.8 ТЗ, раздел 4.8.3 ПР3). */
export function EmptyState({ icon, children, actions }: { icon?: string; children: ReactNode; actions?: ReactNode }) {
  return (
    <div className={s.empty}>
      {icon && <span className={s.emptyIcon} aria-hidden="true">{icon}</span>}
      <div>{children}</div>
      {actions && <div className={s.emptyActions}>{actions}</div>}
    </div>
  );
}

/** Блок ошибки загрузки с кнопкой «Повторить» (табл. 4.8, строка 5xx). */
export function ErrorBlock({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className={s.empty} role="alert">
      <span className={s.emptyIcon} aria-hidden="true">⚠</span>
      <div>{message}</div>
      {onRetry && (
        <Button variant="outline" size="small" onClick={onRetry}>
          Повторить
        </Button>
      )}
    </div>
  );
}

/**
 * Заголовок экрана. При смене экрана фокус переходит на заголовок,
 * и экранный диктор объявляет новый экран (раздел 4.9 ПР3).
 */
export function PageHeader({ title, lead, children }: { title: string; lead?: ReactNode; children?: ReactNode }) {
  const ref = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    document.title = `${title} · Vocab Deck`;
    ref.current?.focus({ preventScroll: true });
  }, [title]);
  return (
    <header className={s.pageHeader}>
      <h1 ref={ref} tabIndex={-1} className={s.pageTitle}>
        {title}
      </h1>
      {lead && <p className={s.lead}>{lead}</p>}
      {children}
    </header>
  );
}
