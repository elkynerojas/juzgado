// Carga el JavaScript de legacy/control_procesos.html en un contexto aislado
// y ejecuta `extra` en el mismo ámbito; `extra` debe asignar globalThis.__out (string JSON).
import fs from 'node:fs';
import vm from 'node:vm';

export function cargar(extra) {
  const html = fs.readFileSync(new URL('../legacy/control_procesos.html', import.meta.url), 'utf8');
  const ini = html.indexOf('<script>') + '<script>'.length;
  const fin = html.indexOf('/* ===== init ===== */');
  if (ini < 8 || fin < 0) throw new Error('No se encontró el script del HTML');
  const el = { style: {}, classList: { add() {}, remove() {}, toggle() {} }, setAttribute() {}, removeAttribute() {} };
  const ctx = vm.createContext({
    window: {},
    document: { querySelector: () => el, querySelectorAll: () => [], documentElement: el, body: el },
    localStorage: { getItem: () => null, setItem() {} },
    setTimeout: () => 0,
    console,
  });
  vm.runInContext(html.slice(ini, fin) + '\n;' + extra, ctx);
  return JSON.parse(ctx.__out);
}
