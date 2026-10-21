/** Форматирование чисел, дат и склонение (встроенный Intl, без библиотек — раздел 4.1.3). */

/** plural(5, ['слово', 'слова', 'слов']) → 'слов'. */
export function plural(n: number, forms: [string, string, string]): string {
  const m10 = n % 10;
  const m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return forms[0];
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return forms[1];
  return forms[2];
}

export const countOf = (n: number, forms: [string, string, string]) => `${n} ${plural(n, forms)}`;

export const WORD_FORMS: [string, string, string] = ['слово', 'слова', 'слов'];
export const DAY_FORMS: [string, string, string] = ['день', 'дня', 'дней'];
export const ANSWER_FORMS: [string, string, string] = ['ответ', 'ответа', 'ответов'];

const weekday = new Intl.DateTimeFormat('ru-RU', { weekday: 'short' });
const dayMonth = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long' });

/** '2026-10-20' → 'вт' (дата без часового пояса — как календарный день). */
export const shortWeekday = (isoDate: string) => weekday.format(new Date(`${isoDate}T12:00:00`));
export const longDate = (isoDate: string) => dayMonth.format(new Date(`${isoDate}T12:00:00`));

/** Календарная дата в часовом поясе устройства: 'YYYY-MM-DD'. */
export function localIsoDate(d: Date = new Date()): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export function addDays(isoDate: string, days: number): string {
  const d = new Date(`${isoDate}T12:00:00`);
  d.setDate(d.getDate() + days);
  return localIsoDate(d);
}

/** Время в формате ISO 8601 UTC без миллисекунд, как его ожидает и возвращает API. */
export const nowIso = () => new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');

export function uuid(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID();
  // запасной вариант для старых браузеров (RFC 4122 v4)
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}
