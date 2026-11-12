/**
 * Адаптер хранилища (раздел 4.6.4 ПР3).
 *
 * - NFR-R-01: если localStorage недоступен (приватный режим, запрет, переполнение),
 *   тот же интерфейс работает с объектом в памяти — обучение не блокируется.
 * - NFR-R-03: каждая запись хранит номер версии формата; старые данные проходят
 *   цепочку миграций v1 → v2 → …; повреждённые данные откладываются под резервный ключ.
 */

export interface KeyValueStore {
  get(key: string): string | null;
  set(key: string, value: string): void;
  remove(key: string): void;
  /** false — данные живут только до закрытия вкладки. */
  readonly persistent: boolean;
}

export function memoryStore(): KeyValueStore {
  const map = new Map<string, string>();
  return {
    get: (k) => map.get(k) ?? null,
    set: (k, v) => void map.set(k, v),
    remove: (k) => void map.delete(k),
    persistent: false,
  };
}

/** Проверяет запись и чтение пробного значения; при неудаче — хранилище в памяти. */
export function createStorage(backend: Storage | undefined = globalThis.localStorage): KeyValueStore {
  const PROBE = 'vocabdeck:probe';
  try {
    if (!backend) throw new Error('no storage');
    backend.setItem(PROBE, '1');
    const ok = backend.getItem(PROBE) === '1';
    backend.removeItem(PROBE);
    if (!ok) throw new Error('probe failed');
  } catch {
    return memoryStore();
  }
  const fallback = memoryStore();
  return {
    get: (k) => {
      try {
        return backend.getItem(k);
      } catch {
        return fallback.get(k);
      }
    },
    set: (k, v) => {
      try {
        backend.setItem(k, v);
      } catch {
        fallback.set(k, v); // переполнение: хотя бы до закрытия вкладки
      }
    },
    remove: (k) => {
      try {
        backend.removeItem(k);
      } catch {
        fallback.remove(k);
      }
    },
    persistent: true,
  };
}

export const storage: KeyValueStore = createStorage();

/** Миграция данных с версии N на N+1. */
export type Migration = (data: Record<string, unknown>) => Record<string, unknown>;

export interface Versioned {
  format_version: number;
}

/**
 * Читает запись с номером версии. Отсутствует — empty; старая версия — миграции
 * и запись обратно; не разбирается или из будущей версии — резервная копия и empty.
 */
export function readVersioned<T extends Versioned>(
  store: KeyValueStore,
  key: string,
  empty: T,
  migrations: Record<number, Migration> = {},
): T {
  const raw = store.get(key);
  if (raw === null) return empty;
  try {
    let data = JSON.parse(raw) as Record<string, unknown>;
    let version = Number(data.format_version);
    if (!Number.isInteger(version) || version < 1 || version > empty.format_version) throw new Error('version');
    while (version < empty.format_version) {
      const migrate = migrations[version];
      if (!migrate) throw new Error(`no migration from v${version}`);
      data = { ...migrate(data), format_version: version + 1 };
      version += 1;
    }
    if (raw !== JSON.stringify(data)) store.set(key, JSON.stringify(data));
    return data as unknown as T;
  } catch {
    store.set(`${key}:corrupt`, raw);
    store.remove(key);
    return empty;
  }
}

export function writeVersioned(store: KeyValueStore, key: string, value: Versioned): void {
  store.set(key, JSON.stringify(value));
}
