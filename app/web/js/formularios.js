import { api } from './api.js';
import { S, nav, puede, cat } from './estado.js';
import { $, esc, fmtL, toast, badge, abrir, cerrar, debounce, opciones } from './util.js';

const val = id => $('#' + id).value;
const pon = (id, v) => { $('#' + id).value = v == null ? '' : v; };
function llenarDatalist(id, arr) { $('#' + id).innerHTML = arr.map(o => '<option value="' + esc(o) + '">').join(''); }

/* ===== PROCESO ===== */
let editProc = null;

export function openProc(p) {
  editProc = p || null;
  $('#procTitle').textContent = p ? 'Editar proceso' : 'Nuevo proceso';
  pon('p_rad', p && p.radicado); pon('p_nat', p ? p.naturaleza : 'Civil'); pon('p_clase', p && p.clase);
  pon('p_dte', p && p.demandante); pon('p_dda', p && p.demandado); pon('p_frad', p && p.fecha_rad);
  pon('p_sit', p ? p.situacion : 'Activo'); pon('p_macro', p && p.macroetapa);
  syncAsuntos(); llenarDatalist('macroetapas', cat('macroetapas'));
  $('#p_del').style.display = p && puede('procesos.eliminar') ? '' : 'none';
  abrir('ovProc');
}

function syncAsuntos() { llenarDatalist('asuntos', cat(val('p_nat') === 'Familia' ? 'asuntos_familia' : 'asuntos_civil')); }

async function saveProc() {
  const o = {
    radicado: val('p_rad').trim(), naturaleza: val('p_nat'), clase: val('p_clase'), demandante: val('p_dte'), demandado: val('p_dda'),
    fecha_rad: val('p_frad'), situacion: val('p_sit'), macroetapa: val('p_macro'),
  };
  if (!o.radicado) { toast('Escriba el radicado'); return; }
  let p;
  if (editProc) p = await api.put('/api/procesos/' + editProc.id, Object.assign(o, { version: editProc.version }));
  else p = await api.post('/api/procesos', o);
  cerrar('ovProc'); toast('Proceso guardado');
  if (editProc) nav.detalle(p.id); else nav.refrescar();
}

async function delProc() {
  if (!editProc || !confirm('¿Eliminar el proceso y todas sus actuaciones?')) return;
  await api.del('/api/procesos/' + editProc.id);
  cerrar('ovProc'); toast('Proceso eliminado'); nav.ir('procesos');
}

/* ===== ACTUACIÓN ===== */
let editAct = null, pasoIdx = null;

const PERSONALIZADO = '(personalizado)';
const rutaPorId = id => S.cfg.rutas.find(r => r.id === id) || null;

export function openAct(a) {
  if (!S.proc) { toast('Abra un proceso primero'); return; }
  editAct = a || null;
  $('#actTitle').textContent = a ? 'Editar actuación' : 'Nueva actuación';
  $('#a_cua').innerHTML = opciones(cat('cuadernos'), a ? a.cuaderno : 'Principal');
  $('#a_mat').innerHTML = opciones(cat('materias'), a ? a.materia : 'Admisión / subsanación');
  $('#a_tipo').innerHTML = opciones(cat('tipos_solicitud'), a ? a.tipo_solicitud : '', '— sin especificar —');
  pon('a_ori', a ? a.origen : 'Memorial'); pon('a_desc', a && a.descripcion); pon('a_mem', a && a.fecha_memorial);
  pon('a_cons', a && a.constancia); pon('a_pasa', a && a.pasa); pon('a_pase', a && a.pase);
  pon('a_prov', a && a.providencia); pon('a_ejec', a && a.ejecutoria); pon('a_cump', a && a.cumplida);
  const terminos = [[PERSONALIZADO, PERSONALIZADO]].concat(S.cfg.terminos.map(t => [t.nombre, t.nombre + ' (' + t.dias + 'd · ' + t.categoria + ')']));
  $('#a_term').innerHTML = opciones(terminos, a ? a.termino : '', '— sin término —');
  pon('a_tdias', a && a.termino_dias); pon('a_thab', a ? String(a.termino_habil !== false) : 'true');
  pon('a_ini', a && a.fecha_inicio); $('#a_susp').checked = a ? !!a.suspende : false; pon('a_obs', a && a.obs);
  pasoIdx = a && typeof a.paso_idx === 'number' ? a.paso_idx : null;
  $('#a_ruta').innerHTML = opciones(S.cfg.rutas.map(r => [r.id, r.nombre]), a ? a.ruta_id : '', '— sin ruta —');
  $('#a_del').style.display = a && puede('actuaciones.eliminar') ? '' : 'none';
  syncActForm(); actualizaRutaPrev(); abrir('ovAct');
}

function readAct() {
  return {
    cuaderno: val('a_cua'), materia: val('a_mat'), tipo_solicitud: val('a_tipo'), origen: val('a_ori'), descripcion: val('a_desc').trim(),
    fecha_memorial: val('a_mem'), constancia: val('a_cons'), pasa: val('a_pasa'), pase: val('a_pase'), providencia: val('a_prov'),
    ejecutoria: val('a_ejec'), cumplida: val('a_cump'), termino: val('a_term'), termino_dias: val('a_tdias') ? Number(val('a_tdias')) : null,
    termino_habil: val('a_thab') === 'true', fecha_inicio: val('a_ini'), suspende: $('#a_susp').checked, obs: val('a_obs').trim(),
    ruta_id: val('a_ruta'), paso_idx: typeof pasoIdx === 'number' ? pasoIdx : null,
  };
}

