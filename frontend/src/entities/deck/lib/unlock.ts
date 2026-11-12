/**
 * Признак locked для гостя: сервер не знает прогресс гостя, поэтому условие
 * открытия unlock_rule сравнивается с локальной проекцией журнала (раздел 4.7.1, п. 9).
 */
import type { Deck } from '../model/types';

export interface LocalProgress {
  xp: number;
  learnedInDeck: (deckId: number) => number;
}

export function isLockedFor(deck: Deck, local: LocalProgress | null): boolean {
  if (!local || !deck.unlock_rule) return deck.locked;
  const rule = deck.unlock_rule;
  if ('min_xp' in rule) return local.xp < rule.min_xp;
  return local.learnedInDeck(rule.learned_in_deck.deck_id) < rule.learned_in_deck.count;
}

/** Процент изученного для шкалы плитки. */
export const learnedShare = (deck: Deck, learnedLocal?: number) => {
  const learned = deck.progress?.learned ?? learnedLocal ?? 0;
  return { learned, total: deck.words_count };
};
