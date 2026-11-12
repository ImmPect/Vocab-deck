/**
 * Импорт CSV в личный список (US-10, табл. 4.2 ПР3). Клиент проверяет расширение
 * и размер, сервер — содержимое каждой строки; отчёт: «добавлено N, пропущено M».
 */
import { useId, useRef, useState } from 'react';
import { useImportCsvMutation, type ImportReport } from '@/entities/deck';
import { asApiError } from '@/shared/api';
import { WORD_FORMS, countOf } from '@/shared/lib';
import { Button } from '@/shared/ui';
import s from './ImportCsvForm.module.css';

const MAX_BYTES = 1024 * 1024;

export function ImportCsvForm({ deckId, onDone }: { deckId: number; onDone?: (report: ImportReport) => void }) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<ImportReport | null>(null);
  const [importCsv, { isLoading }] = useImportCsvMutation();

  function pick(f: File | undefined) {
    setReport(null);
    setError(null);
    if (!f) return setFile(null);
    if (!f.name.toLowerCase().endsWith('.csv')) return setError('Нужен файл .csv'), setFile(null);
    if (f.size > MAX_BYTES) return setError('Файл больше 1 МБ'), setFile(null);
    setFile(f);
  }

  async function upload() {
    if (!file) return;
    try {
      const r = await importCsv({ deckId, file }).unwrap();
      setReport(r);
      setFile(null);
      if (inputRef.current) inputRef.current.value = '';
      onDone?.(r);
    } catch (e) {
      setError(asApiError(e)?.message ?? 'Не удалось загрузить файл');
    }
  }

  return (
    <div className={s.box}>
      <label htmlFor={inputId} className={s.label}>
        Импорт из CSV
      </label>
      <p className={s.hint}>
        Столбцы: <code>en</code>, <code>ru</code>, <code>example</code> (необязательный). Первая строка — заголовок. До 1 МБ.
      </p>
      <div className={s.row}>
        <input
          ref={inputRef}
          id={inputId}
          type="file"
          accept=".csv,text/csv"
          className={s.file}
          onChange={(e) => pick(e.target.files?.[0])}
        />
        <Button variant="outlinePaper" size="small" loading={isLoading} disabled={!file} onClick={upload}>
          Загрузить
        </Button>
      </div>
      {error && <p className={s.error} role="alert">{error}</p>}
      {report && (
        <div className={s.report} role="status">
          <b>
            Добавлено {countOf(report.added, WORD_FORMS)}
            {report.skipped.length > 0 && `; пропущено ${report.skipped.length}`}
          </b>
          {report.skipped.length > 0 && (
            <ul>
              {report.skipped.slice(0, 20).map((r) => (
                <li key={r.line}>
                  Строка {r.line}
                  {r.en ? ` («${r.en}»)` : ''} — {r.reason}
                </li>
              ))}
              {report.skipped.length > 20 && <li>…и ещё {report.skipped.length - 20}</li>}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
