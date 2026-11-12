/** Очередь неотправленных ответов в localStorage (табл. 4.6 ПР3). */
import { STORAGE_KEYS } from '@/shared/config';
import { readVersioned, writeVersioned, type KeyValueStore, type Migration } from '@/shared/lib';
import { OUTBOX_FORMAT_VERSION, type OutboxItem } from '../model/outboxSlice';

export const outboxMigrations: Record<number, Migration> = {};

interface StoredOutbox {
  format_version: number;
  items: OutboxItem[];
}

export const loadOutbox = (store: KeyValueStore): OutboxItem[] =>
  readVersioned<StoredOutbox>(store, STORAGE_KEYS.outbox, { format_version: OUTBOX_FORMAT_VERSION, items: [] }, outboxMigrations).items;

export function saveOutbox(store: KeyValueStore, items: OutboxItem[]): void {
  if (items.length) writeVersioned(store, STORAGE_KEYS.outbox, { format_version: OUTBOX_FORMAT_VERSION, items } as StoredOutbox);
  else store.remove(STORAGE_KEYS.outbox);
}
