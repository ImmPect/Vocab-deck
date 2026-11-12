/**
 * Типизированные хуки Redux. Типы состояния и dispatch объявляет слой app
 * (глобальные AppRootState и AppStoreDispatch в app/store) — так нижние слои
 * получают типы, не импортируя верхний слой (правило зависимостей FSD).
 */
import type { Action, ThunkAction } from '@reduxjs/toolkit';
import { useDispatch, useSelector } from 'react-redux';

export type RootState = AppRootState;
export type AppDispatch = AppStoreDispatch;
export type AppThunk<R = void> = ThunkAction<R, RootState, unknown, Action>;

export const useAppDispatch = useDispatch.withTypes<AppDispatch>();
export const useAppSelector = useSelector.withTypes<RootState>();
