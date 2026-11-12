/** Чтение и запись журнала гостя в localStorage с версией формата (табл. 4.6 ПР3, NFR-R-03). */
import { STORAGE_KEYS } from '@/shared/config';
import { readVersioned, writeVersioned, type KeyValueStore, type Migration } from '@/shared/lib';
import { emptyGuestProgress, type GuestProgressState } from '../model/guestSlice';

/**
 * Цепочка миграций формата: ключ — версия, С которой выполняется переход.
 * Формат v1 — первый; при изменении структуры сюда добавляется 1: (d) => ({ ...v2 }).
 */
export const guestMigrations: Record<number, Migration> = {};

export const loadGuestProgress = (store: KeyValueStore): GuestProgressState =>
  readVersioned(store, STORAGE_KEYS.guest, emptyGuestProgress(), guestMigrations);

export function saveGuestProgress(store: KeyValueStore, state: GuestProgressState): void {
  if (state.events.length) writeVersioned(store, STORAGE_KEYS.guest, state);
  else store.remove(STORAGE_KEYS.guest);
}
