/* Panel de audiencias: rango, filtros, las que faltan por confirmar y los dos modales (v2 del HTML).
   En la v2 este panel vivía dentro de Estadística y su contador nunca se pintaba; aquí tiene pestaña propia. */
import { api } from './api.js';
import { S, nav, puede } from './estado.js';
import { $, esc, fmt, fmtL, toast, abrir, cerrar, delegar, opciones } from './util.js';
import { listasDe, opcionesPersonal } from './catalogos.js';

const val = id => { const el = $('#' + id); return el ? el.value : ''; };
const pon = (id, v) => { const el = $('#' + id); if (el) el.value = v == null ? '' : v; };
const mostrar = (id, cond) => { const el = $('#' + id); if (el) el.style.display = cond ? '' : 'none'; };

const BADGE = { 'Programada': 'b-blue', 'Realizada': 'b-green', 'Suspendida': 'b-amber', 'Aplazada': 'b-amber', 'Cancelada / no realizada': 'b-gray' };
// los cuatro botones con que se resuelve una audiencia de la lista de pendientes
const RESULTADOS = [['Realizada', '✓ Se realizó', 'primary'], ['Aplazada', 'Aplazada', ''], ['Suspendida', 'Suspendida', ''], ['Cancelada / no realizada', 'No se realizó', 'danger']];

let filas = [];
let resolviendo = null;
// los procesos del selector de "fijar audiencia", para no pedirlos a cada cambio
let procesos = [];
const procPorId = id => procesos.find(x => x.id === id) || {};

