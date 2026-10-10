// Genera tests/golden/respaldo_legacy.json (v1) y respaldo_legacy_v2.json (v2): lo que exporta
// "Exportar respaldo" del HTML original, con cambios de configuración y, en la v2, datos penales,
// constitucionales, audiencias, personal y datos estadísticos manuales.
import fs from 'node:fs';
import { cargar, V2 } from './legacy.mjs';

const fechas = `
todayISO=function(){return '2026-09-30';};
addISO=function(off){const d=parse('2026-09-30');d.setDate(d.getDate()+off);return iso(d);};
DB={procesos:[],actuaciones:[]};seed();ensureDefaults();`;

const v1 = cargar(`${fechas}
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
escribir('respaldo_legacy.json', v1);

const v2 = cargar(`${fechas}DB.statEventos=[];
DB.config.roles.push('Notificador');
DB.config.personal=[{id:'pe1',nombre:'ANA RUIZ',rol:'Oficial Mayor'},{id:'pe2',nombre:'LUIS PAZ',rol:'Citador'}];
var base={radicado:'',naturaleza:'',clase:'',demandante:'',demandado:'',fechaRad:'2026-09-01',situacion:'Activo',macroetapa:'',notas:''};
DB.procesos.push(Object.assign({},base,{id:'pg',radicado:'2026-00100',naturaleza:'Penal 906 - Garantías',
  clase:'ARTÍCULO 239. HURTO',tipoSierju:'ARTÍCULO 239. HURTO',via:'Oral',noticiaCriminal:'541726000000202600123',
  solicitudPenal:'LEGALIZACIÓN DE CAPTURA',delitosAdicionales:['ARTÍCULO 111. LESIONES DOLOSAS'],cuadernoInicial:'Principal',cuadernos:['Principal'],
  solicitudesPenales:[
    {id:'s1',tipo:'LEGALIZACIÓN DE CAPTURA',fecha:'2026-09-01',entrada:'Nueva solicitud',salida:'Autos decisiones de fondo',fechaSalida:'2026-09-02',horaSalida:'10:30',detalleSalida:''},
    {id:'s2',tipo:'FORMULACIÓN DE IMPUTACIÓN',fecha:'2026-09-01',entrada:'Reingreso',salida:'',fechaSalida:'',horaSalida:'',detalleSalida:''}]}));
DB.procesos.push(Object.assign({},base,{id:'pt',radicado:'2026-00101',naturaleza:'Tutela',clase:'Salud',tipoSierju:'Salud',via:'Oral',
  fechaTerminacion:'2026-09-15',formaSalida:'Concede',impugnacion:'Sí',fechaImpugnacion:'2026-09-18',decision2da:'Confirma',medidaTutela:'Sí',
  tipoEntrada:'Ingreso por reparto de tutelas durante el periodo',cuadernoInicial:'Principal',cuadernos:['Principal','Incidente de desacato 1']}));
DB.procesos.push(Object.assign({},base,{id:'pd',radicado:'2026-00102',naturaleza:'Incidente de desacato',desTutela:'2026-00101',
  desReq:'2026-09-20',desApertura:'Apertura',desConsulta:'Confirma',tramitePosterior:true,fechaTramitePosterior:'2026-09-25'}));
DB.procesos.push(Object.assign({},base,{id:'pv',radicado:'2026-00103',naturaleza:'Penal 1826 - Garantías',solicitudPenal:'LEGALIZACIÓN DE CAPTURA'}));
var act={procesoId:'pg',cuaderno:'Principal',materia:'Audiencia / diligencia',tipoSolicitud:'Solicitudes de control de garantías',origen:'Providencia (auto/sentencia)',
  descripcion:'Audiencia: Ley 906 Garantías',fechaMemorial:'2026-09-01',constancia:'',pasa:'',pase:'',providencia:'2026-09-01',ejecutoria:'',cumplida:'',termino:'',
  terminoDias:null,terminoHabil:true,fechaInicio:'',suspende:false,obs:'',rutaId:'r_garantias',pasoIdx:1};
DB.actuaciones.push(Object.assign({},act,{id:'aa',esAudiencia:true,audFecha:'2026-09-03',audHora:'09:00',audEstado:'Aplazada',audTipo:'Ley 906 Garantías',
  audCausa:'Inasistencia del fiscal o acusador privado',audInmediata:true,asignadoA:'ANA RUIZ (Oficial Mayor)',tipoProvidencia:'Auto interlocutorio',modoCierre:'Providencia'}));
DB.actuaciones.push(Object.assign({},act,{id:'ab',procesoId:'pt',rutaId:'',pasoIdx:null,esAudiencia:false,recursoTipo:'Impugnación',recursoFecha:'2026-09-18',
  recursoObjeto:'Sentencia',recTraslado:'2026-09-19',superiorResultado:'Revocan',superiorFecha:'2026-10-01',recImpug:'Sí',recImpugResult:'Confirman',
  recImpugFecha:'2026-10-05',remateRealizado:true,amparoPobrezaConcedido:true,notifFecha:'2026-09-16',notifForma:'Personal / electrónica',ejecDias:5,
  tpTipo:'Remates',salidaStat:'Concede',entradaStat:'Acción de tutela',cancelacionDe:'aa'}));
DB.statEventos.push(statEvent('2026-09-10','SEC4416','AUTOS INTERLOCUTORIOS','TUTELAS',2,'Manual','pt','registro a mano'));
DB.statEventos.push(statEvent('2026-09-11','SEC3746','OTROS','ARCHIVADOS',1,'Manual','no_existe',''));
DB.statEventos.push(statEvent('','SEC3746','sin fecha','x',1,'Manual','',''));
globalThis.__out=JSON.stringify(DB);`, V2);
escribir('respaldo_legacy_v2.json', v2);

function escribir(nombre, db) {
  fs.writeFileSync(new URL('../tests/golden/' + nombre, import.meta.url), JSON.stringify(db) + '\n');
  console.log(nombre, 'procesos', db.procesos.length, 'actuaciones', db.actuaciones.length, 'claves config', Object.keys(db.config).join(','));
}
