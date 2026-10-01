import { api } from './api.js';
import { S, puede, cargarCfg, cat, guardarTema } from './estado.js';
import { $, esc, fmt, toast, delegar, opciones, elegirImagen } from './util.js';
import { formModal } from './modal.js';
import { cargarResp, cfgResp, accionesResp } from './respaldo.js';

const TABS = [
  ['cat', 'Catálogos', 'config.catalogos'], ['term', 'Términos', 'config.terminos'], ['rutas', 'Rutas procesales', 'config.rutas'],
  ['cal', 'Calendario judicial', 'config.calendario'], ['plt', 'Plantillas y firma', 'config.plantillas'], ['jz', 'Datos del juzgado', 'config.juzgado'],
  ['resp', 'Respaldos', 'respaldo.exportar'], ['look', 'Apariencia', null], ['usr', 'Usuarios', 'usuarios.gestionar'], ['rol', 'Roles y permisos', 'roles.gestionar'], ['aud', 'Auditoría', 'auditoria.ver'],
];
const ORIGENES = ['Memorial', 'Vencimiento de término', 'Providencia (auto/sentencia)', 'Respuesta externa', 'Oficiosa'];
const CAMPOS_PLANTILLA = 'Campos: {{radicado}} {{radicado_full}} {{proceso}} {{demandante}} {{demandado}} {{cuaderno}} {{descripcion}} {{materia}} {{termino}} {{fecha_inicio}} {{vencimiento}} {{motivo_pase}} {{fecha}} {{fecha_letras}} {{ciudad}}';

const el = () => $('#view-config');
// datos de las pestañas de administración (no hacen parte de /api/config)
let usuarios = [], roles = [], permisos = [], auditoria = { total: 0, filas: [] }, audFiltro = { entidad: '', usuario: '' };

export async function renderConfig() {
  const tabs = TABS.filter(t => !t[2] || puede(t[2]));
  if (!tabs.some(t => t[0] === S.cfgTab)) S.cfgTab = tabs[0][0];
  await cargarCfg();
  if (S.cfgTab === 'usr') [usuarios, roles] = await Promise.all([api.get('/api/usuarios'), api.get('/api/roles')]);
  if (S.cfgTab === 'rol') [roles, permisos] = await Promise.all([api.get('/api/roles'), api.get('/api/permisos')]);
  if (S.cfgTab === 'resp') await cargarResp();
  if (S.cfgTab === 'aud') auditoria = await api.get('/api/auditoria', Object.assign({ limite: 200 }, audFiltro));
  let h = '<h2 style="margin:12px 2px 4px">⚙️ Configuración del sistema</h2><div class="chips">';
  tabs.forEach(t => { h += '<div class="chip ' + (S.cfgTab === t[0] ? 'active' : '') + '" data-acc="tab" data-t="' + t[0] + '">' + t[1] + '</div>'; });
  h += '</div>' + VISTAS[S.cfgTab]();
  el().innerHTML = h;
  delegar(el(), ACCIONES);
  enlazarCampos();
}

const recargar = msg => { if (msg) toast(msg); return renderConfig(); };
const borrar = async (url, pregunta) => { if (pregunta && !confirm(pregunta)) return false; await api.del(url); await recargar(); };

/* ===== catálogos ===== */
const CATALOGOS = [['materias', 'Materias / tipos de gestión'], ['tipos_solicitud', 'Tipos de solicitud'], ['cuadernos', 'Cuadernos / trámites'], ['macroetapas', 'Macroetapas'], ['asuntos_civil', 'Asuntos civiles'], ['asuntos_familia', 'Asuntos de familia']];

