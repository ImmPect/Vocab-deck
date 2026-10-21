/**
 * Итоги раунда (табл. 4.2 ПР3): «Верно N из 5 · +X опыта», повышение или «до повышения
 * осталось …», ответы «ожидают проверки». Гостю после первого раунда — не чаще раза
 * за сессию — предложение сохранить прогресс (NFR-O-03).
 */
import { useEffect, useState } from 'react';
import { selectGame } from '@/features/play-deadline';
import { useLearner } from '@/features/guest-progress-sync';
import { ROUTES } from '@/shared/config';
import { ANSWER_FORMS, countOf } from '@/shared/lib';
import { selectRegisterPromptShown, ui, useAppDispatch, useAppSelector } from '@/shared/model';
import { Button, ButtonLink, Paper } from '@/shared/ui';
import s from './RoundSummary.module.css';

const OUTCOME: Record<string, { icon: string; label: string }> = {
  correct: { icon: '✓', label: 'верно' },
  wrong: { icon: '✗', label: 'ошибка' },
  deferred: { icon: '⏳', label: 'ожидает проверки' },
  skipped: { icon: '—', label: 'нет ответа' },
};

export function RoundSummary({ onReplay }: { onReplay: () => void }) {
  const dispatch = useAppDispatch();
  const g = useAppSelector(selectGame);
  const learner = useLearner();
  const promptShown = useAppSelector(selectRegisterPromptShown);
  // Флаг фиксируется при первом показе итогов — повторная отрисовка не прячет предложение
  const [showPrompt] = useState(() => learner.kind === 'guest' && !promptShown);
  useEffect(() => {
    if (showPrompt) dispatch(ui.registerPromptShown());
  }, [showPrompt, dispatch]);

  const sum = g.summary;
  const correct = sum?.correct ?? g.correct;
  const xp = sum?.xp_earned ?? g.xp;
  const pending = g.log.filter((l) => l.outcome === 'deferred').length;
  const levelUp = sum?.level_up;
  const next = sum?.next_level ?? learner.next;

  return (
    <Paper className={s.result}>
      <h1 className={s.h} tabIndex={-1}>
        {g.timeExpired ? 'Время вышло!' : 'Раунд завершён'}
      </h1>
      <p className={s.score}>
        Верно <b>{correct}</b> из {g.questions.length} · <b>+{xp}</b> опыта
        {g.deckTitle && <> · отдел «{g.deckTitle}»</>}
      </p>
      {pending > 0 && (
        <p className={s.pending}>
          {countOf(pending, ANSWER_FORMS)} ожидают проверки — отправим, когда появится связь
        </p>
      )}

      {levelUp ? (
        <div className={s.promo} role="status">
          <div>Повышение! Теперь вы</div>
          <div className={s.role}>{levelUp.to.title}</div>
          {levelUp.unlocked.length > 0 && <div className={s.unlocked}>Открыто: {levelUp.unlocked.join('; ')}</div>}
        </div>
      ) : (
        next && (
          <p className={s.next}>
            До должности «{next.title}» осталось {next.xp_left} опыта
          </p>
        )
      )}

      {sum?.achievements_earned?.length ? (
        <p className={s.ach}>🏅 Новое достижение: {sum.achievements_earned.map((a) => a.title).join(', ')}</p>
      ) : null}

      <ol className={s.log}>
        {g.log
          .slice()
          .sort((a, b) => a.questionId - b.questionId)
          .map((l) => (
            <li key={l.questionId} className={s[l.outcome]}>
              <span aria-hidden="true">{OUTCOME[l.outcome].icon}</span>
              <span lang="en" className={s.word}>{l.prompt}</span>
              <span className={s.tr}>{l.correctText ?? ''}</span>
              <span className="sr-only">{OUTCOME[l.outcome].label}</span>
            </li>
          ))}
      </ol>

      {showPrompt && (
        <div className={s.save}>
          Опыт гостя хранится только на этом устройстве. Создайте аккаунт — прогресс перенесётся, и его можно будет
          продолжить с телефона.
        </div>
      )}
      <div className={s.actions}>
        {showPrompt && (
          <ButtonLink to={ROUTES.register} variant="primary" block>
            Сохранить прогресс
          </ButtonLink>
        )}
        <Button variant={showPrompt ? 'outlinePaper' : 'game'} block onClick={onReplay}>
          Сыграть ещё раунд
        </Button>
        <ButtonLink to={ROUTES.home} variant="outlinePaper" block>
          В кабинет
        </ButtonLink>
      </div>
    </Paper>
  );
}
