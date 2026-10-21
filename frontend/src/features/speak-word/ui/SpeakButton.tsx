/**
 * Озвучка слова или примера (US-03). Звук — нейросетевой голос с сервера;
 * без сети — английский голос браузера; если нет и его — понятное сообщение.
 */
import { useState } from 'react';
import { selectAccent, ui, useAppDispatch, useAppSelector } from '@/shared/model';
import { playSpeech, type SpeakPart } from '../lib/player';
import s from './SpeakButton.module.css';

export function SpeakButton({
  text,
  wordId,
  part = 'word',
  onDesk = false,
  label,
}: {
  text: string;
  wordId?: number;
  part?: SpeakPart;
  onDesk?: boolean;
  label?: string;
}) {
  const dispatch = useAppDispatch();
  const accent = useAppSelector(selectAccent);
  const [busy, setBusy] = useState(false);
  const title = label ?? (part === 'example' ? 'Прослушать пример' : `Прослушать «${text}»`);

  async function onClick(e: React.MouseEvent) {
    e.stopPropagation();
    setBusy(true);
    const result = await playSpeech({ text, wordId, part, accent });
    setBusy(false);
    if (result === 'none') {
      dispatch(ui.toastShown('Озвучка недоступна: нет связи с сервером, а в системе нет английского голоса', 'info'));
    }
  }

  return (
    <button
      type="button"
      className={`${s.say} ${onDesk ? s.onDesk : ''} ${busy ? s.busy : ''}`}
      aria-label={title}
      title={title}
      aria-busy={busy || undefined}
      onClick={onClick}
      onKeyDown={(e) => e.stopPropagation()}
    >
      <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
        <path d="M4 9v6h4l5 4V5L8 9H4z" fill="currentColor" />
        <path d="M16 8.5a5 5 0 0 1 0 7M18.5 6a8.5 8.5 0 0 1 0 12" stroke="currentColor" strokeWidth="1.8" fill="none" strokeLinecap="round" />
      </svg>
    </button>
  );
}
