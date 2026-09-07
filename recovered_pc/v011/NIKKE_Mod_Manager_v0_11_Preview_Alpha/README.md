# NIKKE Mod Library v0.11 Preview Alpha


Inventario local de mods de NIKKE para Windows. No activa ni desactiva mods: escanea la carpeta que uses con tu activador externo.


## Novedad v0.11 — Preview Alpha

- Se agregó el botón **👁 Vista previa** junto a cada mod, también dentro de Conflictos y en la ficha de cada personaje.
- Esta primera versión abre el archivo real del mod, detecta el contenedor **NKAB v1/v2**, lo descifra localmente y usa **UnityPy** para extraer la textura `Texture2D` del bundle.
- El preview se guarda en caché local para que la segunda apertura sea rápida.
- Si el mod está en una carpeta, la app prueba automáticamente los archivos internos hasta encontrar un bundle compatible. También admite `.zip`.
- **RAR/7Z todavía no se previsualizan directamente** en esta alpha.
- Importante: por ahora se muestra la **textura/atlas real del mod**, no la animación ensamblada. Esta versión sirve para comprobar compatibilidad y extracción antes de desarrollar nuestro renderer animado propio.
- No usa el visualizador ni la clave/token de otro Mod Manager y no ejecuta ningún archivo del mod.

Para probarlo, abre un mod desde **Mods**, **Conflictos** o la ficha del personaje y pulsa **👁**. Si un mod falla, conserva el mensaje de error: nos servirá para ampliar compatibilidad en la siguiente versión.


## Novedades v0.8

- La clasificación **NPC / Extra** ya no se puede editar por jugador. Se mantiene centralmente en el repositorio público del proyecto.
- Al pulsar **Actualizar**, Windows descarga las correcciones publicadas por el dueño/admin y aplica de inmediato la regla NPC = solo Standing.
- Las imágenes globales se leen primero desde `assets/characters/manifest.json`; una imagen subida por el admin al repositorio pasa a todos los clientes al actualizar.
- Prydwen y Nikke-DB continúan como respaldo cuando el proyecto todavía no tiene una imagen propia.
- Las etiquetas siguen siendo personales y se sincronizan entre PC y Android.

## Administración central

El dueño del proyecto puede cambiar una clasificación desde GitHub Actions → **Admin - Character classification** usando la clave `ID_Ver` (por ejemplo `472_00`). Para publicar una imagen global, basta subir `c<ID>_<VER>.png` a `assets/characters/manual/`; el manifiesto se regenera automáticamente.

## Créditos / Credits

**ES:** Este proyecto nació rápidamente porque se hacía incómodo recordar qué mods estaban instalados, cuáles estaban duplicados y qué skin/acción afectaba cada uno. La idea y parte de la inspiración visual y de flujo vienen de **BD2ModManager de bruhnn** para Brown Dust 2. Todo el crédito para ese proyecto por la inspiración. NIKKE Mod Library/Tracker fue desarrollado con ayuda de IA y se comparte por si también le resulta útil a otros jugadores.

**EN:** This project started as a quick solution because keeping track of installed mods, duplicates, and the skin/action affected by each mod was getting inconvenient. The idea and part of the UI/workflow inspiration came from **bruhnn's BD2ModManager** for Brown Dust 2. Full credit to that project for the inspiration. NIKKE Mod Library/Tracker was developed with AI assistance and is shared in case other players find it useful too.

BD2ModManager: https://github.com/bruhnn/BD2ModManager

## Novedades v0.6

- Sincronización directa con **NIKKE Mod Tracker Android v0.2** por la misma red Wi‑Fi.
- El PC sigue siendo la fuente real del inventario: envía al móvil personaje/skin, Aim/Cover/Standing, nombre del mod, autor detectado y conflictos.
- Las **etiquetas se sincronizan en ambos sentidos**. Si agregas o quitas una etiqueta en Android, el cambio vuelve al PC en la próxima sincronización; y viceversa.
- No hay cuentas, nube ni base de datos central. La conexión está protegida por un token aleatorio incluido en el QR.
- En Configuración aparece un QR. Escanéalo con la cámara del teléfono para vincular el APK.

## Uso

1. Ejecuta `INSTALAR_Y_ABRIR.bat` la primera vez.
2. Selecciona tu carpeta de mods y escanéala.
3. En **Configuración → Sincronización con Android**, abre el APK en el teléfono y escanea el QR con la cámara.
4. PC y teléfono deben estar en la misma Wi‑Fi al sincronizar. Windows puede pedir permiso de firewall la primera vez; permite acceso en redes privadas.

La app solo expone por la red local un resumen del inventario, nunca los archivos del mod.


## v0.9
- Primer inicio: selección Español / English.
- En PC se solicita inmediatamente la carpeta de mods.
- La clasificación NPC / Extra es central y no editable por jugadores.
- Las imágenes globales se administran con la herramienta separada NIKKE Admin.
- La app mantiene la detección automática de nuevos ID + Ver desde Nikke-DB.


## v0.10
- En el primer inicio pregunta **Español / English** y luego solicita la carpeta de mods.
- Cada instalación genera su propio token aleatorio para sincronización local con Android.
- Los personajes detectados automáticamente quedan **pendientes** y no aparecen a jugadores hasta ser aprobados por el administrador.
- Los candidatos marcados **Descartado** por el administrador permanecen ocultos aunque vuelvan a aparecer en la fuente externa.
- Las clasificaciones NPC / Extra publicadas por el administrador se aplican a todos al pulsar **Actualizar**.
