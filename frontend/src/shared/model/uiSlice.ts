/**
 * Slice ui (раздел 4.6.2 ПР3): уведомления, признак офлайн-режима,
 * флаг «предложение регистрации уже показано» (NFR-O-03), подсказки первого запуска (NFR-O-02).
 * Не содержит бизнес-логики, поэтому лежит в shared и доступен любому слою.
 */
import { createSlice, type PayloadAction } from '@reduxjs/toolkit';

export type ToastKind = 'success' | 'error' | 'info';

export interface Toast {
  id: number;
  text: string;
  kind: ToastKind;
}

/** Произношение озвучки: британское (как транскрипции в словаре) или американское. */
export type Accent = 'uk' | 'us';

export interface UiState {
  toasts: Toast[];
  accent: Accent;
  online: boolean;
  registerPromptShown: boolean;
  onboardingStep: number;
  onboardingDone: boolean;
}

export const ONBOARDING_STEPS = 3;

const initialState: UiState = {
  toasts: [],
  accent: 'uk',
  online: typeof navigator === 'undefined' ? true : navigator.onLine,
  registerPromptShown: false,
  onboardingStep: 0,
  onboardingDone: false,
};

let nextToastId = 1;

export const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    toastShown: {
      reducer(state, action: PayloadAction<Toast>) {
        state.toasts.push(action.payload);
      },
      prepare(text: string, kind: ToastKind = 'success') {
        return { payload: { id: nextToastId++, text, kind } };
      },
    },
    toastHidden(state, action: PayloadAction<number>) {
      state.toasts = state.toasts.filter((t) => t.id !== action.payload);
    },
    networkChanged(state, action: PayloadAction<boolean>) {
      state.online = action.payload;
    },
    registerPromptShown(state) {
      state.registerPromptShown = true;
    },
    onboardingStepChanged(state, action: PayloadAction<number>) {
      state.onboardingStep = action.payload;
      if (action.payload >= ONBOARDING_STEPS) state.onboardingDone = true;
    },
    onboardingSkipped(state) {
      state.onboardingDone = true;
    },
    onboardingRestored(state, action: PayloadAction<boolean>) {
      state.onboardingDone = action.payload;
    },
    accentChanged(state, action: PayloadAction<Accent>) {
      state.accent = action.payload;
    },
  },
});

export const ui = uiSlice.actions;

type WithUi = { ui: UiState };
export const selectToast = (s: WithUi): Toast | undefined => s.ui.toasts[0];
export const selectOnline = (s: WithUi) => s.ui.online;
export const selectRegisterPromptShown = (s: WithUi) => s.ui.registerPromptShown;
export const selectAccent = (s: WithUi) => s.ui.accent;
export const selectOnboarding = (s: WithUi) => ({ step: s.ui.onboardingStep, done: s.ui.onboardingDone });
