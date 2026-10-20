/** DTO модуля decks (раздел 3.5 ПР3). */

export type UnlockRule = { min_xp: number } | { learned_in_deck: { deck_id: number; count: number } };

export interface DeckProgress {
  learned: number;
  in_progress: number;
  new: number;
}

export interface Deck {
  id: number;
  kind: 'shared' | 'personal';
  title: string;
  sort_order: number;
  words_count: number;
  /** null для гостя: прогресс гостя — в локальном журнале. */
  progress: DeckProgress | null;
  locked: boolean;
  unlock_rule: UnlockRule | null;
  /** Готовый текст условия открытия (NFR-O-04). */
  unlock_condition: string | null;
  can_edit?: boolean;
}

export interface ImportReport {
  total_rows: number;
  added: number;
  skipped: { line: number; en: string | null; reason_code: string; reason: string }[];
}
