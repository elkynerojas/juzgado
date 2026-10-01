// Genera tests/golden/respaldo_legacy.json: lo que exporta "Exportar respaldo" del HTML original,
// con algunos cambios de configuración para probar que la restauración los respeta.
import fs from 'node:fs';
import { cargar } from './legacy.mjs';

const db = cargar(`
todayISO=function(){return '2026-09-30';};
addISO=function(off){const d=parse('2026-09-30');d.setDate(d.getDate()+off);return iso(d);};
DB={procesos:[],actuaciones:[]};seed();ensureDefaults();
DB.procesos[0].notas='Nota del respaldo viejo';
DB.config.juzgado='JUZGADO DE PRUEBA';DB.config.prefijo='99-000-';
DB.config.materias.push('Materia propia');
DB.config.terminos[0].d=25;DB.config.terminos.push({n:'Término propio',d:7,h:false,r:'Parte',c:'Control'});
DB.config.calendario={suspensiones:[{desde:'2026-11-03',hasta:'2026-11-05',motivo:'paro'}],cerrados:['2026-10-01'],reabiertos:['2026-10-12']};
DB.config.rutas[0].pasos.push({nombre:'Paso extra',materia:'',origen:'Oficiosa',termino:'',descripcion:'agregado'});
DB.config.tipoRuta['Memorial']='r_despacho';
DB.config.firmantes.push({id:'f2',nombre:'ANA RUIZ',cargo:'Escribiente',firma:''});
DB.plantillas.push({id:'p_propia',tipo:'Constancia',nombre:'Propia',cuerpo:'Texto {{radicado}}'});
DB.actuaciones.push(Object.assign({},DB.actuaciones[0],{id:'huerfana',procesoId:'no_existe'}));
globalThis.__out=JSON.stringify(DB);`);
fs.writeFileSync(new URL('../tests/golden/respaldo_legacy.json', import.meta.url), JSON.stringify(db) + '\n');
console.log('procesos', db.procesos.length, 'actuaciones', db.actuaciones.length, 'claves config', Object.keys(db.config).join(','));
