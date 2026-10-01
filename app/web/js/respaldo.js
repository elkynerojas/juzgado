import { api } from './api.js';
import { S, nav, puede, cargarCfg } from './estado.js';
import { $, esc, hoyISO, toast, guardarArchivo } from './util.js';
import { formModal } from './modal.js';

const TIPO = 'Respaldo JSON (*.json)';
const puedeUsuarios = () => puede('usuarios.gestionar') && puede('roles.gestionar');

export async function exportarRespaldo() {
  const datos = await api.get('/api/respaldo');
  await guardarArchivo('respaldo_control_procesos_' + hoyISO() + '.json', JSON.stringify(datos, null, 1), 'application/json', TIPO);
  toast('Respaldo exportado');
}

export function restaurarDesdeArchivo() {
  const inp = $('#fileJson');
  inp.onchange = async () => {
    const f = inp.files[0]; inp.value = '';
    if (!f) return;
    let datos;
    try { datos = JSON.parse(await f.text()); } catch (e) { toast('El archivo no es un JSON válido'); return; }
    if (!datos || !Array.isArray(datos.procesos) || !Array.isArray(datos.actuaciones)) { toast('El archivo no es un respaldo de Control de Procesos'); return; }
    confirmarRestauracion(f.name, datos, usuarios => api.post('/api/respaldo/restaurar' + (usuarios ? '?usuarios=true' : ''), datos));
  };
  inp.click();
}

/* datos puede ser null cuando el respaldo está en el servidor y no se ha descargado */
function confirmarRestauracion(nombre, datos, enviar) {
  const viejo = datos && !datos.formato;
  const resumen = datos ? datos.procesos.length + ' proceso(s) y ' + datos.actuaciones.length + ' actuación(es)' + (viejo ? ', en el formato del archivo HTML anterior' : '') : 'el contenido del archivo';
  const campos = [{ k: 'nota', tipo: 'nota', valor: 'Se van a REEMPLAZAR todos los procesos, las actuaciones y la configuración por ' + resumen + ' de «' + nombre + '». Antes se guarda automáticamente un respaldo del estado actual en el servidor.' }];
  const traeUsuarios = !datos || (Array.isArray(datos.usuarios) && datos.usuarios.length);
  if (traeUsuarios && puedeUsuarios()) campos.push({ k: 'usuarios', tipo: 'checkbox', label: 'Restaurar también usuarios y roles (cierra todas las sesiones, incluida la suya)' });
  formModal({
    titulo: 'Restaurar respaldo', campos, textoGuardar: 'Restaurar',
    guardar: async v => {
      const r = await enviar(!!v.usuarios);
      toast('Restaurado: ' + r.procesos + ' proceso(s), ' + r.actuaciones + ' actuación(es)' + (r.actuaciones_omitidas ? ' (' + r.actuaciones_omitidas + ' sin proceso, omitidas)' : ''));
      if (r.usuarios_restaurados) { location.reload(); return; }
      await cargarCfg();
      $('#brandJz').textContent = S.cfg.juzgado.juzgado;
      await nav.ir('tablero');
    },
  });
}

/* ===== pestaña de configuración ===== */
let prog = null, archivos = [];

export async function cargarResp() {
  [prog, archivos] = await Promise.all([api.get('/api/respaldo/programacion'), api.get('/api/respaldo/archivos')]);
}

function tamano(b) { return b > 1048576 ? (b / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round(b / 1024)) + ' KB'; }

export function cfgResp() {
  const edita = puede('respaldo.restaurar');
  let h = '<div class="card"><div class="block"><div class="bt">Respaldo manual</div><div class="tiny muted" style="margin-bottom:8px">El archivo .json incluye procesos, actuaciones, configuración, usuarios y roles. Guárdelo en un lugar seguro: contiene los accesos cifrados de los usuarios.</div>'
    + '<button class="btn sm primary" data-acc="respExportar">⬇ Exportar respaldo (.json)</button> ' + (edita ? '<button class="btn sm" data-acc="respImportar">⬆ Restaurar desde un archivo…</button>' : '') + '</div>';
  h += '<div class="block"><div class="bt">Respaldo automático diario</div>'
    + '<div class="field"><label><input type="checkbox" id="rsActivo"' + (prog.activo ? ' checked' : '') + (edita ? '' : ' disabled') + ' style="width:auto;margin-right:6px">Hacer un respaldo cada día en el equipo servidor</label></div>'
    + '<div class="frow"><div class="field"><label>Hora</label><input type="time" id="rsHora" value="' + esc(prog.hora) + '"' + (edita ? '' : ' disabled') + '></div>'
    + '<div class="field"><label>Respaldos que se conservan</label><input type="number" id="rsConservar" min="1" max="365" value="' + prog.conservar + '"' + (edita ? '' : ' disabled') + '></div></div>'
    + '<div class="hint" style="margin-bottom:8px">Se hace a esa hora si la aplicación está abierta en el servidor; si no, apenas se abra ese día después de la hora. Último: ' + (prog.ultimo ? esc(prog.ultimo) : 'ninguno') + '.</div>'
    + (edita ? '<button class="btn sm" data-acc="respProg">Guardar programación</button>' : '') + '</div>';
  h += '<div class="block"><div class="bt">Respaldos guardados en el servidor (' + archivos.length + ')</div>';
  if (!archivos.length) h += '<div class="tiny muted">Aún no hay respaldos.</div>';
  archivos.forEach(a => {
    h += '<div class="firmante"><div style="flex:1"><b>' + esc(a.fecha.replace('T', ' ')) + '</b> <span class="badge ' + (a.automatico ? 'b-blue' : 'b-amber') + '">' + (a.automatico ? 'respaldo' : 'previo a restauración') + '</span><div class="tiny muted">' + esc(a.nombre) + ' · ' + tamano(a.bytes) + '</div></div>'
      + '<button class="btn sm" data-acc="respDescargar" data-n="' + esc(a.nombre) + '">Descargar</button>' + (edita ? '<button class="btn sm" data-acc="respRestaurar" data-n="' + esc(a.nombre) + '">Restaurar</button>' : '') + '</div>';
  });
  return h + '<button class="btn sm" data-acc="respCrear">+ Crear respaldo ahora</button></div></div>';
}

export function accionesResp(recargar) {
  return {
    respExportar: exportarRespaldo,
    respImportar: restaurarDesdeArchivo,
    respProg: async () => {
      await api.put('/api/respaldo/programacion', { activo: $('#rsActivo').checked, hora: $('#rsHora').value, conservar: Number($('#rsConservar').value) });
      await recargar('Programación guardada');
    },
    respCrear: async () => { await api.post('/api/respaldo/archivos'); await recargar('Respaldo creado'); },
    respDescargar: async d => {
      const datos = await api.get('/api/respaldo/archivos/' + encodeURIComponent(d.dataset.n));
      await guardarArchivo(d.dataset.n, JSON.stringify(datos, null, 1), 'application/json', TIPO);
    },
    respRestaurar: d => confirmarRestauracion(d.dataset.n, null, usuarios => api.post('/api/respaldo/archivos/' + encodeURIComponent(d.dataset.n) + '/restaurar' + (usuarios ? '?usuarios=true' : ''))),
  };
}
