import { api, onSesionVencida } from './api.js';
import { S, nav, puede, cargarCfg, aplicarTema, guardarTema } from './estado.js';
import { $, $$, toast, abrir, cerrar, debounce, hayModalAbierto } from './util.js';
import { renderTablero, renderProcesos, renderGestion, cargarEjemplos } from './vistas.js';
import { openDetalle } from './detalle.js';
import { renderConfig } from './config.js';
import { renderAudiencias, iniciarAudiencias } from './audiencias.js';
import { renderEstadistica, iniciarEstadistica } from './estadistica.js';
import { openProc, iniciarFormularios } from './formularios.js';
import { iniciarDocs } from './docs.js';
import { mostrarLogin, cambiarPassword, iniciarAuth } from './auth.js';
import { exportarRespaldo, restaurarDesdeArchivo } from './respaldo.js';

const VISTAS = ['tablero', 'procesos', 'gestion', 'audiencias', 'estadistica', 'config', 'detalle'];
const RENDER = { tablero: renderTablero, procesos: renderProcesos, gestion: renderGestion, audiencias: renderAudiencias, estadistica: renderEstadistica, config: renderConfig };
const REFRESCO_MS = 30000;
const MANUAL = '/ayuda/Manual_de_usuario_Control_de_Procesos.pdf';

function mostrar(v) {
  S.vista = v;
  VISTAS.forEach(x => { $('#view-' + x).style.display = x === v ? '' : 'none'; });
  $$('.tab').forEach(t => t.classList.toggle('active', t.dataset.view === v));
}

nav.mostrar = mostrar;
const VEDADA = { gestion: 'paquetes.ver', audiencias: 'audiencias.ver', estadistica: 'estadistica.ver' };
nav.ir = v => { if (VEDADA[v] && !puede(VEDADA[v])) v = 'procesos'; mostrar(v); return RENDER[v](); };
nav.detalle = pid => { if (S.vista !== 'detalle') S.volverA = S.vista; return openDetalle(pid); };
nav.refrescar = () => (S.vista === 'detalle' ? openDetalle(S.proc, false) : RENDER[S.vista]());

function aplicarPermisos() {
  $$('[data-permiso]').forEach(el => { el.style.display = puede(el.dataset.permiso) ? '' : 'none'; });
  $('#userChip').textContent = S.me.nombre + ' · ' + S.me.rol;
}

async function arrancar() {
  S.me = await api.get('/api/me');
  await cargarCfg();
  aplicarTema(); aplicarPermisos();
  $('#brandJz').textContent = S.cfg.juzgado.juzgado;
  // otro usuario pudo haber dejado filtros puestos en esta misma ventana
  Object.assign(S, {
    filtro: null, gMat: null, gSit: null, gTipo: null, gDesde: null, gHasta: null,
    pAnio: null, pSit: null, pUbic: null, pArea: null,
    aDesde: null, aHasta: null, aEstado: null, aArea: null,
    eDesde: null, eHasta: null, cfgTab: null, proc: null,
  });
  $('#search').value = '';
  await nav.ir('tablero');
}

async function mostrarAcerca() {
  const a = await api.get('/api/acerca');
  $('#acNombre').textContent = a.nombre;
  $('#acVersion').textContent = 'Versión ' + a.version;
  $('#acJuzgado').textContent = S.cfg ? S.cfg.juzgado.juzgado : '';
  $('#acDev').textContent = a.desarrollador.nombre;
  $('#acTel').textContent = a.desarrollador.telefono;
  $('#acCorreo').textContent = a.desarrollador.correo;
  abrir('ovAcerca');
}

/* El PDF lo sirve el servidor; en la ventana de escritorio se abre en el visor de Windows para no salir de la aplicación. */
async function abrirManual() {
  const url = location.origin + MANUAL;
  if (window.pywebview && window.pywebview.api) await window.pywebview.api.abrir_en_navegador(url);
  else window.open(url, '_blank');
}