function cfgCat() {
  return '<div class="card">' + CATALOGOS.map(([k, label]) => {
    const arr = S.cfg.catalogos[k];
    return '<div class="block"><div class="bt">' + label + ' <span class="muted" style="font-weight:400">(' + arr.length + ')</span></div><div class="chips">'
      + arr.map(x => '<span class="chip" style="color:var(--ink)"><span data-acc="catEditar" data-k="' + k + '" data-id="' + x.id + '" title="Editar">' + esc(x.valor) + '</span> <b data-acc="catBorrar" data-k="' + k + '" data-id="' + x.id + '" style="color:var(--red)" title="Eliminar">✕</b></span>').join('')
      + '</div><div style="display:flex;gap:6px;margin-top:8px"><input id="add_' + k + '" placeholder="Agregar nuevo…" style="max-width:320px"><button class="btn sm" data-acc="catAgregar" data-k="' + k + '">+ Agregar</button></div></div>';
  }).join('') + '<div class="tiny muted">Al eliminar una opción, las actuaciones ya registradas conservan su valor; solo desaparece de las listas nuevas.</div></div>';
}

/* ===== términos ===== */
function cfgTerm() {
  const arr = S.cfg.terminos;
  let h = '<div class="card"><div class="bt">Catálogo de términos (' + arr.length + ')</div><div class="tablewrap"><table><thead><tr><th>Término</th><th>Días</th><th>Cómputo</th><th>Resp.</th><th>Cat.</th><th></th></tr></thead><tbody>';
  arr.forEach(t => {
    h += '<tr class="fija"><td class="tiny">' + esc(t.nombre) + '</td><td>' + t.dias + '</td><td class="tiny">' + (t.habil ? 'Hábiles' : 'Calendario') + '</td><td class="tiny">' + esc(t.responsable) + '</td><td class="tiny">' + esc(t.categoria)
      + '</td><td style="white-space:nowrap"><button class="btn sm" data-acc="termEditar" data-id="' + t.id + '">Editar</button></td></tr>';
  });
  return h + '</tbody></table></div><button class="btn sm" data-acc="termEditar" style="margin-top:10px">+ Nuevo término</button></div>';
}

function editarTermino(t) {
  formModal({
    titulo: t ? 'Editar término' : 'Nuevo término',
    campos: [
      { k: 'nombre', label: 'Nombre del término', valor: t && t.nombre },
      { k: 'dias', label: 'Días', tipo: 'number', valor: t && t.dias },
      { k: 'habil', label: 'Cómputo', tipo: 'select', valor: String(t ? t.habil : true), opciones: [['true', 'Días hábiles judiciales'], ['false', 'Días calendario']] },
      { k: 'responsable', label: 'Responsable', valor: t && t.responsable, lista: ['Parte', 'Despacho', 'Secretaría', 'Juez', 'Tercero'] },
      { k: 'categoria', label: 'Categoría', valor: t && t.categoria, lista: ['Traslado', 'Control', 'Ejecutoria', 'Probatorio', 'Recurso', 'Cautelar'] },
    ],
    guardar: async v => {
      v.habil = v.habil === 'true';
      if (t) await api.put('/api/config/terminos/' + t.id, v); else await api.post('/api/config/terminos', v);
      await recargar('Término guardado');
    },
    eliminar: t && (() => borrar('/api/config/terminos/' + t.id, '¿Eliminar término?')),
  });
}

