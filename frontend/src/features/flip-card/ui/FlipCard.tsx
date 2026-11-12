/**
 * Карточка слова с двумя сторонами (табл. 4.2 ПР3). Переворачивается по клику,
 * Enter или Пробелу за 0,5 с; при prefers-reduced-motion сторона меняется мгновенно.
 * Флип — локальное состояние компонента: родитель сбрасывает его, меняя key при смене слова.
 * Пользовательский текст выводится как текст — React экранирует его (NFR-S-06).
 */
import { useState, type KeyboardEvent, type ReactNode } from 'react';
import s from './FlipCard.module.css';

export interface FlipCardWord {
  en: string;
  ipa?: string | null;
  ru: string;
  example?: string | null;
  tag?: string;
}

export function FlipCard({
  word,
  speakSlot,
  exampleSlot,
  onFlip,
}: {
  word: FlipCardWord;
  /** Кнопка озвучки (фича speak-word) — вставляет страница. */
  speakSlot?: ReactNode;
  /** Кнопка озвучки примера на обороте. */
  exampleSlot?: ReactNode;
  onFlip?: (flipped: boolean) => void;
}) {
  const [flipped, setFlipped] = useState(false);
  const toggle = () => {
    setFlipped((f) => !f);
    onFlip?.(!flipped);
  };
  const onKey = (e: KeyboardEvent) => {
    if (e.target !== e.currentTarget) return;
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      toggle();
    }
  };

  return (
    <div
      className={`${s.flip} ${flipped ? s.on : ''}`}
      role="button"
      tabIndex={0}
      aria-pressed={flipped}
      aria-label={flipped ? `Перевод: ${word.ru}. Нажмите, чтобы вернуть слово` : `${word.en}. Нажмите, чтобы увидеть перевод`}
      onClick={toggle}
      onKeyDown={onKey}
    >
      <div className={s.inner}>
        <div className={`${s.face} paper-lines`} aria-hidden={flipped}>
          {word.tag && <span className={s.tag}>{word.tag}</span>}
          <span className={s.en} lang="en">
            {word.en}
          </span>
          <span className={s.ipa}>
            {word.ipa}
            {speakSlot && (
              <span onClick={(e) => e.stopPropagation()} onKeyDown={(e) => e.stopPropagation()}>
                {speakSlot}
              </span>
            )}
          </span>
          <span className={s.hint}>Нажмите или Пробел — перевод</span>
        </div>
        <div className={`${s.face} ${s.back} paper-lines`} aria-hidden={!flipped}>
          <span className={s.ru}>{word.ru}</span>
          {word.example && (
            <span className={s.exRow}>
              <span className={s.ex} lang="en">
                {word.example}
              </span>
              {/* кнопка только на открытом обороте — иначе фокус попадал бы на невидимую сторону */}
              {exampleSlot && flipped && (
                <span onClick={(e) => e.stopPropagation()} onKeyDown={(e) => e.stopPropagation()}>
                  {exampleSlot}
                </span>
              )}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
