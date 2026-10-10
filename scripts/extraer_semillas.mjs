// Extrae los catálogos por defecto del HTML original (v2) a app/server/db/seed/
// Uso: node scripts/extraer_semillas.mjs [--ejemplos]   (--ejemplos también reescribe ejemplos.json)
import fs from 'node:fs';
import zlib from 'node:zlib';
import { cargar, V2 } from './legacy.mjs';

const d = cargar(`
// fechas relativas a hoy: se guardan como "@desplazamiento" y se resuelven al cargar los ejemplos
addISO=function(off){return '@'+off;};
DB={procesos:[],actuaciones:[]};seed();
const __ej={procesos:DB.procesos,actuaciones:DB.actuaciones};
globalThis.__out = JSON.stringify({
  festivos: Array.from(FESTIVOS).sort(),
  terminos: TERMINOS.map(t => ({ nombre: t.n, dias: t.d, habil: t.h !== false, responsable: t.r || '', categoria: t.c || '' })),
  asuntos: ASUNTOS, cuadernos: CUADERNOS, materias: MATERIAS, macroetapas: MACROETAPAS,
  tiposSolicitud: TIPOS_SOLICITUD, sugerencias: SUG,
  rutas: DEFAULT_RUTAS.map(r => ({ id: r.id, nombre: r.nombre, desc: r.desc, pasos: r.pasos.map(p => ({
    nombre: p.nombre, materia: p.materia || '', origen: p.origen || '', termino: p.termino || '', descripcion: p.descripcion || '',
    es_audiencia: !!p.esAudiencia, aud_estado: p.audEstado || '' })) })),
  tipoRuta: DEFAULT_TIPORUTA,
  motivosPase: MOTIVOS_PASE, plantillas: DEFAULT_PLANTILLAS,
  cargos: ['Juez', 'Secretario', 'Oficial Mayor', 'Escribiente', 'Citador'],
  juzgado: { juzgado: 'JUZGADO PROMISCUO MUNICIPAL', ciudad: 'CHINÁCOTA NORTE DE SANTANDER', prefijo: '54-172-40-89-001-' },
  firmante: { nombre: 'JOSE LUIS MORENO MILLAN', cargo: 'Secretario' },
  membrete: MEMBRETE_DEFAULT, firma: FIRMA_DEFAULT, ejemplos: __ej,
  sierju: {
    delitos: { penal: PENAL_DELITOS, garantias_906: DELITOS_GAR_906, garantias_1826: DELITOS_GAR_1826,
      conocimiento_906: DELITOS_CONOC_906, conocimiento_1826: DELITOS_CONOC_1826 },
    solicitudes_garantias: { '906': PENAL_SOL_GAR_906, '1826': PENAL_SOL_GAR_1826_ADULT },
    entradas: { civil: ENTRADAS_CIVIL, familia: ENTRADAS_FAMILIA, tutela: ENTRADAS_TUTELA, habeas: ENTRADAS_HABEAS,
      penal_conocimiento: PENAL_ENTRADAS_CONOC },
    salidas: { civil: SIERJU_SALIDAS, tutela: SALIDAS_TUTELA, desacato: SALIDAS_DESACATO, habeas: SALIDAS_HABEAS,
      penal_conocimiento: SALIDAS_PENAL_CONOC, penal_garantias: SALIDAS_PENAL_GAR },
    tipos: { civil: SIERJU_CIVIL, familia: SIERJU_FAMILIA, derechos: SIERJU_DERECHOS, habeas: HABEAS_TIPO },
    mapa_tipos: SIERJU_MAP,
    audiencias: { tipos_civil_familia: AUD_CIVFAM, tipos_penal: AUD_PENAL,
      columnas_causa: { civil_aplazada: AUDCOL_CIV_APL, civil_cancelada: AUDCOL_CIV_CAN,
        penal_aplazada: AUDCOL_PEN_APL, penal_cancelada: AUDCOL_PEN_CAN } },
    alias_columnas: STAT_COL_ALIAS,
    origen_por_gestion: ORIGEN_POR_GESTION,
  },
  secciones: SIERJU_MASTER,
  plantilla: { mapa: TPL_MAP, hojas: TPL_SHEET2CODE, archivos: TPL_FILES },
});`, V2);

