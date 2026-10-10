/* Borradores automáticos de los formularios grandes (v2 del HTML).
   Se guardan en el navegador bajo la clave del usuario, para que un equipo compartido no mezcle borradores
   de distintas personas. Se descartan al guardar y se ofrecen al reabrir el formulario. */
import { S } from './estado.js';
import { $, $$, debounce, esc, fmt } from './util.js';

const clave = () => 'cp_borrador_' + (S.me ? S.me.id : 'anon');

function leer() {
  try { return JSON.parse(localStorage.getItem(clave()) || '{}'); } catch { return {}; }
}

function escribir(todo) {
  try { localStorage.setItem(clave(), JSON.stringify(todo)); } catch { /* sin espacio: el borrador es opcional */ }
}

export function limpiar(tipo) {
  const todo = leer();
  delete todo[tipo];
  escribir(todo);
}

export function guardado(tipo) {
  return leer()[tipo] || null;
}

/* Captura el valor de todos los campos del modal, por id. */
export function tomar(selector) {
  const datos = {};
  $$(selector + ' [id]').forEach(el => {
    if (el.tagName === 'INPUT' && el.type === 'checkbox') datos[el.id] = el.checked;
    else if ('value' in el && el.tagName !== 'BUTTON') datos[el.id] = el.value;
  });
  return datos;
}

/* Devuelve los valores a los campos. Los selectores dinámicos ya deben estar pintados. */
export function aplicar(datos) {
  Object.entries(datos || {}).forEach(([id, v]) => {
    const el = document.getElementById(id);
    if (!el) return;
    if (el.tagName === 'INPUT' && el.type === 'checkbox') el.checked = !!v;
    else el.value = v;
  });
}

export function programar(tipo, selector, extra) {
  const todo = leer();
  todo[tipo] = Object.assign({ datos: tomar(selector), cuando: new Date().toISOString() }, extra || {});
  escribir(todo);
}

/* Barra "hay un borrador sin guardar" con los dos botones. `onRecuperar` recibe el borrador. */
export function barra(tipo, idBarra, b, onRecuperar) {
  const el = $('#' + idBarra);
  if (!el) return;
  if (!b) { el.style.display = 'none'; el.innerHTML = ''; return; }
  const cuando = (b.cuando || '').slice(0, 10);
  el.style.display = '';
  el.innerHTML = '💾 Hay un borrador sin guardar' + (cuando ? ' del ' + esc(fmt(cuando)) : '')
    + '<span class="spacer" style="flex:1"></span>'
    + '<button class="btn sm" data-bor="usar">Recuperar</button>'
    + '<button class="btn ghost sm" data-bor="descartar">Descartar</button>';
  el.querySelector('[data-bor="usar"]').onclick = () => { onRecuperar(b); barra(tipo, idBarra, null); };
  el.querySelector('[data-bor="descartar"]').onclick = () => { limpiar(tipo); barra(tipo, idBarra, null); };
}

/* Un solo temporizador por tipo de formulario. */
export function autoguardado(tipo, selector, extra) {
  return debounce(() => programar(tipo, selector, typeof extra === 'function' ? extra() : extra), 500);
}
