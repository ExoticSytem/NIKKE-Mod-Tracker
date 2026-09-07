NIKKE Mod Manager v0.13 Classic
===============================

ESTA ACTUALIZACION ESTA HECHA PARA:
NIKKE Mod Manager v0.11 Preview Alpha.

OBJETIVO
- Conservar la interfaz de v0.11.
- No sustituir el Manager por la interfaz Tkinter nueva de las pruebas v0.12/v0.13.
- No abrir el preview en una pagina HTML/iframe aparte.

CAMBIOS
- El preview mejorado se monta dentro del MISMO modal Preview Alpha.
- 3DMigoto: intento Spine/Unity primero.
- Reparacion en memoria de la cadena de version UnityFS corrupta de ciertos 3DMigoto.
- Si no existe un set Spine completo, muestra una sola textura candidata y permite cambiarla, no un mosaico de assets.
- Demo Idle, Demo Accion y Demo Auto cuando se detectan animaciones Spine.
- Standing/Aim/Cover se pueden cambiar desde el propio preview.
- La gestion de imagenes de personajes queda oculta del Mod Manager. Las imagenes se siguen mostrando; su administracion queda para la futura app Admin.
- Nombre visible cambiado de Mod Library a NIKKE Mod Manager sin redisenar la interfaz.
- El motor auxiliar usa la carpeta TEMP de Windows para su cache y cambia su directorio de trabajo fuera del Manager. Ademas se auto-cierra si deja de recibir el heartbeat del Manager, evitando el problema de tener que cerrar Python desde el Administrador de tareas para borrar la carpeta.

INSTALACION RECOMENDADA
1. Extrae NIKKE Mod Manager v0.11 Preview Alpha en una carpeta limpia.
2. Ejecuta una vez INSTALAR_Y_ABRIR.bat de v0.11 y cierralo.
3. Extrae esta actualizacion en otra carpeta.
4. Ejecuta INSTALAR_ACTUALIZACION_v0_13.bat.
5. Selecciona la carpeta de v0.11 cuando la pida.
6. A partir de ahi abre el Manager con el mismo INSTALAR_Y_ABRIR.bat de siempre.

El actualizador conserva una copia del launcher original como:
INSTALAR_Y_ABRIR_v011_ORIGINAL.bat

Si el preview mejorado no puede montar un mod, dentro del mismo modal puedes pulsar "Usar Alpha" para volver temporalmente al comportamiento original.