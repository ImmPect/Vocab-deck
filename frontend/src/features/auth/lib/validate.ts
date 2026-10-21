/** Клиентская проверка форм: подсказывает сразу, окончательно проверяет сервер (поток 4.7.4, шаг 3). */

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export type Errors = Record<string, string>;

export function validateRegister(v: { name: string; email: string; password: string; consent: boolean }): Errors {
  const e: Errors = {};
  if (!v.name.trim()) e.name = 'Укажите имя';
  else if (v.name.trim().length > 100) e.name = 'Имя должно содержать не более 100 символов';
  if (!EMAIL_RE.test(v.email.trim())) e.email = 'Укажите почту в формате name@example.ru';
  if (v.password.length < 8) e.password = 'Не короче 8 символов';
  else if (v.password.length > 128) e.password = 'Не длиннее 128 символов';
  if (!v.consent) e.consent = 'Нужно согласие на обработку персональных данных';
  return e;
}

export function validateLogin(v: { email: string; password: string }): Errors {
  const e: Errors = {};
  if (!v.email.trim()) e.email = 'Введите почту';
  if (!v.password) e.password = 'Введите пароль';
  return e;
}

/** Фокус на первое ошибочное поле (табл. 4.8, ответ 422). */
export function focusFirstError(form: HTMLFormElement | null, errors: Errors) {
  const first = Object.keys(errors)[0];
  if (first) form?.querySelector<HTMLElement>(`[name="${first}"]`)?.focus();
}
