/**
 * Реестр предзагрузки чанков страниц (раздел 4.1.3 ПР3): слой app регистрирует
 * загрузчики ленивых страниц, а нижние слои вызывают их по имени — например,
 * при наведении на кнопку «Дедлайн» фоном подгружается чанк мини-игры.
 */
const loaders = new Map<string, () => Promise<unknown>>();
const started = new Set<string>();

export function registerPrefetch(name: string, load: () => Promise<unknown>) {
  loaders.set(name, load);
}

export function prefetch(name: string) {
  if (started.has(name)) return;
  const load = loaders.get(name);
  if (!load) return;
  started.add(name);
  load().catch(() => started.delete(name));
}
