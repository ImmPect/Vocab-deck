/**
 * Сессия разбора карточек (раздел 4.6.3 ПР3): очередь и индекс — локальное состояние
 * экрана. Очередь фиксируется при первой загрузке, чтобы фоновое обновление данных
 * не перемешивало карточки посреди разбора. Прерванный разбор оставляет
 * неразобранные слова во входящих (UC-01 7а): на сервер уходят только оценённые.
 */
import { useCallback, useEffect, useState } from 'react';
import type { AnswerMode, BatchAnswer, Direction } from '@/entities/progress';
import { nowIso, uuid } from '@/shared/lib';

export interface ReviewItem {
  key: string;
  word_id: number;
  direction: Direction;
}

export function useReviewSession<T extends ReviewItem>(source: T[] | undefined) {
  const [queue, setQueue] = useState<T[] | null>(null);
  const [index, setIndex] = useState(0);
  const [stats, setStats] = useState({ remembered: 0, again: 0 });

  useEffect(() => {
    if (queue === null && source) setQueue(source);
  }, [source, queue]);

  const current = queue && index < queue.length ? queue[index] : null;

  const rate = useCallback(
    (remembered: boolean) => {
      setStats((s) => (remembered ? { ...s, remembered: s.remembered + 1 } : { ...s, again: s.again + 1 }));
      setIndex((i) => i + 1);
    },
    [],
  );

  const restart = useCallback(() => {
    setQueue(null);
    setIndex(0);
    setStats({ remembered: 0, again: 0 });
  }, []);

  return {
    current,
    index,
    total: queue?.length ?? 0,
    done: queue !== null && index >= queue.length,
    ready: queue !== null,
    stats,
    rate,
    restart,
  };
}

/** Ответ самооценки для POST /answers/batch (mode = review | self_check). */
export function buildSelfAnswer(
  mode: Extract<AnswerMode, 'review' | 'self_check'>,
  item: { word_id: number; direction: Direction },
  isCorrect: boolean,
  currentBox?: number,
): BatchAnswer {
  return {
    client_event_id: uuid(),
    mode,
    word_id: item.word_id,
    direction: item.direction,
    is_correct: isCorrect,
    answered_at: nowIso(),
    ...(currentBox ? { current_box: currentBox } : {}),
  };
}
