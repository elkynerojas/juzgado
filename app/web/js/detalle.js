import { api } from './api.js';
import { S, nav, puede, cat } from './estado.js';
import { $, esc, fmt, fmtL, hoyISO, diasEntre, toast, badge, delegar } from './util.js';
import { openProc, openAct, openAudiencia, crearSiguiente } from './formularios.js';
import { openGen } from './docs.js';

let actual = null;

const esPenal = p => (p.naturaleza || '').startsWith('Penal');
const esConstitucional = p => ['Tutela', 'Incidente de desacato', 'Desacato', 'Hábeas corpus'].includes(p.naturaleza);

/* Los campos de la v2 que solo aplican a cierta naturaleza o a un proceso ya terminado. */
function metaExtra(p) {
  let h = '';
  if (p.tipo_sierju) h += meta(esPenal(p) ? 'Delito' : esConstitucional(p) ? 'Derecho' : 'Tipo SIERJU', esc(p.tipo_sierju));
  if (p.via) h += meta('Vía', esc(p.via));
  if (p.tipo_entrada) h += meta('Entrada', esc(p.tipo_entrada));
  if (p.noticia_criminal) h += meta('CUI', esc(p.noticia_criminal));
  if (p.fecha_terminacion) h += meta('Terminación', fmtL(p.fecha_terminacion));
  if (p.fecha_archivo) h += meta('Archivo', fmtL(p.fecha_archivo));
  if (p.forma_salida) h += meta('Forma de salida', esc(p.forma_salida));
  if (p.tramite_posterior) h += meta('Trámite posterior', fmtL(p.fecha_tramite_posterior));
  if (p.naturaleza === 'Tutela') {
    if (p.medida_tutela) h += meta('Medida provisional', esc(p.medida_tutela));
    if (p.impugnacion) h += meta('Impugnada', esc(p.impugnacion) + (p.fecha_impugnacion ? ' · ' + fmt(p.fecha_impugnacion) : ''));
    if (p.decision_2da) h += meta('Segunda instancia', esc(p.decision_2da));
  }
  if (p.des_tutela || p.des_req || p.des_apertura || p.des_consulta) {
    if (p.des_tutela) h += meta('Tutela de origen', esc(p.des_tutela));
    if (p.des_req) h += meta('Requerimiento', fmtL(p.des_req));
    if (p.des_apertura) h += meta('Apertura', esc(p.des_apertura));
    if (p.des_consulta) h += meta('Consulta', esc(p.des_consulta));
  }
  return h;
}

/* Las solicitudes de control de garantías, que entran y salen una por una. */
function solicitudesHTML(p) {
  const sols = p.solicitudes_penales || [];
  if (!sols.length) return '';
  let h = '<div class="card" style="margin-top:10px"><div class="sec-title">⚖️ Solicitudes de control de garantías</div>';
  sols.forEach((s, i) => {
    const estado = s.salida
      ? '<span class="badge b-gray">' + esc(s.salida) + (s.fecha_salida ? ' · ' + fmt(s.fecha_salida) : '') + '</span>'
      : '<span class="badge b-amber">abierta</span>';
    h += '<div class="list-row"><span class="rad">' + (i + 1) + '</span><span class="tiny">' + esc(s.tipo || '—')
      + (s.fecha ? '<div class="muted">radicada ' + fmt(s.fecha) + '</div>' : '') + '</span><span class="spacer"></span>' + estado
      + (s.detalle_salida ? ' <span class="tiny muted">' + esc(s.detalle_salida) + '</span>' : '') + '</div>';
  });
  return h + '</div>';
}

