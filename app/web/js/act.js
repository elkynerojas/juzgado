/* Modal de actuación en tres fases: ingreso, cierre y audiencia, más las opciones avanzadas (v2 del HTML).
   Las reglas las calcula el servidor: la vista previa llama a /api/actuaciones/derivar, que además devuelve
   lo que se llenaría solo al guardar (constancia, pase, ejecutoria, cumplida). */
import { api } from './api.js';
import { S, nav, puede, cat } from './estado.js';
import { $, esc, fmtL, toast, badge, abrir, cerrar, debounce, opciones } from './util.js';
import { listasDe, mostrar, pintar, opcionesPersonal, cuadernosDe } from './catalogos.js';
import * as borrador from './borrador.js';

const val = id => { const el = $('#' + id); return el ? el.value : ''; };
const pon = (id, v) => { const el = $('#' + id); if (el) el.value = v == null ? '' : v; };
const marca = id => { const el = $('#' + id); return !!el && el.checked; };
const ponMarca = (id, v) => { const el = $('#' + id); if (el) el.checked = !!v; };

const PERSONALIZADO = '(personalizado)';
const rutaPorId = id => S.cfg.rutas.find(r => r.id === id) || null;

let editAct = null;
let pasoIdx = null;
let proc = null;      // el proceso abierto, para saber la naturaleza y sus cuadernos
let hermanas = [];

const guardarBorrador = borrador.autoguardado('act', '#ovAct', () => ({ proceso_id: S.proc, paso_idx: pasoIdx }));

export async function openAct(a, detalle) {
  if (!S.proc) { toast('Abra un proceso primero'); return; }
  editAct = a || null;
  proc = detalle || proc;
  hermanas = (detalle && detalle.actuaciones) || hermanas;
  $('#actTitle').textContent = a ? 'Editar actuación' : 'Nueva actuación';

  const nat = proc ? proc.naturaleza : 'Civil';
  const l = await listasDe(nat, proc ? proc.clase : '');

  pintar('a_cua', cuadernosDe(proc, hermanas), a ? a.cuaderno : (proc && proc.cuaderno_inicial) || 'Principal');
  pintar('a_mat', cat('materias'), a ? a.materia : 'Admisión / subsanación');
  pintar('a_tipo', l.tipos_gestion, a ? a.tipo_solicitud : '', '— sin especificar —');
  pintar('a_salstat', l.salidas_act, a ? a.salida_stat : '', '— sin salida —');
  pintar('a_audtipo', l.aud_tipos, a ? a.aud_tipo : '');
  pintar('a_audestado', S.cfg.audiencias.estados, a ? a.aud_estado : 'Programada');
  pintar('a_tprov', S.cfg.actuacion.tipos_providencia, a ? a.tipo_providencia : '', '— ninguna / auto de trámite —');
  pintar('a_notifforma', S.cfg.actuacion.notif_formas, a ? a.notif_forma : '', '— no aplica —');
  pintar('a_recurso', S.cfg.actuacion.recursos, a ? a.recurso_tipo : '', '— ninguno —');
  pintar('a_recobj', S.cfg.actuacion.objetos_recurso, a ? a.recurso_objeto : 'Auto');
  pintar('a_supres', S.cfg.actuacion.resultados_superior, a ? a.superior_resultado : '', '— pendiente / sin decidir —');
  pintar('a_recimpugres', S.cfg.actuacion.resultados_superior, a ? a.rec_impug_result : '', '— pendiente —');
  pintar('a_tp', S.cfg.actuacion.tramites_posteriores, a ? a.tp_tipo : '', '— no es trámite posterior —');
  $('#a_asig').innerHTML = opcionesPersonal(a ? a.asignado_a : '');

  pon('a_ori', a ? a.origen : 'Memorial'); pon('a_desc', a && a.descripcion); pon('a_mem', a && a.fecha_memorial);
  pon('a_cons', a && a.constancia); pon('a_pasa', a && a.pasa); pon('a_pase', a && a.pase);
  pon('a_prov', a && a.providencia); pon('a_ejec', a && a.ejecutoria); pon('a_cump', a && a.cumplida);
  pon('a_cierre', a && a.modo_cierre);
  pon('a_notif', a && a.notif_fecha); pon('a_ejecdias', a ? a.ejec_dias : S.cfg.actuacion.ejec_dias);
  pon('a_recfecha', a && a.recurso_fecha); pon('a_rectraslado', a && a.rec_traslado);
  pon('a_supfecha', a && a.superior_fecha);
  pon('a_recimpug', a && a.rec_impug); pon('a_recimpugfecha', a && a.rec_impug_fecha);
  pon('a_audfecha', a && a.aud_fecha); pon('a_audhora', a && a.aud_hora);
  ponMarca('a_esaud', a && a.es_audiencia); ponMarca('a_audinmediata', a && a.aud_inmediata);
  ponMarca('a_remate', a && a.remate_realizado); ponMarca('a_amparo', a && a.amparo_pobreza_concedido);

  const terminos = [[PERSONALIZADO, PERSONALIZADO]].concat(S.cfg.terminos.map(t => [t.nombre, t.nombre + ' (' + t.dias + 'd · ' + t.categoria + ')']));
  pintar('a_term', terminos, a ? a.termino : '', '— sin término —');
  pon('a_tdias', a && a.termino_dias); pon('a_thab', a ? String(a.termino_habil !== false) : 'true');
  pon('a_ini', a && a.fecha_inicio); ponMarca('a_susp', a && a.suspende); pon('a_obs', a && a.obs);
  pasoIdx = a && typeof a.paso_idx === 'number' ? a.paso_idx : null;
  pintar('a_ruta', S.cfg.rutas.map(r => [r.id, r.nombre]), a ? a.ruta_id : '', '— sin ruta —');

  $('#a_del').style.display = a && puede('actuaciones.eliminar') ? '' : 'none';
  mostrar('btnDesac', l.es_desacato);
  mostrar('audInmediataBox', l.es_garantias);
  // las opciones avanzadas quedan abiertas si traen algo diligenciado
  $('#advBox').classList.toggle('open', !!(a && (a.termino || a.tp_tipo || a.asignado_a || a.suspende || a.remate_realizado || a.amparo_pobreza_concedido)));

  await syncActForm();
  actualizaRutaPrev();
  const b = !a && borrador.guardado('act');
  borrador.barra('act', 'actDraft', b && b.proceso_id === S.proc ? b : null, recuperar);
  abrir('ovAct');
}

