/** DTO модуля words (разделы 3.6, 3.8 ПР3). */

export type WordStatus = 'draft' | 'published' | 'archived';

export interface Word {
  id: number;
  deck_id: number;
  en: string;
  ipa: string | null;
  ru: string;
  example: string | null;
  status: WordStatus;
}

export interface WordFields {
  en: string;
  ru: string;
  ipa?: string | null;
  example?: string | null;
}

export interface AdminWord extends Omit<Word, 'deck_id'> {
  deck: { id: number; title: string };
  created_by: { id: number; name: string } | null;
  updated_by: { id: number; name: string } | null;
  created_at: string;
  updated_at: string;
  learners_count: number;
}

export interface AdminWordsFilter {
  q?: string;
  deck_id?: number;
  status?: WordStatus;
  page?: number;
  limit?: number;
}

export const STATUS_LABEL: Record<WordStatus, string> = {
  published: 'Опубликовано',
  draft: 'Черновик',
  archived: 'Архив',
};

/** Допустимые символы слова: латиница, пробел, дефис, апостроф (как на сервере, words/schemas.py). */
export const EN_PATTERN = /^[A-Za-z' -]+$/;
