/* Listas que dependen de la naturaleza del proceso.
   El servidor es la única fuente de verdad (domain/naturaleza.py); aquí solo se guardan en caché
   porque la lista de delitos tiene cientos de entradas y el formulario la repinta a cada cambio. */
import { api } from './api.js';
import { S } from './estado.js';
import { $, esc, opciones } from './util.js';

const cacheListas = new Map();
const cacheDelitos = new Map();

export async function listasDe(naturaleza, clase) {
  // la clase solo afecta "sugerido", así que entra en la clave
  const k = (naturaleza || '') + '\n' + (clase || '');
  if (!cacheListas.has(k)) cacheListas.set(k, api.get('/api/config/naturaleza', { naturaleza, clase }));
  return cacheListas.get(k);
}

export async function delitosDe(procedimiento) {
  if (!cacheDelitos.has(procedimiento)) cacheDelitos.set(procedimiento, api.get('/api/config/delitos', { procedimiento }));
  return cacheDelitos.get(procedimiento);
}

export const mostrar = (id, cond) => { const el = $('#' + id); if (el) el.style.display = cond ? '' : 'none'; };

export function pintar(id, lista, valor, vacio) {
  const el = $('#' + id);
  if (el) el.innerHTML = opciones(lista, valor == null ? '' : valor, vacio);
}

/* Personal activo, para los selectores de responsable. "Nombre (Cargo)" como en la v2. */
export function opcionesPersonal(valor) {
  const gente = (S.cfg.personal || []).filter(p => p.activo || p.nombre === valor);
  return opciones(gente.map(p => [p.nombre, p.nombre + (p.cargo ? ' (' + p.cargo + ')' : '')]), valor || '', '— sin asignar —');
}

/* Cuadernos disponibles para un proceso: el catálogo, los suyos y los que ya usan sus actuaciones. */
export function cuadernosDe(proc, actuaciones) {
  const vistos = new Set();
  const out = [];
  const añadir = c => { if (c && !vistos.has(c)) { vistos.add(c); out.push(c); } };
  (S.cfg.catalogos.cuadernos || []).forEach(x => añadir(x.valor));
  if (proc) { añadir(proc.cuaderno_inicial); (proc.cuadernos || []).forEach(añadir); }
  (actuaciones || []).forEach(a => añadir(a.cuaderno));
  return out;
}

export const etiqueta = (id, texto) => { const el = $('#' + id); if (el) el.innerHTML = esc(texto); };