export async function renderAudiencias() {
  const r = await api.get('/api/audiencias', { desde: S.aDesde, hasta: S.aHasta, estado: S.aEstado, area: S.aArea });
  filas = r.filas.concat(r.pendientes);
  const gestiona = puede('audiencias.gestionar');

  let h = '<div class="card" style="margin:12px 0;padding:12px 14px"><div class="sec-title" style="margin:0 0 4px">📅 Audiencias y diligencias</div>'
    + '<div class="tiny muted">Lo que se fija aquí queda como actuación del cuaderno y alimenta la estadística. '
    + 'Al pasar la fecha, la audiencia aparece arriba hasta que se registre qué pasó.</div></div>';

  if (r.pendientes.length) {
    h += '<div class="card" style="border-color:var(--amber)"><div class="sec-title">⚠️ ' + r.pendientes.length
      + ' audiencia(s) por confirmar</div><div class="tiny muted" style="margin-bottom:6px">Ya pasó la fecha y siguen como programadas.</div>';
    r.pendientes.forEach(a => {
      h += '<div class="list-row"><span class="rad">' + esc(a.radicado) + '</span>'
        + '<span class="tiny">' + fmtL(a.aud_fecha) + (a.aud_hora ? ' · ' + esc(a.aud_hora) : '')
        + '<div class="muted">' + esc(a.aud_tipo || a.cuaderno) + '</div></span><span class="spacer"></span>'
        + (gestiona ? RESULTADOS.map(([e, l, cls]) => '<button class="btn sm ' + cls + '" data-acc="resolver" data-a="' + a.actuacion_id + '" data-e="' + esc(e) + '">' + l + '</button>').join(' ') : '')
        + '</div>';
    });
    h += '</div>';
  }

  h += '<div class="filterbar"><div class="lbl">Rango y filtros</div>'
    + '<input type="date" id="aDesde" class="fltsel" value="' + esc(S.aDesde || '') + '">'
    + '<input type="date" id="aHasta" class="fltsel" value="' + esc(S.aHasta || '') + '">'
    + '<select class="fltsel" id="aEstado">' + opciones(S.cfg.audiencias.estados, S.aEstado || '', 'Todo estado') + '</select>'
    + '<select class="fltsel" id="aArea">' + opciones(S.cfg.areas, S.aArea || '', 'Toda área') + '</select>'
    + (S.aDesde || S.aHasta || S.aEstado || S.aArea ? '<button class="btn sm" data-acc="aClr">✕ Limpiar</button>' : '')
    + (gestiona ? '<span class="spacer" style="flex:1"></span><button class="btn primary sm" data-acc="fijar">+ Fijar audiencia</button>' : '')
    + '</div>';

  h += '<div class="grid kpis">';
  S.cfg.audiencias.estados.forEach(e => {
    h += '<div class="card kpi"><div class="n">' + (r.kpis[e] || 0) + '</div><div class="l">' + esc(e) + '</div></div>';
  });
  h += '</div>';

  h += '<div class="tablewrap"><table><thead><tr><th>Fecha</th><th>Radicado</th><th>Área</th><th>Cuaderno</th><th>Clase</th><th>Estado</th><th>Causa</th><th>Responsable</th><th></th></tr></thead><tbody>';
  if (!r.filas.length) h += '<tr class="fija"><td colspan="9" class="muted" style="text-align:center;padding:26px">No hay audiencias en este rango.</td></tr>';
  r.filas.forEach(a => {
    h += '<tr class="fija"><td class="tiny" style="white-space:nowrap">' + fmt(a.aud_fecha) + (a.aud_hora ? '<div class="muted">' + esc(a.aud_hora) + '</div>' : '') + '</td>'
      + '<td class="rad" data-acc="abrir" data-p="' + a.proceso_id + '" style="cursor:pointer">' + esc(a.radicado) + '</td>'
      + '<td class="tiny">' + esc(a.area) + '</td><td class="tiny">' + esc(a.cuaderno) + '</td>'
      + '<td class="tiny">' + esc(a.aud_tipo || '—') + (a.aud_inmediata ? ' <span class="badge b-blue">inmediata</span>' : '') + '</td>'
      + '<td><span class="badge ' + (BADGE[a.aud_estado] || 'b-blue') + '">' + esc(a.aud_estado) + '</span></td>'
      + '<td class="tiny">' + esc(a.aud_causa || '—') + '</td><td class="tiny">' + esc(a.asignado_a || '—') + '</td>'
      + '<td>' + (gestiona ? '<button class="btn sm" data-acc="resolver" data-a="' + a.actuacion_id + '">Resultado</button>' : '') + '</td></tr>';
  });
  h += '</tbody></table></div>';

  const el = $('#view-audiencias');
  el.innerHTML = h;
  delegar(el, {
    abrir: c => nav.detalle(c.dataset.p),
    fijar: abrirFijar,
    resolver: c => abrirResolver(c.dataset.a, c.dataset.e || ''),
    aClr: () => { S.aDesde = S.aHasta = S.aEstado = S.aArea = null; renderAudiencias(); },
  });
  [['aDesde', 'aDesde'], ['aHasta', 'aHasta'], ['aEstado', 'aEstado'], ['aArea', 'aArea']].forEach(([id, clave]) => {
    $('#' + id).onchange = e => { S[clave] = e.target.value || null; renderAudiencias(); };
  });
  pintarContador(r.pendientes.length);
}

export function pintarContador(n) {
  const dot = $('#audDot');
  if (!dot) return;
  dot.textContent = n || '';
  dot.style.display = n ? '' : 'none';
}

/* ----- fijar ----- */

async function abrirFijar() {
  procesos = (await api.get('/api/procesos')).filas;
  pon('au_f', ''); pon('au_h', '');
  $('#au_proc').innerHTML = opciones(procesos.map(p => [p.id, p.radicado + ' · ' + (p.demandante || '') + ' c/ ' + (p.demandado || '')]), '', '— elija el proceso —');
  $('#au_est').innerHTML = opciones(S.cfg.audiencias.estados, 'Programada');
  $('#au_resp').innerHTML = opcionesPersonal('');
  await sincronizarFijar();
  abrir('ovAud');
}

async function sincronizarFijar() {
  const pid = val('au_proc');
  if (!pid) { $('#au_cua').innerHTML = ''; $('#au_tipo').innerHTML = ''; mostrar('au_causaBox', false); return; }
  const p = procPorId(pid);
  const [cuadernos, l] = await Promise.all([api.get('/api/audiencias/cuadernos/' + pid), listasDe(p.naturaleza, p.clase)]);
  $('#au_cua').innerHTML = opciones(cuadernos, val('au_cua') || cuadernos[0] || 'Principal');
  $('#au_tipo').innerHTML = opciones(l.aud_tipos, val('au_tipo'));
  pintarCausa('au', p.naturaleza, val('au_est'));
}

