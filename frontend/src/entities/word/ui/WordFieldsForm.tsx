/**
 * Поля слова: слово, транскрипция, перевод, пример. Общий презентационный блок
 * для окна администратора и формы личного списка. Проверка — как на сервере.
 */
import { Input, Textarea } from '@/shared/ui';
import { EN_PATTERN } from '../model/types';
import s from './WordFieldsForm.module.css';

export interface WordValues {
  en: string;
  ipa: string;
  ru: string;
  example: string;
}

export const emptyWordValues: WordValues = { en: '', ipa: '', ru: '', example: '' };

export function validateWord(v: WordValues): Record<string, string> {
  const e: Record<string, string> = {};
  const en = v.en.trim();
  if (!en) e.en = 'Заполните слово на английском';
  else if (en.length > 100) e.en = 'Слово должно быть не длиннее 100 символов';
  else if (!EN_PATTERN.test(en) || !/[A-Za-z]/.test(en)) e.en = 'Допустимы латинские буквы, пробел, дефис и апостроф';
  if (!v.ru.trim()) e.ru = 'Заполните перевод';
  else if (v.ru.trim().length > 200) e.ru = 'Перевод должен быть не длиннее 200 символов';
  if (v.ipa.trim().length > 100) e.ipa = 'Транскрипция должна быть не длиннее 100 символов';
  if (v.example.trim().length > 500) e.example = 'Пример должен быть не длиннее 500 символов';
  return e;
}

/** Значения формы → тело запроса API (пустые необязательные поля — null). */
export const toWordBody = (v: WordValues) => ({
  en: v.en.trim(),
  ru: v.ru.trim(),
  ipa: v.ipa.trim() || null,
  example: v.example.trim() || null,
});

export function WordFieldsForm({
  values,
  errors,
  onChange,
}: {
  values: WordValues;
  errors: Record<string, string | undefined>;
  onChange: (field: keyof WordValues, value: string) => void;
}) {
  return (
    <>
      <div className={s.row2}>
        <Input label="Слово (EN)" name="en" lang="en" value={values.en} error={errors.en} onChange={(e) => onChange('en', e.target.value)} />
        <Input label="Транскрипция" name="ipa" value={values.ipa} error={errors.ipa} placeholder="/ˈdedlaɪn/" onChange={(e) => onChange('ipa', e.target.value)} />
      </div>
      <Input label="Перевод (RU)" name="ru" value={values.ru} error={errors.ru} onChange={(e) => onChange('ru', e.target.value)} />
      <Textarea label="Пример употребления" name="example" lang="en" value={values.example} error={errors.example} onChange={(e) => onChange('example', e.target.value)} />
    </>
  );
}