function pedirIngreso() {
  $$('.overlay.open').forEach(o => o.classList.remove('open'));
  if (!$('#login').classList.contains('open')) mostrarLogin(arrancar);
}

/* Los errores de la API llegan aquí cuando la acción no los maneja: se avisa y, si otro usuario cambió el dato, se recarga. */
window.addEventListener('unhandledrejection', e => {
  const err = e.reason || {};
  e.preventDefault();
  if (err.status === 401) return;
  toast(err.message || 'Ocurrió un error');
  if (err.status === 409 || err.status === 404) { $$('.overlay.open').forEach(o => o.classList.remove('open')); if (S.me) nav.refrescar(); }
});

function enlazar() {
  $$('.tab').forEach(t => { t.onclick = () => { S.filtro = null; nav.ir(t.dataset.view); }; });
  document.addEventListener('click', e => {
    if (e.target.matches('[data-close]')) e.target.closest('.overlay').classList.remove('open');
    else if (e.target.classList.contains('overlay')) e.target.classList.remove('open');
    if (!e.target.closest('.menu')) $('#menuPop').classList.remove('open');
  });
  $('#btnNuevoProc').onclick = () => openProc(null);
  $('#search').addEventListener('input', debounce(() => (S.vista === 'gestion' ? renderGestion() : nav.ir('procesos')), 250));

  const menu = (id, fn) => { $('#' + id).onclick = () => { $('#menuPop').classList.remove('open'); return fn(); }; };
  $('#btnMenu').onclick = () => {
    // solo existe dentro de la ventana de escritorio
    $('#miModo').style.display = window.pywebview && window.pywebview.api ? '' : 'none';
    $('#menuPop').classList.toggle('open');
  };
  menu('miConfig', () => nav.ir('config'));
  menu('miExport', exportarRespaldo);
  menu('miImport', restaurarDesdeArchivo);
  menu('miEjemplos', async () => {
    const t = await api.get('/api/tablero');
    if (t.procesos && !confirm('Esto reemplazará los datos actuales por los de ejemplo. ¿Continuar?')) return;
    await cargarEjemplos();
  });
  menu('miVaciar', async () => {
    if (!confirm('¿Borrar TODOS los procesos y actuaciones? Exporte un respaldo antes.')) return;
    await api.post('/api/datos/vaciar'); toast('Datos borrados'); await nav.ir('tablero');
  });
  menu('miTema', async () => {
    const oscuro = S.me.preferencias.modo ? S.me.preferencias.modo === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
    await guardarTema({ modo: oscuro ? 'light' : 'dark' });
    if (S.vista === 'config') renderConfig();
  });
  menu('miModo', async () => {
    if (!confirm('Este equipo olvidará si es servidor o cliente y lo preguntará al abrir de nuevo. Los datos no se borran. ¿Continuar?')) return;
    await window.pywebview.api.reconfigurar();
    toast('Listo. Cierre y vuelva a abrir la aplicación.');
  });
  menu('miPassword', cambiarPassword);
  menu('miManual', abrirManual);
  menu('miAcerca', mostrarAcerca);
  menu('miSalir', async () => { await api.post('/api/auth/logout'); S.me = null; cerrar('ovForm'); pedirIngreso(); });

  // otros usuarios cambian datos: se refresca solo mientras nadie está escribiendo
  setInterval(() => {
    const escribiendo = ['INPUT', 'SELECT', 'TEXTAREA'].includes((document.activeElement || {}).tagName);
    if (S.me && !hayModalAbierto() && !escribiendo && !document.hidden && S.vista !== 'config') nav.refrescar();
  }, REFRESCO_MS);
}

async function inicio() {
  iniciarAuth(); iniciarFormularios(); iniciarAudiencias(); iniciarEstadistica(); iniciarDocs(); enlazar();
  onSesionVencida(pedirIngreso);
  try { await api.get('/api/me', null, true); } catch (e) { pedirIngreso(); return; }
  await arrancar();
}

inicio();
