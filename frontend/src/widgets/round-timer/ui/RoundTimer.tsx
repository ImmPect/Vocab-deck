/**
 * Оставшееся время раунда (табл. 4.2 ПР3). Остаток вычисляется из endsAt раз в секунду
 * и в store не пишется — один action в секунду засорял бы журнал DevTools (раздел 4.6.3).
 * На нуле один раз запускается завершение раунда.
 */
import { useEffect, useRef } from 'react';
import { expireRound, selectGame } from '@/features/play-deadline';
import { ROUND } from '@/shared/config';
import { useNow } from '@/shared/lib';
import { useAppDispatch, useAppSelector } from '@/shared/model';
import s from './RoundTimer.module.css';

export function RoundTimer() {
  const dispatch = useAppDispatch();
  const { endsAt, timeLimitS, status } = useAppSelector(selectGame);
  const running = endsAt !== null && ['playing', 'checking', 'checked'].includes(status);
  const now = useNow(250, running);
  const left = endsAt ? Math.max(0, Math.ceil((endsAt - now) / 1000)) : timeLimitS;
  const fired = useRef(false);

  useEffect(() => {
    fired.current = false;
  }, [endsAt]);

  useEffect(() => {
    if (running && left === 0 && !fired.current) {
      fired.current = true;
      dispatch(expireRound());
    }
  }, [running, left, dispatch]);

  const low = left <= ROUND.lowTimeS;
  const pct = (left / timeLimitS) * 100;
  return (
    <div className={s.wrap}>
      <div
        className={`${s.timer} ${low ? s.low : ''}`}
        role="progressbar"
        aria-label="Оставшееся время раунда"
        aria-valuemin={0}
        aria-valuemax={timeLimitS}
        aria-valuenow={left}
        aria-valuetext={`Осталось ${left} с`}
      >
        <i style={{ width: `${pct}%` }} />
      </div>
      <span className={`${s.left} ${low ? s.lowText : ''}`}>осталось {left} с</span>
    </div>
  );
}
