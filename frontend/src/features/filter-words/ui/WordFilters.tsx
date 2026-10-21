/**
 * Поиск и фильтры списка слов администратора (табл. 4.2 ПР3). Применённые фильтры
 * хранятся в адресе страницы — ссылкой можно поделиться; текст поиска применяется
 * с задержкой 300 мс, до этого он — локальное состояние поля.
 */
import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { Deck } from '@/entities/deck';
import { STATUS_LABEL, type AdminWordsFilter, type WordStatus } from '@/entities/word';
import { useDebounced } from '@/shared/lib';
import { darkControlClass } from '@/shared/ui';
import s from './WordFilters.module.css';

/** Фильтр из адреса: ?q=&deck_id=&status=&page= */
export function useWordFilter(): AdminWordsFilter {
  const [params] = useSearchParams();
  const q = params.get('q') ?? '';
  return {
    q: q.trim().length >= 2 ? q.trim() : undefined,
    deck_id: Number(params.get('deck_id')) || undefined,
    status: (params.get('status') as WordStatus | null) ?? undefined,
    page: Number(params.get('page')) || 1,
    limit: 20,
  };
}

export function WordFilters({ decks }: { decks: Deck[] }) {
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState(params.get('q') ?? '');
  const debounced = useDebounced(q, 300);

  const patch = (key: string, value: string) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (value) next.set(key, value);
        else next.delete(key);
        next.delete('page');
        return next;
      },
      { replace: true },
    );

  useEffect(() => {
    if ((params.get('q') ?? '') !== debounced) patch('q', debounced);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced]);

  return (
    <div className={s.tools} role="search">
      <input
        className={`${darkControlClass} ${s.search}`}
        type="search"
        placeholder="Поиск по слову или переводу"
        aria-label="Поиск по слову или переводу"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      <select className={darkControlClass} aria-label="Отдел" value={params.get('deck_id') ?? ''} onChange={(e) => patch('deck_id', e.target.value)}>
        <option value="">Все отделы</option>
        {decks
          .filter((d) => d.kind === 'shared')
          .map((d) => (
            <option key={d.id} value={d.id}>
              {d.title}
            </option>
          ))}
      </select>
      <select className={darkControlClass} aria-label="Статус" value={params.get('status') ?? ''} onChange={(e) => patch('status', e.target.value)}>
        <option value="">Все статусы</option>
        {(Object.keys(STATUS_LABEL) as WordStatus[]).map((st) => (
          <option key={st} value={st}>
            {STATUS_LABEL[st]}
          </option>
        ))}
      </select>
    </div>
  );
}
