/** Скелетоны оболочки и страницы — пока грузится чанк или не известен статус сессии (раздел 4.8.2). */
import { useDelayedFlag } from '@/shared/lib';
import { Skeleton } from '@/shared/ui';
import s from './ShellSkeleton.module.css';

export function PageSkeleton() {
  const shown = useDelayedFlag(true);
  if (!shown) return null;
  return (
    <div className={s.page} aria-busy="true" aria-label="Загрузка">
      <Skeleton height={44} width="40%" />
      <Skeleton height={16} width="70%" />
      <div className={s.grid}>
        <Skeleton height={190} />
        <Skeleton height={190} />
      </div>
    </div>
  );
}

export function ShellSkeleton({ bare = false }: { bare?: boolean }) {
  const shown = useDelayedFlag(true);
  if (!shown) return null;
  return (
    <div className={bare ? s.bare : s.shell} aria-busy="true" aria-label="Загрузка">
      {!bare && <div className={s.side} />}
      <PageSkeleton />
    </div>
  );
}