/* ===== rutas ===== */
function cfgRutas() {
  let h = '<div class="card"><div class="tiny muted" style="margin-bottom:10px">Una ruta es una secuencia de pasos. Cuando cierre un paso, el cuadro le ofrecerá crear el siguiente (usted confirma). Edite los pasos o asocie cada tipo de solicitud a su ruta.</div>';
  S.cfg.rutas.forEach(r => {
    h += '<div class="block"><div class="bt">' + esc(r.nombre) + ' <button class="btn sm" data-acc="rutaEditar" data-id="' + r.id + '" style="float:right;margin-top:-4px">Editar ruta</button></div><div class="tiny muted" style="margin:-6px 0 8px">' + esc(r.descripcion || '') + '</div>';
    r.pasos.forEach((p, i) => {
      h += '<div class="firmante"><div style="flex:1"><b>' + (i + 1) + '. ' + esc(p.nombre) + '</b><div class="tiny muted">' + esc(p.origen || '') + (p.termino ? ' · término: ' + esc(p.termino) : '') + '</div><div class="tiny">' + esc(p.descripcion || '') + '</div></div>'
        + '<button class="btn sm" data-acc="pasoEditar" data-r="' + r.id + '" data-id="' + p.id + '">Editar</button></div>';
    });
    h += '<button class="btn sm" data-acc="pasoEditar" data-r="' + r.id + '">+ Paso</button></div>';
  });
  h += '<button class="btn sm" data-acc="rutaEditar" style="margin-bottom:12px">+ Nueva ruta</button>';
  h += '<div class="block"><div class="bt">Asociación: tipo de solicitud → ruta</div><div class="tiny muted" style="margin-bottom:8px">Al registrar una actuación con ese tipo, el cuadro sugiere la ruta.</div><div class="tablewrap"><table><thead><tr><th>Tipo de solicitud</th><th>Ruta por defecto</th></tr></thead><tbody>';
  const rutas = S.cfg.rutas.map(r => [r.id, r.nombre]);
  cat('tipos_solicitud').forEach(t => {
    h += '<tr class="fija"><td class="tiny">' + esc(t) + '</td><td><select data-tr="' + esc(t) + '">' + opciones(rutas, S.cfg.tipo_ruta[t] || '', '— ninguna —') + '</select></td></tr>';
  });
  return h + '</tbody></table></div></div></div>';
}

function editarRuta(r) {
  formModal({
    titulo: r ? 'Editar ruta' : 'Nueva ruta',
    campos: [{ k: 'nombre', label: 'Nombre', valor: r && r.nombre }, { k: 'descripcion', label: 'Descripción', valor: r && r.descripcion }],
    guardar: async v => { if (r) await api.put('/api/config/rutas/' + r.id, v); else await api.post('/api/config/rutas', v); await recargar('Ruta guardada'); },
    eliminar: r && (() => borrar('/api/config/rutas/' + r.id, '¿Eliminar la ruta y sus pasos?')),
  });
}

function editarPaso(rutaId, p) {
  formModal({
    titulo: p ? 'Editar paso' : 'Nuevo paso',
    campos: [
      { k: 'nombre', label: 'Nombre del paso', valor: p && p.nombre },
      { k: 'origen', label: 'Origen', tipo: 'select', valor: p ? p.origen : 'Memorial', opciones: ORIGENES },
      { k: 'materia', label: 'Materia', tipo: 'select', valor: p ? p.materia : '', opciones: [['', '— sin materia —']].concat(cat('materias')) },
      { k: 'termino', label: 'Término aplicable', tipo: 'select', valor: p ? p.termino : '', opciones: [['', '— sin término —']].concat(S.cfg.terminos.map(t => t.nombre)) },
      { k: 'descripcion', label: 'Descripción por defecto', valor: p && p.descripcion },
    ],
    guardar: async v => {
      if (p) await api.put('/api/config/pasos/' + p.id, v); else await api.post('/api/config/rutas/' + rutaId + '/pasos', v);
      await recargar('Paso guardado');
    },
    eliminar: p && (() => borrar('/api/config/pasos/' + p.id, '¿Eliminar paso?')),
  });
}

/* ===== calendario ===== */
function chipsFecha(lista, acc) {
  return lista.length ? '<div class="chips">' + lista.map(d => '<span class="chip">' + fmt(d) + ' <b data-acc="' + acc + '" data-f="' + d + '" style="color:var(--red)">✕</b></span>').join('') + '</div>' : '<div class="tiny muted">Ninguno.</div>';
}

