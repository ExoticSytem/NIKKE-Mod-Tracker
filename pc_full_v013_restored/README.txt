NIKKE MOD MANAGER v0.13 - RESTORED NATIVE PREVIEW
=================================================

Esta version restaura el funcionamiento anterior del preview:

- El Manager sigue siendo la aplicacion de escritorio nativa.
- Vista previa abre una ventana dentro de la aplicacion, NO el navegador.
- No se muestra localhost ni una pagina HTML al usuario.
- Se conserva el diseno del Manager v0.12.
- El motor v0.12 se reutiliza solo internamente para leer NKAB/Unity y 3DMigoto.
- Spine/Unity: extrae las texturas reales del mod y las muestra en la ventana nativa.
- 3DMigoto: muestra las texturas detectadas sin intentar tratarlo como AssetBundle.
- Standing / Aim / Cover relacionados pueden cambiarse desde la misma ventana cuando existen.
- Zoom con rueda o botones +/-, arrastre con el mouse y Ajustar para centrar.

INSTALACION
-----------
1. Extrae la carpeta completa.
2. Ejecuta INSTALAR_Y_ABRIR.bat.
3. La primera vez puede instalar UnityPy, Pillow, cryptography y send2trash.
4. Selecciona tu carpeta de mods si el Manager lo solicita.
5. Selecciona un mod y pulsa Vista previa.

NOTA
----
Esta version prioriza recuperar el preview nativo que funcionaba antes. El ensamblado/animacion Spine completo no se abre en una pagina web en esta build; primero se restaura una vista previa estable y local de las texturas reales del mod.
