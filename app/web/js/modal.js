import { $, $$, esc, opciones, toast, abrir, cerrar } from './util.js';

/* Formulario genérico en modal.
   campos: [{k, label, tipo: text|number|password|date|textarea|select|checkbox|checks, valor, opciones, lista, hint, filas}]
   guardar(valores) y eliminar() pueden lanzar: el modal queda abierto y se muestra el error. */
export function formModal({ titulo, campos, guardar, eliminar, ancho }) {
  $('#formTitle').textContent = titulo;
  $('#formModal').style.maxWidth = ancho || '';
  $('#formBody').innerHTML = campos.map(campoHTML).join('');
  const del = $('#formDel');
  del.style.display = eliminar ? '' : 'none';
  del.onclick = () => ejecutar(eliminar);
  $('#formSave').onclick = () => ejecutar(() => guardar(leer(campos)));
  abrir('ovForm');
  const primero = $('#formBody input:not([type=checkbox]), #formBody textarea');
  if (primero) primero.focus();
}

async function ejecutar(fn) {
  try { if (await fn() !== false) cerrar('ovForm'); } catch (e) { toast(e.message); }
}

function campoHTML(c) {
  const id = 'f_' + c.k, v = c.valor == null ? '' : c.valor;
  let ctl;
  if (c.tipo === 'select') ctl = '<select id="' + id + '">' + opciones(c.opciones, String(v)) + '</select>';
  else if (c.tipo === 'textarea') ctl = '<textarea id="' + id + '" rows="' + (c.filas || 6) + '">' + esc(v) + '</textarea>';
  else if (c.tipo === 'checkbox') return '<div class="field"><label><input type="checkbox" id="' + id + '"' + (v ? ' checked' : '') + ' style="width:auto;margin-right:6px">' + esc(c.label) + '</label></div>';
  else if (c.tipo === 'checks') {
    let grupo = null;
    ctl = '<div class="checks" id="' + id + '">' + c.opciones.map(o => {
      const g = o.grupo !== grupo ? '<div class="grp">' + esc(grupo = o.grupo) + '</div>' : '';
      return g + '<label><input type="checkbox" value="' + esc(o.v) + '"' + (v.includes(o.v) ? ' checked' : '') + '>' + esc(o.l) + '</label>';
    }).join('') + '</div>';
  } else {
    const lista = c.lista ? ' list="' + id + '_l"' : '';
    ctl = '<input id="' + id + '" type="' + (c.tipo || 'text') + '" value="' + esc(v) + '"' + lista + (c.tipo === 'number' ? ' min="1"' : '') + (c.tipo === 'password' ? ' autocomplete="new-password"' : '') + '>';
    if (c.lista) ctl += '<datalist id="' + id + '_l">' + c.lista.map(o => '<option value="' + esc(o) + '">').join('') + '</datalist>';
  }
  return '<div class="field"><label>' + esc(c.label) + '</label>' + ctl + (c.hint ? '<div class="hint">' + esc(c.hint) + '</div>' : '') + '</div>';
}

function leer(campos) {
  const v = {};
  campos.forEach(c => {
    const el = $('#f_' + c.k);
    if (c.tipo === 'checkbox') v[c.k] = el.checked;
    else if (c.tipo === 'checks') v[c.k] = $$('input:checked', el).map(x => x.value);
    else if (c.tipo === 'number') v[c.k] = el.value === '' ? null : Number(el.value);
    else v[c.k] = c.tipo === 'textarea' || c.tipo === 'password' ? el.value : el.value.trim();
  });
  return v;
}