function cfgCal() {
  const cal = S.cfg.calendario;
  let h = '<div class="card"><div class="tiny muted" style="margin-bottom:10px">El cómputo descuenta sábados, domingos y los festivos/vacancia oficiales. Aquí registra situaciones excepcionales; los términos se recalculan solos.</div>';
  h += '<div class="block"><div class="bt">Suspensión de términos (rango de fechas)</div>'
    + (cal.suspensiones.length ? cal.suspensiones.map(r => '<div class="firmante"><div style="flex:1"><b>' + fmt(r.desde) + ' → ' + fmt(r.hasta) + '</b> <span class="muted tiny">' + esc(r.motivo || '') + '</span></div><button class="btn sm" data-acc="susBorrar" data-id="' + r.id + '">✕</button></div>').join('') : '<div class="tiny muted">Ninguna.</div>')
    + '<div class="frow" style="margin-top:8px"><div class="field"><label>Desde</label><input type="date" id="susD"></div><div class="field"><label>Hasta</label><input type="date" id="susH"></div></div><input id="susM" placeholder="Motivo (paro judicial, orden del CSJ, falla eléctrica…)"><button class="btn sm" data-acc="susAgregar" style="margin-top:8px">+ Agregar suspensión</button></div>';
  h += '<div class="block"><div class="bt">Días cerrados sueltos</div>' + chipsFecha(cal.cerrados, 'cerBorrar')
    + '<div style="display:flex;gap:6px;margin-top:8px;align-items:center"><input type="date" id="cerD" style="max-width:200px"><button class="btn sm" data-acc="diaAgregar" data-tipo="cerrado" data-in="cerD">+ Cerrar día</button></div></div>';
  h += '<div class="block"><div class="bt">Habilitar un festivo como día hábil</div>' + chipsFecha(cal.reabiertos, 'reaBorrar')
    + '<div style="display:flex;gap:6px;margin-top:8px;align-items:center"><input type="date" id="reaD" style="max-width:200px"><button class="btn sm" data-acc="diaAgregar" data-tipo="reabierto" data-in="reaD">+ Habilitar día</button></div></div>';
  h += '<div class="block"><div class="bt">Festivos y vacancia (' + cal.festivos.length + ')</div><details><summary class="tiny muted" style="cursor:pointer">Ver y editar la lista (cargada hasta ' + esc((cal.festivos[cal.festivos.length - 1] || '').slice(0, 4)) + ')</summary>' + chipsFecha(cal.festivos, 'fesBorrar') + '</details>'
    + '<div style="display:flex;gap:6px;margin-top:8px;align-items:center"><input type="date" id="fesD" style="max-width:200px"><button class="btn sm" data-acc="fesAgregar">+ Agregar festivo</button></div></div>';
  h += '<div class="block"><div class="bt">Verificar un día</div><div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><input type="date" id="chkD" style="max-width:200px"><button class="btn sm" data-acc="verificar">Comprobar</button><span id="chkRes" class="tiny"></span></div></div>';
  return h + '</div>';
}

/* ===== plantillas y firmantes ===== */
function cfgPlt() {
  let h = '<div class="card"><div class="block"><div class="bt">Firmantes (antefirma)</div>';
  h += S.cfg.firmantes.map(f => '<div class="firmante">' + (f.tiene_firma ? '<img src="/api/config/firmantes/' + f.id + '/firma?v=' + Date.now() + '">' : '<span class="tiny muted" style="width:44px;text-align:center">sin firma</span>')
    + '<div style="flex:1"><b>' + esc(f.nombre) + '</b><div class="tiny muted">' + esc(f.cargo) + '</div></div><button class="btn sm" data-acc="firmEditar" data-id="' + f.id + '">Datos</button><button class="btn sm" data-acc="firmSubir" data-id="' + f.id + '">Subir firma</button></div>').join('') || '<div class="tiny muted">Sin firmantes.</div>';
  h += '<button class="btn sm" data-acc="firmEditar">+ Agregar firmante</button><div class="hint" style="margin-top:8px">La imagen de la antefirma es una comodidad de oficina; no autentica el documento por sí sola.</div></div>';
  h += '<div class="block"><div class="bt">Plantillas</div>' + S.cfg.plantillas.map(t => '<div class="plt"><div class="pt">' + esc(t.nombre) + ' <span class="badge b-gray">' + esc(t.tipo) + '</span></div><div class="tiny muted" style="margin:4px 0">' + esc(t.cuerpo.slice(0, 90)) + '…</div><div class="tpl-actions"><button class="btn sm" data-acc="tplEditar" data-id="' + t.id + '">Editar</button></div></div>').join('');
  return h + '<button class="btn sm" data-acc="tplEditar">+ Nueva plantilla</button><div class="hint" style="margin-top:8px">' + CAMPOS_PLANTILLA + '</div></div></div>';
}

