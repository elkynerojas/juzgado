/* Estadística SIERJU: cobertura por sección, avisos de lo que no se pudo clasificar,
   datos especiales registrados a mano y las tres descargas (v2 del HTML).
   Los números los calcula el servidor; aquí solo se eligen el periodo y lo que se pinta. */
import { api } from './api.js';
import { S, nav, puede } from './estado.js';
import { $, esc, fmt, toast, abrir, cerrar, delegar, opciones, guardarArchivo, guardarArchivoBinario } from './util.js';

const val = id => { const el = $('#' + id); return el ? el.value : ''; };
const pon = (id, v) => { const el = $('#' + id); if (el) el.value = v == null ? '' : v; };

let resumen = null;
let abiertas = new Set();
let procesos = [];

/* Trimestres del año en curso y del anterior, que es como se reporta. */
function trimestres() {
  const hoy = new Date();
  const out = [];
  for (const anio of [hoy.getFullYear(), hoy.getFullYear() - 1]) {
    for (let t = 0; t < 4; t++) {
      const desde = new Date(anio, t * 3, 1), hasta = new Date(anio, t * 3 + 3, 0);
      out.push({ clave: anio + '-T' + (t + 1), etiqueta: 'T' + (t + 1) + ' ' + anio, desde: iso(desde), hasta: iso(hasta) });
    }
  }
  return out;
}
const pad = n => String(n).padStart(2, '0');
const iso = d => d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());

function trimestreActual() {
  const hoy = new Date();
  return hoy.getFullYear() + '-T' + (Math.floor(hoy.getMonth() / 3) + 1);
}

function periodo() {
  return { desde: S.eDesde, hasta: S.eHasta };
}

function asegurarPeriodo() {
  if (S.eDesde && S.eHasta) return;
  const t = trimestres().find(x => x.clave === trimestreActual());
  S.eDesde = t.desde; S.eHasta = t.hasta;
}

