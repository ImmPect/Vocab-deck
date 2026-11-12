/** Поля форм: подпись, текст ошибки с пояснением, подсказка (табл. 4.3, Input / Select / Textarea). */
import {
  forwardRef,
  useId,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from 'react';
import s from './ui.module.css';

interface FieldShell {
  label: string;
  error?: string;
  hint?: ReactNode;
}

function Shell({ id, label, error, hint, children }: FieldShell & { id: string; children: ReactNode }) {
  return (
    <div className={[s.field, error && s.invalid].filter(Boolean).join(' ')}>
      <label className={s.fieldLabel} htmlFor={id}>
        {label}
      </label>
      {children}
      {error ? (
        <span className={s.fieldError} id={`${id}-err`} role="alert">
          {error}
        </span>
      ) : (
        hint && <span className={s.fieldHint} id={`${id}-hint`}>{hint}</span>
      )}
    </div>
  );
}

const describedBy = (id: string, error?: string, hint?: ReactNode) =>
  error ? `${id}-err` : hint ? `${id}-hint` : undefined;

export const Input = forwardRef<HTMLInputElement, FieldShell & InputHTMLAttributes<HTMLInputElement>>(
  function Input({ label, error, hint, id, ...rest }, ref) {
    const auto = useId();
    const fid = id ?? auto;
    return (
      <Shell id={fid} label={label} error={error} hint={hint}>
        <input
          ref={ref}
          id={fid}
          className={s.control}
          aria-invalid={!!error || undefined}
          aria-describedby={describedBy(fid, error, hint)}
          {...rest}
        />
      </Shell>
    );
  },
);

export function Textarea({ label, error, hint, id, ...rest }: FieldShell & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const auto = useId();
  const fid = id ?? auto;
  return (
    <Shell id={fid} label={label} error={error} hint={hint}>
      <textarea id={fid} className={s.control} aria-invalid={!!error || undefined} aria-describedby={describedBy(fid, error, hint)} {...rest} />
    </Shell>
  );
}

export function Select({ label, error, hint, id, children, ...rest }: FieldShell & SelectHTMLAttributes<HTMLSelectElement>) {
  const auto = useId();
  const fid = id ?? auto;
  return (
    <Shell id={fid} label={label} error={error} hint={hint}>
      <select id={fid} className={s.control} aria-invalid={!!error || undefined} aria-describedby={describedBy(fid, error, hint)} {...rest}>
        {children}
      </select>
    </Shell>
  );
}

/** Поле на тёмном фоне стола без подписи сверху (поиск и фильтры админки). */
export const darkControlClass = s.controlDark;
