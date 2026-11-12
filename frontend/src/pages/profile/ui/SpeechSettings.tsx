/** Блок «Озвучка» в профиле: выбор произношения с прослушиванием образца. */
import { useGetDecksQuery } from '@/entities/deck';
import { useGetDeckWordsQuery } from '@/entities/word';
import { AccentSwitch } from '@/features/speak-word';
import { Paper } from '@/shared/ui';
import s from './ProfilePage.module.css';

export function SpeechSettings() {
  const { data: decks } = useGetDecksQuery();
  const first = decks?.find((d) => d.kind === 'shared' && !d.locked);
  const { data: words } = useGetDeckWordsQuery({ deckId: first?.id ?? 0, limit: 1 }, { skip: !first });
  const sample = words?.items[0];
  return (
    <Paper as="section" plain className={s.panel} aria-label="Озвучка">
      <AccentSwitch sampleWordId={sample?.id} sampleText={sample?.en ?? 'schedule'} />
    </Paper>
  );
}
