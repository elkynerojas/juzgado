---
Para: el personal del juzgado que usa Control de Procesos a diario
Versión: 1.2
---

# Manual operativo — Control de Procesos

Este es el texto fuente del manual. De aquí se genera el PDF que abre el menú **Ayuda → Manual de usuario**
(`app/web/ayuda/Manual_de_usuario_Control_de_Procesos.pdf`), que además lleva las capturas de pantalla.
Al cambiar algo en la aplicación, se corrige aquí primero.

---

## 1. ¿Qué es este sistema y para qué sirve?

Es el libro de control del juzgado. Reemplaza el cuaderno de registros y las hojas de cálculo sueltas: en un
solo lugar quedan los procesos, lo que está pendiente en cada uno, las audiencias y los números que exige la
estadística trimestral.

Tres ideas sostienen todo lo demás:

1. **El proceso** es el expediente: su radicado, sus partes, su naturaleza.
2. **La actuación** es cada cosa que hay que hacer o que ya se hizo dentro del proceso. Un proceso tiene
   muchas actuaciones, repartidas en cuadernos.
3. **Nada se calcula a mano.** Las fechas de vencimiento, la firmeza de una providencia y los conteos del
   SIERJU los calcula el sistema con el calendario judicial cargado. Si un número no cuadra, se corrige el
   dato de origen, no el número.

El sistema no decide: propone. Toda fecha que pone sola se puede cambiar.

## 2. Palabras clave, en cristiano

| Palabra | Qué significa aquí |
|---|---|
| **Cuaderno** | Un frente del expediente: Principal, Medidas cautelares, Incidente de desacato 1… Cada incidente va en su propio cuaderno numerado. |
| **Materia** | La categoría amplia de la actuación. Sirve para trabajar por paquetes: todas las liquidaciones el mismo día. |
| **Compuerta de secretaría** | Los tres pasos por los que pasa un memorial: constancia, decisión de pasar al despacho, y pase. |
| **Término** | Los días que corren. El sistema sabe si son hábiles o calendario y descuenta festivos, suspensiones y días cerrados. |
| **Ejecutoria** | La fecha en que una providencia queda en firme. Se cuenta desde la notificación, y un recurso sin resolver la suspende. |
| **Tipo SIERJU** | La fila del formato oficial a la que pertenece el proceso: el asunto en civil y familia, el delito en penal, el derecho invocado en tutela. |
| **Vía** | Oral o escrito. Cambia la columna del formato en providencias y recursos. |
| **Forma de salida** | Cómo terminó el proceso. Es lo que alimenta la columna de salidas de la estadística. |

## 3. Registrar un proceso

Botón **+ Proceso**. El formulario cambia según la **naturaleza**, así que esa es la primera casilla a llenar.

- **Civil y familia.** Radicado, clase o asunto, partes y fecha de radicación. El **tipo SIERJU** se sugiere
  solo a partir de la clase; conviene revisarlo porque es lo que después se reporta.
- **Penal.** Se elige el procedimiento (control de garantías o conocimiento) y luego el **delito**: de ahí el
  sistema deduce la ley (906 o 1826). En penal la clase del proceso *es* el delito, así que esa casilla
  desaparece. Se registra el **CUI** (número de noticia criminal) y, si hay más de un delito, se agregan como
  delitos adicionales; la estadística cuenta el principal.
- **Control de garantías.** Se agrega **una fila por solicitud**. Cada solicitud entra y sale por separado en
  la estadística, aunque todas se radiquen juntas y compartan una sola audiencia. Por eso en garantías la
  forma de salida del proceso no aparece: la salida se registra en cada solicitud.
- **Tutela.** Se marca si se concedió medida provisional, si se impugnó el fallo y qué decidió la segunda
  instancia.
- **Incidente de desacato.** Se anota el radicado de la tutela de origen, la fecha del requerimiento previo y
  las decisiones de apertura y de consulta. El derecho debe ser el mismo de la tutela.

Al guardar, el sistema hace tres cosas solo:

1. Si marcó la casilla, **crea la actuación con que arranca el expediente** usando la fecha de radicación, y
   calcula la fecha de gestión secretarial y el pase según el calendario. En tutela y desacato le pone el
   término de 10 días hábiles.