function editarFirmante(f) {
  formModal({
    titulo: f ? 'Datos del firmante' : 'Nuevo firmante',
    campos: [{ k: 'nombre', label: 'Nombre del firmante', valor: f && f.nombre }, { k: 'cargo', label: 'Cargo', valor: f ? f.cargo : 'Secretario' }],
    guardar: async v => { if (f) await api.put('/api/config/firmantes/' + f.id, v); else await api.post('/api/config/firmantes', v); await recargar('Firmante guardado'); },
    eliminar: f && (() => borrar('/api/config/firmantes/' + f.id, '¿Eliminar firmante?')),
  });
}

function editarPlantilla(t) {
  formModal({
    titulo: t ? 'Editar plantilla' : 'Nueva plantilla',
    campos: [
      { k: 'nombre', label: 'Nombre', valor: t && t.nombre },
      { k: 'tipo', label: 'Tipo', tipo: 'select', valor: t ? t.tipo : 'Constancia', opciones: ['Constancia', 'Pase al despacho'] },
      { k: 'cuerpo', label: 'Texto', tipo: 'textarea', valor: t && t.cuerpo, hint: CAMPOS_PLANTILLA },
    ],
    guardar: async v => { if (t) await api.put('/api/config/plantillas/' + t.id, v); else await api.post('/api/config/plantillas', v); await recargar('Plantilla guardada'); },
    eliminar: t && (() => borrar('/api/config/plantillas/' + t.id, '¿Eliminar plantilla?')),
  });
}

/* ===== juzgado y apariencia ===== */
function cfgJz() {
  const c = S.cfg.juzgado;
  return '<div class="card"><div class="block"><div class="bt">Datos del juzgado</div>'
    + '<div class="frow"><div class="field"><label>Juzgado</label><input id="c_jz" value="' + esc(c.juzgado) + '"></div><div class="field"><label>Ciudad / departamento</label><input id="c_ciu" value="' + esc(c.ciudad) + '"></div></div>'
    + '<div class="field"><label>Prefijo del radicado</label><input id="c_pref" value="' + esc(c.prefijo) + '"><div class="hint">Se antepone al radicado corto para formar el consecutivo completo (…-00).</div></div><button class="btn primary sm" data-acc="jzGuardar">Guardar</button></div>'
    + '<div class="block"><div class="bt">Membrete (encabezado de los documentos)</div>' + (S.cfg.tiene_membrete ? '<img src="/api/config/membrete?v=' + Date.now() + '" style="max-width:100%;max-height:80px;background:#fff;border:1px solid var(--line);border-radius:8px;padding:4px">' : '<span class="tiny muted">Sin membrete.</span>')
    + '<div style="margin-top:8px"><button class="btn sm" data-acc="memSubir">Cambiar membrete</button></div></div></div>';
}

function cfgLook() {
  const t = S.me.preferencias || {};
  return '<div class="card"><div class="block"><div class="bt">Apariencia (solo para su usuario)</div>'
    + '<div class="frow"><div class="field"><label>Color principal</label><input type="color" id="tmColor" value="' + (t.color || '#1f3864') + '" style="height:42px;padding:2px"></div>'
    + '<div class="field"><label>Tema</label><select id="tmModo">' + opciones([['', 'Automático (según el equipo)'], ['light', 'Claro'], ['dark', 'Oscuro']], t.modo || '') + '</select></div></div>'
    + '<div class="field"><label>Tamaño de letra</label><select id="tmFont">' + opciones([['', 'Normal'], ['15px', 'Grande'], ['16px', 'Muy grande']], t.font || '') + '</select></div>'
    + '<button class="btn sm" data-acc="temaReset">Restablecer apariencia</button></div></div>';
}

