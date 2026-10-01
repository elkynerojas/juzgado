// Ejecuta las reglas originales del HTML con fecha fija y guarda los valores esperados
// en tests/golden/ para comparar contra la implementación en Python.
import fs from 'node:fs';
import { cargar } from './legacy.mjs';

const out = cargar(`
function __fijar(h){
  todayISO=function(){return h;};
  addISO=function(off){const d=parse(h);d.setDate(d.getDate()+off);return iso(d);};
}
const __CAMPOS='R={{radicado}}|F={{radicado_full}}|P={{proceso}}|DTE={{demandante}}|DDA={{demandado}}|CU={{cuaderno}}|D={{descripcion}}|M={{materia}}|T={{termino}}|FI={{fecha_inicio}}|V={{vencimiento}}|MP={{motivo_pase}}|FE={{fecha}}|FL={{fecha_letras}}|C={{ciudad}}|R2={{radicado}}';
function __snap(a){
  const c=codigo(a), r=resultado(a,c), sp=siguientePaso(a), p=DB.procesos.find(x=>x.id===a.procesoId);
  return {a:a,codigo:c,fechaActiva:fechaActiva(a),vencimiento:vencimiento(a),estTermino:estTermino(a),
    diasEstado:diasEstado(a,c),ubicacion:ubicacion(c),resultado:[r.t,r.b],pasoCerrado:pasoCerrado(a),
    siguiente:sp?{ruta:sp.r.id,idx:sp.idx,nombre:sp.paso.nombre}:null,
    fechaConstancia:fechaDoc(a,'Constancia'),fechaPase:fechaDoc(a,'Pase al despacho'),
    textoHoy:fillTpl(__CAMPOS,a,p,'Recurso',''),textoFecha:fillTpl(__CAMPOS,a,p,'','2027-01-21')};
}
function __extras(pid){
  const A=o=>Object.assign({id:uid(),procesoId:pid,cuaderno:'Principal',materia:'Otro',tipoSolicitud:'',origen:'Memorial',descripcion:'extra',fechaMemorial:'',constancia:'',pasa:'',pase:'',providencia:'',ejecutoria:'',cumplida:'',termino:'',terminoDias:null,terminoHabil:true,fechaInicio:'',suspende:false,obs:'',rutaId:'',pasoIdx:null},o);
  const V='Vencimiento de término';
  return [
    A({origen:V,descripcion:'personalizado hábil',termino:'(personalizado)',terminoDias:7,terminoHabil:true,fechaInicio:addISO(-3)}),
    A({origen:V,descripcion:'personalizado calendario vencido',termino:'(personalizado)',terminoDias:30,terminoHabil:false,fechaInicio:addISO(-40)}),
    A({origen:V,descripcion:'personalizado sin días',termino:'(personalizado)',terminoDias:null,fechaInicio:addISO(-4)}),
    A({origen:V,descripcion:'término suspendido',termino:'Traslado de la demanda',fechaInicio:addISO(-5),suspende:true}),
    A({origen:V,descripcion:'término latente',termino:'Traslado de la demanda'}),
    A({origen:V,descripcion:'término fuera de catálogo',termino:'No existe',fechaInicio:addISO(-5)}),
    A({origen:V,descripcion:'término calendario de catálogo',termino:'1 año para posible desistimiento tácito',fechaInicio:addISO(-200)}),
    A({origen:V,descripcion:'vence hoy',termino:'(personalizado)',terminoDias:5,terminoHabil:false,fechaInicio:addISO(-5)}),
    A({origen:V,descripcion:'vence en 3 días',termino:'(personalizado)',terminoDias:5,terminoHabil:false,fechaInicio:addISO(-2)}),
    A({origen:V,descripcion:'vence en 4 días',termino:'(personalizado)',terminoDias:5,terminoHabil:false,fechaInicio:addISO(-1)}),
    A({descripcion:'memorial sin fecha'}),
    A({descripcion:'memorial futuro',fechaMemorial:addISO(6)}),
    A({descripcion:'memorial de hoy',fechaMemorial:addISO(0)}),
    A({descripcion:'memorial con término corriendo',fechaMemorial:addISO(-2),termino:'Traslado Avalúos',fechaInicio:addISO(-2)}),
    A({descripcion:'constancia sin decidir pase',fechaMemorial:addISO(-9),constancia:addISO(-8)}),
    A({descripcion:'ejecutoriado pendiente cumplir',fechaMemorial:addISO(-30),constancia:addISO(-29),pasa:'Sí',pase:addISO(-28),providencia:addISO(-20),ejecutoria:addISO(-14)}),
    A({descripcion:'ciclo completo',fechaMemorial:addISO(-30),constancia:addISO(-29),pasa:'Sí',pase:addISO(-28),providencia:addISO(-20),ejecutoria:addISO(-14),cumplida:addISO(-10)}),
    A({descripcion:'secretaría con ejecutoria',fechaMemorial:addISO(-12),constancia:addISO(-11),pasa:'No – trámite secretaría',ejecutoria:addISO(-3)}),
    A({origen:'Oficiosa',descripcion:'oficiosa con fecha',fechaMemorial:addISO(-1)}),
    A({cuaderno:'Liquidación de costas',origen:V,descripcion:'ruta paso 0 vencido',termino:'Traslado Liquidación de costas',fechaInicio:addISO(-15),rutaId:'r_traslado',pasoIdx:0}),
    A({cuaderno:'Remate',origen:V,descripcion:'ruta paso 0 con sucesor',termino:'Traslado Avalúos',fechaInicio:addISO(-15),rutaId:'r_traslado',pasoIdx:0}),
    A({cuaderno:'Remate',descripcion:'ruta paso 1 al despacho',fechaMemorial:addISO(-6),constancia:addISO(-6),pasa:'Sí',pase:addISO(-5),rutaId:'r_traslado',pasoIdx:1}),
    A({cuaderno:'Nulidad',origen:V,descripcion:'ruta último paso',termino:'Ejecutoria de sentencia',fechaInicio:addISO(-1),rutaId:'r_traslado',pasoIdx:2}),
    A({cuaderno:'Queja',descripcion:'ruta inexistente',fechaMemorial:addISO(-1),rutaId:'r_no_existe',pasoIdx:0}),
    A({cuaderno:'Incidente',descripcion:'ruta sin índice',fechaMemorial:addISO(-1),rutaId:'r_recurso',pasoIdx:null}),
    A({cuaderno:'Reposición',descripcion:'ruta paso 0 abierto',fechaMemorial:addISO(-1),rutaId:'r_recurso',pasoIdx:0}),
  ];
}
const __CALS=[
  {suspensiones:[],cerrados:[],reabiertos:[]},
  {suspensiones:[{desde:'2026-09-14',hasta:'2026-09-25',motivo:'paro'},{desde:'2026-12-20',hasta:'2027-01-10',motivo:'vacancia'}],cerrados:['2026-10-01','2026-10-03','2027-04-06'],reabiertos:['2026-10-12','2026-12-25','2026-10-04']},
];
const __esc=[];
[['2026-09-30',0],['2026-09-30',1],['2026-12-28',1],['2027-04-01',0],['2026-10-13',1]].forEach(function(e){
  __fijar(e[0]);DB={procesos:[],actuaciones:[]};seed();ensureDefaults();
  DB.config.calendario=JSON.parse(JSON.stringify(__CALS[e[1]]));
  DB.procesos[1].situacion='Suspendido';
  DB.actuaciones=DB.actuaciones.concat(__extras(DB.procesos[0].id));
  __esc.push({hoy:e[0],calendario:DB.config.calendario,terminos:DB.config.terminos,rutas:DB.config.rutas,
    config:{prefijo:DB.config.prefijo,ciudad:DB.config.ciudad},procesos:DB.procesos,
    acts:DB.actuaciones.map(__snap),
    procs:DB.procesos.map(function(p){const d=procDeriv(p);return {id:p.id,vivas:d.vivas,repD:d.repD,repS:d.repS,enSec:d.enSec,enDes:d.enDes,inact:d.inact,prox:d.prox,diasSin:d.diasSin};}),
    stats:globalStats()});
});
const __cal=__CALS.map(function(c){
  DB.config.calendario=c;
  let habiles='';const d=parse('2026-01-01');const fin=parse('2027-06-30');
  while(d<=fin){habiles+=esHabil(d)?'1':'0';d.setDate(d.getDate()+1);}
  const venc=[];
  ['2026-01-02','2026-03-27','2026-09-11','2026-09-30','2026-10-09','2026-12-18','2027-03-19','2030-12-20'].forEach(function(ini){
    [1,3,5,10,20,30,365].forEach(function(n){[true,false].forEach(function(h){venc.push([ini,n,h,calcVenc(ini,n,h)]);});});});
  return {calendario:c,desde:'2026-01-01',habiles:habiles,venc:venc};
});
const __fechas=[];
(function(){const d=parse('2026-01-01');const fin=parse('2026-12-31');
  while(d<=fin){const s=iso(d);__fechas.push([s,fechaLarga(s),fechaLetras(s)]);d.setDate(d.getDate()+1);}
  ['2000-01-01','2010-10-10','2020-02-20','2030-12-31','2031-01-30','2045-05-16','2099-07-29'].forEach(function(s){__fechas.push([s,fechaLarga(s),fechaLetras(s)]);});})();
globalThis.__out=JSON.stringify({festivos:Array.from(FESTIVOS).sort(),escenarios:__esc,calendario:__cal,fechas:__fechas,sit:SIT,sitBadge:SITBADGE});
`);

const dir = new URL('../tests/golden/', import.meta.url);
const { escenarios, calendario, fechas, festivos, sit, sitBadge } = out;
fs.writeFileSync(new URL('escenarios.json', dir), JSON.stringify({ festivos, sit, sitBadge, escenarios }) + '\n');
fs.writeFileSync(new URL('calendario.json', dir), JSON.stringify({ festivos, casos: calendario }) + '\n');
fs.writeFileSync(new URL('fechas.json', dir), JSON.stringify(fechas) + '\n');
const cods = {};
escenarios.forEach(e => e.acts.forEach(x => { cods[x.codigo] = (cods[x.codigo] || 0) + 1; }));
console.log('escenarios', escenarios.length, 'acts', escenarios[0].acts.length, 'codigos', JSON.stringify(cods));
