/* Modal de proceso. Los campos visibles y las listas dependen de la naturaleza (v2 del HTML). */
import { api } from './api.js';
import { S, nav, puede, cat } from './estado.js';
import { $, $$, esc, toast, abrir, cerrar, opciones } from './util.js';
import { listasDe, delitosDe, mostrar, pintar, etiqueta, cuadernosDe } from './catalogos.js';
import * as borrador from './borrador.js';

const val = id => { const el = $('#' + id); return el ? el.value : ''; };
const pon = (id, v) => { const el = $('#' + id); if (el) el.value = v == null ? '' : v; };
const marca = id => { const el = $('#' + id); return !!el && el.checked; };
const ponMarca = (id, v) => { const el = $('#' + id); if (el) el.checked = !!v; };
function llenarDatalist(id, arr) { const el = $('#' + id); if (el) el.innerHTML = arr.map(o => '<option value="' + esc(o) + '">').join(''); }

let editProc = null;
let solicitudes = [];
let delitosExtra = [];
// la ley penal la determina el delito elegido; se recuerda para componer la naturaleza
let leyPorDelito = new Map();

const guardarBorrador = borrador.autoguardado('proc', '#ovProc', () => ({ solicitudes, delitos: delitosExtra }));

/* La naturaleza que se guarda: "Penal" a secas se compone con la ley del delito y el procedimiento. */
function naturalezaEfectiva() {
  const base = val('p_nat');
  if (base !== 'Penal') return base;
  const ley = leyPorDelito.get(val('p_sierju')) || '906';
  return 'Penal ' + ley + ' - ' + (val('p_penproc') === 'Conocimiento' ? 'Conocimiento' : 'Garantías');
}

/* De la naturaleza guardada se vuelve a la del selector, para poder editar. */
function descomponer(nat) {
  if (!nat || !nat.startsWith('Penal')) return { base: nat || 'Civil', procedimiento: 'Garantías' };
  return { base: 'Penal', procedimiento: nat.includes('Conocimiento') ? 'Conocimiento' : 'Garantías' };
}

export async function openProc(p) {
  editProc = p || null;
  $('#procTitle').textContent = p ? 'Editar proceso' : 'Nuevo proceso';
  const { base, procedimiento } = descomponer(p && p.naturaleza);
  pintar('p_nat', S.cfg.naturalezas, base);
  pon('p_penproc', procedimiento);

  pon('p_rad', p && p.radicado); pon('p_clase', p && p.clase);
  pon('p_dte', p && p.demandante); pon('p_dda', p && p.demandado); pon('p_frad', p && p.fecha_rad);
  pon('p_sit', p ? p.situacion : 'Activo'); pon('p_macro', p && p.macroetapa);
  pon('p_noticia', p && p.noticia_criminal); pon('p_via', p ? p.via : 'Oral');
  pon('p_fterm', p && p.fecha_terminacion); pon('p_farch', p && p.fecha_archivo);
  pon('p_impugna', p && p.impugnacion); pon('p_impugfecha', p && p.fecha_impugnacion);
  pon('p_dec2da', p && p.decision_2da); pon('p_medidatut', p && p.medida_tutela);
  pon('p_desTutela', p && p.des_tutela); pon('p_desReq', p && p.des_req);
  pon('p_desApertura', p && p.des_apertura); pon('p_desConsulta', p && p.des_consulta);
  ponMarca('p_tp', p && p.tramite_posterior); pon('p_tpfecha', p && p.fecha_tramite_posterior);
  pon('p_crearmed', 'no');
  ponMarca('p_crearact', !p);
  // al crear no se pueden crear actuaciones solas dos veces; al editar la opción no aplica
  mostrar('pCrearActWrap', !p);

  pintar('p_cuainicial', cuadernosDe(p, null), p ? p.cuaderno_inicial : 'Principal');
  solicitudes = p ? (p.solicitudes_penales || []).map(x => Object.assign({}, x)) : [];
  delitosExtra = p ? (p.delitos_adicionales || []).slice() : [];

  $('#p_del').style.display = p && puede('procesos.eliminar') ? '' : 'none';
  await sincronizar(p ? p.tipo_sierju : null, p ? p.forma_salida : null, p ? p.tipo_entrada : null, p ? p.solicitud_penal : null);
  borrador.barra('proc', 'procDraft', !p && borrador.guardado('proc'), recuperar);
  abrir('ovProc');
}