/* ===== usuarios y roles ===== */
function cfgUsr() {
  let h = '<div class="card"><div class="tablewrap"><table><thead><tr><th>Usuario</th><th>Nombre</th><th>Rol</th><th>Estado</th><th>Último ingreso</th><th></th></tr></thead><tbody>';
  usuarios.forEach(u => {
    h += '<tr class="fija"><td class="rad">' + esc(u.usuario) + '</td><td>' + esc(u.nombre) + '</td><td>' + esc(u.rol) + '</td><td>' + (u.activo ? '<span class="badge b-green">Activo</span>' : '<span class="badge b-gray">Inactivo</span>')
      + '</td><td class="tiny">' + fechaHora(u.ultimo_acceso) + '</td><td><button class="btn sm" data-acc="usrEditar" data-id="' + u.id + '">Editar</button></td></tr>';
  });
  return h + '</tbody></table></div><button class="btn sm" data-acc="usrEditar" style="margin-top:10px">+ Nuevo usuario</button></div>';
}

function editarUsuario(u) {
  const campos = [
    { k: 'nombre', label: 'Nombre completo', valor: u && u.nombre },
    { k: 'rol_id', label: 'Rol', tipo: 'select', valor: String(u ? u.rol_id : roles[roles.length - 1].id), opciones: roles.map(r => [String(r.id), r.nombre]) },
    { k: 'password', label: u ? 'Nueva contraseña (vacío = no cambiar)' : 'Contraseña', tipo: 'password', hint: 'Mínimo 8 caracteres.' },
  ];
  if (u) campos.push({ k: 'activo', label: 'Usuario activo (puede ingresar)', tipo: 'checkbox', valor: u.activo });
  else campos.unshift({ k: 'usuario', label: 'Usuario (para ingresar)' });
  formModal({
    titulo: u ? 'Editar usuario ' + u.usuario : 'Nuevo usuario',
    campos,
    guardar: async v => {
      v.rol_id = Number(v.rol_id);
      if (!v.password) v.password = null;
      if (u) await api.put('/api/usuarios/' + u.id, v); else await api.post('/api/usuarios', v);
      await recargar('Usuario guardado');
    },
  });
}

function cfgRol() {
  let h = '<div class="card">';
  roles.forEach(r => {
    h += '<div class="firmante"><div style="flex:1"><b>' + esc(r.nombre) + '</b> <span class="badge b-gray">' + r.usuarios + ' usuario(s)</span><div class="tiny muted">' + esc(r.descripcion || '') + '</div><div class="tiny">'
      + (r.es_sistema ? 'Todos los permisos (rol de sistema, no se modifica)' : r.permisos.length + ' de ' + permisos.length + ' permisos') + '</div></div>'
      + (r.es_sistema ? '' : '<button class="btn sm" data-acc="rolEditar" data-id="' + r.id + '">Editar</button>') + '</div>';
  });
  return h + '<button class="btn sm" data-acc="rolEditar">+ Nuevo rol</button><div class="hint" style="margin-top:8px">Los cambios de permisos aplican de inmediato a los usuarios con ese rol.</div></div>';
}

function editarRol(r) {
  formModal({
    titulo: r ? 'Editar rol' : 'Nuevo rol', ancho: '820px',
    campos: [
      { k: 'nombre', label: 'Nombre del rol', valor: r && r.nombre },
      { k: 'descripcion', label: 'Descripción', valor: r && r.descripcion },
      { k: 'permisos', label: 'Permisos', tipo: 'checks', valor: r ? r.permisos : [], opciones: permisos.map(p => ({ v: p.clave, l: p.descripcion, grupo: p.modulo })) },
    ],
    guardar: async v => { if (r) await api.put('/api/roles/' + r.id, v); else await api.post('/api/roles', v); await recargar('Rol guardado'); },
    eliminar: r && (() => borrar('/api/roles/' + r.id, '¿Eliminar el rol?')),
  });
}