export async function openDetalle(pid, alInicio = true) {
  const p = actual = await api.get('/api/procesos/' + pid);
  S.proc = pid;
  const d = p.derivado;
  let h = '<button class="backlink" data-acc="volver">‹ Volver</button>';
  h += '<div class="card" style="margin-top:10px"><div class="detail-head"><div style="flex:1;min-width:200px"><h2>' + esc(p.radicado) + '</h2>'
    + '<div class="muted">' + esc(p.clase || '') + ' · ' + esc(p.naturaleza || '') + (p.macroetapa ? ' · ' + esc(p.macroetapa) : '') + '</div><div class="meta">'
    + meta(esPenal(p) ? 'Indiciado' : esConstitucional(p) ? 'Accionante' : 'Demandante', esc(p.demandante || '—'))
    + meta(esPenal(p) ? 'Víctima' : esConstitucional(p) ? 'Accionado' : 'Demandado', esc(p.demandado || '—'))
    + meta('Radicación', fmtL(p.fecha_rad))
    + meta('Situación', esc(p.situacion)) + meta('Inactividad', esc(d.inactividad)) + meta('Próx. vencimiento', d.proximo ? fmtL(d.proximo) : '—')
    + metaExtra(p)
    + '</div></div><div style="display:flex;flex-direction:column;gap:6px">'
    + (puede('actuaciones.crear') ? '<button class="btn primary" data-acc="actNueva">+ Actuación</button>' : '')
    + (puede('audiencias.gestionar') ? '<button class="btn sm" data-acc="audNueva">+ Audiencia</button>' : '')
    + (puede('procesos.editar') ? '<button class="btn sm" data-acc="procEditar">Editar proceso</button>' : '') + '</div></div>';
  const editaNotas = puede('procesos.notas');
  h += '<div class="notes' + (p.notas ? ' open' : '') + '" id="noteBox"><div class="nh" data-acc="notasToggle"><span>🗒️ Notas y consideraciones del proceso</span>'
    + (p.notas ? '<span class="badge b-amber" style="margin-left:6px">con notas</span>' : '<span class="tiny muted" style="margin-left:6px">(vacío)</span>')
    + '<span class="chev">▸</span></div><div class="nb"><textarea id="noteText"' + (editaNotas ? '' : ' readonly')
    + ' placeholder="Ej: posible sentencia anticipada · testigo no aparece, debe ser conducido · asegurar conexión presencial del demandante a la audiencia…">' + esc(p.notas || '') + '</textarea>'
    + '<div style="display:flex;gap:8px;margin-top:8px">' + (editaNotas ? '<button class="btn primary sm" data-acc="notasGuardar">Guardar notas</button>' : '')
    + '<span class="tiny muted" style="align-self:center">Compartidas por el despacho. No entran al paso a paso ni a los cómputos.</span></div></div></div></div>';
  h += solicitudesHTML(p);

  const porCuaderno = {};
  p.actuaciones.forEach(a => { (porCuaderno[a.cuaderno] = porCuaderno[a.cuaderno] || []).push(a); });
  const orden = cat('cuadernos').filter(c => porCuaderno[c]).concat(Object.keys(porCuaderno).filter(c => !cat('cuadernos').includes(c)));
  if (!orden.length) h += '<div class="empty">Sin actuaciones. ' + (puede('actuaciones.crear') ? '<button class="btn primary sm" data-acc="actNueva">+ Agregar</button>' : '') + '</div>';
  orden.forEach(cu => {
    const arr = porCuaderno[cu].sort((a, b) => a.derivado.codigo - b.derivado.codigo);
    h += '<div class="cuaderno"><h3>📁 ' + esc(cu) + ' <span class="muted tiny" style="font-weight:400">(' + arr.length + ')</span></h3>' + arr.map(actHTML).join('') + '</div>';
  });

  const el = $('#view-detalle');
  el.innerHTML = h;
  nav.mostrar('detalle');
  if (alInicio) window.scrollTo(0, 0);
  const act = el => actual.actuaciones.find(a => a.id === el.dataset.a);
  delegar(el, {
    volver: () => nav.ir(S.volverA),
    actNueva: () => openAct(null, actual),
    audNueva: () => openAudiencia(actual),
    procEditar: () => openProc(actual),
    notasToggle: () => $('#noteBox').classList.toggle('open'),
    notasGuardar: async () => {
      await api.put('/api/procesos/' + actual.id + '/notas', { notas: $('#noteText').value, version: actual.version });
      toast('Notas guardadas'); openDetalle(actual.id);
    },
    actEditar: el => openAct(act(el), actual),
    siguiente: el => crearSiguiente(act(el), actual),
    gen: el => openGen(act(el), el.dataset.tipo),
  });
}

function meta(k, v) { return '<div><div class="k">' + k + '</div><div class="v">' + v + '</div></div>'; }