async function recuperar(b) {
  solicitudes = (b.solicitudes || []).map(x => Object.assign({}, x));
  delitosExtra = (b.delitos || []).slice();
  // primero el selector de naturaleza, luego las listas que dependen de él, y al final los valores
  borrador.aplicar({ p_nat: b.datos.p_nat, p_penproc: b.datos.p_penproc, p_clase: b.datos.p_clase });
  await sincronizar(b.datos.p_sierju, b.datos.p_salida, b.datos.p_entrada, b.datos.p_penalsol);
  borrador.aplicar(b.datos);
  await sincronizar(b.datos.p_sierju, b.datos.p_salida, b.datos.p_entrada, b.datos.p_penalsol);
  toast('Borrador recuperado');
}

/* Repinta todo lo que depende de la naturaleza y muestra u oculta los bloques. */
async function sincronizar(sierju, salida, entrada, penalsol) {
  const nat = naturalezaEfectiva();
  const l = await listasDe(nat, val('p_clase'));

  mostrar('penalCampos', l.es_penal);
  mostrar('penalSolicitudUnica', l.es_penal && !l.es_garantias);
  mostrar('penalSolicitudesMulti', l.es_garantias);
  mostrar('delitosExtra', l.es_penal);
  mostrar('tutelaCampos', nat === 'Tutela');
  mostrar('desacatoCampos', l.es_desacato);
  mostrar('claseCampo', !l.es_penal);
  // en garantías la salida se lleva por solicitud, no por proceso
  mostrar('p_salida_wrap', !l.es_garantias);
  mostrar('tpCampos', !l.es_penal && !l.es_constitucional);
  mostrar('impugBox', val('p_impugna') === 'Sí');
  mostrar('dec2daBox', val('p_impugna') === 'Sí');
  mostrar('tpFechaBox', marca('p_tp'));

  llenarDatalist('asuntos', cat(nat === 'Familia' ? 'asuntos_familia' : 'asuntos_civil'));
  llenarDatalist('macroetapas', cat('macroetapas'));

  etiqueta('lblSierju', l.es_penal ? 'Delito (tipo SIERJU)' : l.es_constitucional ? 'Derecho invocado (tipo SIERJU)' : 'Tipo SIERJU (estadística)');
  etiqueta('lblClase', l.es_constitucional ? 'Asunto' : 'Clase / asunto');
  etiqueta('lblDte', l.es_penal ? 'Indiciado / procesado' : l.es_constitucional ? 'Accionante' : 'Demandante');
  etiqueta('lblDda', l.es_penal ? 'Víctima' : l.es_constitucional ? 'Accionado' : 'Demandado');

  if (l.es_penal) {
    const pares = await delitosDe(val('p_penproc') === 'Conocimiento' ? 'Conocimiento' : 'Garantías');
    leyPorDelito = new Map(pares.map(x => [x.delito, x.ley]));
    pintar('p_sierju', pares.map(x => x.delito), sierju != null ? sierju : val('p_sierju'), '— elija el delito —');
    pintar('p_penalsol', l.penal_solicitudes, penalsol != null ? penalsol : val('p_penalsol'), '— sin especificar —');
  } else {
    leyPorDelito = new Map();
    const sug = sierju != null ? sierju : (val('p_sierju') || l.sugerido);
    pintar('p_sierju', l.tipo_sierju, sug, '— sin clasificar —');
  }
  pintar('p_salida', l.salidas, salida != null ? salida : val('p_salida'), '— sin salida —');
  pintar('p_entrada', l.entradas, entrada != null ? entrada : val('p_entrada'), '— sin especificar —');
  renderSolicitudes();
  renderDelitos();
}