/* Abre el modal ya configurado como audiencia (botón "+ Audiencia" del detalle). */
export async function openAudiencia(detalle) {
  await openAct(null, detalle);
  pon('a_mat', S.cfg.audiencias.materia);
  pon('a_ori', 'Providencia (auto/sentencia)');
  ponMarca('a_esaud', true);
  await syncActForm();
  const f = $('#a_audfecha');
  if (f) f.focus();
}

async function recuperar(b) {
  borrador.aplicar(b.datos);
  pasoIdx = typeof b.paso_idx === 'number' ? b.paso_idx : null;
  await syncActForm();
  actualizaRutaPrev();
  toast('Borrador recuperado');
}

function leerAct() {
  return {
    cuaderno: val('a_cua'), materia: val('a_mat'), tipo_solicitud: val('a_tipo'), origen: val('a_ori'),
    descripcion: val('a_desc').trim(), fecha_memorial: val('a_mem'), constancia: val('a_cons'),
    pasa: val('a_pasa'), pase: val('a_pase'), providencia: val('a_prov'), ejecutoria: val('a_ejec'),
    cumplida: val('a_cump'), termino: val('a_term'), termino_dias: val('a_tdias') ? Number(val('a_tdias')) : null,
    termino_habil: val('a_thab') === 'true', fecha_inicio: val('a_ini'), suspende: marca('a_susp'),
    obs: val('a_obs').trim(), ruta_id: val('a_ruta'), paso_idx: typeof pasoIdx === 'number' ? pasoIdx : null,
    tp_tipo: val('a_tp'), asignado_a: val('a_asig'), tipo_providencia: val('a_tprov'), modo_cierre: val('a_cierre'),
    salida_stat: val('a_salstat'), entrada_stat: editAct ? editAct.entrada_stat : '',
    es_audiencia: marca('a_esaud'), aud_fecha: val('a_audfecha'), aud_hora: val('a_audhora'),
    aud_estado: val('a_audestado'), aud_tipo: val('a_audtipo'), aud_causa: val('a_audcausa'),
    aud_inmediata: marca('a_audinmediata'),
    recurso_tipo: val('a_recurso'), recurso_fecha: val('a_recfecha'), recurso_objeto: val('a_recobj'),
    rec_traslado: val('a_rectraslado'), superior_resultado: val('a_supres'), superior_fecha: val('a_supfecha'),
    rec_impug: val('a_recimpug'), rec_impug_result: val('a_recimpugres'), rec_impug_fecha: val('a_recimpugfecha'),
    remate_realizado: marca('a_remate'), amparo_pobreza_concedido: marca('a_amparo'),
    notif_fecha: val('a_notif'), notif_forma: val('a_notifforma'),
    ejec_dias: val('a_ejecdias') ? Number(val('a_ejecdias')) : S.cfg.actuacion.ejec_dias,
  };
}

