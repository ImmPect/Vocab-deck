/**
 * Проигрывание озвучки: MP3 с сервера (нейросетевой голос, GET /words/{id}/audio),
 * при сбое — английский голос браузера. Одновременно звучит только один источник.
 */
import { API_URL } from '@/shared/config';
import { speak, stopSpeech, type SpeechAccent } from '@/shared/lib';

export type SpeakPart = 'word' | 'example';

export interface SpeakRequest {
  text: string;
  wordId?: number;
  part?: SpeakPart;
  accent: SpeechAccent;
}

const cache = new Map<string, HTMLAudioElement>();
let current: HTMLAudioElement | null = null;

export const audioUrl = (wordId: number, part: SpeakPart, accent: SpeechAccent) =>
  `${API_URL}/words/${wordId}/audio?${new URLSearchParams({ part, accent })}`;

function stopAll() {
  if (current) {
    current.pause();
    current.currentTime = 0;
  }
  stopSpeech();
}

async function playUrl(url: string): Promise<void> {
  let audio = cache.get(url);
  if (!audio) {
    audio = new Audio();
    // API на другом поддомене: cookie сессии нужна для слов личного списка
    if (/^https?:/.test(url)) audio.crossOrigin = 'use-credentials';
    audio.preload = 'auto';
    audio.src = url;
    cache.set(url, audio);
  }
  current = audio;
  audio.currentTime = 0;
  try {
    await audio.play();
  } catch (e) {
    cache.delete(url); // следующая попытка запросит файл заново
    throw e;
  }
}

/** Загружает озвучку заранее, чтобы по нажатию звук начинался без задержки. */
export function preloadAudio(wordId: number, part: SpeakPart, accent: SpeechAccent) {
  const url = audioUrl(wordId, part, accent);
  if (cache.has(url)) return;
  const audio = new Audio();
  if (/^https?:/.test(url)) audio.crossOrigin = 'use-credentials';
  audio.preload = 'auto';
  audio.src = url;
  cache.set(url, audio);
}

/** 'server' — звучит MP3, 'browser' — голос браузера, 'none' — озвучить нечем. */
export async function playSpeech({ text, wordId, part = 'word', accent }: SpeakRequest): Promise<'server' | 'browser' | 'none'> {
  stopAll();
  if (wordId) {
    try {
      await playUrl(audioUrl(wordId, part, accent));
      return 'server';
    } catch {
      /* сервер недоступен или нет сети — запасной вариант ниже */
    }
  }
  return (await speak(text, accent)) ? 'browser' : 'none';
}
