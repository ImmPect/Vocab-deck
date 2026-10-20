/**
 * Граница ошибок на уровне страницы (табл. 4.8, последняя строка): исключение
 * при отрисовке показывает «Что-то пошло не так», а меню остаётся рабочим.
 */
import { Component, type ErrorInfo, type ReactNode } from 'react';
import { Button, EmptyState } from '@/shared/ui';

interface State {
  error: Error | null;
}

export class PageErrorBoundary extends Component<{ children: ReactNode; resetKey?: string }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidUpdate(prev: { resetKey?: string }) {
    // Переход на другой экран сбрасывает ошибку
    if (prev.resetKey !== this.props.resetKey && this.state.error) this.setState({ error: null });
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Ошибка интерфейса', error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <EmptyState
        icon="⚠"
        actions={
          <Button variant="outline" size="small" onClick={() => this.setState({ error: null })}>
            Перезагрузить экран
          </Button>
        }
      >
        Что-то пошло не так. Ваш прогресс сохранён
      </EmptyState>
    );
  }
}
