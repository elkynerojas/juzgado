import { api } from './api.js';

/* Estado compartido de la interfaz. Los datos de negocio no se guardan aquí: cada vista los pide a la API. */
export const S = {
  me: null, cfg: null,
  vista: 'tablero', filtro: null, proc: null, volverA: 'procesos',
  gMat: null, gSit: null, gTipo: null,
  cfgTab: null,
};

/* Navegación: main.js registra las funciones para evitar importaciones circulares entre vistas. */
export const nav = { ir() {}, detalle() {}, refrescar() {} };

export const puede = p => !!S.me && S.me.permisos.includes(p);

export async function cargarCfg() { S.cfg = await api.get('/api/config'); return S.cfg; }

export const cat = tipo => (S.cfg.catalogos[tipo] || []).map(x => x.valor);

export function aplicarTema() {
  const t = (S.me && S.me.preferencias) || {};
  const r = document.documentElement;
  if (t.modo) r.setAttribute('data-theme', t.modo); else r.removeAttribute('data-theme');
  ['--navy', '--navy2', '--accent'].forEach(v => { if (t.color) r.style.setProperty(v, t.color); else r.style.removeProperty(v); });
  document.body.style.fontSize = t.font || '';
}

export async function guardarTema(cambios) {
  S.me.preferencias = await api.put('/api/me/preferencias', Object.assign({}, S.me.preferencias, cambios));
  aplicarTema();
}
