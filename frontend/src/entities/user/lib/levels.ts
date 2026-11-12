/** Должность по опыту — для гостя, у которого нет GET /me (проекция журнала, раздел 4.6.2). */
import type { Level, NextLevel } from '../model/types';

export function levelFor(xp: number, levels: Level[]): Level | undefined {
  let found: Level | undefined;
  for (const l of [...levels].sort((a, b) => a.min_xp - b.min_xp)) if (xp >= l.min_xp) found = l;
  return found;
}

export function nextLevelFor(xp: number, levels: Level[]): NextLevel | null {
  const next = [...levels].sort((a, b) => a.min_xp - b.min_xp).find((l) => l.min_xp > xp);
  return next ? { code: next.code, title: next.title, min_xp: next.min_xp, xp_left: next.min_xp - xp } : null;
}

/** Первая буква имени для «фото» на пропуске. */
export const initialOf = (name: string | undefined) => (name?.trim()[0] ?? '?').toUpperCase();
