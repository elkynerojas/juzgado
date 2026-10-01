export const $ = (s, r = document) => r.querySelector(s);
export const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

const ENT = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
export function esc(s) { return (s == null ? '' : String(s)).replace(/[&<>"']/g, c => ENT[c]); }

const pad = n => String(n).padStart(2, '0');
export function hoyISO() { const d = new Date(); return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
export function fmt(s) { if (!s) return ''; const p = s.split('-'); return p[2] + '/' + p[1] + '/' + p[0].slice(2); }
const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
export function fmtL(s) { if (!s) return '—'; const p = s.split('-'); return p[2] + ' ' + MESES[+p[1] - 1] + ' ' + p[0]; }
function aFecha(s) { const p = s.split('-'); return new Date(+p[0], +p[1] - 1, +p[2]); }
export function diasEntre(a, b) { return Math.round((aFecha(a) - aFecha(b)) / 86400000); }
export function fechaLarga(s) {
  const m = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
  const p = s.split('-'); return (+p[2]) + ' de ' + m[+p[1] - 1] + ' de ' + p[0];
}

let toastTimer = 0;
export function toast(m) {
  const t = $('#toast'); t.textContent = m; t.classList.add('show');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove('show'), 2600);
}

export function badge(d) { return '<span class="badge ' + d.badge + '">' + esc(d.situacion) + '</span>'; }
const TERM_BADGE = { 'Vencido': 'b-red', 'Próximo a vencer': 'b-amber', 'Latente': 'b-gray' };
export function badgeTermino(et) { return '<span class="badge ' + (TERM_BADGE[et] || 'b-blue') + '">' + esc(et) + '</span>'; }

export function abrir(id) { $('#' + id).classList.add('open'); }
export function cerrar(id) { $('#' + id).classList.remove('open'); }
export function hayModalAbierto() { return !!$('.overlay.open, .login.open'); }

export function debounce(fn, ms) { let t = 0; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }

/* Un solo manejador de clics por contenedor: los elementos declaran data-acc="nombre". */
export function delegar(raiz, acciones) {
  raiz.onclick = e => {
    const el = e.target.closest('[data-acc]');
    if (el && raiz.contains(el) && acciones[el.dataset.acc]) acciones[el.dataset.acc](el, e);
  };
}

export function opciones(lista, valor, vacio) {
  let h = vacio == null ? '' : '<option value="">' + esc(vacio) + '</option>';
  let esta = false;
  lista.forEach(o => {
    const [v, l] = Array.isArray(o) ? o : [o, o];
    if (v === valor) esta = true;
    h += '<option value="' + esc(v) + '"' + (v === valor ? ' selected' : '') + '>' + esc(l) + '</option>';
  });
  // un valor guardado que ya no está en el catálogo se conserva como opción
  if (valor && !esta) h += '<option value="' + esc(valor) + '" selected>' + esc(valor) + '</option>';
  return h;
}

const nativo = () => !!(window.pywebview && window.pywebview.api);

export async function guardarArchivo(nombre, contenido, mime, descripcion) {
  if (nativo()) {
    const ruta = await window.pywebview.api.guardar_texto(nombre, contenido, descripcion);
    if (ruta) toast('Guardado en ' + ruta);
    return;
  }
  const u = URL.createObjectURL(new Blob([contenido], { type: mime }));
  const a = document.createElement('a'); a.href = u; a.download = nombre; a.click(); URL.revokeObjectURL(u);
}

export function imprimir(html) {
  const viejo = document.getElementById('printFrame'); if (viejo) viejo.remove();
  const f = document.createElement('iframe'); f.id = 'printFrame';
  f.style.cssText = 'position:fixed;right:0;bottom:0;width:0;height:0;border:0';
  f.onload = () => {
    const w = f.contentWindow;
    const pendientes = Array.from(w.document.images).filter(im => !im.complete)
      .map(im => new Promise(ok => { im.onload = im.onerror = ok; }));
    Promise.all(pendientes).then(() => setTimeout(() => { w.focus(); w.print(); }, 150));
  };
  f.srcdoc = html;
  document.body.appendChild(f);
}

export function elegirImagen() {
  return new Promise(ok => {
    const inp = $('#fileImagen');
    inp.onchange = () => { const f = inp.files[0]; inp.value = ''; if (f) ok(f); };
    inp.click();
  });
}
