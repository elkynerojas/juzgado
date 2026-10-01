import { api } from './api.js';
import { S, nav, puede, cat } from './estado.js';
import { $, esc, fmt, fmtL, hoyISO, diasEntre, toast, badge, delegar } from './util.js';
import { openProc, openAct, crearSiguiente } from './formularios.js';
import { openGen } from './docs.js';

let actual = null;

export async function openDetalle(pid, alInicio = true) {
  const p = actual = await api.get('/api/procesos/' + pid);
  S.proc = pid;
  const d = p.derivado;
  let h = '<button class="backlink" data-acc="volver">‹ Volver</button>';
  h += '<div class="card" style="margin-top:10px"><div class="detail-head"><div style="flex:1;min-width:200px"><h2>' + esc(p.radicado) + '</h2>'
    + '<div class="muted">' + esc(p.clase || '') + ' · ' + esc(p.naturaleza || '') + (p.macroetapa ? ' · ' + esc(p.macroetapa) : '') + '</div><div class="meta">'
    + meta('Demandante', esc(p.demandante || '—')) + meta('Demandado', esc(p.demandado || '—')) + meta('Radicación', fmtL(p.fecha_rad))
    + meta('Situación', esc(p.situacion)) + meta('Inactividad', esc(d.inactividad)) + meta('Próx. vencimiento', d.proximo ? fmtL(d.proximo) : '—')
    + '</div></div><div style="display:flex;flex-direction:column;gap:6px">'
    + (puede('actuaciones.crear') ? '<button class="btn primary" data-acc="actNueva">+ Actuación</button>' : '')
    + (puede('procesos.editar') ? '<button class="btn sm" data-acc="procEditar">Editar proceso</button>' : '') + '</div></div>';
  const editaNotas = puede('procesos.notas');
  h += '<div class="notes' + (p.notas ? ' open' : '') + '" id="noteBox"><div class="nh" data-acc="notasToggle"><span>🗒️ Notas y consideraciones del proceso</span>'
    + (p.notas ? '<span class="badge b-amber" style="margin-left:6px">con notas</span>' : '<span class="tiny muted" style="margin-left:6px">(vacío)</span>')
    + '<span class="chev">▸</span></div><div class="nb"><textarea id="noteText"' + (editaNotas ? '' : ' readonly')
    + ' placeholder="Ej: posible sentencia anticipada · testigo no aparece, debe ser conducido · asegurar conexión presencial del demandante a la audiencia…">' + esc(p.notas || '') + '</textarea>'
    + '<div style="display:flex;gap:8px;margin-top:8px">' + (editaNotas ? '<button class="btn primary sm" data-acc="notasGuardar">Guardar notas</button>' : '')
    + '<span class="tiny muted" style="align-self:center">Compartidas por el despacho. No entran al paso a paso ni a los cómputos.</span></div></div></div></div>';

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
    actNueva: () => openAct(null),
    procEditar: () => openProc(actual),
    notasToggle: () => $('#noteBox').classList.toggle('open'),
    notasGuardar: async () => {
      await api.put('/api/procesos/' + actual.id + '/notas', { notas: $('#noteText').value, version: actual.version });
      toast('Notas guardadas'); openDetalle(actual.id);
    },
    actEditar: el => openAct(act(el)),
    siguiente: el => crearSiguiente(act(el)),
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
  let h = '<div class="act ' + (c >= 3 && c <= 5 ? 'rz' : '') + '"><div class="top">' + badge(d) + '<span class="badge b-gray">' + esc(a.materia || '—') + '</span><span class="desc">' + esc(a.descripcion) + '</span>'
    + (a.suspende ? '<span class="badge b-blue">suspende</span>' : '') + '<span class="spacer"></span>' + alerta;
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
  h += '</div>' + (a.obs ? '<div class="muted tiny" style="margin-top:8px">' + esc(a.obs) + '</div>' : '') + '</div>';
  return h;
}