function actHTML(a) {
  const d = a.derivado, c = d.codigo;
  let alerta = '';
  if (c === 1 && d.fecha_activa) alerta = '<span class="badge b-blue">Faltan ' + diasEntre(d.fecha_activa, hoyISO()) + 'd</span>';
  else if (c === 3 || c === 4) alerta = '<span class="badge b-red">Secretaría ' + d.dias + 'd</span>';
  else if (c === 5) alerta = '<span class="badge b-red">Despacho ' + d.dias + 'd</span>';
  const AUD_BADGE = { 'Programada': 'b-blue', 'Realizada': 'b-green', 'Suspendida': 'b-amber', 'Aplazada': 'b-amber', 'Cancelada / no realizada': 'b-gray' };
  const aud = a.es_audiencia && a.aud_fecha
    ? '<span class="badge ' + (AUD_BADGE[a.aud_estado] || 'b-blue') + '" title="' + esc(a.aud_tipo || '') + (a.aud_causa ? ' · ' + esc(a.aud_causa) : '') + '">📅 '
      + fmt(a.aud_fecha) + (a.aud_hora ? ' ' + esc(a.aud_hora) : '') + ' · ' + esc(a.aud_estado || 'Programada') + '</span>'
    : '';
  let h = '<div class="act ' + (c >= 3 && c <= 5 ? 'rz' : '') + '"><div class="top">' + badge(d) + '<span class="badge b-gray">' + esc(a.materia || '—') + '</span><span class="desc">' + esc(a.descripcion) + '</span>'
    + aud + (a.suspende ? '<span class="badge b-blue">suspende</span>' : '') + '<span class="spacer"></span>' + alerta;
  if (puede('documentos.generar')) {
    h += '<button class="btn sm" data-acc="gen" data-a="' + a.id + '" data-tipo="Constancia" title="Generar constancia">📄</button>'
      + '<button class="btn sm" data-acc="gen" data-a="' + a.id + '" data-tipo="Pase al despacho" title="Generar pase al despacho">⬆️</button>';
  }
  if (puede('actuaciones.editar')) h += '<button class="btn sm" data-acc="actEditar" data-a="' + a.id + '">Editar</button>';
  h += '</div>';
  if (a.siguiente && puede('actuaciones.crear')) {
    h += '<div style="margin-top:8px"><button class="btn sm primary" data-acc="siguiente" data-a="' + a.id + '">➡ Siguiente paso: ' + esc(a.siguiente.paso.nombre) + '</button> <span class="tiny muted">' + esc(a.siguiente.ruta) + '</span></div>';
  }
  const pasos = [['Activa', d.fecha_activa], ['Constancia', a.constancia], ['Pase', a.pase], ['Providencia', a.providencia], ['Ejecutoria', a.ejecutoria], ['Cumplida', a.cumplida]];
  h += '<div class="timeline">' + pasos.map(([l, v]) => '<div class="step ' + (v ? 'done' : 'pend') + '"><span class="sl">' + l + '</span><span class="sd">' + (v ? fmt(v) : '—') + '</span></div>').join('');
  if (d.est_termino) h += '<div class="step"><span class="sl">Término</span><span class="sd">' + esc(d.est_termino) + (d.vencimiento ? ' · ' + fmt(d.vencimiento) : '') + '</span></div>';
  // con recurso la firmeza no se lee de la fecha de ejecutoria: la calcula el servidor
  const ej = d.ejecutoria_estado;
  if (a.recurso_tipo) {
    const txt = ej.estado === 'suspendida'
      ? 'suspendida · falta ' + (ej.pendiente === 'impugnacion' ? 'la impugnación' : 'el superior')
      : ej.estado === 'en_firme' ? 'en firme ' + fmt(ej.fecha) : esc(a.recurso_tipo);
    h += '<div class="step"><span class="sl">' + esc(a.recurso_tipo) + '</span><span class="sd">' + txt + '</span></div>';
  }
  if (a.asignado_a) h += '<div class="step"><span class="sl">Asignado</span><span class="sd">' + esc(a.asignado_a) + '</span></div>';
  if (a.tp_tipo) h += '<div class="step"><span class="sl">Trámite post.</span><span class="sd">' + esc(a.tp_tipo) + '</span></div>';
  h += '</div>' + (a.obs ? '<div class="muted tiny" style="margin-top:8px">' + esc(a.obs) + '</div>' : '') + '</div>';
  return h;
}
