/**
 * Данные «кто учится» для пропуска, меню и профиля: у пользователя — из кэша GET /me,
 * у гостя — из проекции локального журнала и порогов GET /levels (раздел 4.7.1, пп. 8–9).
 * Так все экраны читают одно значение и не могут разойтись.
 */
import { levelFor, nextLevelFor, selectSession, useGetLevelsQuery, useGetMeQuery, type Me, type NextLevel } from '@/entities/user';
import { useAppSelector } from '@/shared/model';
import { selectGuestProjection } from './projection';

export interface Learner {
  kind: 'loading' | 'guest' | 'user';
  isAdmin: boolean;
  name: string;
  email?: string;
  xp: number;
  levelTitle: string;
  levelMinXp: number;
  next: NextLevel | null;
  streakDays: number;
  freezes: number;
  inboxCount: number;
  me?: Me;
}

export function useLearner(): Learner {
  const session = useAppSelector(selectSession);
  const guest = useAppSelector(selectGuestProjection);
  const isUser = session.status === 'authenticated';
  const { data: me } = useGetMeQuery(undefined, { skip: !isUser });
  const { data: levels = [] } = useGetLevelsQuery();

  if (session.status === 'unknown' || (isUser && !me)) {
    return { kind: 'loading', isAdmin: false, name: '', xp: 0, levelTitle: '', levelMinXp: 0, next: null, streakDays: 0, freezes: 0, inboxCount: 0 };
  }
  if (isUser && me) {
    return {
      kind: 'user',
      isAdmin: me.role === 'admin',
      name: me.name,
      email: me.email,
      xp: me.xp,
      levelTitle: me.level.title,
      levelMinXp: me.level.min_xp,
      next: me.next_level,
      streakDays: me.streak_days,
      freezes: me.streak_freezes,
      inboxCount: me.inbox_count,
      me,
    };
  }
  const level = levelFor(guest.xp, levels);
  return {
    kind: 'guest',
    isAdmin: false,
    name: 'Гость',
    xp: guest.xp,
    levelTitle: level?.title ?? 'Стажёр',
    levelMinXp: level?.min_xp ?? 0,
    next: nextLevelFor(guest.xp, levels),
    streakDays: guest.streakDays,
    freezes: 0,
    inboxCount: guest.inbox.length,
  };
}
