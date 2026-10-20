/**
 * Формы входа и регистрации (UC-03, US-05, US-06; табл. 4.2 ПР3).
 * Перенос гостевого прогресса собирает страница: она передаёт сводку и функцию,
 * которая возвращает журнал guest_progress (фича не читает соседнюю фичу).
 */
import { useRef, useState, type FormEvent } from 'react';
import { asApiError, fieldErrors, type ApiError } from '@/shared/api';
import { useAppSelector, selectOnline } from '@/shared/model';
import { Button, Input } from '@/shared/ui';
import { useLoginMutation, useRegisterMutation, type AuthResult, type GuestProgressPayload } from '../api/authApi';
import { focusFirstError, validateLogin, validateRegister, type Errors } from '../lib/validate';
import s from './AuthForms.module.css';

export interface GuestCarry {
  /** «12 слов, 140 опыта, серия 4 дня» */
  summary: string;
  payload: () => GuestProgressPayload | undefined;
}

interface CommonProps {
  carry?: GuestCarry;
  /** Отправка очереди outbox перед переносом (поток 4.7.4, шаг 4). */
  beforeSubmit?: () => Promise<void>;
  onSuccess: (result: AuthResult, carried: boolean) => void;
}

function OfflineNote() {
  return <p className={s.note}>Нет соединения. Войти можно, когда сеть появится — прогресс гостя сохранится</p>;
}

function CarryCheckbox({ carry, checked, onChange }: { carry: GuestCarry; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className={s.carry}>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span>
        Перенести в аккаунт прогресс гостя: <b>{carry.summary}</b>
      </span>
    </label>
  );
}

export function RegisterForm({ carry, beforeSubmit, onSuccess, onEmailTaken }: CommonProps & { onEmailTaken: (email: string) => void }) {
  const formRef = useRef<HTMLFormElement>(null);
  const online = useAppSelector(selectOnline);
  const [register, { isLoading }] = useRegisterMutation();
  const [v, setV] = useState({ name: '', email: '', password: '', consent: false });
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [serverErrors, setServerErrors] = useState<Errors>({});
  const [apiError, setApiError] = useState<ApiError | null>(null);
  const [carryOn, setCarryOn] = useState(true);

  const clientErrors = validateRegister(v);
  const shown = (f: string) => serverErrors[f] ?? (touched[f] ? clientErrors[f] : undefined);
  const set = (f: keyof typeof v) => (val: string | boolean) => {
    setV((p) => ({ ...p, [f]: val }));
    setServerErrors((p) => ({ ...p, [f]: '' }));
  };

  async function submit(e: FormEvent) {
    e.preventDefault();
    setTouched({ name: true, email: true, password: true, consent: true });
    setApiError(null);
    if (Object.keys(clientErrors).length) return focusFirstError(formRef.current, clientErrors);
    try {
      await beforeSubmit?.();
      const guest_progress = carry && carryOn ? carry.payload() : undefined;
      const res = await register({
        name: v.name.trim(),
        email: v.email.trim(),
        password: v.password,
        consent: v.consent,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'Europe/Moscow',
        ...(guest_progress ? { guest_progress } : {}),
      }).unwrap();
      onSuccess(res, !!guest_progress);
    } catch (err) {
      const api = asApiError(err);
      const fe = fieldErrors(api);
      setServerErrors(fe);
      setApiError(api);
      focusFirstError(formRef.current, fe);
    }
  }

  return (
    <form ref={formRef} onSubmit={submit} noValidate>
      <Input label="Имя" name="name" autoComplete="name" value={v.name} error={shown('name')}
        onChange={(e) => set('name')(e.target.value)} onBlur={() => setTouched((t) => ({ ...t, name: true }))} />
      <Input label="Почта" name="email" type="email" autoComplete="email" value={v.email} error={shown('email')}
        onChange={(e) => set('email')(e.target.value)} onBlur={() => setTouched((t) => ({ ...t, email: true }))} />
      <Input label="Пароль" name="password" type="password" autoComplete="new-password" value={v.password}
        error={shown('password')} hint="Не короче 8 символов"
        onChange={(e) => set('password')(e.target.value)} onBlur={() => setTouched((t) => ({ ...t, password: true }))} />
      {carry && <CarryCheckbox carry={carry} checked={carryOn} onChange={setCarryOn} />}
      <label className={s.consent}>
        <input type="checkbox" name="consent" checked={v.consent} onChange={(e) => set('consent')(e.target.checked)} />
        <span>Согласен на обработку персональных данных (имя и почта) для работы аккаунта</span>
      </label>
      {shown('consent') && <p className={s.error} role="alert">{shown('consent')}</p>}

      {apiError?.code === 'email_taken' ? (
        <div className={s.alert} role="alert">
          {apiError.message}
          <Button variant="link" onClick={() => onEmailTaken(v.email.trim())}>Войти</Button>
        </div>
      ) : (
        apiError && !Object.keys(serverErrors).some((k) => serverErrors[k]) && (
          <p className={s.alert} role="alert">{apiError.message}</p>
        )
      )}
      {!online && <OfflineNote />}
      <Button type="submit" block loading={isLoading} disabled={!online}>
        Создать аккаунт
      </Button>
    </form>
  );
}

export function LoginForm({ carry, beforeSubmit, onSuccess, initialEmail = '' }: CommonProps & { initialEmail?: string }) {
  const formRef = useRef<HTMLFormElement>(null);
  const online = useAppSelector(selectOnline);
  const [login, { isLoading }] = useLoginMutation();
  const [v, setV] = useState({ email: initialEmail, password: '' });
  const [errors, setErrors] = useState<Errors>({});
  const [apiError, setApiError] = useState<ApiError | null>(null);
  const [carryOn, setCarryOn] = useState(true);
  const locked = apiError?.status === 423;

  async function submit(e: FormEvent) {
    e.preventDefault();
    const ce = validateLogin(v);
    setErrors(ce);
    setApiError(null);
    if (Object.keys(ce).length) return focusFirstError(formRef.current, ce);
    try {
      await beforeSubmit?.();
      // Журнал гостя при входе объединяется с прогрессом аккаунта (UC-03 4б)
      const guest_progress = carry && carryOn ? carry.payload() : undefined;
      const res = await login({ email: v.email.trim(), password: v.password, ...(guest_progress ? { guest_progress } : {}) }).unwrap();
      onSuccess(res, !!guest_progress);
    } catch (err) {
      const api = asApiError(err);
      setErrors(fieldErrors(api));
      setApiError(api);
    }
  }

  return (
    <form ref={formRef} onSubmit={submit} noValidate>
      <Input label="Почта" name="email" type="email" autoComplete="email" value={v.email} error={errors.email}
        onChange={(e) => setV((p) => ({ ...p, email: e.target.value }))} />
      <Input label="Пароль" name="password" type="password" autoComplete="current-password" value={v.password}
        error={errors.password} onChange={(e) => setV((p) => ({ ...p, password: e.target.value }))} />
      {carry && <CarryCheckbox carry={carry} checked={carryOn} onChange={setCarryOn} />}
      {/* При неверных данных — общее сообщение без уточнения, что именно неверно */}
      {apiError && !errors.email && !errors.password && <p className={s.alert} role="alert">{apiError.message}</p>}
      {!online && <OfflineNote />}
      <Button type="submit" block loading={isLoading} disabled={!online || locked}>
        Войти
      </Button>
    </form>
  );
}
