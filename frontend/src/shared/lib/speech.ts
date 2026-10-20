/** Обёртка над Web Speech API (speechSynthesis) с проверкой доступности (NFR-U-05). */

export const speechSupported = (): boolean =>
  typeof window !== 'undefined' && 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window;

function englishVoice(): SpeechSynthesisVoice | undefined {
  const voices = window.speechSynthesis.getVoices();
  return voices.find((v) => v.lang === 'en-GB') ?? voices.find((v) => v.lang.startsWith('en'));
}

export function speak(text: string): boolean {
  if (!speechSupported()) return false;
  const u = new SpeechSynthesisUtterance(text);
  u.lang = 'en-GB';
  u.rate = 0.9;
  const voice = englishVoice();
  if (voice) u.voice = voice;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(u);
  return true;
}
