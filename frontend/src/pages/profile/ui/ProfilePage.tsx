/**
 * Профиль: карьерная лестница, статистика за неделю, достижения (табл. 4.2 ПР3).
 * Три независимых блока со своими скелетонами и ошибками. Гостю — лестница по локальному опыту.
 */
import { useLearner } from '@/features/guest-progress-sync';
import { ROUTES } from '@/shared/config';
import { ButtonLink, EmptyState, PageHeader } from '@/shared/ui';
import { AchievementsList } from '@/widgets/achievements-list';
import { ActivityChart } from '@/widgets/activity-chart';
import { CareerLadder } from '@/widgets/career-ladder';
import { EmployeeBadge } from '@/widgets/employee-badge';
import { AccountSettings } from './AccountSettings';
import { SpeechSettings } from './SpeechSettings';
import s from './ProfilePage.module.css';

export default function ProfilePage() {
  const l = useLearner();
  return (
    <>
      <PageHeader title="Профиль" lead={l.kind === 'user' ? `${l.name} · ${l.email}` : undefined} />
      <div className={s.grid}>
        <div className={s.col}>
          <EmployeeBadge />
          <SpeechSettings />
          <CareerLadder />
        </div>
        <div className={s.col}>
          {l.kind === 'guest' ? (
            <EmptyState icon="🪪" actions={<ButtonLink to={ROUTES.register} variant="primary" size="small">Сохранить прогресс</ButtonLink>}>
              Гостевой профиль. После регистрации статистика сохранится на сервере
            </EmptyState>
          ) : (
            l.kind === 'user' && (
              <>
                <ActivityChart />
                <AchievementsList />
                <AccountSettings me={l.me!} />
              </>
            )
          )}
        </div>
      </div>
    </>
  );
}
