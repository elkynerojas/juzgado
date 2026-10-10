// Ejecuta las reglas nuevas de legacy/control_procesos_v2.html con fecha fija y guarda los valores
// esperados en tests/golden/v2_dominio.json para comparar contra Python (fase 8).
// Las funciones que leen el formulario se corren con un DOM falso (__form).
import fs from 'node:fs';
import { cargar, V2 } from './legacy.mjs';

const out = cargar(`
const __form={};
function __el(v){return {value:v===undefined?'':v,checked:false,style:{},innerHTML:'',textContent:'',options:[],
  classList:{add(){},remove(){},toggle(){}}};}
document.getElementById=function(id){return __form[id]||null;};
document.querySelector=function(s){var k=s.charAt(0)==='#'?s.slice(1):s;return __form[k]||__el('');};
toast=function(){};
function __fijar(h){
  todayISO=function(){return h;};
  addISO=function(off){const d=parse(h);d.setDate(d.getDate()+off);return iso(d);};
}
__fijar('2026-09-30');DB={procesos:[],actuaciones:[]};seed();ensureDefaults();

const __CALS=[
  {suspensiones:[],cerrados:[],reabiertos:[]},
  {suspensiones:[{desde:'2026-09-14',hasta:'2026-09-25',motivo:'paro'},{desde:'2026-12-20',hasta:'2027-01-10',motivo:'vacancia'}],cerrados:['2026-10-01','2026-10-03','2027-04-06'],reabiertos:['2026-10-12','2026-12-25','2026-10-04']},
];
const NATS=['Civil','Familia','Penal 906 - Garantías','Penal 1826 - Garantías','Penal 906 - Conocimiento','Penal 1826 - Conocimiento','Tutela','Incidente de desacato','Hábeas corpus','Otro'];

// ---------- listas por naturaleza ----------
const naturalezas=NATS.map(function(n){return {nat:n,esPenal:esPenal(n),esGarantias:esGarantias(n),esConocimiento:esConocimiento(n),
  esConstitucional:esConstitucional(n),listaSierju:listaSierju(n),listaSalidas:listaSalidas(n),penalSolicitudes:penalSolicitudes(n),
  entradasSierju:entradasSierju(n),tiposGestion:tiposGestionPorNat(n),salidasAct:salidasActPorNat(n)};});
const delitos={};
['Garantías','Conocimiento'].forEach(function(p){__form.p_penproc=__el(p);delitos[p]=delitosUnif().map(function(o){return [o.d,o.ley];});});

// ---------- sugSierju ----------
const __textos=[].concat(ASUNTOS.civil,ASUNTOS.familia,Object.keys(SIERJU_MAP),['',
  'Acción de tutela por salud','Pensión de vejez','derecho a la vida','Mínimo vital','IGUALDAD','educación','debido proceso administrativo',
  'derecho de petición','acceso a la información','tutela contra providencia','medio ambiente sano','vivienda',
  'Inasistencia alimentaria agravada','inasistencia alimentaria','violencia intrafamiliar','lesiones culposas','lesiones personales dolosas',
  'hurto calificado y agravado','hurto simple','daño en bien ajeno','dano','injuria','calumnia','estafa','ejercicio arbitrario de la custodia',
  'homicidio culposo','homicidio','concierto para delinquir','SGD','sgde','Garantía mobiliaria','prueba anticipada','despacho comisorio',
  'avalúo de perjuicios','Permiso para salir del país','Restitución internacional de menores','régimen de visitas','adopción']);
const __vistos={};const sug=[];
function __sug(c,n){var k=c+'|'+n;if(__vistos[k])return;__vistos[k]=1;sug.push([c,n,sugSierju(c,n)]);}
__textos.forEach(function(c){NATS.concat(['Desacato']).forEach(function(n){if(n!=='Incidente de desacato')__sug(c,n);});});
PENAL_DELITOS.forEach(function(c){NATS.filter(esPenal).forEach(function(n){__sug(c,n);});});

// ---------- fechaGestionSecretaria ----------
const gestion=__CALS.map(function(c){
  DB.config.calendario=c;var r=[];const d=parse('2026-01-01');const fin=parse('2027-06-30');
  while(d<=fin){r.push(fechaGestionSecretaria(iso(d)));d.setDate(d.getDate()+1);}
  return {calendario:c,desde:'2026-01-01',fechas:r};
});

// ---------- recomputeEjec ----------
const ejecutoria=[];
__CALS.forEach(function(c,ic){DB.config.calendario=c;
  ['','2026-09-30','2026-12-18','2026-10-09','2027-01-08'].forEach(function(nf){
    [3,5,0].forEach(function(dias){
      [['','','','','',''],['Apelación','','','','',''],['Apelación','Confirman totalmente','2026-11-20','','',''],
       ['Reposición','Revocan','','','',''],['Impugnación','Confirman','2026-11-20','Sí','',''],
       ['Impugnación','Confirman','2026-11-20','Sí','Revocan','2026-12-01'],['Impugnación','Confirman','2026-11-20','Sí','Revocan','']
      ].forEach(function(r){['','2026-10-02'].forEach(function(prev){
        Object.assign(__form,{a_notif:__el(nf),a_ejecdias:__el(dias?String(dias):''),a_recurso:__el(r[0]),a_supres:__el(r[1]),a_supfecha:__el(r[2]),
          a_recimpug:__el(r[3]),a_recimpugres:__el(r[4]),a_recimpugfecha:__el(r[5]),a_ejec:__el(prev),ejecPrev:__el(''),recImpugBox:__el('')});
        recomputeEjec();
        var t=__form.ejecPrev.innerHTML||__form.ejecPrev.textContent;
        var estado=t.indexOf('Indique')===0?'sin_notificacion':(t.indexOf('suspendida')>=0?'suspendida':(t.indexOf('Recurso resuelto')===0?'en_firme':'corre'));
        ejecutoria.push({cal:ic,notif:nf,dias:dias,recurso:r,previa:prev,estado:estado,pendiente:t.indexOf('Pendiente de resolver la impugnación')>=0?'impugnacion':(t.indexOf('Pendiente de resolver.')>=0?'superior':''),ejecutoria:__form.a_ejec.value});
      });});
    });
  });
});

// ---------- globalStats con ejecutorias ----------
DB.config.calendario=__CALS[1];
var __base={procesoId:DB.procesos[0].id,cuaderno:'Principal',materia:'Otro',tipoSolicitud:'',origen:'Memorial',fechaMemorial:'',constancia:'',pasa:'',pase:'',providencia:'',ejecutoria:'',cumplida:'',termino:'',terminoDias:null,terminoHabil:true,fechaInicio:'',suspende:false,obs:'',rutaId:'',pasoIdx:null};
[['notificada ayer',addISO(-1),0,''],['notificada hace 20 días',addISO(-20),0,''],['notificada hoy, 5 días',addISO(0),5,''],
 ['con recurso',addISO(-1),0,'Apelación'],['ejecutoria vence hoy',addISO(-3),1,'']].forEach(function(x,i){
  DB.actuaciones.push(Object.assign({},__base,{id:'ej'+i,descripcion:x[0],notifFecha:x[1],ejecDias:x[2]||undefined,recursoTipo:x[3]}));});
const statsActs=DB.actuaciones.slice();
const statsProcesos=DB.procesos.slice();
const stats=globalStats();

// ---------- automatismos al crear y editar procesos ----------
function __limpiar(a){var o=Object.assign({},a);delete o.id;return o;}
const automatismos=[];
function __caso(nombre,p,form,antes){
  DB.actuaciones=(antes||[]).map(function(a){return Object.assign({},a);});
  Object.assign(__form,{p_crearact:Object.assign(__el(''),{checked:form.crear!==false}),p_entrada:__el(p.tipoEntrada||''),p_cuainicial:__el(p.cuadernoInicial||'')});
  var entrada={proceso:JSON.parse(JSON.stringify(p)),antes:DB.actuaciones.map(function(a){return Object.assign({},a);}),crear:form.crear!==false,accion:form.accion};
  if(form.accion==='nuevo'){crearActuacionInicial(p);if(esGarantias(p.naturaleza))syncGarantiasAudienciaCancelada(p);}
  else{crearActuacionGestionGarantias(p);syncGarantiasAudienciaCancelada(p);}
  entrada.nombre=nombre;entrada.despues=DB.actuaciones.map(__limpiar);
  automatismos.push(entrada);
}
DB.config.calendario=__CALS[0];
var P=function(o){return Object.assign({id:'p1',radicado:'2026-00001',naturaleza:'Civil',clase:'',demandante:'',demandado:'',fechaRad:'2026-10-03',situacion:'Activo',macroetapa:'',notas:'',tipoEntrada:'Por reparto',cuadernoInicial:'Principal',solicitudesPenales:[]},o);};
__caso('civil radicado en sábado',P({}),{accion:'nuevo'});
__caso('civil sin crear actuación',P({}),{accion:'nuevo',crear:false});
__caso('civil sin fecha',P({fechaRad:''}),{accion:'nuevo'});
__caso('familia en cuaderno propio',P({naturaleza:'Familia',fechaRad:'2026-10-12',cuadernoInicial:'Medidas cautelares',tipoEntrada:''}),{accion:'nuevo'});
__caso('tutela',P({naturaleza:'Tutela',fechaRad:'2026-12-24',tipoEntrada:'Ingreso por competencia'}),{accion:'nuevo'});
__caso('incidente de desacato',P({naturaleza:'Incidente de desacato',fechaRad:'2026-10-05'}),{accion:'nuevo'});
__caso('penal conocimiento',P({naturaleza:'Penal 906 - Conocimiento',tipoEntrada:'ESCRITO DE ACUSACIÓN'}),{accion:'nuevo'});
__caso('penal conocimiento sin entrada',P({naturaleza:'Penal 1826 - Conocimiento',tipoEntrada:''}),{accion:'nuevo'});
__caso('hábeas corpus',P({naturaleza:'Hábeas corpus'}),{accion:'nuevo'});
__caso('otro',P({naturaleza:'Otro'}),{accion:'nuevo'});
var S=function(o){return Object.assign({id:'s',tipo:'LEGALIZACIÓN DE CAPTURA',fecha:'2026-10-03',entrada:'Nueva solicitud',salida:'',fechaSalida:'',horaSalida:'',detalleSalida:''},o);};
var G=function(sols,o){return P(Object.assign({naturaleza:'Penal 906 - Garantías',solicitudesPenales:sols},o||{}));};
__caso('garantías una solicitud',G([S({})]),{accion:'nuevo'});
__caso('garantías dos solicitudes sin fecha propia',G([S({fecha:''}),S({id:'s2',tipo:'FORMULACIÓN DE IMPUTACIÓN',fecha:''})],{fechaRad:'2026-10-10'}),{accion:'nuevo'});
var gestion0={id:'g0',procesoId:'p1',cuaderno:'Principal',materia:'Audiencia / diligencia',tipoSolicitud:'Solicitudes de control de garantías',origen:'Memorial',descripcion:'viejo',fechaMemorial:'2026-10-01',constancia:'',pasa:'',pase:'',providencia:'',ejecutoria:'',cumplida:'',termino:'',terminoDias:null,terminoHabil:true,fechaInicio:'',suspende:false,obs:'',rutaId:'r_garantias',pasoIdx:0};
__caso('garantías editada actualiza la gestión',G([S({}),S({id:'s2',tipo:'FORMULACIÓN DE IMPUTACIÓN'})]),{accion:'editar'},[gestion0]);
__caso('garantías editada respeta lo ya llenado',G([S({fecha:'2026-10-09'})]),{accion:'editar'},[Object.assign({},gestion0,{constancia:'2026-10-02',pasa:'No – trámite secretaría',pase:''})]);
var aud=Object.assign({},gestion0,{id:'aud1',descripcion:'Auto fija audiencia',pasoIdx:1,esAudiencia:true,audFecha:'2026-10-20',audHora:'09:00',audEstado:'Programada',audTipo:'Ley 906 Garantías'});
var salidas=function(d1,h1,det){return [S({salida:'Autos decisiones de fondo',fechaSalida:'2026-10-15',horaSalida:'08:00'}),S({id:'s2',tipo:'FORMULACIÓN DE IMPUTACIÓN',salida:'Otras salidas no efectivas',fechaSalida:d1,horaSalida:h1,detalleSalida:det})];};
__caso('garantías todas salen antes: cancela',G(salidas('2026-10-18','','Retiro de la solicitud por la Fiscalía')),{accion:'editar'},[gestion0,aud]);
__caso('garantías cancelación por las demás partes',G(salidas('2026-10-20','08:59','Retiro de la solicitud por las demás partes')),{accion:'editar'},[gestion0,aud]);
__caso('garantías otra causa',G(salidas('2026-10-16','','Muerte del indiciado')),{accion:'editar'},[gestion0,aud]);
__caso('garantías una sale después: no cancela',G(salidas('2026-10-20','09:00','Retiro de la solicitud por la Fiscalía')),{accion:'editar'},[gestion0,aud]);
__caso('garantías una sin salida: no cancela',G([S({salida:'Autos decisiones de fondo',fechaSalida:'2026-10-15'}),S({id:'s2'})]),{accion:'editar'},[gestion0,aud]);
__caso('garantías audiencia sin hora',G(salidas('2026-10-20','','Retiro de la solicitud por la Fiscalía')),{accion:'editar'},[gestion0,Object.assign({},aud,{audHora:''})]);
var cancelada={id:'c1',procesoId:'p1',cuaderno:'Principal',materia:'Audiencia / diligencia',tipoSolicitud:'Cancelación de audiencia de control de garantías',origen:'Oficiosa',descripcion:'editada a mano',fechaMemorial:'2026-10-16',constancia:'',pasa:'No – trámite secretaría',pase:'',providencia:'',ejecutoria:'',cumplida:'2026-10-16',termino:'',terminoDias:null,terminoHabil:true,fechaInicio:'',suspende:false,obs:'',esAudiencia:true,audFecha:'2026-10-01',audHora:'',audEstado:'Cancelada / no realizada',audCausa:'Otras causas',rutaId:'r_garantias',pasoIdx:2,cancelacionDe:'aud1'};
__caso('garantías ya cancelada: actualiza sin duplicar',G(salidas('2026-10-18','','Retiro de la solicitud por la Fiscalía')),{accion:'editar'},[gestion0,aud,cancelada]);
__caso('garantías nueva con audiencia ya cancelable',G(salidas('2026-10-18','','')),{accion:'nuevo'},[aud]);

// ---------- normalización de saveProc (fechas automáticas, cuadernos, clase penal) ----------
// Se corre el saveProc real con el formulario falso y se recoge el proceso tal como queda guardado.
const normalizacion=[];
save=function(){};draftClear=function(){};setView=function(){};openDetalle=function(){};curView='procesos';
function __norm(nombre,campos,sols,delitos2){
  var base={p_rad:'2026-09-001',p_nat:'Civil',p_sierju:'',p_penproc:'Garantías',p_clase:'Ejecutivo',p_dte:'Banco',p_dda:'Pérez',
    p_frad:'2026-09-10',p_sit:'Activo',p_macro:'',p_fterm:'',p_farch:'',p_via:'Oral',p_salida:'',p_noticia:'',p_penalsol:'',
    p_entrada:'',p_tpfecha:'',p_impugna:'',p_impugfecha:'',p_dec2da:'',p_desTutela:'',p_desReq:'',p_desApertura:'',
    p_desConsulta:'',p_medidatut:'',p_cuainicial:'Principal',p_crearmed:'No'};
  Object.keys(base).forEach(function(k){__form[k]=__el(campos[k]!==undefined?campos[k]:base[k]);});
  __form.p_tp=Object.assign(__el(''),{checked:!!campos.p_tp});
  __form.p_crearact=Object.assign(__el(''),{checked:false});
  // effNat lee la ley del delito elegido
  __form.p_sierju.selectedOptions=[{dataset:{ley:campos.__ley||'906'}}];
  tempPenalSolicitudes=(sols||[]).map(function(x){return Object.assign({},x);});
  tempDelitos=(delitos2||[]).slice();
  DB.procesos=[];DB.actuaciones=[];editProc=null;
  saveProc();
  var p=DB.procesos[0];
  // uid() es aleatorio: se fija para que el golden sea reproducible
  normalizacion.push({nombre:nombre,entrada:{campos:campos,solicitudes:sols||[],delitos:delitos2||[]},
    proceso:p?Object.assign({},p,{id:'pn'}):null});
}
__fijar('2026-09-30');
__norm('civil activo',{});
__norm('terminado sin fecha',{p_sit:'Terminado'});
__norm('terminado con fecha escrita',{p_sit:'Terminado',p_fterm:'2026-08-01'});
__norm('archivado sin fecha',{p_sit:'Archivado'});
__norm('trámite posterior sin fecha',{p_tp:true});
__norm('trámite posterior con terminación',{p_sit:'Terminado',p_tp:true});
__norm('trámite posterior con fecha propia',{p_tp:true,p_tpfecha:'2026-09-20'});
__norm('sin trámite posterior ignora la fecha',{p_tpfecha:'2026-09-20'});
__norm('cuaderno inicial propio',{p_cuainicial:'Incidente de desacato'});
__norm('medidas cautelares',{p_crearmed:'Sí'});
__norm('medidas cautelares en su cuaderno',{p_cuainicial:'Medidas cautelares',p_crearmed:'Sí'});
__norm('civil con forma de salida',{p_sit:'Terminado',p_salida:'Sentencia'});
__norm('penal conocimiento: la clase es el delito',{p_nat:'Penal',p_penproc:'Conocimiento',p_sierju:'ARTÍCULO 239. HURTO',p_clase:'se descarta'},[],['ARTÍCULO 103. HOMICIDIO','']);
__norm('garantías vacía la forma de salida',{p_nat:'Penal',p_penproc:'Garantías',p_sierju:'ARTÍCULO 239. HURTO',p_salida:'Sentencia'},[{id:'s',tipo:'LEGALIZACIÓN DE CAPTURA',fecha:'',entrada:'Nueva solicitud',salida:'',fechaSalida:'',horaSalida:'',detalleSalida:''}]);
__norm('garantías toma la fecha de radicación',{p_nat:'Penal',p_penproc:'Garantías',p_sierju:'ARTÍCULO 239. HURTO',p_frad:'2026-09-11'},[{id:'s',tipo:'IMPUTACIÓN',fecha:'',entrada:'Nueva solicitud',salida:'',fechaSalida:'',horaSalida:'',detalleSalida:''}]);
__norm('civil descarta los delitos adicionales',{},[],['ARTÍCULO 103. HOMICIDIO']);
__norm('tutela',{p_nat:'Tutela',p_sierju:'Salud',p_medidatut:'Sí',p_impugna:'Sí',p_impugfecha:'2026-09-20'});

globalThis.__out=JSON.stringify({festivos:Array.from(FESTIVOS).sort(),terminos:DB.config.terminos,tiposSolicitud:DB.config.tiposSolicitud,
  naturalezas:naturalezas,delitos:delitos,sug:sug,gestion:gestion,ejecutoria:ejecutoria,
  stats:{hoy:'2026-09-30',calendario:__CALS[1],procesos:statsProcesos,acts:statsActs,prox:stats.prox},automatismos:automatismos,
  normalizacion:normalizacion});
`, V2);

fs.writeFileSync(new URL('../tests/golden/v2_dominio.json', import.meta.url), JSON.stringify(out) + '\n');
console.log('sug', out.sug.length, 'ejecutoria', out.ejecutoria.length, 'automatismos', out.automatismos.length,
  'creadas', out.automatismos.map(c => c.despues.length - c.antes.length).join(','));