/* Muestra u oculta lo condicional y repinta las causas de audiencia, que dependen de naturaleza y estado. */
async function syncActForm() {
  $('#a_mem').disabled = val('a_ori') === 'Vencimiento de término';
  mostrar('fPase', val('a_pasa') === 'Sí');
  mostrar('termCustom', val('a_term') === PERSONALIZADO);
  mostrar('audBox', marca('a_esaud'));
  mostrar('recBox', !!val('a_recurso'));
  mostrar('recImpugBox', val('a_recimpug') === 'Sí');

  const estado = val('a_audestado');
  const aplaza = estado.indexOf('Aplaz') >= 0 || estado.indexOf('Cancel') >= 0;
  mostrar('audCausaBox', marca('a_esaud') && aplaza);
  if (marca('a_esaud') && aplaza) {
    const nat = proc ? proc.naturaleza : 'Civil';
    const l = await listasDe(nat, proc ? proc.clase : '');
    const rama = l.es_penal ? 'penal' : 'civil';
    const clave = rama + (estado.indexOf('Aplaz') >= 0 ? '_aplazada' : '_cancelada');
    const previa = val('a_audcausa');
    pintar('a_audcausa', S.cfg.audiencias.causas[clave] || [], previa, '— elija la causa —');
    $('#audCausaLbl').textContent = estado.indexOf('Aplaz') >= 0 ? 'Causa del aplazamiento' : 'Causa de la cancelación';
  }
  vistaPrevia();
}

/* La clasificación y el autocompletado los calcula el servidor: es la misma regla que se aplica al guardar. */
const vistaPrevia = debounce(async () => {
  const d = await api.post('/api/actuaciones/derivar', leerAct());
  const ti = d.termino_info, tp = $('#termPrev');
  if (!ti || !ti.dias) tp.textContent = 'Sin término.';
  else if (!d.vencimiento) tp.innerHTML = 'Término de <b>' + ti.dias + ' ' + (ti.habil ? 'días hábiles' : 'días calendario') + '</b>. <span style="color:var(--amber)">Latente</span> — falta fecha de inicio.';
  else tp.innerHTML = 'Vence el <b>' + fmtL(d.vencimiento) + '</b> (' + ti.dias + ' ' + (ti.habil ? 'días hábiles' : 'días') + ') · <b>' + esc(d.est_termino) + '</b>';
  $('#actPrev').innerHTML = 'Se clasificará como: ' + badge(d) + (d.ubicacion ? ' · Ubicación: <b>' + d.ubicacion + '</b>' : '');
  pintarEjecutoria(d);
  pintarAutocompletado(d.autocompletado);
}, 200);

const EJEC_TEXTO = {
  sin_notificacion: 'Indique la fecha de notificación para computar la ejecutoria.',
  corre: 'Queda en firme el ',
  suspendida: 'Ejecutoria <b>suspendida</b>: ',
  en_firme: 'Recurso resuelto: queda en firme el ',
};

function pintarEjecutoria(d) {
  const e = d.ejecutoria_estado, caja = $('#ejecPrev');
  if (!caja || !e) return;
  if (e.estado === 'sin_notificacion') { caja.innerHTML = EJEC_TEXTO.sin_notificacion; return; }
  if (e.estado === 'suspendida') {
    caja.innerHTML = EJEC_TEXTO.suspendida
      + (e.pendiente === 'impugnacion' ? 'pendiente de resolver la impugnación.' : 'pendiente de resolver el recurso.');
    return;
  }
  caja.innerHTML = EJEC_TEXTO[e.estado] + '<b>' + fmtL(e.fecha) + '</b>.';
}

