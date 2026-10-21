/**
 * Сборка Redux store (Flux, раздел 4.2 ПР3): slices + кэш RTK Query + listener middleware.
 * До первой отрисовки из хранилища восстанавливаются журнал гостя и очередь
 * (поток 4.7.1, шаг 2) — с проверкой доступности localStorage и миграциями формата.
 */
import { combineReducers, configureStore } from '@reduxjs/toolkit';
import { setupListeners } from '@reduxjs/toolkit/query';
import { guestProgressSlice, loadGuestProgress } from '@/features/guest-progress-sync';
import { emptyOutbox, flushOutbox, loadOutbox, outbox, outboxSlice } from '@/features/offline-outbox';
import { gameSlice } from '@/features/play-deadline';
import { sessionSlice } from '@/entities/user';
import { baseApi } from '@/shared/api';
import { STORAGE_KEYS } from '@/shared/config';
import { storage } from '@/shared/lib';
import { ui, uiSlice } from '@/shared/model';
import { listener } from './listeners';

const rootReducer = combineReducers({
  [baseApi.reducerPath]: baseApi.reducer,
  session: sessionSlice.reducer,
  ui: uiSlice.reducer,
  game: gameSlice.reducer,
  guestProgress: guestProgressSlice.reducer,
  outbox: outboxSlice.reducer,
});

function readPrefs(): { onboarding_done?: boolean; accent?: string } {
  try {
    return JSON.parse(storage.get(STORAGE_KEYS.prefs) ?? '{}');
  } catch {
    return {};
  }
}

export function makeStore() {
  const store = configureStore({
    reducer: rootReducer,
    preloadedState: {
      guestProgress: loadGuestProgress(storage),
      outbox: { ...emptyOutbox(), items: loadOutbox(storage) },
    },
    middleware: (getDefault) => getDefault().prepend(listener.middleware).concat(baseApi.middleware),
    devTools: import.meta.env.DEV, // Redux DevTools только в режиме разработки
  });
  setupListeners(store.dispatch); // refetchOnFocus / refetchOnReconnect
  const prefs = readPrefs();
  if (prefs.onboarding_done) store.dispatch(ui.onboardingRestored(true));
  if (prefs.accent === 'uk' || prefs.accent === 'us') store.dispatch(ui.accentChanged(prefs.accent));
  return store;
}

export const store = makeStore();

export type AppStore = typeof store;

declare global {
  /** Типы для нижних слоёв (shared/model/hooks.ts) без импорта из слоя app. */
  type AppRootState = ReturnType<typeof rootReducer>;
  type AppStoreDispatch = AppStore['dispatch'];
}

/** События браузера online/offline и синхронизация вкладок через событие storage (раздел 4.6.4). */
export function connectBrowserEvents(s: AppStore) {
  const onOnline = () => s.dispatch(ui.networkChanged(true));
  const onOffline = () => s.dispatch(ui.networkChanged(false));
  const onVisible = () => {
    if (document.visibilityState === 'visible') void s.dispatch(flushOutbox());
  };
  const onStorage = (e: StorageEvent) => {
    if (e.key === STORAGE_KEYS.outbox) s.dispatch(outbox.restored(loadOutbox(storage)));
    if (e.key === STORAGE_KEYS.guest) s.dispatch(guestProgressSlice.actions.restored(loadGuestProgress(storage)));
  };
  window.addEventListener('online', onOnline);
  window.addEventListener('offline', onOffline);
  document.addEventListener('visibilitychange', onVisible);
  window.addEventListener('storage', onStorage);
  void s.dispatch(flushOutbox()); // при старте приложения непустая очередь отправляется
  return () => {
    window.removeEventListener('online', onOnline);
    window.removeEventListener('offline', onOffline);
    document.removeEventListener('visibilitychange', onVisible);
    window.removeEventListener('storage', onStorage);
  };
}