const dir = new URL('../app/server/db/seed/', import.meta.url);
const escribir = (archivo, datos) => fs.writeFileSync(new URL(archivo, dir), JSON.stringify(datos, null, 1) + '\n');

for (const [campo, archivo] of [['membrete', 'membrete.png'], ['firma', 'antefirma.png']]) {
  const m = /^data:image\/png;base64,(.+)$/.exec(d[campo]);
  if (!m) throw new Error(campo + ' no es un PNG en base64');
  fs.writeFileSync(new URL(archivo, dir), Buffer.from(m[1], 'base64'));
  delete d[campo];
}
if (process.argv.includes('--ejemplos')) escribir('ejemplos.json', d.ejemplos);
delete d.ejemplos;

// plantilla oficial SIERJU: se reconstruye el .xlsx a partir de sus partes en base64
fs.writeFileSync(new URL('sierju_plantilla.xlsx', dir), zip(d.plantilla.archivos.map(f => [f.n, Buffer.from(f.b, 'base64')])));
escribir('sierju_tpl_map.json', { mapa: d.plantilla.mapa, hojas: d.plantilla.hojas });
escribir('sierju_secciones.json', d.secciones);
escribir('sierju.json', d.sierju);
for (const k of ['plantilla', 'secciones', 'sierju']) delete d[k];
escribir('catalogos.json', d);
console.log('festivos', d.festivos.length, 'terminos', d.terminos.length, 'tipos', d.tiposSolicitud.length,
  'cuadernos', d.cuadernos.length, 'rutas', d.rutas.length, 'plantillas', d.plantillas.length);

function crc32(buf) {
  let c, crc = 0xffffffff;
  for (const b of buf) {
    c = (crc ^ b) & 0xff;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    crc = (crc >>> 8) ^ c;
  }
  return (crc ^ 0xffffffff) >>> 0;
}

// ZIP con deflate y fecha fija (1980-01-01) para que el archivo sea reproducible
function zip(archivos) {
  const locales = [], centrales = [];
  let offset = 0;
  for (const [nombre, datos] of archivos) {
    const n = Buffer.from(nombre, 'utf8'), comp = zlib.deflateRawSync(datos, { level: 9 }), crc = crc32(datos);
    const loc = Buffer.alloc(30);
    loc.writeUInt32LE(0x04034b50, 0); loc.writeUInt16LE(20, 4); loc.writeUInt16LE(0x0800, 6); loc.writeUInt16LE(8, 8);
    loc.writeUInt16LE(0, 10); loc.writeUInt16LE(0x21, 12); loc.writeUInt32LE(crc, 14);
    loc.writeUInt32LE(comp.length, 18); loc.writeUInt32LE(datos.length, 22); loc.writeUInt16LE(n.length, 26);
    const cen = Buffer.alloc(46);
    cen.writeUInt32LE(0x02014b50, 0); cen.writeUInt16LE(20, 4); cen.writeUInt16LE(20, 6); cen.writeUInt16LE(0x0800, 8);
    cen.writeUInt16LE(8, 10); cen.writeUInt16LE(0, 12); cen.writeUInt16LE(0x21, 14); cen.writeUInt32LE(crc, 16);
    cen.writeUInt32LE(comp.length, 20); cen.writeUInt32LE(datos.length, 24); cen.writeUInt16LE(n.length, 28);
    cen.writeUInt32LE(offset, 42);
    locales.push(loc, n, comp);
    centrales.push(cen, n);
    offset += 30 + n.length + comp.length;
  }
  const central = Buffer.concat(centrales), fin = Buffer.alloc(22);
  fin.writeUInt32LE(0x06054b50, 0); fin.writeUInt16LE(archivos.length, 8); fin.writeUInt16LE(archivos.length, 10);
  fin.writeUInt32LE(central.length, 12); fin.writeUInt32LE(offset, 16);
  return Buffer.concat([...locales, central, fin]);
}
