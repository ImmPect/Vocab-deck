/**
 * Кабинет (табл. 4.2 ПР3): пропуск, входящие на сегодня, отделы. Данные запрашиваются
 * параллельно; ошибка отделов не скрывает пропуск (поток 4.7.1).
 */
import { useLearner } from '@/features/guest-progress-sync';
import { prefetch } from '@/shared/config';
import { PageHeader } from '@/shared/ui';
import { DeptGrid } from '@/widgets/dept-grid';
import { EmployeeBadge } from '@/widgets/employee-badge';
import { InboxCard } from '@/widgets/inbox-card';
import { OnboardingHints } from '@/widgets/onboarding-hints';
import s from './HomePage.module.css';

export default function HomePage() {
  const l = useLearner();
  const greeting = l.kind === 'user' ? `Здравствуйте, ${l.name.split(' ')[0]}` : 'Кабинет';
  return (
    <>
      <PageHeader
        title={greeting}
        lead={
          l.kind === 'guest'
            ? 'Вы работаете как гость: прогресс хранится на этом устройстве. Сыграйте раунд в любом открытом отделе.'
            : 'Разберите входящие и сыграйте раунд — так серия не прервётся.'
        }
      />
      <OnboardingHints />
      <div className={s.grid}>
        <div className={s.left}>
          <EmployeeBadge />
          <InboxCard />
        </div>
        <div>
          <DeptGrid onPrefetchGame={() => prefetch('deadline')} />
        </div>
      </div>
    </>
  );
}