2. En **garantías** crea la actuación de radicación de las solicitudes, una sola para todas.
3. Si marcó Terminado o Archivado sin poner la fecha, pone la de hoy.

Si deja un borrador a medias y cierra el formulario, al volver a abrirlo aparece una barra para recuperarlo.

## 4. Registrar una actuación: las tres fases

El formulario está dividido para que se llene en el orden en que pasan las cosas.

**① Ingreso.** Cuaderno, tipo de gestión, origen, descripción y la compuerta de secretaría. Al guardar, si
puso la fecha del memorial, el sistema **pone la constancia en el mismo día si es hábil, o en el siguiente
hábil**, y hace lo mismo con el pase cuando dijo que pasa al despacho. El cuadro de abajo avisa qué fechas va
a llenar, para no digitarlas dos veces.

**② Cierre.** Fecha de la providencia y su **tipo**: solo los autos interlocutorios, las sentencias y las
medidas cautelares cuentan como providencias en la estadística. Luego la notificación y los días de
ejecutoria; el cuadro muestra cuándo queda en firme. Si hubo recurso, se registra y la ejecutoria queda
**suspendida** hasta que el superior decida.

**📅 Audiencia.** Si esta actuación o providencia fija una audiencia, se marca la casilla y se llenan fecha,
hora y clase. El estado arranca en Programada; la **causa** solo se pide cuando la audiencia se aplaza o se
cancela, y la lista que aparece es exactamente la del formato oficial.

**⚙️ Opciones avanzadas.** Término, suspensión del proceso, trámite posterior y responsable. Está plegado
porque la mayoría de las actuaciones no lo necesita.

## 5. Audiencias

La pestaña **Audiencias** reúne todo lo que está fijado. Una audiencia puede nacer de tres formas:

- como **consecuencia de una providencia** (marcando la casilla en la actuación),
- de forma **directa**, con el botón **+ Audiencia** del proceso o del panel,
- **dentro de otra audiencia**: al registrar el resultado se fija la siguiente.

Cuando llega la fecha y nadie ha dicho qué pasó, la audiencia aparece arriba en **«por confirmar»**, y la
pestaña muestra un contador rojo. Esa lista no debería quedar con nada al cerrar el trimestre: lo que siga
ahí no se cuenta como realizada ni como aplazada.

Al resolver se elige entre **se realizó**, **aplazada**, **suspendida** y **no se realizó**. Si en la
diligencia se fijó otra fecha, se anota ahí mismo: si la audiencia se aplazó o se suspendió, la nueva queda
como **reprogramación**; en cualquier otro caso, como audiencia nueva.

## 6. Recursos y firmeza

Una providencia queda en firme pasados los días de ejecutoria contados desde la notificación. Pero si se
interpone un recurso, la firmeza se detiene:

- mientras el superior no decida, la ejecutoria aparece **suspendida**;
- si la decisión del superior se impugna, sigue suspendida hasta que esa impugnación se resuelva;
- resueltos todos los medios de impugnación, la fecha de firmeza es la de la última decisión.

El sistema no deja la fecha de ejecutoria puesta mientras haya un recurso pendiente, justamente para que no
se cuente un término que todavía no corre.

## 7. Cómo se arma la estadística SIERJU

La estadística **no se digita**: se deriva de los procesos y las actuaciones del periodo. Cada dato se ubica
en una celda del formato oficial —una sección, una fila y una columna— y la pestaña **Estadística** muestra
cuántos datos cayó en cada sección.

Qué alimenta qué:

| Lo que usted registra | A dónde va |
|---|---|
| Fecha de radicación y forma de entrada | Entradas del movimiento de procesos |
| Cada solicitud de garantías | Entradas y salidas, una por solicitud |
| Fecha de terminación y forma de salida | Salidas |
| Fecha de archivo | Procesos archivados |
| Providencia con su tipo | Providencias, por naturaleza y vía |
| Audiencia con su estado y causa | Audiencias civiles o penales |
| Recurso interpuesto y decisión del superior | Recursos interpuestos y decididos |
| Remate realizado y amparo de pobreza | Actuaciones especiales |
| Trámite posterior | Las dos secciones de trámite posterior |
| Procesos abiertos al inicio y al final | Inventarios |

