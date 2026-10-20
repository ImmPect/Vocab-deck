/**
 * Озвучка английского слова (US-03) через Web Speech API. Если API недоступен,
 * кнопка неактивна с пояснением (табл. 4.2 ПР3). Сервер не вызывается.
 */
import { speak, speechSupported } from '@/shared/lib';
import s from './SpeakButton.module.css';

export function SpeakButton({ text, onDesk = false }: { text: string; onDesk?: boolean }) {
  const supported = speechSupported();
  const label = supported ? `Прослушать «${text}»` : 'Озвучка не поддерживается в этом браузере';
  return (
    <button
      type="button"
      className={`${s.say} ${onDesk ? s.onDesk : ''}`}
      disabled={!supported}
      aria-label={label}
      title={label}
      onClick={(e) => {
        e.stopPropagation();
        speak(text);
      }}
    >
      <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
        <path d="M4 9v6h4l5 4V5L8 9H4z" fill="currentColor" />
        <path d="M16 8.5a5 5 0 0 1 0 7M18.5 6a8.5 8.5 0 0 1 0 12" stroke="currentColor" strokeWidth="1.8" fill="none" strokeLinecap="round" />
      </svg>
    </button>
  );
}