export async function renderEstadistica() {
  asegurarPeriodo();
  resumen = await api.get('/api/estadistica', periodo());
  const k = resumen.kpis;
  const registra = puede('estadistica.registrar');
  const exporta = puede('estadistica.exportar');

  let h = '<div class="card" style="margin:12px 0;padding:12px 14px"><div class="sec-title" style="margin:0 0 4px">📊 Estadística SIERJU</div>'
    + '<div class="tiny muted">Los datos se cuentan a partir de los procesos y las actuaciones del periodo. '
    + 'Lo que no se puede clasificar aparece abajo como aviso, para corregirlo antes de reportar.</div></div>';

  h += '<div class="filterbar"><div class="lbl">Periodo</div>'
    + '<select class="fltsel" id="eTrim">' + opciones(trimestres().map(t => [t.clave, t.etiqueta]), '', '— a la medida —') + '</select>'
    + '<input type="date" id="eDesde" class="fltsel" value="' + esc(S.eDesde) + '">'
    + '<input type="date" id="eHasta" class="fltsel" value="' + esc(S.eHasta) + '">'
    + '<span class="spacer" style="flex:1"></span>'
    + (registra ? '<button class="btn sm" data-acc="nuevoDato">+ Dato especial</button>' : '')
    + (exporta ? '<button class="btn primary sm" data-acc="oficial">⬇️ Excel oficial</button>'
      + '<button class="btn sm" data-acc="completo">⬇️ Excel completo</button>'
      + '<button class="btn sm" data-acc="bitacora">⬇️ Bitácora (CSV)</button>' : '')
    + '</div>';

  h += '<div class="grid kpis">'
    + kpi('navy', k.secciones, 'Secciones del formato')
    + kpi('', k.con_movimiento, 'Con movimiento')
    + kpi('', k.automaticos, 'Datos automáticos')
    + kpi('', k.manuales, 'Datos especiales')
    + kpi(k.avisos ? 'red' : '', k.avisos, 'Sin clasificar')
    + '</div>';

  h += '<div class="tablewrap"><table><thead><tr><th style="width:40px"></th><th>#</th><th>Sección del formato</th><th style="width:90px">Total</th></tr></thead><tbody>';
  resumen.secciones.forEach(x => {
    const ab = abiertas.has(x.code);
    h += '<tr class="fija" data-acc="desplegar" data-c="' + x.code + '" style="cursor:pointer">'
      + '<td class="tiny">' + (x.total ? (ab ? '▾' : '▸') : '') + '</td><td class="tiny muted">' + x.n + '</td>'
      + '<td class="tiny">' + esc(x.title) + '</td>'
      + '<td>' + (x.total ? '<b>' + x.total + '</b>' : '<span class="muted">—</span>') + '</td></tr>';
    if (ab) h += '<tr class="fija"><td></td><td colspan="3" id="det_' + x.code + '"><span class="muted tiny">Cargando…</span></td></tr>';
  });
  h += '</tbody></table></div>';

  if (resumen.avisos.length) {
    h += '<div class="card" style="border-color:var(--red);margin-top:12px"><div class="sec-title">⚠️ ' + resumen.avisos.length
      + ' dato(s) que no se pudieron clasificar</div><div class="tiny muted" style="margin-bottom:6px">'
      + 'Se cuentan en la bitácora pero no llegan al formato. Revise el proceso o regístrelos como dato especial.</div>';
    resumen.avisos.forEach(a => {
      h += '<div class="list-row">' + (a.radicado ? '<span class="rad" data-acc="abrirProc" data-p="' + a.proceso_id + '" style="cursor:pointer">' + esc(a.radicado) + '</span>' : '<span class="muted">—</span>')
        + '<span class="tiny">' + esc(a.nota) + '<div class="muted">' + fmt(a.fecha) + ' · ' + esc(a.title || a.seccion) + '</div></span>'
        + '<span class="spacer"></span>'
        + (registra ? '<button class="btn sm" data-acc="clasificar" data-c="' + a.seccion + '" data-f="' + esc(a.fecha || '') + '" data-p="' + (a.proceso_id || '') + '">Clasificar</button>' : '')
        + '</div>';
    });
    h += '</div>';
  }

  if (resumen.manuales.length) {
    h += '<div class="card" style="margin-top:12px"><div class="sec-title">✍️ Datos especiales del periodo</div>';
    resumen.manuales.forEach(e => {
      h += '<div class="list-row"><span class="tiny">' + fmt(e.fecha) + '</span>'
        + '<span class="tiny">' + esc(e.seccion) + ' · <b>' + e.cantidad + '</b>'
        + (e.nota ? '<div class="muted">' + esc(e.nota) + '</div>' : '') + '</span><span class="spacer"></span>'
        + (e.radicado ? '<span class="badge b-gray">' + esc(e.radicado) + '</span> ' : '')
        + (registra ? '<button class="btn sm danger" data-acc="borrarDato" data-id="' + e.id + '">Eliminar</button>' : '')
        + '</div>';
    });
    h += '</div>';
  }

  const el = $('#view-estadistica');
  el.innerHTML = h;
  delegar(el, {
    desplegar: c => desplegar(c.dataset.c),
    abrirProc: c => nav.detalle(c.dataset.p),
    nuevoDato: () => abrirDato(''),
    clasificar: c => abrirDato(c.dataset.c, c.dataset.f, c.dataset.p),
    borrarDato: async c => {
      if (!confirm('¿Eliminar este dato especial?')) return;
      await api.del('/api/estadistica/eventos/' + c.dataset.id);
      toast('Dato eliminado'); renderEstadistica();
    },
    oficial: () => descargar('/api/estadistica/oficial.xlsx'),
    completo: () => descargar('/api/estadistica/completo.xlsx'),
    bitacora: descargarBitacora,
  });
  $('#eTrim').onchange = e => {
    const t = trimestres().find(x => x.clave === e.target.value);
    if (t) { S.eDesde = t.desde; S.eHasta = t.hasta; abiertas = new Set(); renderEstadistica(); }
  };
  $('#eDesde').onchange = e => { S.eDesde = e.target.value; abiertas = new Set(); renderEstadistica(); };
  $('#eHasta').onchange = e => { S.eHasta = e.target.value; abiertas = new Set(); renderEstadistica(); };
  abiertas.forEach(cargarDetalle);
}

function kpi(cls, n, l) {
  return '<div class="card kpi ' + cls + '"><div class="n">' + n + '</div><div class="l">' + l + '</div></div>';
}

/* El desglose se pide solo al abrir la sección: son cientos de filas por sección. */
function desplegar(code) {
  const x = resumen.secciones.find(s => s.code === code);
  if (!x || !x.total) return;
  if (abiertas.has(code)) abiertas.delete(code); else abiertas.add(code);
  renderEstadistica();
}

