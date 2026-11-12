/**
 * Четыре варианта перевода (табл. 4.2 ПР3). Выбор кликом или клавишами 1–4 (NFR-U-02).
 * Сразу после выбора вариант помечается «выбран», остальные блокируются; цвет
 * «верно/неверно» появляется только после ответа сервера и дублируется текстом и значком.
 */
import { XP_RULE_LABEL } from '@/entities/progress';
import { useHotkeys } from '@/shared/lib';
import { useAppSelector } from '@/shared/model';
import { selectCurrentQuestion, selectGame } from '../model/gameSlice';
import s from './AnswerOptions.module.css';

export function AnswerOptions({ onPick }: { onPick: (index: number) => void }) {
  const g = useAppSelector(selectGame);
  const q = useAppSelector(selectCurrentQuestion);
  const canPick = g.status === 'playing';

  useHotkeys({ '1': () => onPick(0), '2': () => onPick(1), '3': () => onPick(2), '4': () => onPick(3) }, canPick);

  if (!q) return null;

  const stateOf = (i: number): 'ok' | 'bad' | 'picked' | 'idle' => {
    if (g.check) {
      if (i === g.check.correctIndex) return 'ok';
      if (i === g.selected) return 'bad';
      return 'idle';
    }
    return i === g.selected ? 'picked' : 'idle';
  };

  return (
    <>
      <div className={s.opts} role="group" aria-label="Варианты перевода">
        {q.options.map((text, i) => {
          const st = stateOf(i);
          return (
            <button
              key={`${q.question_id}-${i}`}
              type="button"
              className={`${s.opt} ${s[st]}`}
              disabled={!canPick}
              aria-pressed={g.selected === i}
              onClick={() => onPick(i)}
            >
              <span className={s.key} aria-hidden="true">
                {i + 1}
              </span>
              <span className={s.text}>{text}</span>
              {st === 'ok' && <span className={s.mark}>✓<span className="sr-only"> верный ответ</span></span>}
              {st === 'bad' && <span className={s.mark}>✗<span className="sr-only"> ваш ответ, неверно</span></span>}
              {st === 'picked' && <span className={s.mark} aria-hidden="true">…</span>}
            </button>
          );
        })}
      </div>
      <p className={s.feedback} aria-live="polite">
        <Feedback />
      </p>
    </>
  );
}

function Feedback() {
  const g = useAppSelector(selectGame);
  if (g.deferred) return <>Ответ сохранён, проверим при подключении</>;
  if (g.status === 'checking') return <>Проверяем…</>;
  if (!g.check) return null;
  if (g.check.isCorrect) {
    const extra = g.check.breakdown
      .filter((b) => b.rule !== 'correct_answer' && b.rule !== 'combo' && b.xp > 0)
      .map((b) => XP_RULE_LABEL[b.rule] ?? b.rule)
      .join(', ');
    return (
      <>
        <b className={s.okText}>Верно, +{g.check.xp} опыта</b>
        {g.check.combo >= 2 && <span className={s.combo}> · серия ×{g.check.combo}</span>}
        {extra && <span className={s.muted}> ({extra})</span>}
      </>
    );
  }
  return (
    <>
      Правильно: «{g.check.correctText}». Слово вернётся во входящие завтра
    </>
  );
}
