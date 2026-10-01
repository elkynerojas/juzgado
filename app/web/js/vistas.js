import { api } from './api.js';
import { S, nav, puede, cat } from './estado.js';
import { $, esc, fmt, hoyISO, fechaLarga, toast, badge, badgeTermino, delegar, opciones, guardarArchivo, imprimir } from './util.js';
import { openProc } from './formularios.js';

const buscado = () => ($('#search').value || '').trim();

/* ===== TABLERO ===== */
function kpi(cls, f, n, l) {
  return '<div class="card kpi ' + cls + '"' + (f ? ' data-acc="kpi" data-f="' + f + '"' : '') + '><div class="n">' + n + '</div><div class="l">' + l + '</div></div>';
}

export async function renderTablero() {
  const s = await api.get('/api/tablero');
  let h;
  if (!s.procesos) {
    h = '<div class="empty">Aún no hay procesos.<br><br>'
      + (puede('procesos.crear') ? '<button class="btn primary" data-acc="nuevo">+ Registrar el primer proceso</button> &nbsp; ' : '')
      + (puede('respaldo.restaurar') ? '<button class="btn" data-acc="ejemplos">Cargar datos de ejemplo</button>' : '') + '</div>';
  } else {
    h = '<div class="grid kpis">'
      + kpi('red', 'sc', s.sin_constancia, 'Secretaría: sin constancia')
      + kpi('red', 'fp', s.falta_pasar, 'Secretaría: falta pasar al despacho')
      + kpi('red', 'ad', s.al_despacho, 'Al despacho: pendiente proveer')
      + kpi('navy', '', s.procesos, 'Procesos registrados') + '</div>';
    h += '<div class="two"><div class="card"><div class="sec-title">⏰ Próximos vencimientos</div>';
    if (!s.proximos.length) h += '<div class="muted tiny">No hay términos corriendo.</div>';
    s.proximos.forEach(x => {
      h += '<div class="list-row" data-acc="abrir" data-p="' + x.proceso_id + '" style="cursor:pointer"><span class="rad">' + esc(x.radicado) + '</span>'
        + '<span class="muted tiny" style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + esc(x.descripcion) + '</span><span class="spacer"></span>'
        + '<span class="badge ' + (x.faltan <= 3 ? 'b-amber' : 'b-blue') + '">' + fmt(x.fecha) + ' · faltan ' + x.faltan + 'd</span></div>';
    });
    h += '</div><div class="card"><div class="sec-title">📊 Actuaciones por situación</div>';
    s.por_situacion.forEach(x => { if (x.total) h += '<div class="list-row">' + badge(x) + '<span class="spacer"></span><b>' + x.total + '</b></div>'; });
    h += '<div class="list-row" style="border-top:2px solid var(--line);margin-top:4px"><span class="muted">Ubicación</span><span class="spacer"></span>'
      + '<span class="badge b-red">Despacho ' + s.en_despacho + '</span> <span class="badge b-slate">Secretaría ' + s.en_secretaria + '</span></div></div></div>';
  }
  const el = $('#view-tablero');
  el.innerHTML = h;
  delegar(el, {
    kpi: k => { S.filtro = k.dataset.f; nav.ir('procesos'); },
    abrir: r => nav.detalle(r.dataset.p),
    nuevo: () => openProc(null),
    ejemplos: cargarEjemplos,
  });
}

export async function cargarEjemplos() {
  await api.post('/api/datos/ejemplos');
  toast('Ejemplos cargados');
  nav.ir('tablero');
}

/* ===== PROCESOS ===== */
const CHIPS = [['', 'Todos'], ['ad', 'Al despacho'], ['rs', 'Represa secretaría'], ['sc', 'Sin constancia'], ['fp', 'Falta pasar'], ['esp', 'Esperando término'], ['susp', 'Suspendidos']];