async function cargarDetalle(code) {
  const caja = $('#det_' + code);
  if (!caja) return;
  const d = await api.get('/api/estadistica/secciones/' + code, periodo());
  caja.innerHTML = '<table style="width:100%"><thead><tr><th>Fila</th><th>Columna</th><th style="width:70px">Cantidad</th></tr></thead><tbody>'
    + d.detalle.map(x => '<tr><td class="tiny">' + esc(x.fila) + '</td><td class="tiny">' + esc(x.columna)
      + '</td><td><b>' + x.cantidad + '</b></td></tr>').join('')
    + '</tbody></table>';
}

/* ----- dato especial ----- */

async function abrirDato(code, fecha, procesoId) {
  if (!procesos.length) procesos = (await api.get('/api/procesos')).filas;
  const secciones = await api.get('/api/estadistica/secciones');
  pon('se_fecha', fecha || S.eDesde);
  pon('se_cant', 1); pon('se_nota', '');
  $('#se_proc').innerHTML = opciones(procesos.map(p => [p.id, p.radicado]), procesoId || '', '— sin proceso —');
  $('#se_sec').innerHTML = opciones(secciones.map(s => [s.code, s.n + '. ' + s.title]), code || '', '— elija la sección —');
  await cargarEtiquetas();
  abrir('ovStatEvent');
}

async function cargarEtiquetas() {
  const code = val('se_sec');
  if (!code) { $('#se_row').innerHTML = ''; $('#se_col').innerHTML = ''; return; }
  const d = await api.get('/api/estadistica/secciones/' + code + '/etiquetas');
  $('#se_row').innerHTML = opciones(d.filas.map(f => [f.valor, f.etiqueta]), '', '— elija la fila —');
  $('#se_col').innerHTML = opciones(d.columnas.map(c => [c.valor, c.etiqueta]), '', '— elija la columna —');
}

async function guardarDato() {
  if (!val('se_fecha') || !val('se_sec') || !val('se_row') || !val('se_col')) { toast('Complete fecha, sección, fila y columna'); return; }
  await api.post('/api/estadistica/eventos', {
    fecha: val('se_fecha'), seccion: val('se_sec'), fila: val('se_row'), columna: val('se_col'),
    cantidad: Number(val('se_cant')) || 1, proceso_id: val('se_proc'), nota: val('se_nota'),
  });
  cerrar('ovStatEvent'); toast('Dato registrado'); renderEstadistica();
}

/* ----- descargas ----- */

async function descargar(url) {
  pon('xd_desde', S.eDesde); pon('xd_hasta', S.eHasta);
  $('#xd_trim').innerHTML = opciones(trimestres().map(t => [t.clave, t.etiqueta]), '', '— a la medida —');
  $('#xd_go').dataset.url = url;
  abrir('ovExp');
}

async function confirmarDescarga() {
  const url = $('#xd_go').dataset.url;
  const desde = val('xd_desde'), hasta = val('xd_hasta');
  if (!desde || !hasta || desde > hasta) { toast('Revise el periodo'); return; }
  $('#xd_status').textContent = 'Generando el archivo…';
  const { blob, aviso } = await api.archivo(url, { desde, hasta });
  const oficial = url.indexOf('oficial') >= 0;
  const nombre = (oficial ? 'SIERJU_' + desde + '_a_' + hasta : 'SIERJU_COMPLETO_' + desde + '_' + hasta) + '.xlsx';
  await guardarArchivoBinario(nombre, blob, 'Libro de Excel (*.xlsx)');
  cerrar('ovExp');
  if (aviso) toast('Atención: columnas sin lugar en la plantilla: ' + aviso);
  else toast('Excel generado conservando el formato oficial');
}

async function descargarBitacora() {
  const csv = await api.get('/api/estadistica/bitacora.csv', periodo());
  const nombre = 'SIERJU_bitacora_' + S.eDesde + '_' + S.eHasta + '.csv';
  await guardarArchivo(nombre, '﻿' + csv.replace(/^﻿/, ''), 'text/csv;charset=utf-8', 'CSV (*.csv)');
}

export function iniciarEstadistica() {
  $('#se_sec').onchange = cargarEtiquetas;
  $('#se_save').onclick = guardarDato;
  $('#xd_go').onclick = confirmarDescarga;
  $('#xd_trim').onchange = e => {
    const t = trimestres().find(x => x.clave === e.target.value);
    if (t) { pon('xd_desde', t.desde); pon('xd_hasta', t.hasta); }
  };
}
