/**
 * Личные списки (E6, US-10): создать, переименовать, удалить список;
 * добавить, изменить, удалить слово. При 409 — «Такое слово уже есть в списке».
 */
import { useState, type FormEvent } from 'react';
import { useCreateListMutation, useDeleteListMutation, useRenameListMutation, type Deck } from '@/entities/deck';
import {
  WordFieldsForm,
  emptyWordValues,
  toWordBody,
  useAddWordMutation,
  useDeleteWordMutation,
  useUpdateWordMutation,
  validateWord,
  type Word,
  type WordValues,
} from '@/entities/word';
import { asApiError, fieldErrors } from '@/shared/api';
import { Button, Input, Modal } from '@/shared/ui';

function TitleModal({
  title,
  initial = '',
  submitLabel,
  loading,
  onSubmit,
  onClose,
}: {
  title: string;
  initial?: string;
  submitLabel: string;
  loading: boolean;
  onSubmit: (title: string) => Promise<void>;
  onClose: () => void;
}) {
  const [value, setValue] = useState(initial);
  const [error, setError] = useState<string>();
  async function submit(e?: FormEvent) {
    e?.preventDefault();
    if (!value.trim()) return setError('Введите название');
    try {
      await onSubmit(value.trim());
    } catch (err) {
      const api = asApiError(err);
      setError(fieldErrors(api).title ?? api?.message);
    }
  }
  return (
    <Modal
      title={title}
      onClose={onClose}
      actions={
        <>
          <Button variant="outlinePaper" onClick={onClose}>Отмена</Button>
          <Button loading={loading} onClick={() => submit()}>{submitLabel}</Button>
        </>
      }
    >
      <form onSubmit={submit}>
        <Input label="Название списка" name="title" value={value} error={error} maxLength={100}
          placeholder="Например, «Слова с планёрок»" onChange={(e) => setValue(e.target.value)} />
      </form>
    </Modal>
  );
}

export function CreateListModal({ onClose, onCreated }: { onClose: () => void; onCreated: (deck: Deck) => void }) {
  const [create, { isLoading }] = useCreateListMutation();
  return (
    <TitleModal title="Новый список" submitLabel="Создать" loading={isLoading} onClose={onClose}
      onSubmit={async (title) => onCreated(await create({ title }).unwrap())} />
  );
}

export function RenameListModal({ deck, onClose, onDone }: { deck: Deck; onClose: () => void; onDone: () => void }) {
  const [rename, { isLoading }] = useRenameListMutation();
  return (
    <TitleModal title="Переименовать список" initial={deck.title} submitLabel="Сохранить" loading={isLoading} onClose={onClose}
      onSubmit={async (title) => {
        await rename({ id: deck.id, title }).unwrap();
        onDone();
      }} />
  );
}

export function ConfirmModal({
  title,
  text,
  confirmLabel,
  loading,
  error,
  onConfirm,
  onClose,
}: {
  title: string;
  text: string;
  confirmLabel: string;
  loading: boolean;
  error?: string;
  onConfirm: () => void;
  onClose: () => void;
}) {
  return (
    <Modal
      title={title}
      onClose={onClose}
      actions={
        <>
          <Button variant="outlinePaper" onClick={onClose}>Отмена</Button>
          <Button variant="danger" loading={loading} onClick={onConfirm}>{confirmLabel}</Button>
        </>
      }
    >
      <p style={{ margin: '0 0 8px', lineHeight: 1.5 }}>{text}</p>
      {error && <p role="alert" style={{ color: 'var(--red)', fontSize: 13 }}>{error}</p>}
    </Modal>
  );
}

export function DeleteListModal({ deck, onClose, onDeleted }: { deck: Deck; onClose: () => void; onDeleted: () => void }) {
  const [remove, { isLoading, error }] = useDeleteListMutation();
  return (
    <ConfirmModal
      title="Удалить список?"
      text={`Список «${deck.title}» и его слова (${deck.words_count}) будут удалены вместе с прогрессом по ним.`}
      confirmLabel="Удалить"
      loading={isLoading}
      error={asApiError(error)?.message}
      onClose={onClose}
      onConfirm={async () => {
        await remove(deck.id).unwrap();
        onDeleted();
      }}
    />
  );
}

export function PersonalWordModal({
  deckId,
  word,
  onClose,
  onSaved,
}: {
  deckId: number;
  word?: Word;
  onClose: () => void;
  onSaved: (message: string) => void;
}) {
  const [values, setValues] = useState<WordValues>(
    word ? { en: word.en, ipa: word.ipa ?? '', ru: word.ru, example: word.example ?? '' } : emptyWordValues,
  );
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<string>();
  const [add, addState] = useAddWordMutation();
  const [update, updateState] = useUpdateWordMutation();

  async function save() {
    const ce = validateWord(values);
    setErrors(ce);
    setMessage(undefined);
    if (Object.keys(ce).length) return;
    try {
      if (word) await update({ id: word.id, deckId, ...toWordBody(values) }).unwrap();
      else await add({ deckId, ...toWordBody(values) }).unwrap();
      onSaved(word ? 'Слово изменено' : 'Слово добавлено');
    } catch (e) {
      const api = asApiError(e);
      setErrors(fieldErrors(api));
      setMessage(api?.status === 409 ? 'Такое слово уже есть в списке' : api?.message);
    }
  }

  return (
    <Modal
      title={word ? 'Изменить слово' : 'Новое слово'}
      onClose={onClose}
      actions={
        <>
          <Button variant="outlinePaper" onClick={onClose}>Отмена</Button>
          <Button loading={addState.isLoading || updateState.isLoading} onClick={save}>Сохранить</Button>
        </>
      }
    >
      <WordFieldsForm values={values} errors={errors} onChange={(f, v) => setValues((p) => ({ ...p, [f]: v }))} />
      {message && <p role="alert" style={{ color: 'var(--red)', fontSize: 13, margin: 0 }}>{message}</p>}
    </Modal>
  );
}

export function DeleteWordModal({ word, deckId, onClose, onDeleted }: { word: Word; deckId: number; onClose: () => void; onDeleted: () => void }) {
  const [remove, { isLoading, error }] = useDeleteWordMutation();
  return (
    <ConfirmModal
      title="Удалить слово?"
      text={`«${word.en}» — ${word.ru}. Прогресс по слову тоже будет удалён.`}
      confirmLabel="Удалить"
      loading={isLoading}
      error={asApiError(error)?.message}
      onClose={onClose}
      onConfirm={async () => {
        await remove({ id: word.id, deckId }).unwrap();
        onDeleted();
      }}
    />
  );
}
