import { api, onSesionVencida } from './api.js';
import { S, nav, puede, cargarCfg, aplicarTema, guardarTema } from './estado.js';
import { $, $$, toast, cerrar, debounce, hayModalAbierto } from './util.js';
import { renderTablero, renderProcesos, renderGestion, cargarEjemplos } from './vistas.js';
import { openDetalle } from './detalle.js';
import { renderConfig } from './config.js';
import { openProc, iniciarFormularios } from './formularios.js';
import { iniciarDocs } from './docs.js';
import { mostrarLogin, cambiarPassword, iniciarAuth } from './auth.js';

const VISTAS = ['tablero', 'procesos', 'gestion', 'config', 'detalle'];
const RENDER = { tablero: renderTablero, procesos: renderProcesos, gestion: renderGestion, config: renderConfig };
const REFRESCO_MS = 30000;

function mostrar(v) {
  S.vista = v;
  VISTAS.forEach(x => { $('#view-' + x).style.display = x === v ? '' : 'none'; });
  $$('.tab').forEach(t => t.classList.toggle('active', t.dataset.view === v));
}

nav.mostrar = mostrar;
nav.ir = v => { if (v === 'gestion' && !puede('paquetes.ver')) v = 'procesos'; mostrar(v); return RENDER[v](); };
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
  Object.assign(S, { filtro: null, gMat: null, gSit: null, gTipo: null, cfgTab: null, proc: null });
  $('#search').value = '';
  await nav.ir('tablero');
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
  $('#btnMenu').onclick = () => $('#menuPop').classList.toggle('open');
  menu('miConfig', () => nav.ir('config'));
  menu('miEjemplos', async () => {
    const t = await api.get('/api/tablero');
    if (t.procesos && !confirm('Esto reemplazará los datos actuales por los de ejemplo. ¿Continuar?')) return;
    await cargarEjemplos();
  });
  menu('miVaciar', async () => {
    if (!confirm('¿Borrar TODOS los procesos y actuaciones? Esta acción no se puede deshacer.')) return;
    await api.post('/api/datos/vaciar'); toast('Datos borrados'); await nav.ir('tablero');
  });
  menu('miTema', async () => {
    const oscuro = S.me.preferencias.modo ? S.me.preferencias.modo === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
    await guardarTema({ modo: oscuro ? 'light' : 'dark' });
    if (S.vista === 'config') renderConfig();
  });
  menu('miPassword', cambiarPassword);
  menu('miSalir', async () => { await api.post('/api/auth/logout'); S.me = null; cerrar('ovForm'); pedirIngreso(); });

  // otros usuarios cambian datos: se refresca solo mientras nadie está escribiendo
  setInterval(() => {
    const escribiendo = ['INPUT', 'SELECT', 'TEXTAREA'].includes((document.activeElement || {}).tagName);
    if (S.me && !hayModalAbierto() && !escribiendo && !document.hidden && S.vista !== 'config') nav.refrescar();
  }, REFRESCO_MS);
}

async function inicio() {
  iniciarAuth(); iniciarFormularios(); iniciarDocs(); enlazar();
  onSesionVencida(pedirIngreso);
  try { await api.get('/api/me', null, true); } catch (e) { pedirIngreso(); return; }
  await arrancar();
}

inicio();
