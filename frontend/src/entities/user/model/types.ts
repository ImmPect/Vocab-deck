/** DTO модуля users (раздел 3.4 ПР3) — поля в snake_case, как в API. */

export type Role = 'user' | 'admin';

export interface LevelShort {
  code: string;
  title: string;
  min_xp: number;
}

/** Должность карьерной лестницы из GET /levels (табл. 4 ТЗ). */
export interface Level extends LevelShort {
  unlocks: string[];
}

export interface NextLevel extends LevelShort {
  xp_left: number;
}

export interface Me {
  id: number;
  name: string;
  email: string;
  role: Role;
  timezone: string;
  xp: number;
  level: LevelShort;
  next_level: NextLevel | null;
  streak_days: number;
  streak_freezes: number;
  inbox_count: number;
  features: { dictation: boolean; ru_en: boolean; unlimited_lists: boolean };
  created_at: string;
}

export interface StatsDay {
  date: string;
  answers: number;
  correct: number;
  xp: number;
}

export interface Stats {
  from: string;
  to: string;
  timezone: string;
  days: StatsDay[];
  totals: { answers: number; correct: number; xp: number; active_days: number; learned_words: number };
}

export interface Achievement {
  code: string;
  title: string;
  earned_at?: string;
  progress?: { current: number; target: number };
}

export interface Achievements {
  earned: Achievement[];
  available: Achievement[];
}

export interface UpdateMeBody {
  name?: string;
  current_password?: string;
  new_password?: string;
  timezone?: string;
}