export async function renderProcesos() {
  const filas = await api.get('/api/procesos', { q: buscado(), filtro: S.filtro });
  let h = '<div class="chips">';
  CHIPS.forEach(([f, l]) => { h += '<div class="chip ' + ((S.filtro || '') === f ? 'active' : '') + '" data-acc="chip" data-c="' + f + '">' + l + '</div>'; });
  h += '</div><div class="tablewrap"><table><thead><tr><th>Radicado</th><th>Partes</th><th>Situación</th><th>Ubicación</th><th>Represam.</th><th>Inactividad</th><th>Próx. venc.</th><th>Sin mov.</th></tr></thead><tbody>';
  if (!filas.length) h += '<tr class="fija"><td colspan="8" class="muted" style="text-align:center;padding:26px">Sin resultados.</td></tr>';
  filas.forEach(p => {
    const d = p.derivado;
    const loc = (d.en_despacho ? '<span class="badge b-red">Despacho</span> ' : '') + (d.en_secretaria ? '<span class="badge b-slate">Secretaría</span>' : '') || '<span class="muted">—</span>';
    const rep = [];
    if (d.rep_despacho) rep.push('<span class="badge b-red">Desp ' + d.rep_despacho + '</span>');
    if (d.rep_secretaria) rep.push('<span class="badge b-amber">Secr ' + d.rep_secretaria + '</span>');
    const sit = p.situacion !== 'Activo' ? ' <span class="badge b-blue">' + esc(p.situacion) + '</span>' : '';
    h += '<tr data-acc="abrir" data-p="' + p.id + '"><td class="rad">' + esc(p.radicado) + sit + (p.notas ? ' 📝' : '') + '</td>'
      + '<td class="tiny">' + esc(p.demandante || '—') + '<div class="muted">c/ ' + esc(p.demandado || '—') + '</div></td>'
      + '<td class="tiny">' + esc(p.clase || '') + '<div class="muted">' + d.vivas + ' viva(s)</div></td><td>' + loc + '</td>'
      + '<td>' + (rep.join(' ') || '<span class="muted">—</span>') + '</td><td class="tiny">' + esc(d.inactividad) + '</td>'
      + '<td class="tiny">' + (d.proximo ? fmt(d.proximo) : '<span class="muted">—</span>') + '</td>'
      + '<td class="tiny">' + (d.dias_sin_mov > 0 ? d.dias_sin_mov + 'd' : '—') + '</td></tr>';
  });
  h += '</tbody></table></div>';
  const el = $('#view-procesos');
  el.innerHTML = h;
  delegar(el, {
    chip: c => { S.filtro = c.dataset.c || null; renderProcesos(); },
    abrir: r => nav.detalle(r.dataset.p),
  });
}

/* ===== GESTIÓN POR PAQUETES ===== */
const ESTADOS = [[1, 'Esperando término'], [3, 'Sin constancia'], [4, 'Falta pasar'], [5, 'Al despacho'], [6, 'Corre ejecutoria'], [7, 'Pendiente cumplir'], [8, 'Trámite secretaría']];
let filasPaquete = [];

function filtrosPaquete() { return { materia: S.gMat, situacion: S.gSit, tipo: S.gTipo, q: buscado() }; }
function tituloPaquete() { const q = buscado(); return S.gTipo || S.gMat || (q ? '“' + q + '”' : 'Todos los paquetes'); }

export async function renderGestion() {
  const r = await api.get('/api/paquetes', filtrosPaquete());
  filasPaquete = r.filas;
  // primero las materias del catálogo, luego las que solo existen en actuaciones ya registradas
  const materias = cat('materias').concat(Object.keys(r.materias).filter(m => !cat('materias').includes(m)));
  let h = '<div class="card" style="margin:12px 0;padding:12px 14px"><div class="sec-title" style="margin:0 0 4px">🗂️ Trabajo por paquetes (jornadas)</div><div class="tiny muted">Elija una <b>materia</b> y trabaje ese día todos los expedientes que la tengan pendiente. También puede escribir en el buscador de arriba: “liquidación”, “terminación”, “subsanación”…</div></div>';
  h += '<div class="filterbar"><div class="lbl">Materia / tipo de solicitud</div>';
  h += '<div class="chip ' + (!S.gMat ? 'active' : '') + '" data-acc="mat" data-m="">Todas <span class="c">' + r.total + '</span></div>';
  materias.forEach(m => { if (r.materias[m]) h += '<div class="chip ' + (S.gMat === m ? 'active' : '') + '" data-acc="mat" data-m="' + esc(m) + '">' + esc(m) + ' <span class="c">' + r.materias[m] + '</span></div>'; });
  h += '</div><div class="filterbar"><div class="lbl">Estado (todas son pendientes de cierre)</div>';
  h += '<div class="chip ' + (S.gSit === null ? 'active' : '') + '" data-acc="sit" data-s="">Todos</div>';
  ESTADOS.forEach(([c, l]) => { h += '<div class="chip ' + (S.gSit === c ? 'active' : '') + '" data-acc="sit" data-s="' + c + '">' + l + '</div>'; });
  h += '</div><div class="filterbar"><div class="lbl">Tipo de solicitud (catálogo detallado)</div><select id="gTipoSel" style="max-width:360px">'
    + opciones(cat('tipos_solicitud'), S.gTipo || '', 'Todos los tipos') + '</select>'
    + (S.gTipo ? '<button class="btn sm" data-acc="tipoClr">✕ quitar</button>' : '') + '</div>';
  h += '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:6px 2px 8px"><div class="tiny muted" style="flex:1"><b>' + r.filas.length + '</b> expediente(s) en <b>' + esc(tituloPaquete()) + '</b> — clic en una fila para abrir el proceso.</div>';
  if (r.filas.length && puede('paquetes.exportar')) h += '<button class="btn sm" data-acc="imprimir">🖨️ Imprimir lista</button><button class="btn sm" data-acc="csv">⬇️ Exportar</button>';
  h += '</div><div class="tablewrap"><table><thead><tr><th>Radicado</th><th>Cuaderno</th><th>Materia</th><th>Descripción</th><th>Situación</th><th>Término / vence</th><th>Resultado</th></tr></thead><tbody>';
  if (!r.filas.length) h += '<tr class="fija"><td colspan="7" class="muted" style="text-align:center;padding:26px">No hay actuaciones pendientes en este paquete.</td></tr>';
  r.filas.forEach(a => {
    const d = a.derivado;
    const term = d.est_termino ? badgeTermino(d.est_termino) + (d.vencimiento ? ' <span class="tiny muted">' + fmt(d.vencimiento) + '</span>' : '') : '<span class="muted">—</span>';
    h += '<tr data-acc="abrir" data-p="' + a.proceso_id + '"><td class="rad">' + esc(a.radicado) + '</td><td class="tiny">' + esc(a.cuaderno) + '</td>'
      + '<td class="tiny"><b>' + esc(a.materia || '—') + '</b></td><td class="tiny">' + esc(a.descripcion) + (a.tipo_solicitud ? '<div class="muted">' + esc(a.tipo_solicitud) + '</div>' : '') + '</td>'
      + '<td>' + badge(d) + '</td><td>' + term + '</td><td>' + (d.resultado.texto ? '<span class="badge ' + d.resultado.badge + '">' + esc(d.resultado.texto) + '</span>' : '') + '</td></tr>';
  });
  h += '</tbody></table></div>';
  const el = $('#view-gestion');
  el.innerHTML = h;
  delegar(el, {
    mat: c => { S.gMat = c.dataset.m || null; renderGestion(); },
    sit: c => { S.gSit = c.dataset.s === '' ? null : Number(c.dataset.s); renderGestion(); },
    tipoClr: () => { S.gTipo = null; renderGestion(); },
    abrir: r => nav.detalle(r.dataset.p),
    imprimir: imprimirLista,
    csv: exportarCSV,
  });
  $('#gTipoSel').onchange = e => { S.gTipo = e.target.value || null; renderGestion(); };
}

