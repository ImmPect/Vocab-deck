import { describe, expect, it } from 'vitest';
import { pickVoice } from './speech';

const v = (name: string, lang: string, localService = true) => ({ name, lang, localService });

describe('выбор голоса для запасной озвучки', () => {
  it('русские голоса не используются для английских слов', () => {
    // так выглядит список голосов в русской Windows без языковых пакетов
    const voices = [v('Microsoft Irina - Russian (Russia)', 'ru-RU'), v('Microsoft Pavel - Russian (Russia)', 'ru-RU')];
    expect(pickVoice(voices, 'uk')).toBeUndefined();
  });

  it('нейросетевой голос важнее локального, акцент учитывается', () => {
    const voices = [
      v('Microsoft Hazel - English (United Kingdom)', 'en-GB'),
      v('Microsoft Sonia Online (Natural) - English (United Kingdom)', 'en-GB', false),
      v('Microsoft Aria Online (Natural) - English (United States)', 'en-US', false),
      v('Microsoft Irina - Russian (Russia)', 'ru-RU'),
    ];
    expect(pickVoice(voices, 'uk')?.name).toContain('Sonia');
    expect(pickVoice(voices, 'us')?.name).toContain('Aria');
  });

  it('при отсутствии голоса нужного акцента берётся любой английский', () => {
    expect(pickVoice([v('Google US English', 'en-US', false), v('Irina', 'ru-RU')], 'uk')?.name).toBe('Google US English');
  });
});