/* ===== auditoría ===== */
// el servidor guarda en UTC sin zona
function fechaHora(s) { return s ? new Date(s + 'Z').toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' }) : '—'; }

const IGNORAR = new Set(['version', 'actualizado_en', 'actualizado_por', 'creado_en', 'creado_por']);
function corto(v) { const s = v == null || v === '' ? '∅' : typeof v === 'object' ? JSON.stringify(v) : String(v); return s.length > 60 ? s.slice(0, 60) + '…' : s; }
function cambios(x) {
  const a = x.antes || {}, d = x.despues || {};
  if (x.accion === 'editar') return Object.keys(d).filter(k => !IGNORAR.has(k) && JSON.stringify(a[k]) !== JSON.stringify(d[k])).map(k => '<b>' + esc(k) + '</b>: ' + esc(corto(a[k])) + ' → ' + esc(corto(d[k]))).join('<br>');
  const o = x.accion === 'crear' ? d : a;
  return esc(corto(o.radicado || o.descripcion || o.nombre || o.valor || o.usuario || o.fecha || JSON.stringify(o)));
}

function cfgAud() {
  const entidades = ['proceso', 'actuacion', 'usuario', 'rol', 'catalogo', 'termino', 'ruta', 'ruta_paso', 'tipo_ruta', 'cal_suspension', 'cal_dia', 'festivo', 'plantilla', 'firmante', 'juzgado', 'datos', 'respaldo'];
  let h = '<div class="card"><div class="filterbar"><select id="audEnt" style="max-width:220px">' + opciones(entidades, audFiltro.entidad, 'Todas las entidades') + '</select>'
    + '<input id="audUsr" placeholder="Usuario…" value="' + esc(audFiltro.usuario) + '" style="max-width:180px"><button class="btn sm" data-acc="audFiltrar">Filtrar</button>'
    + '<span class="tiny muted">' + auditoria.filas.length + ' de ' + auditoria.total + ' registro(s), del más reciente al más antiguo.</span></div>';
  h += '<div class="tablewrap"><table><thead><tr><th>Fecha</th><th>Usuario</th><th>Acción</th><th>Entidad</th><th>Cambio</th></tr></thead><tbody>';
  if (!auditoria.filas.length) h += '<tr class="fija"><td colspan="5" class="muted" style="text-align:center;padding:26px">Sin registros.</td></tr>';
  const color = { crear: 'b-green', editar: 'b-blue', eliminar: 'b-red' };
  auditoria.filas.forEach(x => {
    h += '<tr class="fija"><td class="tiny" style="white-space:nowrap">' + fechaHora(x.fecha) + '</td><td>' + esc(x.usuario_nombre) + '</td><td><span class="badge ' + (color[x.accion] || 'b-gray') + '">' + esc(x.accion) + '</span></td><td class="tiny">' + esc(x.entidad) + '</td><td class="cambios">' + cambios(x) + '</td></tr>';
  });
  return h + '</tbody></table></div></div>';
}

const VISTAS = { cat: cfgCat, term: cfgTerm, rutas: cfgRutas, cal: cfgCal, plt: cfgPlt, jz: cfgJz, look: cfgLook, usr: cfgUsr, rol: cfgRol, aud: cfgAud, resp: cfgResp };

const porId = (lista, d) => lista.find(x => String(x.id) === d.dataset.id) || null;
const fechaDe = id => { const v = $('#' + id).value; if (!v) toast('Elija una fecha'); return v; };

const ACCIONES = {
  tab: d => { S.cfgTab = d.dataset.t; renderConfig(); },

  catAgregar: async d => { const v = $('#add_' + d.dataset.k).value.trim(); if (!v) return; await api.post('/api/config/catalogos/' + d.dataset.k, { valor: v }); await recargar(); },
  catBorrar: d => borrar('/api/config/catalogos/' + d.dataset.k + '/' + d.dataset.id),
  catEditar: d => {
    const x = porId(S.cfg.catalogos[d.dataset.k], d);
    formModal({ titulo: 'Editar opción', campos: [{ k: 'valor', label: 'Valor', valor: x.valor }], guardar: async v => { await api.put('/api/config/catalogos/' + d.dataset.k + '/' + x.id, v); await recargar(); } });
  },

  termEditar: d => editarTermino(porId(S.cfg.terminos, d)),
  rutaEditar: d => editarRuta(porId(S.cfg.rutas, d)),
  pasoEditar: d => editarPaso(d.dataset.r, porId(S.cfg.rutas.find(r => r.id === d.dataset.r).pasos, d)),

  susAgregar: async () => {
    const desde = $('#susD').value, hasta = $('#susH').value;
    if (!desde || !hasta) { toast('Indique desde y hasta'); return; }
    await api.post('/api/config/calendario/suspensiones', { desde, hasta, motivo: $('#susM').value }); await recargar();
  },
  susBorrar: d => borrar('/api/config/calendario/suspensiones/' + d.dataset.id),
  diaAgregar: async d => { const fecha = fechaDe(d.dataset.in); if (!fecha) return; await api.post('/api/config/calendario/dias', { fecha, tipo: d.dataset.tipo }); await recargar(); },
  cerBorrar: d => borrar('/api/config/calendario/dias/cerrado/' + d.dataset.f),
  reaBorrar: d => borrar('/api/config/calendario/dias/reabierto/' + d.dataset.f),
  fesAgregar: async () => { const fecha = fechaDe('fesD'); if (!fecha) return; await api.post('/api/config/calendario/festivos', { fecha }); await recargar(); },
  fesBorrar: d => borrar('/api/config/calendario/festivos/' + d.dataset.f, '¿Quitar el festivo ' + fmt(d.dataset.f) + '? Los términos se recalculan.'),
  verificar: async () => {
    const fecha = fechaDe('chkD'); if (!fecha) return;
    const r = await api.get('/api/config/calendario/verificar', { fecha });
    $('#chkRes').innerHTML = r.habil ? '<span style="color:var(--green)">✓ Es día HÁBIL</span>' : '<span style="color:var(--red)">✕ NO es hábil</span>';
  },

  firmEditar: d => editarFirmante(porId(S.cfg.firmantes, d)),
  firmSubir: async d => { await api.put('/api/config/firmantes/' + d.dataset.id + '/firma', await elegirImagen()); await recargar('Antefirma cargada'); },
  tplEditar: d => editarPlantilla(porId(S.cfg.plantillas, d)),

  jzGuardar: async () => {
    await api.put('/api/config/juzgado', { juzgado: $('#c_jz').value, ciudad: $('#c_ciu').value, prefijo: $('#c_pref').value });
    await recargar('Datos guardados');
    $('#brandJz').textContent = S.cfg.juzgado.juzgado;
  },
  memSubir: async () => { await api.put('/api/config/membrete', await elegirImagen()); await recargar('Membrete actualizado'); },
  temaReset: async () => { await guardarTema({ color: '', modo: '', font: '' }); renderConfig(); },

  usrEditar: d => editarUsuario(porId(usuarios, d)),
  rolEditar: d => editarRol(porId(roles, d)),
  audFiltrar: () => { audFiltro = { entidad: $('#audEnt').value, usuario: $('#audUsr').value.trim() }; renderConfig(); },
};

Object.assign(ACCIONES, accionesResp(recargar));

/* controles que no son clics */
function enlazarCampos() {
  el().querySelectorAll('select[data-tr]').forEach(s => {
    s.onchange = async () => { await api.put('/api/config/tipo-ruta', { tipo_solicitud: s.dataset.tr, ruta_id: s.value || null }); S.cfg.tipo_ruta[s.dataset.tr] = s.value; toast('Asociación guardada'); };
  });
  const color = $('#tmColor'), modo = $('#tmModo'), font = $('#tmFont');
  if (color) color.onchange = () => guardarTema({ color: color.value });
  if (modo) modo.onchange = () => guardarTema({ modo: modo.value });
  if (font) font.onchange = () => guardarTema({ font: font.value });
}
