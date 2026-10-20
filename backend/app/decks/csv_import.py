"""Разбор CSV-файла для импорта слов в личный список (раздел 3.5.5 ПР3).

Модуль только читает файл и проверяет каждую строку по правилам слова;
дубликаты, лимит списка и запись в БД — забота decks.service.
"""
import csv
import io
from dataclasses import dataclass

from app.core.errors import AppError, PayloadTooLarge
from app.words.schemas import clean_en, clean_example, clean_ipa, clean_ru

MAX_FILE_BYTES = 1024 * 1024  # 1 МБ (NFR-M-03)
MAX_ROWS = 5000
REQUIRED = ("en", "ru")
OPTIONAL = ("ipa", "example")


class InvalidFile(AppError):
    status_code, code, message = 400, "invalid_file", "Файл не удалось прочитать как CSV"


@dataclass
class Row:
    """Строка данных: номер строки файла (заголовок — 1) и сырые значения."""

    line: int
    values: dict[str, str]


@dataclass
class RowError:
    line: int
    en: str
    reason_code: str
    reason: str

    def as_dict(self) -> dict:
        return {"line": self.line, "en": self.en, "reason_code": self.reason_code, "reason": self.reason}


def check_size(raw: bytes) -> None:
    if len(raw) > MAX_FILE_BYTES:
        raise PayloadTooLarge("Файл больше 1 МБ")


def parse(raw: bytes) -> list[Row]:
    """Декодирует UTF-8 (BOM допускается), читает заголовок и строки данных."""
    check_size(raw)
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise InvalidFile("Сохраните файл в кодировке UTF-8") from None
    if "\x00" in text:
        raise InvalidFile("Файл не похож на CSV")
    reader = csv.reader(io.StringIO(text, newline=""))
    try:
        header = next(reader, None)
        if not header or not any(h.strip() for h in header):
            raise InvalidFile("В первой строке файла нужен заголовок со столбцами en и ru")
        columns = [h.strip().lower() for h in header]
        missing = [c for c in REQUIRED if c not in columns]
        if missing:
            raise InvalidFile(f"Нет обязательных столбцов: {', '.join(missing)}")
        index = {c: columns.index(c) for c in REQUIRED + OPTIONAL if c in columns}
        rows: list[Row] = []
        last_line = reader.line_num
        for record in reader:
            start, last_line = last_line + 1, reader.line_num
            if not record or not any(cell.strip() for cell in record):
                continue  # пустые строки не считаются строками данных
            if len(rows) >= MAX_ROWS:
                raise PayloadTooLarge(f"В файле больше {MAX_ROWS} строк данных")
            values = {c: (record[i] if i < len(record) else "") for c, i in index.items()}
            rows.append(Row(start, values))
    except csv.Error:
        raise InvalidFile("Файл повреждён: проверьте кавычки в строках") from None
    return rows


def validate(row: Row) -> tuple[dict | None, RowError | None]:
    """Проверяет строку по правилам POST /decks/{id}/words: (поля слова, None) или (None, ошибка)."""
    raw_en = row.values.get("en", "")
    en_shown = raw_en.strip()
    for col in REQUIRED:
        if not row.values.get(col, "").strip():
            return None, RowError(row.line, en_shown, "missing_field", f"Не заполнен столбец {col}")
    try:
        en = clean_en(raw_en)
    except ValueError as e:
        return None, RowError(row.line, en_shown, "invalid_en", str(e))
    checks = (("ru", clean_ru), ("ipa", clean_ipa), ("example", clean_example))
    data = {"en": en}
    for col, fn in checks:
        try:
            data[col] = fn(row.values.get(col)) if col == "ru" or row.values.get(col) else None
        except ValueError as e:
            return None, RowError(row.line, en_shown, f"invalid_{col}", str(e))
    return data, None