/* ----- solicitudes de control de garantías ----- */

const SOL_VACIA = () => ({ id: '', tipo: '', fecha: '', entrada: 'Nueva solicitud', salida: '', fecha_salida: '', hora_salida: '', detalle_salida: '' });

async function renderSolicitudes() {
  const caja = $('#p_solicitudes_lista');
  if (!caja) return;
  const l = await listasDe(naturalezaEfectiva(), val('p_clase'));
  const sc = S.cfg.solicitud_penal;
  caja.innerHTML = solicitudes.map((s, i) => '<div class="solrow">'
    + '<div class="sh">Solicitud ' + (i + 1) + '<span class="spacer" style="flex:1"></span>'
    + '<button type="button" class="btn ghost sm" data-acc="delSol" data-i="' + i + '">Quitar</button></div>'
    + '<div class="frow"><div class="field"><label>Tipo</label><select data-s="' + i + '" data-k="tipo">'
    + opciones(l.penal_solicitudes, s.tipo, '— elija —') + '</select></div>'
    + '<div class="field"><label>Fecha de radicación</label><input type="date" data-s="' + i + '" data-k="fecha" value="' + esc(s.fecha || '') + '"></div></div>'
    + '<div class="frow"><div class="field"><label>Entrada</label><select data-s="' + i + '" data-k="entrada">'
    + opciones(sc.entradas, s.entrada) + '</select></div>'
    + '<div class="field"><label>Salida</label><select data-s="' + i + '" data-k="salida">'
    + opciones(l.salidas, s.salida, '— sigue abierta —') + '</select></div></div>'
    + (s.salida ? '<div class="frow"><div class="field"><label>Fecha de salida</label><input type="date" data-s="' + i + '" data-k="fecha_salida" value="' + esc(s.fecha_salida || '') + '"></div>'
      + '<div class="field"><label>Hora de salida</label><input type="time" data-s="' + i + '" data-k="hora_salida" value="' + esc(s.hora_salida || '') + '"></div></div>' : '')
    + (s.salida === 'Otras salidas no efectivas' ? '<div class="field"><label>Motivo de la salida no efectiva</label><select data-s="' + i + '" data-k="detalle_salida">'
      + opciones(sc.detalles_no_efectiva, s.detalle_salida, '— elija el motivo —') + '</select></div>' : '')
    + '</div>').join('') || '<div class="hint">Agregue al menos una solicitud.</div>';
  $$('#p_solicitudes_lista [data-s]').forEach(el => {
    el.onchange = () => {
      solicitudes[+el.dataset.s][el.dataset.k] = el.value;
      // la salida abre o cierra sus propios campos
      if (el.dataset.k === 'salida') renderSolicitudes();
      guardarBorrador();
    };
  });
}

/* ----- delitos adicionales ----- */

async function renderDelitos() {
  const caja = $('#delitosExtraLista');
  if (!caja) return;
  const pares = leyPorDelito.size ? Array.from(leyPorDelito.keys()) : [];
  caja.innerHTML = delitosExtra.map((d, i) => '<div class="frow" style="margin-bottom:6px"><div class="field">'
    + '<label>Delito adicional ' + (i + 1) + '</label><select data-d="' + i + '">' + opciones(pares, d, '— elija —') + '</select></div>'
    + '<div class="field" style="max-width:110px"><label>&nbsp;</label>'
    + '<button type="button" class="btn ghost sm" data-acc="delDelito" data-i="' + i + '">Quitar</button></div></div>').join('');
  $$('#delitosExtraLista [data-d]').forEach(el => {
    el.onchange = () => { delitosExtra[+el.dataset.d] = el.value; guardarBorrador(); };
  });
}

