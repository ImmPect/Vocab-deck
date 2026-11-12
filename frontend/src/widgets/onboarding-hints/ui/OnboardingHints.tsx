/** Подсказки первого запуска: не больше 3 шагов, можно пропустить (NFR-O-02). */
import { ONBOARDING_STEPS, selectOnboarding, ui, useAppDispatch, useAppSelector } from '@/shared/model';
import { Button } from '@/shared/ui';
import s from './OnboardingHints.module.css';

const HINTS = [
  { icon: '🪪', text: 'Это ваш пропуск: опыт и должность растут с каждым раундом. Новые должности открывают отделы и режимы.' },
  { icon: '📥', text: 'Во «Входящие» приходят слова, которые пора повторить, — по системе Лейтнера, всё реже по мере запоминания.' },
  { icon: '⏱', text: '«Карточки» — знакомство со словами без очков. «Дедлайн» — 5 вопросов за 60 секунд, за верные ответы начисляется опыт.' },
];

export function OnboardingHints() {
  const dispatch = useAppDispatch();
  const { step, done } = useAppSelector(selectOnboarding);
  if (done || step >= ONBOARDING_STEPS) return null;
  const hint = HINTS[step];
  const last = step === ONBOARDING_STEPS - 1;
  return (
    <aside className={s.hint} aria-label={`Подсказка ${step + 1} из ${ONBOARDING_STEPS}`}>
      <span className={s.icon} aria-hidden="true">{hint.icon}</span>
      <p className={s.text}>{hint.text}</p>
      <div className={s.actions}>
        <span className={s.step}>
          {step + 1} / {ONBOARDING_STEPS}
        </span>
        {!last && (
          <Button variant="linkLight" size="small" onClick={() => dispatch(ui.onboardingSkipped())}>
            Пропустить
          </Button>
        )}
        <Button variant="outline" size="small" onClick={() => dispatch(ui.onboardingStepChanged(step + 1))}>
          {last ? 'Понятно' : 'Далее'}
        </Button>
      </div>
    </aside>
  );
}
