/**
 * Окно создания и редактирования слова общей колоды (UC-04, табл. 4.2 ПР3).
 * «Сохранить черновик» — status=draft, «Опубликовать» — published, «В архив» — archived
 * с подтверждением. При 409 показывает ссылку на существующую запись (UC-04 4в).
 */
import { useState } from 'react';
import type { Deck } from '@/entities/deck';
import {
  STATUS_LABEL,
  WordFieldsForm,
  emptyWordValues,
  toWordBody,
  validateWord,
  type AdminWord,
  type WordStatus,
  type WordValues,
} from '@/entities/word';
import { asApiError, fieldErrors, type ApiError } from '@/shared/api';
import { Button, Chip, Modal, Select } from '@/shared/ui';
import { useCreateAdminWordMutation, useUpdateAdminWordMutation } from '../api/adminWordApi';
import s from './WordEditModal.module.css';

const SAVED: Record<WordStatus, string> = {
  draft: 'Черновик сохранён',
  published: 'Слово опубликовано',
  archived: 'Слово перенесено в архив',
};

export function WordEditModal({
  word,
  decks,
  onClose,
  onSaved,
  onOpenExisting,
}: {
  word?: AdminWord;
  decks: Deck[];
  onClose: () => void;
  onSaved: (message: string) => void;
  onOpenExisting: (wordId: number, en: string) => void;
}) {
  const shared = decks.filter((d) => d.kind === 'shared');
  const [values, setValues] = useState<WordValues>(
    word ? { en: word.en, ipa: word.ipa ?? '', ru: word.ru, example: word.example ?? '' } : emptyWordValues,
  );
  const [deckId, setDeckId] = useState<number>(word?.deck.id ?? shared[0]?.id ?? 0);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState<ApiError | null>(null);
  const [confirmArchive, setConfirmArchive] = useState(false);
  const [create, createState] = useCreateAdminWordMutation();
  const [update, updateState] = useUpdateAdminWordMutation();
  const [pending, setPending] = useState<WordStatus | null>(null);
  const busy = createState.isLoading || updateState.isLoading;

  async function save(status: WordStatus) {
    setApiError(null);
    if (status !== 'archived') {
      const ce = validateWord(values);
      if (!deckId) ce.deck_id = 'Выберите отдел';
      setErrors(ce);
      if (Object.keys(ce).length) return;
    }
    setPending(status);
    try {
      const body = { ...toWordBody(values), deck_id: deckId, status };
      if (word) await update(status === 'archived' ? { id: word.id, status } : { id: word.id, ...body }).unwrap();
      else await create(body).unwrap();
      onSaved(SAVED[status]);
    } catch (e) {
      const err = asApiError(e);
      setApiError(err);
      setErrors(fieldErrors(err));
    } finally {
      setPending(null);
    }
  }

  const existingId = apiError?.status === 409 ? apiError.details?.find((d) => d.existing_word_id)?.existing_word_id : undefined;

  return (
    <Modal
      title={word ? 'Изменить слово' : 'Новое слово'}
      onClose={onClose}
      actions={
        confirmArchive ? (
          <>
            <span className={s.confirm}>Перенести слово в архив? Оно пропадёт из колоды у всех пользователей.</span>
            <Button variant="outlinePaper" onClick={() => setConfirmArchive(false)}>Нет</Button>
            <Button variant="danger" loading={pending === 'archived'} onClick={() => save('archived')}>В архив</Button>
          </>
        ) : (
          <>
            {word && word.status !== 'archived' && (
              <Button variant="link" className={s.archive} disabled={busy} onClick={() => setConfirmArchive(true)}>
                В архив
              </Button>
            )}
            <Button variant="outlinePaper" onClick={onClose} disabled={busy}>Отмена</Button>
            <Button variant="outlinePaper" loading={pending === 'draft'} disabled={busy} onClick={() => save('draft')}>
              Сохранить черновик
            </Button>
            <Button variant="primary" loading={pending === 'published'} disabled={busy} onClick={() => save('published')}>
              Опубликовать
            </Button>
          </>
        )
      }
    >
      {word && (
        <p className={s.meta}>
          <Chip tone={word.status}>{STATUS_LABEL[word.status]}</Chip>
          {word.learners_count > 0 && <span>Изучают: {word.learners_count}</span>}
        </p>
      )}
      <WordFieldsForm
        values={values}
        errors={errors}
        onChange={(f, v) => {
          setValues((p) => ({ ...p, [f]: v }));
          setErrors((p) => ({ ...p, [f]: '' }));
        }}
      />
      <Select label="Отдел" name="deck_id" value={deckId} error={errors.deck_id} onChange={(e) => setDeckId(Number(e.target.value))}>
        {shared.map((d) => (
          <option key={d.id} value={d.id}>
            {d.title}
          </option>
        ))}
      </Select>
      {apiError && (
        <p className={s.alert} role="alert">
          {apiError.message}
          {existingId && (
            <>
              {' '}
              <Button variant="link" onClick={() => onOpenExisting(existingId, values.en.trim())}>Открыть существующее слово</Button>
            </>
          )}
        </p>
      )}
    </Modal>
  );
}
