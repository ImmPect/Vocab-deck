/** Кнопки самооценки «Ещё учить» / «Помню» и клавиши ← / → (NFR-U-02). */
import { Button } from '@/shared/ui';
import { useHotkeys } from '@/shared/lib';
import s from './ReviewControls.module.css';

export function ReviewControls({ onRate, disabled = false }: { onRate: (remembered: boolean) => void; disabled?: boolean }) {
  useHotkeys({ ArrowLeft: () => onRate(false), ArrowRight: () => onRate(true) }, !disabled);
  return (
    <div className={s.controls}>
      <Button variant="game" onClick={() => onRate(false)} disabled={disabled} aria-keyshortcuts="ArrowLeft">
        ← Ещё учить
      </Button>
      <Button variant="primary" onClick={() => onRate(true)} disabled={disabled} aria-keyshortcuts="ArrowRight">
        Помню →
      </Button>
    </div>
  );
}