/* Avisa qué fechas va a poner la secretaría sola, para que nadie las escriba dos veces. */
function pintarAutocompletado(auto) {
  if (!auto) return;
  const pares = [['a_cons', auto.constancia], ['a_pase', auto.pase], ['a_ejec', auto.ejecutoria], ['a_cump', auto.cumplida]];
  const puestas = pares.filter(([id, v]) => v && !val(id));
  const caja = $('#actPrev');
  if (puestas.length) {
    const nombres = { a_cons: 'constancia', a_pase: 'pase', a_ejec: 'ejecutoria', a_cump: 'cumplida' };
    caja.innerHTML += '<div class="tiny muted" style="margin-top:4px">Al guardar se llenará: '
      + puestas.map(([id, v]) => esc(nombres[id]) + ' ' + fmtL(v)).join(' · ') + '</div>';
  }
}

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
  // un paso de audiencia deja la casilla marcada y su estado puesto
  if (p.es_audiencia) { ponMarca('a_esaud', true); if (p.aud_estado) pon('a_audestado', p.aud_estado); }
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

export async function crearSiguiente(a, detalle) {
  const s = a.siguiente;
  if (!s) { toast('No hay siguiente paso'); return; }
  await openAct(null, detalle);
  pon('a_cua', a.cuaderno); pon('a_ruta', s.ruta_id); pasoIdx = s.idx;
  if (a.tipo_solicitud) pon('a_tipo', a.tipo_solicitud);
  prefillPaso(s.paso); actualizaRutaPrev(); await syncActForm();
  toast('Siguiente paso: ' + s.paso.nombre);
}

/* Abre un cuaderno de incidente numerado sin tener que escribirlo a mano. */
function nuevoIncidente(base) {
  const usados = cuadernosDe(proc, hermanas);
  const rx = new RegExp('^' + base.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\s*(\\d+)$', 'i');
  const n = usados.reduce((max, c) => { const m = rx.exec(c || ''); return m ? Math.max(max, +m[1]) : max; }, 0);
  const nombre = base + ' ' + (n + 1);
  const sel = $('#a_cua');
  sel.innerHTML += '<option value="' + esc(nombre) + '" selected>' + esc(nombre) + '</option>';
  sel.value = nombre;
  toast('Cuaderno: ' + nombre);
  guardarBorrador();
}

async function saveAct() {
  const o = leerAct();
  if (!o.descripcion) { toast('Escriba la descripción'); return; }
  if (editAct) await api.put('/api/actuaciones/' + editAct.id, Object.assign(o, { version: editAct.version }));
  else await api.post('/api/procesos/' + S.proc + '/actuaciones', o);
  borrador.limpiar('act');
  cerrar('ovAct');
  toast('Actuación guardada');
  // se recarga del servidor: el autocompletado pudo cambiar fechas que el formulario no tiene
  nav.detalle(S.proc);
}

async function delAct() {
  if (!editAct || !confirm('¿Eliminar esta actuación?')) return;
  await api.del('/api/actuaciones/' + editAct.id);
  cerrar('ovAct'); toast('Actuación eliminada'); nav.detalle(S.proc);
}

const SINCRONIZAN = [
  'a_cua', 'a_mat', 'a_ori', 'a_pasa', 'a_term', 'a_tdias', 'a_thab', 'a_ini', 'a_mem', 'a_cons', 'a_pase',
  'a_prov', 'a_ejec', 'a_cump', 'a_susp', 'a_esaud', 'a_audestado', 'a_audfecha', 'a_audhora', 'a_recurso',
  'a_recimpug', 'a_supres', 'a_notif', 'a_ejecdias', 'a_cierre', 'a_tprov',
];

export function iniciarAct() {
  $('#a_save').onclick = saveAct;
  $('#a_del').onclick = delAct;
  $('#a_mat').addEventListener('change', sugTermino);
  SINCRONIZAN.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('input', syncActForm);
    el.addEventListener('change', syncActForm);
  });
  $('#a_ruta').addEventListener('change', onRutaChange);
  $('#a_tipo').addEventListener('change', onTipoChange);
  $('#advToggle').onclick = () => $('#advBox').classList.toggle('open');
  $('#ovAct').addEventListener('input', guardarBorrador);
  $('#ovAct').addEventListener('click', e => {
    const b = e.target.closest('[data-acc="incidente"]');
    if (b && $('#ovAct').contains(b)) nuevoIncidente(b.dataset.base);
  });
}
