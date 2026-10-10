# Instalación de Control de Procesos

Guía para dejar funcionando la aplicación en el despacho: un equipo **servidor**, que guarda la información, y los equipos **cliente**, que se conectan a él por la red local.

## Cómo funciona

- Se usa **el mismo instalador** en todos los equipos. La primera vez que se abre la aplicación, cada equipo pregunta si es servidor o cliente.
- El **servidor** guarda la base de datos y atiende a los demás. Debe estar encendido, con sesión de Windows iniciada y con la aplicación abierta (puede estar minimizada en el icono junto al reloj) mientras se trabaja.
- Los **clientes** no guardan información: todo lo que se registra queda en el servidor.
- Todos los equipos deben estar en la misma red local.

## Requisitos

| | Servidor | Cliente |
|---|---|---|
| Sistema | Windows 10 u 11 de 64 bits | Windows 10 u 11 de 64 bits |
| Microsoft Edge WebView2 | Sí | Sí |
| Permisos de administrador | Para instalar | Para instalar |
| Red | Dirección IP fija en la red local | Conexión a la misma red |

WebView2 viene incluido en Windows 11 y en Windows 10 actualizado. Si falta, el instalador avisa; se descarga gratis en <https://developer.microsoft.com/microsoft-edge/webview2/> (opción *Evergreen Bootstrapper*).

## 1. Obtener el instalador

El archivo se llama `ControlProcesos-Setup-<versión>.exe`. Lo genera quien administra el proyecto, en un equipo Windows, desde la carpeta del código:

```powershell
powershell -ExecutionPolicy Bypass -File packaging\construir.ps1
```