/* ----- lectura y guardado ----- */

function leerProc() {
  return {
    radicado: val('p_rad').trim(),
    naturaleza: naturalezaEfectiva(),
    clase: val('p_clase'),
    demandante: val('p_dte'), demandado: val('p_dda'),
    fecha_rad: val('p_frad'), situacion: val('p_sit'), macroetapa: val('p_macro'),
    tipo_sierju: val('p_sierju'), via: val('p_via'), tipo_entrada: val('p_entrada'),
    fecha_terminacion: val('p_fterm'), fecha_archivo: val('p_farch'), forma_salida: val('p_salida'),
    tramite_posterior: marca('p_tp'), fecha_tramite_posterior: val('p_tpfecha'),
    noticia_criminal: val('p_noticia'), solicitud_penal: val('p_penalsol'),
    delitos_adicionales: delitosExtra.filter(Boolean),
    impugnacion: val('p_impugna'), fecha_impugnacion: val('p_impugfecha'),
    decision_2da: val('p_dec2da'), medida_tutela: val('p_medidatut'),
    des_tutela: val('p_desTutela').trim(), des_req: val('p_desReq'),
    des_apertura: val('p_desApertura'), des_consulta: val('p_desConsulta'),
    cuaderno_inicial: val('p_cuainicial'), cuadernos: editProc ? (editProc.cuadernos || []) : [],
    solicitudes_penales: solicitudes,
    crear_inicial: marca('p_crearact'),
    crear_medidas: val('p_crearmed') === 'si',
  };
}

async function saveProc() {
  const o = leerProc();
  if (!o.radicado) { toast('Escriba el radicado'); return; }
  let p;
  if (editProc) p = await api.put('/api/procesos/' + editProc.id, Object.assign(o, { version: editProc.version }));
  else p = await api.post('/api/procesos', o);
  borrador.limpiar('proc');
  cerrar('ovProc');
  toast('Proceso guardado');
  // se abre el detalle siempre: al crear pueden haber nacido actuaciones solas y hay que verlas
  nav.detalle(p.id);
}

async function delProc() {
  if (!editProc || !confirm('¿Eliminar el proceso y todas sus actuaciones?')) return;
  await api.del('/api/procesos/' + editProc.id);
  cerrar('ovProc'); toast('Proceso eliminado'); nav.ir('procesos');
}

export function iniciarProc() {
  $('#p_save').onclick = saveProc;
  $('#p_del').onclick = delProc;
  const resincronizar = async () => { await sincronizar(); guardarBorrador(); };
  ['p_nat', 'p_penproc'].forEach(id => { $('#' + id).onchange = async () => { await sincronizar(''); guardarBorrador(); }; });
  ['p_sierju', 'p_impugna', 'p_tp', 'p_sit'].forEach(id => { $('#' + id).onchange = resincronizar; });
  $('#p_clase').onchange = resincronizar;
  // la sugerencia de tipo SIERJU llega del servidor al cambiar la clase
  $('#ovProc').addEventListener('input', guardarBorrador);
  $('#ovProc').addEventListener('click', e => {
    const b = e.target.closest('[data-acc]');
    if (!b || !$('#ovProc').contains(b)) return;
    if (b.dataset.acc === 'addSol') { solicitudes.push(SOL_VACIA()); renderSolicitudes(); guardarBorrador(); }
    if (b.dataset.acc === 'delSol') { solicitudes.splice(+b.dataset.i, 1); renderSolicitudes(); guardarBorrador(); }
    if (b.dataset.acc === 'addDelito') { delitosExtra.push(''); renderDelitos(); guardarBorrador(); }
    if (b.dataset.acc === 'delDelito') { delitosExtra.splice(+b.dataset.i, 1); renderDelitos(); guardarBorrador(); }
  });
}
