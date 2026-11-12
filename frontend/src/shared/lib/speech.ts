/**
 * Запасная озвучка через Web Speech API (speechSynthesis) — когда сервер не отдал MP3.
 *
 * Голоса зависят от системы: в русской Windows по умолчанию стоят только русские голоса,
 * и они читают английское слово с сильным акцентом. Поэтому голос выбирается явно:
 * только английский, нейросетевые и онлайн-голоса — выше локальных. Если английского
 * голоса нет, функция честно возвращает false, а не читает слово русским голосом.
 */

export type SpeechAccent = 'uk' | 'us';

export const speechSupported = (): boolean =>
  typeof window !== 'undefined' && 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window;

interface VoiceLike {
  name: string;
  lang: string;
  localService: boolean;
}

/** Оценка голоса: < 0 — не английский; чем больше, тем естественнее звучит. */
export function scoreVoice(v: VoiceLike, accent: SpeechAccent): number {
  const lang = v.lang.replace('_', '-').toLowerCase();
  if (!lang.startsWith('en')) return -1;
  let score = 1;
  if (/natural|neural|premium|enhanced/i.test(v.name)) score += 8;
  if (/google|online/i.test(v.name)) score += 4;
  if (!v.localService) score += 1;
  if (lang === (accent === 'uk' ? 'en-gb' : 'en-us')) score += 3;
  return score;
}

export function pickVoice<T extends VoiceLike>(voices: T[], accent: SpeechAccent): T | undefined {
  let best: T | undefined;
  let bestScore = -1;
  for (const v of voices) {
    const s = scoreVoice(v, accent);
    if (s > bestScore) {
      best = v;
      bestScore = s;
    }
  }
  return bestScore > 0 ? best : undefined;
}

/** Список голосов в Chrome приходит асинхронно — ждём событие voiceschanged, но не дольше 1 с. */
function loadVoices(): Promise<SpeechSynthesisVoice[]> {
  const now = window.speechSynthesis.getVoices();
  if (now.length) return Promise.resolve(now);
  return new Promise((resolve) => {
    const done = () => resolve(window.speechSynthesis.getVoices());
    window.speechSynthesis.addEventListener('voiceschanged', done, { once: true });
    setTimeout(done, 1000);
  });
}

export async function hasEnglishVoice(): Promise<boolean> {
  return speechSupported() && !!pickVoice(await loadVoices(), 'uk');
}

/** Произносит текст английским голосом. false — английского голоса в системе нет. */
export async function speak(text: string, accent: SpeechAccent = 'uk'): Promise<boolean> {
  if (!speechSupported()) return false;
  const voice = pickVoice(await loadVoices(), accent);
  if (!voice) return false;
  const u = new SpeechSynthesisUtterance(text);
  u.voice = voice;
  u.lang = voice.lang;
  u.rate = 0.9;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(u);
  return true;
}

export const stopSpeech = () => {
  if (speechSupported()) window.speechSynthesis.cancel();
};
