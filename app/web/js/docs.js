import { api } from './api.js';
import { S } from './estado.js';
import { $, esc, toast, abrir, opciones, imprimir, debounce } from './util.js';

const PASE = 'Pase al despacho';
let act = null;

export async function openGen(a, tipo) {
  const plantillas = S.cfg.plantillas.filter(t => t.tipo === tipo);
  if (!plantillas.length) { toast('No hay plantillas de tipo ' + tipo); return; }
  act = a;
  $('#genTitle').textContent = tipo === PASE ? 'Generar pase al despacho' : 'Generar constancia';
  $('#g_tpl').innerHTML = opciones(plantillas.map(t => [t.id, t.nombre]), plantillas[0].id);
  $('#g_firm').innerHTML = S.cfg.firmantes.map(f => '<option value="' + f.id + '">' + esc(f.nombre) + ' — ' + esc(f.cargo) + '</option>').join('');
  $('#motivos').innerHTML = S.cfg.motivos_pase.map(m => '<option value="' + esc(m) + '">').join('');
  $('#g_motivowrap').style.display = tipo === PASE ? '' : 'none';
  $('#g_motivo').value = ''; $('#g_fecha').value = ''; $('#g_cuerpo').value = '';
  // sin fecha, el servidor propone la registrada para la constancia o el pase
  await rellenar();
  abrir('ovGen');
}

async function rellenar() {
  if (!act) return;
  const r = await api.post('/api/actuaciones/' + act.id + '/documento/texto', { plantilla_id: $('#g_tpl').value, motivo: $('#g_motivo').value, fecha: $('#g_fecha').value });
  $('#g_fecha').value = r.fecha; $('#g_cuerpo').value = r.cuerpo;
}

async function generar() {
  const html = await api.post('/api/actuaciones/' + act.id + '/documento/html', { cuerpo: $('#g_cuerpo').value, fecha: $('#g_fecha').value, firmante_id: $('#g_firm').value || null });
  imprimir(html); toast('Documento generado');
}

export function iniciarDocs() {
  $('#g_tpl').addEventListener('change', rellenar);
  $('#g_motivo').addEventListener('input', debounce(rellenar, 300));
  $('#g_fecha').addEventListener('change', rellenar);
  $('#g_print').onclick = generar;
}
