import { describe, expect, it } from 'vitest';
import { createStorage, memoryStore, readVersioned } from './storage';
import { plural } from './format';

describe('адаптер хранилища (NFR-R-01)', () => {
  it('при недоступном localStorage работает в памяти', () => {
    const broken = {
      setItem: () => {
        throw new Error('QuotaExceededError');
      },
      getItem: () => null,
      removeItem: () => undefined,
    } as unknown as Storage;
    const store = createStorage(broken);
    expect(store.persistent).toBe(false);
    store.set('k', 'v');
    expect(store.get('k')).toBe('v');
  });
});

describe('версия формата и миграции (NFR-R-03)', () => {
  const empty = { format_version: 2, events: [] as unknown[] };

  it('нет записи — пустое состояние', () => {
    expect(readVersioned(memoryStore(), 'x', empty)).toEqual(empty);
  });

  it('старая версия проходит миграцию и записывается обратно', () => {
    const store = memoryStore();
    store.set('x', JSON.stringify({ format_version: 1, log: [1, 2] }));
    const res = readVersioned(store, 'x', empty, { 1: (d) => ({ events: d.log }) });
    expect(res).toEqual({ format_version: 2, events: [1, 2] });
    expect(JSON.parse(store.get('x')!)).toEqual({ format_version: 2, events: [1, 2] });
  });

  it('повреждённые данные откладываются под резервный ключ, приложение не падает', () => {
    const store = memoryStore();
    store.set('x', '{не json');
    expect(readVersioned(store, 'x', empty)).toEqual(empty);
    expect(store.get('x:corrupt')).toBe('{не json');
    expect(store.get('x')).toBeNull();
  });

  it('версия из будущего тоже считается повреждённой', () => {
    const store = memoryStore();
    store.set('x', JSON.stringify({ format_version: 9, events: [] }));
    expect(readVersioned(store, 'x', empty)).toEqual(empty);
  });
});

describe('склонение', () => {
  it.each([
    [1, 'слово'],
    [3, 'слова'],
    [5, 'слов'],
    [11, 'слов'],
    [21, 'слово'],
    [24, 'слова'],
  ])('%i → %s', (n, form) => {
    expect(plural(n, ['слово', 'слова', 'слов'])).toBe(form);
  });
});
