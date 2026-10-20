// После сборки: 1) копия index.html → 404.html для маршрутов SPA на GitHub Pages (раздел 4.1.1);
// 2) проверка бюджета стартовой загрузки NFR-P-04: JS + CSS из index.html ≤ 300 КБ в gzip.
import { readFileSync, copyFileSync, readdirSync } from 'node:fs';
import { gzipSync } from 'node:zlib';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const dist = fileURLToPath(new URL('../dist/', import.meta.url));
copyFileSync(join(dist, 'index.html'), join(dist, '404.html'));

const html = readFileSync(join(dist, 'index.html'), 'utf8');
const initial = [...html.matchAll(/(?:src|href)="\/?(assets\/[^"]+\.(?:js|css))"/g)].map((m) => m[1]);
const gz = (f) => gzipSync(readFileSync(join(dist, f))).length;
const total = initial.reduce((s, f) => s + gz(f), 0);
const all = readdirSync(join(dist, 'assets')).filter((f) => /\.(js|css)$/.test(f));

console.log('\nСтартовый набор (gzip):');
for (const f of initial) console.log(`  ${f.padEnd(48)} ${(gz(f) / 1024).toFixed(1)} КБ`);
console.log(`  Итого: ${(total / 1024).toFixed(1)} КБ из 300 КБ; всего чанков: ${all.length}`);
if (total > 300 * 1024) {
  console.error('Превышен бюджет NFR-P-04');
  process.exit(1);
}