function imprimirLista() {
  const c = S.cfg, titulo = tituloPaquete();
  const membrete = c.tiene_membrete ? '<div class="mem"><img src="/api/config/membrete"></div>' : '<div class="jz">' + esc(c.juzgado.juzgado) + '<br>' + esc(c.juzgado.ciudad) + '</div>';
  let t = '<table><thead><tr><th>#</th><th>Radicado</th><th>Partes</th><th>Descripción</th><th>Situación</th><th>Término / vence</th></tr></thead><tbody>';
  filasPaquete.forEach((a, i) => {
    const d = a.derivado;
    t += '<tr><td>' + (i + 1) + '</td><td>' + esc(a.radicado) + '</td><td>' + esc(a.partes) + '</td><td>' + esc(a.descripcion) + '</td><td>' + esc(d.situacion) + '</td><td>'
      + esc(d.est_termino ? d.est_termino + (d.vencimiento ? ' · ' + fmt(d.vencimiento) : '') : '—') + '</td></tr>';
  });
  t += '</tbody></table>';
  const CSS = '@page{size:Letter landscape;margin:1.6cm}html,body{margin:0}body{font-family:Arial,Helvetica,sans-serif;color:#000;font-size:10pt}.mem{margin-bottom:8pt}.mem img{width:100%;max-width:14cm}.jz{text-align:center;font-weight:bold;font-size:10pt;margin-bottom:8pt}.ti{text-align:center;font-weight:bold;text-decoration:underline;font-size:13pt;margin:4pt 0}.sub{text-align:center;margin-bottom:12pt}table{border-collapse:collapse;width:100%}th,td{border:1px solid #444;padding:4pt 6pt;text-align:left;vertical-align:top}th{background:#e8ecf3}';
  imprimir('<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><base href="' + location.origin + '/"><title>Jornada ' + esc(titulo) + '</title><style>' + CSS + '</style></head><body>'
    + membrete + '<div class="ti">JORNADA DE TRABAJO</div><div class="sub"><b>' + esc(titulo) + '</b> &mdash; ' + fechaLarga(hoyISO()) + ' &mdash; ' + filasPaquete.length + ' expediente(s)</div>' + t + '</body></html>');
}

async function exportarCSV() {
  const csv = await api.get('/api/paquetes.csv', filtrosPaquete());
  const nombre = 'jornada_' + tituloPaquete().replace(/[^a-z0-9]+/gi, '_').toLowerCase() + '_' + hoyISO() + '.csv';
  // el BOM hace que Excel abra bien las tildes; fetch lo quita al decodificar
  await guardarArchivo(nombre, '﻿' + csv.replace(/^﻿/, ''), 'text/csv;charset=utf-8', 'CSV (*.csv)');
}