function syncActForm() {
  $('#a_mem').disabled = val('a_ori') === 'Vencimiento de término';
  $('#fPase').style.display = val('a_pasa') === 'Sí' ? '' : 'none';
  $('#termCustom').style.display = val('a_term') === PERSONALIZADO ? 'grid' : 'none';
  vistaPrevia();
}

/* La clasificación la calcula el servidor: es la misma regla que se aplicará al guardar. */
const vistaPrevia = debounce(async () => {
  const d = await api.post('/api/actuaciones/derivar', readAct());
  const ti = d.termino_info, tp = $('#termPrev');
  if (!ti || !ti.dias) tp.textContent = 'Sin término.';
  else if (!d.vencimiento) tp.innerHTML = 'Término de <b>' + ti.dias + ' ' + (ti.habil ? 'días hábiles' : 'días calendario') + '</b>. <span style="color:var(--amber)">Latente</span> — falta fecha de inicio.';
  else tp.innerHTML = 'Vence el <b>' + fmtL(d.vencimiento) + '</b> (' + ti.dias + ' ' + (ti.habil ? 'días hábiles' : 'días') + ') · <b>' + esc(d.est_termino) + '</b>';
  $('#actPrev').innerHTML = 'Se clasificará como: ' + badge(d) + (d.ubicacion ? ' · Ubicación: <b>' + d.ubicacion + '</b>' : '');
}, 200);

function sugTermino() {
  const sug = S.cfg.sugerencias_termino[val('a_mat')];
  if (sug && val('a_ori') === 'Vencimiento de término' && !val('a_term') && S.cfg.terminos.some(t => t.nombre === sug)) { pon('a_term', sug); syncActForm(); }
}

function actualizaRutaPrev() {
  const rp = $('#rutaPrev'), r = rutaPorId(val('a_ruta'));
  if (!r) { rp.style.display = 'none'; return; }
  rp.style.display = '';
  const idx = typeof pasoIdx === 'number' ? pasoIdx : 0;
  rp.innerHTML = '<b>' + esc(r.nombre) + '</b><br>' + r.pasos.map((p, k) => (k === idx ? '▶ ' : '· ') + (k + 1) + '. ' + esc(p.nombre)).join('<br>');
}

function prefillPaso(p) {
  if (!p) return;
  if (p.materia && cat('materias').includes(p.materia)) pon('a_mat', p.materia);
  if (p.origen) pon('a_ori', p.origen);
  if (p.descripcion && !val('a_desc')) pon('a_desc', p.descripcion);
  if (p.termino && S.cfg.terminos.some(t => t.nombre === p.termino)) pon('a_term', p.termino);
}

function onRutaChange() {
  const r = rutaPorId(val('a_ruta'));
  if (r && !editAct) { pasoIdx = 0; prefillPaso(r.pasos[0]); }
  else if (!r) pasoIdx = null;
  actualizaRutaPrev(); syncActForm();
}

function onTipoChange() {
  const rid = S.cfg.tipo_ruta[val('a_tipo')];
  if (rid && !editAct && !val('a_ruta')) { pon('a_ruta', rid); onRutaChange(); }
}

export function crearSiguiente(a) {
  const s = a.siguiente;
  if (!s) { toast('No hay siguiente paso'); return; }
  openAct(null);
  pon('a_cua', a.cuaderno); pon('a_ruta', s.ruta_id); pasoIdx = s.idx;
  if (a.tipo_solicitud) pon('a_tipo', a.tipo_solicitud);
  prefillPaso(s.paso); actualizaRutaPrev(); syncActForm();
  toast('Siguiente paso: ' + s.paso.nombre);
}

async function saveAct() {
  const o = readAct();
  if (!o.descripcion) { toast('Escriba la descripción'); return; }
  if (editAct) await api.put('/api/actuaciones/' + editAct.id, Object.assign(o, { version: editAct.version }));
  else await api.post('/api/procesos/' + S.proc + '/actuaciones', o);
  cerrar('ovAct'); toast('Actuación guardada'); nav.detalle(S.proc);
}

async function delAct() {
  if (!editAct || !confirm('¿Eliminar esta actuación?')) return;
  await api.del('/api/actuaciones/' + editAct.id);
  cerrar('ovAct'); toast('Actuación eliminada'); nav.detalle(S.proc);
}

export function iniciarFormularios() {
  $('#p_save').onclick = saveProc; $('#p_del').onclick = delProc; $('#p_nat').onchange = syncAsuntos;
  $('#a_save').onclick = saveAct; $('#a_del').onclick = delAct;
  $('#a_mat').addEventListener('change', sugTermino);
  ['a_cua', 'a_mat', 'a_ori', 'a_pasa', 'a_term', 'a_tdias', 'a_thab', 'a_ini', 'a_mem', 'a_cons', 'a_pase', 'a_prov', 'a_ejec', 'a_cump', 'a_susp'].forEach(id => {
    const el = document.getElementById(id);
    el.addEventListener('input', syncActForm); el.addEventListener('change', syncActForm);
  });
  $('#a_ruta').addEventListener('change', onRutaChange);
  $('#a_tipo').addEventListener('change', onTipoChange);
}
