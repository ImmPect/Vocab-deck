/**
 * Итоги раунда. API не вызывает: данные уже получены от finish и лежат в slice game.
 * Если итогов в store нет (перезагрузка страницы) — переход в кабинет (табл. 4.4).
 */
import { useEffect } from 'react';
import { Navigate, useNavigate, useParams } from 'react-router-dom';
import { selectGame } from '@/features/play-deadline';
import { ROUTES } from '@/shared/config';
import { useAppSelector } from '@/shared/model';
import { RoundSummary } from '@/widgets/round-summary';

export default function RoundResultPage() {
  const { roundId } = useParams();
  const g = useAppSelector(selectGame);
  const navigate = useNavigate();
  useEffect(() => {
    document.title = 'Итоги раунда · Vocab Deck';
    document.querySelector<HTMLElement>('h1')?.focus();
  }, []);

  if (g.status !== 'finished' || g.roundId !== roundId || !g.deckId) return <Navigate to={ROUTES.home} replace />;
  return <RoundSummary onReplay={() => navigate(ROUTES.deadline(g.deckId!))} />;
}
