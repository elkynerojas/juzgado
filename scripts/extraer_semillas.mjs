// Extrae los catálogos por defecto del HTML original a app/server/db/seed/
import fs from 'node:fs';
import { cargar } from './legacy.mjs';

const d = cargar(`
// fechas relativas a hoy: se guardan como "@desplazamiento" y se resuelven al cargar los ejemplos
addISO=function(off){return '@'+off;};
DB={procesos:[],actuaciones:[]};seed();
const __ej={procesos:DB.procesos,actuaciones:DB.actuaciones};
globalThis.__out = JSON.stringify({
  festivos: Array.from(FESTIVOS).sort(),
  terminos: TERMINOS.map(t => ({ nombre: t.n, dias: t.d, habil: t.h !== false, responsable: t.r || '', categoria: t.c || '' })),
  asuntos: ASUNTOS, cuadernos: CUADERNOS, materias: MATERIAS, macroetapas: MACROETAPAS,
  tiposSolicitud: TIPOS_SOLICITUD, sugerencias: SUG, rutas: DEFAULT_RUTAS, tipoRuta: DEFAULT_TIPORUTA,
  motivosPase: MOTIVOS_PASE, plantillas: DEFAULT_PLANTILLAS,
  juzgado: { juzgado: 'JUZGADO PROMISCUO MUNICIPAL', ciudad: 'CHINÁCOTA NORTE DE SANTANDER', prefijo: '54-172-40-89-001-' },
  firmante: { nombre: 'JOSE LUIS MORENO MILLAN', cargo: 'Secretario' },
  membrete: MEMBRETE_DEFAULT, firma: FIRMA_DEFAULT, ejemplos: __ej,
});`);

const dir = new URL('../app/server/db/seed/', import.meta.url);
for (const [campo, archivo] of [['membrete', 'membrete.png'], ['firma', 'antefirma.png']]) {
  const m = /^data:image\/png;base64,(.+)$/.exec(d[campo]);
  if (!m) throw new Error(campo + ' no es un PNG en base64');
  fs.writeFileSync(new URL(archivo, dir), Buffer.from(m[1], 'base64'));
  delete d[campo];
}
fs.writeFileSync(new URL('ejemplos.json', dir), JSON.stringify(d.ejemplos, null, 1) + '\n');
delete d.ejemplos;
fs.writeFileSync(new URL('catalogos.json', dir), JSON.stringify(d, null, 1) + '\n');
console.log('festivos', d.festivos.length, 'terminos', d.terminos.length, 'tipos', d.tiposSolicitud.length,
  'asuntos', d.asuntos.civil.length, d.asuntos.familia.length, 'rutas', d.rutas.length, 'plantillas', d.plantillas.length);
