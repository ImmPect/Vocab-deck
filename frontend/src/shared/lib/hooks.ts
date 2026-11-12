/** Общие хуки без бизнес-смысла (слой shared/lib). */
import { useEffect, useRef, useState } from 'react';
import { SKELETON_DELAY_MS } from '../config';

export function useMediaQuery(query: string): boolean {
  const get = () => typeof window !== 'undefined' && window.matchMedia(query).matches;
  const [matches, setMatches] = useState(get);
  useEffect(() => {
    const mql = window.matchMedia(query);
    const onChange = () => setMatches(mql.matches);
    onChange();
    mql.addEventListener('change', onChange);
    return () => mql.removeEventListener('change', onChange);
  }, [query]);
  return matches;
}

/** NFR-U-06: пользователь попросил уменьшить движение. */
export const useReducedMotion = () => useMediaQuery('(prefers-reduced-motion: reduce)');

/** Телефон — меньше 768 px (раздел 4.9 ПР3). */
export const useIsMobile = () => useMediaQuery('(max-width: 767.98px)');

/**
 * Горячие клавиши: { '1': fn, '2': fn, Enter: fn }. Не срабатывают при вводе в поле
 * и с модификаторами, чтобы не мешать сочетаниям браузера.
 */
export function useHotkeys(map: Record<string, () => void>, enabled = true): void {
  const ref = useRef(map);
  ref.current = map;
  useEffect(() => {
    if (!enabled) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const t = e.target as HTMLElement | null;
      if (t && (t.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(t.tagName))) return;
      const fn = ref.current[e.key];
      if (fn) {
        e.preventDefault();
        fn();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [enabled]);
}

/** Флаг загрузки, который включается не раньше чем через 200 мс — без мелькания скелетонов. */
export function useDelayedFlag(flag: boolean, delayMs = SKELETON_DELAY_MS): boolean {
  const [shown, setShown] = useState(false);
  useEffect(() => {
    if (!flag) {
      setShown(false);
      return;
    }
    const t = setTimeout(() => setShown(true), delayMs);
    return () => clearTimeout(t);
  }, [flag, delayMs]);
  return shown;
}

/** Задержка значения (поиск администратора — 300 мс). */
export function useDebounced<T>(value: T, delayMs: number): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), delayMs);
    return () => clearTimeout(t);
  }, [value, delayMs]);
  return v;
}

/** Текущее время, обновляемое с заданным шагом (таймер раунда). */
export function useNow(stepMs: number, enabled = true): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!enabled) return;
    setNow(Date.now());
    const t = setInterval(() => setNow(Date.now()), stepMs);
    return () => clearInterval(t);
  }, [stepMs, enabled]);
  return now;
}
