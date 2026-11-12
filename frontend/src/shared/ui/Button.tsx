import type { ButtonHTMLAttributes } from 'react';
import { Link, type LinkProps } from 'react-router-dom';
import s from './ui.module.css';

export type ButtonVariant = 'primary' | 'game' | 'outline' | 'outlinePaper' | 'danger' | 'link' | 'linkLight';

interface Common {
  variant?: ButtonVariant;
  size?: 'normal' | 'small';
  block?: boolean;
}

const cls = ({ variant = 'primary', size = 'normal', block }: Common, loading = false, extra?: string) =>
  [s.btn, s[variant], size === 'small' && s.small, block && s.block, loading && s.loading, extra]
    .filter(Boolean)
    .join(' ');

export interface ButtonProps extends Common, ButtonHTMLAttributes<HTMLButtonElement> {
  /** Индикатор вместо текста; повторное нажатие заблокировано (табл. 4.3). */
  loading?: boolean;
}

export function Button({ variant, size, block, loading = false, className, children, disabled, ...rest }: ButtonProps) {
  return (
    <button
      type="button"
      className={cls({ variant, size, block }, loading, className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading && <span className={s.spinner} aria-hidden="true" />}
      <span className={s.label}>{children}</span>
    </button>
  );
}

/** Ссылка, которая выглядит как кнопка (переходы между экранами). */
export function ButtonLink({ variant, size, block, className, ...rest }: Common & LinkProps) {
  return <Link className={cls({ variant, size, block }, false, className)} {...rest} />;
}
