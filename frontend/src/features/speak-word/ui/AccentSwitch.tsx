/** Выбор произношения озвучки: британское или американское. Хранится в настройках устройства. */
import { selectAccent, ui, useAppDispatch, useAppSelector, type Accent } from '@/shared/model';
import { playSpeech } from '../lib/player';
import s from './AccentSwitch.module.css';

const OPTIONS: { value: Accent; label: string; hint: string }[] = [
  { value: 'uk', label: 'Британское', hint: 'как транскрипции в словаре' },
  { value: 'us', label: 'Американское', hint: '' },
];

/** sampleWordId — слово, на котором можно прослушать выбранный голос. */
export function AccentSwitch({ sampleWordId, sampleText = 'schedule' }: { sampleWordId?: number; sampleText?: string }) {
  const dispatch = useAppDispatch();
  const accent = useAppSelector(selectAccent);

  const choose = (value: Accent) => {
    dispatch(ui.accentChanged(value));
    void playSpeech({ text: sampleText, wordId: sampleWordId, accent: value });
  };

  return (
    <fieldset className={s.box}>
      <legend className={s.legend}>Произношение в озвучке</legend>
      <div className={s.options}>
        {OPTIONS.map((o) => (
          <label key={o.value} className={`${s.option} ${accent === o.value ? s.on : ''}`}>
            <input type="radio" name="accent" value={o.value} checked={accent === o.value} onChange={() => choose(o.value)} />
            <span>
              <b>{o.label}</b>
              {o.hint && <small> — {o.hint}</small>}
            </span>
          </label>
        ))}
      </div>
      <p className={s.note}>
        При выборе прозвучит слово «{sampleText}». Озвучку делает нейросетевой голос на сервере; без сети используется
        английский голос браузера.
      </p>
    </fieldset>
  );
}