**El panel de avisos es lo más importante de esta pantalla.** Lista los datos que el sistema no pudo
clasificar, casi siempre porque falta el tipo SIERJU o la forma de salida. Esos datos **no llegan al formato**
hasta que se corrija el proceso. Conviene dejarlo en cero antes de reportar.

Lo que no nace de ninguna actuación —caracterización de las partes, turnos de disponibilidad, variables
especiales— se registra con **+ Dato especial**, eligiendo la sección, la fila y la columna oficiales.

## 8. Exportar el Excel oficial

Tres descargas, todas sobre el periodo elegido:

- **Excel oficial.** Llena la plantilla del Consejo Superior **conservando su formato**: encabezados, estilos
  y fórmulas quedan intactos; solo se escriben las celdas de datos, y las que llevan un conteo quedan
  sombreadas. Es el archivo que se reporta.
- **Excel completo.** Un libro propio con una hoja por sección. Sirve para revisar los números con calma,
  sin la rigidez de la plantilla.
- **Bitácora (CSV).** Una línea por dato contado, con el radicado del que salió. Es la forma de responder
  «¿de dónde viene este número?».

Los atajos de trimestre llenan el rango con el periodo que se reporta. Si al generar el Excel oficial queda
alguna columna sin lugar en la plantilla, el sistema lo avisa en vez de descartarla en silencio.

## 9. Respaldo, borradores y seguridad de la información

- **Respaldo.** Menú → *Exportar respaldo*. Es un solo archivo `.json` con todo: procesos, actuaciones,
  configuración, plantillas y datos estadísticos. El equipo servidor además guarda un respaldo automático
  diario y conserva los últimos treinta.
- **Antes de restaurar**, el sistema guarda solo un respaldo del estado actual. Restaurar reemplaza todo.
- **Borradores.** Los formularios de proceso y de actuación se van guardando mientras se escribe, en el
  equipo y bajo el usuario que está trabajando. Si se cierra el formulario sin guardar, al volver se ofrece
  recuperar el borrador.
- **Usuarios y permisos.** Cada persona entra con su usuario. El rol define qué puede ver y qué puede
  cambiar, y toda edición queda en la auditoría con el antes y el después.
- **Personal y cargos** es un catálogo aparte de los usuarios: ahí va quien trabaja en el juzgado, aunque no
  entre a la aplicación, para poder asignarle actuaciones y audiencias.

## 10. Preguntas frecuentes

**Puse una fecha y el sistema la cambió.**
No la cambió: llenó una que estaba vacía. La constancia y el pase se corren al siguiente día hábil, y la
ejecutoria se calcula desde la notificación. Cualquiera de esas fechas se puede editar después.

**Una actuación no aparece en «Gestión por paquetes».**
Esa pantalla solo muestra lo que está pendiente de cierre. Si la actuación ya tiene fecha de cumplida, salió
de la lista.

**La estadística muestra una sección en cero y no debería.**
Revise el panel de avisos. Lo más común es que al proceso le falte el tipo SIERJU o la forma de salida.

**Cambié el nombre de un término o borré una materia del catálogo y las actuaciones viejas siguen igual.**
Es a propósito. Cuaderno, materia, tipo y término se guardan como texto en cada actuación, para que tocar un
catálogo no altere lo ya registrado.

**Dos personas editaron lo mismo al tiempo.**
La segunda recibe un aviso y la pantalla se recarga con lo que quedó guardado. No se pierde nada sin avisar.

**El proceso de garantías no me deja guardar.**
Necesita al menos una solicitud. Y si una solicitud tiene salida, necesita su fecha; si la salida es «otras
salidas no efectivas», necesita el motivo.

**¿Por qué no puedo elegir «Penal» a secas?**
Porque el formato distingue la ley y el procedimiento. Al elegir el procedimiento y el delito, el sistema
compone la naturaleza completa (por ejemplo, *Penal 906 - Garantías*).