El instalador queda en la carpeta `dist`. Para construirlo se necesitan [uv](https://docs.astral.sh/uv/) e [Inno Setup 6](https://jrsoftware.org/isinfo.php). También se puede generar con el flujo **Windows** de GitHub Actions, que lo deja como archivo descargable.

Copie el instalador a una memoria USB o a una carpeta compartida para llevarlo a cada equipo.

## 2. Instalar el servidor

Elija como servidor un equipo que permanezca encendido durante la jornada.

### 2.1 Preparar el equipo

1. **Dirección IP fija.** Los clientes buscan al servidor por su dirección IP; si cambia, dejan de conectarse. Pida al encargado de la red que le asigne una IP fija (o una reserva en el router).
2. **Red marcada como privada.** En *Configuración → Red e Internet*, la red del despacho debe estar como **Privada**. Si está como *Pública*, Windows bloquea las conexiones de los clientes.
3. **Que no se suspenda.** En *Configuración → Sistema → Inicio/apagado*, ponga la suspensión en **Nunca** mientras el equipo esté conectado.

### 2.2 Ejecutar el instalador

1. Abra `ControlProcesos-Setup-<versión>.exe` y acepte el aviso de permisos de administrador.
2. En la pantalla de tareas adicionales marque:
   - **Crear un acceso directo en el escritorio.**
   - **Permitir conexiones de otros equipos de la red (puerto 8765).** Obligatorio en el servidor.
   - **Iniciar con Windows, en segundo plano.** Recomendado en el servidor.
3. Termine la instalación y deje marcada la opción de abrir la aplicación.

### 2.3 Primer arranque

1. En la pantalla **Configurar este equipo**, elija **Este equipo es el servidor**. Deje el puerto en `8765` y pulse **Usar como servidor**.
2. Aparece **Servidor listo** con la dirección para los clientes, por ejemplo `http://192.168.1.10:8765`. **Anótela**: se necesita en cada cliente.
3. Pulse **Entrar a la aplicación**.
4. En **Primer arranque**, cree la cuenta del administrador: nombre completo, usuario y contraseña de mínimo 8 caracteres. Guarde esa contraseña en un lugar seguro; es la cuenta con acceso total.

> Si cambia el puerto en el paso 1, la regla de firewall que crea el instalador (para el 8765) no sirve. Habrá que abrir a mano el puerto elegido en el Firewall de Windows.

### 2.4 Dejarlo listo para el despacho

Ya dentro de la aplicación, con el usuario administrador:

1. **Crear los usuarios.** *Menú → Configuración del sistema → Usuarios → + Nuevo usuario*. A cada persona se le asigna un rol:

   | Rol | Para qué |
   |---|---|
   | Administrador | Acceso total, incluidos usuarios, roles y restauración de respaldos |
   | Secretario | Gestión completa de procesos y configuración; exporta respaldos |
   | Escribiente | Registra y tramita procesos y actuaciones; genera documentos |
   | Juez | Consulta, notas, edición de actuaciones y documentos |
   | Consulta | Solo lectura |

   Los permisos de cada rol se ajustan en la pestaña **Roles y permisos**.
2. **Datos del juzgado.** Pestaña **Datos del juzgado**: nombre, ciudad, prefijo del radicado y membrete.
3. **Firmantes y plantillas.** Pestaña **Plantillas y firma**.
4. **Respaldo automático.** Pestaña **Respaldos**: verifique que esté activo y ajuste la hora a un momento en que el servidor esté encendido.
5. **Traer la información anterior** (si venían usando el archivo `control_procesos.html`): en ese archivo use *Respaldo → Exportar respaldo (.json)*, y en la aplicación nueva *Menú → Restaurar respaldo* con ese archivo.

### 2.5 Cerrar la ventana no apaga el servidor

Al cerrar la ventana en el servidor, la aplicación queda en el icono junto al reloj y sigue atendiendo a los clientes. Desde ese icono:

- **Abrir**: vuelve a mostrar la ventana.
- **Dirección para los clientes**: recuerda la dirección del servidor.
- **Salir y detener el servidor**: cierra del todo. Los clientes quedan sin conexión hasta que se abra de nuevo.

## 3. Instalar un cliente

Repita estos pasos en cada equipo que vaya a usar la aplicación.

1. Abra `ControlProcesos-Setup-<versión>.exe`.
2. En tareas adicionales marque solo **Crear un acceso directo en el escritorio**. No marque las opciones de *Equipo servidor*.
3. Al abrir la aplicación, en **Configurar este equipo** elija **Este equipo es un cliente**.
4. Escriba la dirección del servidor que anotó. Basta con la IP, por ejemplo `192.168.1.10`.
5. Pulse **Probar conexión**. Debe decir *Conexión correcta*. Luego pulse **Conectar**.
6. Ingrese con el usuario y la contraseña que le creó el administrador.

El equipo recuerda la dirección: las siguientes veces abre directo en la pantalla de ingreso.

## 4. Comprobar que todo quedó bien

1. En el servidor, ingrese y cree un proceso de prueba.
2. En un cliente, ingrese con otro usuario y verifique que el proceso aparece.
3. Desde el cliente agregue una actuación; en el servidor debe verse en menos de 30 segundos.
4. Genere una constancia y confirme que se abre el diálogo de impresión.
5. En *Configuración → Respaldos*, pulse **+ Crear respaldo ahora** y confirme que aparece en la lista.

## 5. Dónde queda la información

| Qué | Dónde | En qué equipo |
|---|---|---|
| Base de datos | `C:\ProgramData\ControlProcesos\control_procesos.db` | Servidor |
| Respaldos automáticos | `C:\ProgramData\ControlProcesos\backups\` | Servidor |
| Modo del equipo (servidor o cliente) | `%APPDATA%\ControlProcesos\config.json` | Cada equipo |
| Registro de errores | `%APPDATA%\ControlProcesos\logs\control_procesos.log` | Cada equipo |

Los respaldos automáticos quedan en el mismo disco del servidor. Copie periódicamente un respaldo a otro lugar (*Menú → Exportar respaldo*), porque si el disco falla se pierden ambos. El archivo de respaldo incluye los accesos cifrados de los usuarios: guárdelo con cuidado.

## 6. Actualizar a una versión nueva

1. Pida a todos que cierren la aplicación.
2. En el servidor, exporte un respaldo. Luego use **Salir y detener el servidor** en el icono junto al reloj.
3. Ejecute el instalador nuevo en el servidor y después en cada cliente. Se instala encima de la versión anterior.
4. Abra primero el servidor: la base de datos se actualiza sola.

La información y la configuración de cada equipo se conservan.

Instale la misma versión en el servidor y en todos los clientes. Un respaldo exportado con una versión nueva no se puede restaurar en una anterior (por ejemplo, uno de la 1.2 en la 1.1): el programa lo rechaza con el aviso *"El respaldo fue creado con una versión más nueva del programa"*. Por eso conviene guardar el respaldo del paso 2, hecho con la versión anterior, por si hubiera que volver atrás.

## 7. Cambiar de equipo servidor

1. En el servidor actual: *Menú → Exportar respaldo*.
2. Instale el nuevo servidor siguiendo la sección 2 y cree un administrador provisional.
3. En el nuevo servidor: *Menú → Restaurar respaldo*, elija el archivo y marque **Restaurar también usuarios y roles**. Se cerrará la sesión; ingrese con los usuarios de siempre.
4. En cada cliente: *Menú → Cambiar modo servidor / cliente*, cierre y abra la aplicación, y escriba la nueva dirección.

## 8. Solución de problemas

**El cliente dice "No se pudo conectar con el servidor".**
- El servidor debe estar encendido y con la aplicación abierta (ventana o icono junto al reloj).
- Verifique la dirección. En el servidor, el icono junto al reloj muestra la correcta.
- En el servidor, la red debe estar como **Privada** y el instalador debió ejecutarse con la opción de permitir conexiones. Si no se marcó, vuelva a ejecutar el instalador y márquela.
- Desde el cliente, abra un navegador en `http://IP-del-servidor:8765/api/health`. Si responde `{"status":"ok"}`, la red está bien y el problema es la dirección escrita en la aplicación.

**"El puerto 8765 está ocupado por otro programa".**
Otro programa usa ese puerto. Elija otro (por ejemplo `8770`), abra ese puerto en el Firewall de Windows y use la nueva dirección en los clientes.

**El equipo quedó configurado en el modo equivocado, o cambió la dirección del servidor.**
*Menú → Cambiar modo servidor / cliente*, cierre y vuelva a abrir. Si no logra entrar al menú, ejecute `ControlProcesos.exe --reconfigurar` desde la carpeta de instalación (`C:\Program Files\ControlProcesos`). Los datos no se borran.

**La ventana abre en blanco.**
Falta WebView2. Instálelo desde el enlace de la sección de requisitos.

**Un usuario olvidó la contraseña.**
Un administrador la cambia en *Configuración → Usuarios → Editar*. Tras 5 intentos fallidos, el ingreso de ese usuario se bloquea 5 minutos.

**Se perdió la contraseña del único administrador.**
No hay recuperación desde la aplicación. Consérvela en un lugar seguro y, de ser posible, cree un segundo usuario administrador.

**Cualquier otro error.**
Envíe a soporte el archivo `control_procesos.log` del equipo donde ocurrió (ubicación en la sección 5).

## 9. Desinstalar

*Configuración de Windows → Aplicaciones → Control de Procesos → Desinstalar*. Se quita el programa y la regla de firewall.

La base de datos y los respaldos de `C:\ProgramData\ControlProcesos` **no se borran**. Para eliminarlos definitivamente, exporte antes un respaldo y borre esa carpeta a mano.
