export class ApiError extends Error {
  constructor(status, mensaje) { super(mensaje); this.status = status; }
}

let alExpirar = () => {};
export function onSesionVencida(fn) { alExpirar = fn; }

function qs(params) {
  if (!params) return '';
  const u = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== null && v !== undefined && v !== '') u.set(k, v); });
  const s = u.toString();
  return s ? '?' + s : '';
}

async function mensajeDeError(r) {
  try {
    const j = await r.json();
    if (typeof j.detail === 'string') return j.detail;
    if (Array.isArray(j.detail)) return 'Datos no válidos: ' + j.detail.map(d => (d.loc || []).slice(1).join('.') + ' ' + d.msg).join('; ');
  } catch (e) { /* respuesta sin JSON */ }
  return 'Error ' + r.status;
}

async function pedir(metodo, url, cuerpo, silencioso) {
  const init = { method: metodo, headers: {}, credentials: 'same-origin' };
  if (cuerpo instanceof Blob) { init.body = cuerpo; init.headers['Content-Type'] = cuerpo.type; }
  else if (cuerpo !== undefined) { init.body = JSON.stringify(cuerpo); init.headers['Content-Type'] = 'application/json'; }
  let r;
  try { r = await fetch(url, init); } catch (e) { throw new ApiError(0, 'No hay conexión con el servidor'); }
  if (!r.ok) {
    if (r.status === 401 && !silencioso) alExpirar();
    throw new ApiError(r.status, await mensajeDeError(r));
  }
  if (r.status === 204) return null;
  return (r.headers.get('content-type') || '').includes('json') ? r.json() : r.text();
}

export const api = {
  get: (url, params, silencioso) => pedir('GET', url + qs(params), undefined, silencioso),
  post: (url, cuerpo, silencioso) => pedir('POST', url, cuerpo === undefined ? {} : cuerpo, silencioso),
  put: (url, cuerpo) => pedir('PUT', url, cuerpo),
  del: url => pedir('DELETE', url),
};
