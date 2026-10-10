// Carga el JavaScript de un HTML original de legacy/ en un contexto aislado
// y ejecuta `extra` en el mismo ámbito; `extra` debe asignar globalThis.__out (string JSON).
// La v2 parte su código en varios <script>: se concatenan todos hasta el init.
import fs from 'node:fs';
import vm from 'node:vm';

export const V1 = 'control_procesos.html';
export const V2 = 'control_procesos_v2.html';

export function fuente(archivo = V1) {
  const html = fs.readFileSync(new URL('../legacy/' + archivo, import.meta.url), 'utf8');
  const js = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n;\n');
  const fin = js.indexOf('/* ===== init ===== */');
  if (!js || fin < 0) throw new Error('No se encontró el script del HTML ' + archivo);
  return js.slice(0, fin);
}

export function cargar(extra, archivo = V1) {
  const el = { style: {}, classList: { add() {}, remove() {}, toggle() {} }, setAttribute() {}, removeAttribute() {} };
  const ctx = vm.createContext({
    window: {},
    document: {
      querySelector: () => el, querySelectorAll: () => [], getElementById: () => null,
      documentElement: el, body: el, addEventListener() {},
    },
    localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    setTimeout: () => 0,
    clearTimeout() {},
    atob: s => Buffer.from(s, 'base64').toString('binary'),
    console,
  });
  vm.runInContext(fuente(archivo) + '\n;' + extra, ctx);
  return JSON.parse(ctx.__out);
}