/* Las causas salen de las columnas oficiales, nunca de una lista genérica. */
function pintarCausa(prefijo, naturaleza, estado) {
  const aplaza = (estado || '').indexOf('Aplaz') >= 0;
  const pide = aplaza || (estado || '').indexOf('Cancel') >= 0;
  mostrar(prefijo + '_causaBox', pide);
  if (!pide) { pon(prefijo + '_causa', ''); return; }
  const rama = (naturaleza || '').startsWith('Penal') ? 'penal' : 'civil';
  const causas = S.cfg.audiencias.causas[rama + (aplaza ? '_aplazada' : '_cancelada')] || [];
  const previa = val(prefijo + '_causa');
  $('#' + prefijo + '_causa').innerHTML = opciones(causas, previa, '— elija la causa —');
  $('#' + prefijo + '_causaLbl').textContent = aplaza ? 'Causa del aplazamiento' : 'Causa de la cancelación';
}

async function guardarFijada() {
  if (!val('au_proc')) { toast('Elija el proceso'); return; }
  if (!val('au_f')) { toast('Indique la fecha'); return; }
  await api.post('/api/audiencias', {
    proceso_id: val('au_proc'), cuaderno: val('au_cua'), fecha: val('au_f'), hora: val('au_h'),
    tipo: val('au_tipo'), estado: val('au_est'), causa: val('au_causa'), asignado_a: val('au_resp'),
  });
  cerrar('ovAud'); toast('Audiencia fijada'); renderAudiencias();
}

/* ----- resolver ----- */

export async function abrirResolver(aid, previo) {
  const a = filas.find(x => x.actuacion_id === aid);
  if (!a) { toast('No se encontró la audiencia'); return; }
  resolviendo = a;
  $('#rs_info').innerHTML = '<b>' + esc(a.radicado) + '</b> · ' + fmtL(a.aud_fecha) + (a.aud_hora ? ' ' + esc(a.aud_hora) : '')
    + '<br>' + esc(a.aud_tipo || a.cuaderno);
  // "Programada" no es un resultado: se resuelve con uno de los otros cuatro
  $('#rs_estado').innerHTML = opciones(RESULTADOS.map(([e]) => e), previo || 'Realizada');
  const l = await listasDe(a.naturaleza, '');
  $('#rs_nuevatipo').innerHTML = opciones(l.aud_tipos, a.aud_tipo);
  pon('rs_nueva', ''); pon('rs_nuevahora', ''); pon('rs_causa', '');
  pintarCausa('rs', a.naturaleza, val('rs_estado'));
  abrir('ovResolver');
}

async function guardarResultado() {
  if (!resolviendo) return;
  const r = await api.post('/api/audiencias/' + resolviendo.actuacion_id + '/resolver', {
    version: resolviendo.version, estado: val('rs_estado'), causa: val('rs_causa'),
    nueva_fecha: val('rs_nueva'), nueva_hora: val('rs_nuevahora'), nuevo_tipo: val('rs_nuevatipo'),
  });
  cerrar('ovResolver');
  toast(r.nueva ? 'Resultado registrado y nueva audiencia fijada' : 'Resultado registrado');
  if (S.vista === 'detalle') nav.detalle(S.proc); else renderAudiencias();
}

export function iniciarAudiencias() {
  $('#au_save').onclick = guardarFijada;
  $('#rs_save').onclick = guardarResultado;
  $('#au_proc').onchange = sincronizarFijar;
  $('#au_est').onchange = () => pintarCausa('au', procPorId(val('au_proc')).naturaleza, val('au_est'));
  $('#rs_estado').onchange = () => pintarCausa('rs', resolviendo ? resolviendo.naturaleza : '', val('rs_estado'));
}
