// Golden del motor de clasificación SIERJU de legacy/control_procesos_v2.html.
// Empieza por el motor difuso (statNorm/statClean/statTokens/statBest): si eso diverge, todo lo demás diverge.
import fs from 'node:fs';
import { cargar, V2 } from './legacy.mjs';

const out = cargar(`
toast=function(){};

// ---------- motor difuso ----------
// se puntúa contra las etiquetas reales de las secciones, que es el uso de verdad
const SECS=SIERJU_MASTER;
const consultas=[];
SECS.forEach(function(s){
  s.rows.forEach(function(r){consultas.push(statClean(r));});
  s.cols.forEach(function(c){consultas.push(statClean(c));});
});
// más textos que el motor recibe en la práctica
const extra=['','Civil','FAMILIA','Ejecutivo singular','ARTÍCULO 239. HURTO','hurto','AUDIENCIAS PROGRAMADAS',
  'AUDIENCIAS REALIZADAS','Demanda','Por reparto','Sentencia','Auto','ORAL CIVIL 1 INSTANCIA SENTENCIAS',
  'TUTELAS','INCIDENTES DE DESACATO','HABEAS CORPUS','Salud','Vida','Mínimo vital','Alimentos',
  'inasistencia alimentaria','Remitido a juez de conocimiento','Otras salidas no efectivas','Nueva solicitud',
  'Reingreso','INVENTARIO FINAL','INVENTARIO INICIAL','texto que no existe en ninguna parte'];
const vistos={};
const norm=[],tok=[],best=[];
function probar(q){
  if(vistos[q])return; vistos[q]=1;
  norm.push([q,statNorm(q)]);
  tok.push([q,statTokens(q)]);
}
consultas.concat(extra).forEach(probar);
// statBest sobre cada sección: filas y columnas, con una muestra de consultas
const MUESTRA=extra.concat(consultas.filter(function(_,i){return i%37===0;}));
SECS.forEach(function(s){
  MUESTRA.forEach(function(q){
    best.push([s.code,'rows',q,statBest(s.rows,q)]);
    best.push([s.code,'cols',q,statBest(s.cols,q)]);
  });
});

// ---------- base de prueba y derivación completa ----------
// cubre todas las naturalezas, las dos ramas de audiencia con sus causas, recursos, remate, amparo,
// trámite posterior de proceso y de actuación, e inventario con procesos abiertos antes y después.
const PER={desde:'2026-01-01',hasta:'2026-12-31'};
function P(o){return Object.assign({id:'',radicado:'',naturaleza:'Civil',clase:'',demandante:'A',demandado:'B',
  fechaRad:'',situacion:'Activo',macroetapa:'',notas:'',tipoSierju:'',via:'Oral',tipoEntrada:'',fechaTerminacion:'',
  fechaArchivo:'',formaSalida:'',tramitePosterior:false,fechaTramitePosterior:'',noticiaCriminal:'',solicitudPenal:'',
  solicitudesPenales:[],delitosAdicionales:[],impugnacion:'',fechaImpugnacion:'',decision2da:'',medidaTutela:'',
  desTutela:'',desReq:'',desApertura:'',desConsulta:'',cuadernoInicial:'Principal',cuadernos:['Principal']},o);}
function A(o){return Object.assign({id:'',procesoId:'',cuaderno:'Principal',materia:'Otro',tipoSolicitud:'',
  origen:'Memorial',descripcion:'act',fechaMemorial:'',constancia:'',pasa:'',pase:'',providencia:'',ejecutoria:'',
  cumplida:'',termino:'',terminoDias:null,terminoHabil:true,fechaInicio:'',suspende:false,obs:'',rutaId:'',pasoIdx:null,
  tpTipo:'',asignadoA:'',tipoProvidencia:'',modoCierre:'',salidaStat:'',entradaStat:'',esAudiencia:false,audFecha:'',
  audHora:'',audEstado:'',audTipo:'',audCausa:'',audInmediata:false,cancelacionDe:'',recursoTipo:'',recursoFecha:'',
  recursoObjeto:'',recTraslado:'',superiorResultado:'',superiorFecha:'',recImpug:'',recImpugResult:'',recImpugFecha:'',
  remateRealizado:false,amparoPobrezaConcedido:false,notifFecha:'',notifForma:'',ejecDias:3},o);}

DB.procesos=[
  P({id:'c1',radicado:'2026-00001',naturaleza:'Civil',clase:'Ejecutivo singular',tipoSierju:'Ejecutivos',fechaRad:'2026-02-10',tipoEntrada:'Por reparto'}),
  P({id:'c2',radicado:'2026-00002',naturaleza:'Civil',clase:'Pertenencia',tipoSierju:'Pertenencia',fechaRad:'2026-03-01',tipoEntrada:'Por reparto',situacion:'Terminado',fechaTerminacion:'2026-08-20',formaSalida:'Sentencia',fechaArchivo:'2026-09-01'}),
  P({id:'c3',radicado:'2025-00009',naturaleza:'Civil',clase:'Ejecutivo hipotecario',tipoSierju:'Ejecutivos-Hipotecario',fechaRad:'2025-06-01',tipoEntrada:'Por reparto'}),
  P({id:'c4',radicado:'2026-00004',naturaleza:'Civil',clase:'Ejecutivo singular',tipoSierju:'Ejecutivos',fechaRad:'2026-01-15',situacion:'Terminado',fechaTerminacion:'2026-04-01',formaSalida:'Sentencia',tramitePosterior:true,fechaTramitePosterior:'2026-04-10'}),
  P({id:'c5',radicado:'2025-00010',naturaleza:'Familia',clase:'Alimentos',tipoSierju:'Alimentos (fijación/aumento/disminución/exoneración)',fechaRad:'2025-11-02',tipoEntrada:'Por reparto',tramitePosterior:true,fechaTramitePosterior:'2025-12-01'}),
  P({id:'t1',radicado:'2026-00011',naturaleza:'Tutela',clase:'Salud',tipoSierju:'Salud',fechaRad:'2026-05-02',tipoEntrada:'Por reparto',medidaTutela:'Sí',situacion:'Terminado',fechaTerminacion:'2026-05-12',formaSalida:'Concede'}),
  P({id:'t2',radicado:'2026-00012',naturaleza:'Tutela',clase:'Vida',tipoSierju:'Vida',fechaRad:'2026-06-02',situacion:'Terminado',fechaTerminacion:'2026-06-14',formaSalida:'Niega'}),
  P({id:'d1',radicado:'2026-00021',naturaleza:'Incidente de desacato',clase:'Salud',tipoSierju:'Salud',fechaRad:'2026-07-01',situacion:'Terminado',fechaTerminacion:'2026-07-20',formaSalida:'Sanciona'}),
  P({id:'h1',radicado:'2026-00031',naturaleza:'Hábeas corpus',clase:'Acción de hábeas corpus',tipoSierju:'Acción de hábeas corpus',fechaRad:'2026-04-04',formaSalida:'Concede',situacion:'Terminado',fechaTerminacion:'2026-04-05'}),
  P({id:'o1',radicado:'2026-00041',naturaleza:'Otro',clase:'Comisorio',tipoSierju:'Otros procesos',fechaRad:'2026-03-03'}),
  P({id:'g1',radicado:'2026-00051',naturaleza:'Penal 906 - Garantías',clase:'ARTÍCULO 239. HURTO',tipoSierju:'ARTÍCULO 239. HURTO',fechaRad:'2026-02-02',noticiaCriminal:'54001600',
    solicitudesPenales:[
      {id:'s1',tipo:'LEGALIZACIÓN DE CAPTURA',fecha:'2026-02-02',entrada:'Nueva solicitud',salida:'Auto - decisión de fondo',fechaSalida:'2026-02-20',horaSalida:'09:00',detalleSalida:''},
      {id:'s2',tipo:'FORMULACIÓN DE IMPUTACIÓN',fecha:'2026-02-05',entrada:'Reingreso',salida:'Otras salidas no efectivas',fechaSalida:'2026-03-01',horaSalida:'',detalleSalida:'Retiro de la solicitud por la Fiscalía'},
      {id:'s3',tipo:'LEGALIZACIÓN DE CAPTURA',fecha:'2026-02-06',entrada:'Nueva solicitud',salida:'',fechaSalida:'',horaSalida:'',detalleSalida:''}]}),
  P({id:'k1',radicado:'2026-00061',naturaleza:'Penal 906 - Conocimiento',clase:'ARTÍCULO 103. HOMICIDIO',tipoSierju:'ARTÍCULO 103. HOMICIDIO',fechaRad:'2026-01-20',tipoEntrada:'ESCRITO DE ACUSACIÓN'}),
  P({id:'k2',radicado:'2026-00062',naturaleza:'Penal 1826 - Conocimiento',clase:'ARTÍCULO 239. HURTO',tipoSierju:'ARTÍCULO 239. HURTO',fechaRad:'2026-02-21'}),
  P({id:'g2',radicado:'2026-00063',naturaleza:'Penal 1826 - Garantías',clase:'ARTÍCULO 239. HURTO',tipoSierju:'ARTÍCULO 239. HURTO',fechaRad:'2026-03-21',
    solicitudesPenales:[{id:'s4',tipo:'LEGALIZACIÓN DE CAPTURA',fecha:'2026-03-21',entrada:'Nueva solicitud',salida:'',fechaSalida:'',horaSalida:'',detalleSalida:''}]}),
];
DB.actuaciones=[
  A({id:'a1',procesoId:'c1',providencia:'2026-03-15',tipoProvidencia:'Auto interlocutorio',descripcion:'auto'}),
  A({id:'a2',procesoId:'c2',providencia:'2026-08-20',tipoProvidencia:'Sentencia',descripcion:'sentencia'}),
  A({id:'a3',procesoId:'c1',esAudiencia:true,audFecha:'2026-04-10',audHora:'09:00',audTipo:'Audiencia',audEstado:'Realizada',materia:'Audiencia / diligencia'}),
  A({id:'a4',procesoId:'c1',esAudiencia:true,audFecha:'2026-05-10',audTipo:'Audiencia',audEstado:'Aplazada',audCausa:'Por causa del juez o magistrado (ajenas al funcionario)'}),
  A({id:'a5',procesoId:'c3',esAudiencia:true,audFecha:'2026-06-10',audTipo:'Audiencia',audEstado:'Cancelada / no realizada',audCausa:'Otras causas'}),
  A({id:'a6',procesoId:'c3',esAudiencia:true,audFecha:'2026-07-10',audTipo:'Audiencia',audEstado:'Suspendida'}),
  A({id:'a7',procesoId:'g1',esAudiencia:true,audFecha:'2026-02-18',audTipo:'Ley 906 Garantías',audEstado:'Realizada',audInmediata:true}),
  A({id:'a8',procesoId:'g1',esAudiencia:true,audFecha:'2026-03-18',audTipo:'Ley 906 Garantías',audEstado:'Aplazada',audCausa:'Inasistencia del defensor público'}),
  A({id:'a9',procesoId:'k1',esAudiencia:true,audFecha:'2026-04-18',audTipo:'Ley 906 Conocimiento - Juicio oral',audEstado:'Cancelada / no realizada',audCausa:'Retiro de la solicitud por el fiscal'}),
  A({id:'a10',procesoId:'c1',recursoTipo:'Apelación',recursoFecha:'2026-04-20',recursoObjeto:'Auto',superiorResultado:'Confirman totalmente la decisión',superiorFecha:'2026-06-20'}),
  A({id:'a11',procesoId:'c2',recursoTipo:'Reposición',recursoFecha:'2026-05-20',recursoObjeto:'Sentencia'}),
  A({id:'a12',procesoId:'t1',recursoTipo:'Impugnación',recursoFecha:'2026-05-14',recursoObjeto:'Sentencia',superiorResultado:'Revocan la decisión',superiorFecha:'2026-07-14'}),
  A({id:'a13',procesoId:'c3',esAudiencia:true,audFecha:'2026-08-10',audTipo:'Audiencia',audEstado:'Realizada',remateRealizado:true}),
  A({id:'a14',procesoId:'c3',providencia:'2026-09-10',amparoPobrezaConcedido:true,tipoProvidencia:'Auto interlocutorio'}),
  A({id:'a15',procesoId:'c4',tpTipo:'Liquidación de costas y créditos',fechaMemorial:'2026-05-02',providencia:'2026-06-02'}),
  A({id:'a16',procesoId:'c5',tpTipo:'Remates',fechaMemorial:'2025-12-10',providencia:''}),
  A({id:'a17',procesoId:'c4',fechaMemorial:'2026-07-02',tipoSolicitud:'Nulidad procesal',materia:'Nulidad'}),
  A({id:'a18',procesoId:'c4',providencia:'2026-07-20',tipoSolicitud:'Nulidad procesal',materia:'Nulidad'}),
];
DB.statEventos=[
  {id:'m1',fecha:'2026-03-03',seccion:'SEC4603',fila:SIERJU_MASTER.find(function(s){return s.code==='SEC4603';}).rows[0],
   columna:SIERJU_MASTER.find(function(s){return s.code==='SEC4603';}).cols[0],cantidad:3,origen:'Manual',procesoId:'c1',nota:'a mano'},
  {id:'m2',fecha:'2025-12-31',seccion:'SEC4603',fila:'x',columna:'y',cantidad:1,origen:'Manual',procesoId:'',nota:'fuera del periodo'},
];

const paquete=getAllStatEvents(PER.desde,PER.hasta);
const matrices=buildStatMatrices(PER.desde,PER.hasta);
const eventos=paquete.events.map(function(e){return [e.fecha,e.seccion,e.fila,e.columna,e.cantidad,e.origen,e.procesoId,e.nota];});
const avisos=paquete.warnings.map(function(w){return [w.fecha||'',w.seccion||'',w.procesoId||'',w.nota||''];});
const mats=matrices.sections.map(function(x){return {code:x.sec.code,total:x.total,mapa:x.map};});

// ---------- Excel oficial ----------
// se ejecuta el doFillTemplate real y se captura lo que habría empaquetado, para comparar celda por celda
var capturado=null;
const _zipStore=zipStore;
zipStore=function(files){capturado=files;return new Uint8Array(0);};
URL={createObjectURL:function(){return 'x';},revokeObjectURL:function(){}};
Blob=function(){};
document.createElement=function(){return {click:function(){},style:{}};};
doFillTemplate(PER.desde,PER.hasta);
zipStore=_zipStore;
const dec2=new TextDecoder('utf-8');
// de cada hoja mapeada se extraen valor e índice de estilo de todas sus celdas
const hojas={};
(capturado||[]).forEach(function(f){
  var base=f.name.split('/').pop();
  if(f.name.indexOf('worksheets/')<0||!TPL_SHEET2CODE[base])return;
  var xml=dec2.decode(f.data),celdas={};
  var rx=/<c r="([A-Z]+\\d+)"([^>]*?)(?:\\/>|>([\\s\\S]*?)<\\/c>)/g,m;
  while((m=rx.exec(xml))){
    var attrs=m[2]||'',cuerpo=m[3]||'';
    var sm=/\\s+s="(\\d+)"/.exec(attrs);
    var vm2=/<v>([^<]*)<\\/v>/.exec(cuerpo);
    celdas[m[1]]={s:sm?+sm[1]:null,v:vm2?vm2[1]:null,t:(/t="([^"]*)"/.exec(attrs)||[null,null])[1]};
  }
  hojas[base]={code:TPL_SHEET2CODE[base],celdas:celdas};
});
// y del styles.xml parcheado, los conteos que debe tener
var estilosInfo=null;
(capturado||[]).forEach(function(f){
  if(!/styles\\.xml$/.test(f.name))return;
  var xml=dec2.decode(f.data);
  estilosInfo={fills:+(/<fills count="(\\d+)">/.exec(xml)||[0,0])[1],
    cellXfs:+(/<cellXfs count="(\\d+)">/.exec(xml)||[0,0])[1],
    tieneRelleno:xml.indexOf('FFFFF2CC')>=0};
});

// statFindCol añade los alias del formato y statFindRow cae en "OTROS"; se comparan aparte
const findCol=[],findRow=[];
SECS.forEach(function(s){
  MUESTRA.concat(Object.keys(STAT_COL_ALIAS)).forEach(function(q){
    findCol.push([s.code,q,statFindCol(s,q)]);
    findRow.push([s.code,q,statFindRow(s,q)]);
  });
});

globalThis.__out=JSON.stringify({norm:norm,tokens:tok,best:best,findCol:findCol,findRow:findRow,
  db:{procesos:DB.procesos,actuaciones:DB.actuaciones,statEventos:DB.statEventos},periodo:PER,
  eventos:eventos,avisos:avisos,matrices:mats,conteos:{auto:paquete.auto,manual:paquete.manual},
  excel:{hojas:hojas,estilos:estilosInfo},
  secciones:SECS.map(function(s){return {code:s.code,n:s.n,sheet:s.sheet,title:s.title,rows:s.rows.length,cols:s.cols.length};}),
  activas:activeSecs().map(function(s){return s.code;})});
`, V2);

fs.writeFileSync(new URL('../tests/golden/v2_sierju.json', import.meta.url), JSON.stringify(out) + '\n');
console.log('norm', out.norm.length, 'best', out.best.length, 'eventos', out.eventos.length, 'avisos', out.avisos.length, 'auto', out.conteos.auto, 'manual', out.conteos.manual,
  'secciones', out.secciones.length, 'activas', out.activas.length);
