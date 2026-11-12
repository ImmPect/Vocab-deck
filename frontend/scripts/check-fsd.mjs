// Проверка правил Feature-Sliced Design (раздел 4.3.1 ПР3):
// 1) импорт только из слоёв ниже: app → pages → widgets → features → entities → shared;
// 2) слайсы одного слоя не импортируют друг друга;
// 3) чужой слайс импортируется только через публичный API (index.ts): '@/entities/user', а не '@/entities/user/model/...'.
// Запуск: npm run lint:fsd
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const LAYERS = ['shared', 'entities', 'features', 'widgets', 'pages', 'app'];
const SLICED = new Set(['entities', 'features', 'widgets', 'pages']);
const root = fileURLToPath(new URL('../src/', import.meta.url));

function* walk(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) yield* walk(p);
    else if (/\.(ts|tsx)$/.test(name)) yield p;
  }
}

const where = (parts) => ({ layer: parts[0], slice: SLICED.has(parts[0]) ? parts[1] : null });
const errors = [];
let files = 0;

for (const file of walk(root)) {
  files++;
  const parts = relative(root, file).split(sep);
  const from = where(parts);
  const src = readFileSync(file, 'utf8');
  for (const m of src.matchAll(/(?:import|export)[^'"]*?from\s+['"](@\/[^'"]+)['"]/g)) {
    const spec = m[1].slice(2).split('/');
    const to = where(spec);
    const fi = LAYERS.indexOf(from.layer);
    const ti = LAYERS.indexOf(to.layer);
    const at = `${relative(root, file)}: ${m[1]}`;
    if (ti > fi) errors.push(`${at} — импорт из вышележащего слоя «${to.layer}»`);
    else if (ti === fi && SLICED.has(to.layer) && to.slice !== from.slice)
      errors.push(`${at} — импорт соседнего слайса слоя «${to.layer}»`);
    else if (ti < fi && SLICED.has(to.layer) && spec.length > 2)
      errors.push(`${at} — импорт в обход публичного API слайса`);
  }
}

if (errors.length) {
  console.error(`Нарушения FSD (${errors.length}):\n  ` + errors.join('\n  '));
  process.exit(1);
}
console.log(`FSD: нарушений нет, проверено файлов: ${files}`);
