NIKKE MOD MANAGER v0.13 CLASSIC R2
==================================

OBJETIVO DE ESTA REVISION
-------------------------
Primero hacer funcionar bien los mods normales.
Los mods 3DMigoto se dejan para la siguiente etapa.

BASE
----
Se instala SOBRE NIKKE Mod Manager v0.11 Preview Alpha.
No reemplaza la interfaz antigua por el manager Tkinter de las pruebas anteriores.

QUE CAMBIA
----------
- Conserva la interfaz de v0.11.
- Conserva el mismo modal "Preview Alpha".
- Cuando el mod es normal, intenta extraer .skel + .atlas + texturas del bundle Unity/NKAB.
- Si el set Spine es valido, reemplaza SOLO el area de la textura por el personaje ya armado.
- Intenta reproducir automaticamente una animacion idle/aim/cover apropiada.
- Incluye selector de animacion, pausa, ajustar, zoom y boton para volver a ver la textura Alpha.
- Si no logra montar el personaje, no rompe el modal: mantiene la textura original.
- No abre viewer, iframe ni pagina localhost aparte.
- 3DMigoto no se modifica en R2.
- "NIKKE Mod Library" pasa a mostrarse como "NIKKE Mod Manager".
- Los controles para administrar imagenes se ocultan del Manager; esa tarea queda para la app Admin.

INSTALACION
-----------
1. Usa tu carpeta de NIKKE Mod Manager v0.11 Preview Alpha.
2. Si es una carpeta nueva, ejecuta una vez INSTALAR_Y_ABRIR.bat y cierra el Manager.
3. Ejecuta INSTALAR_ACTUALIZACION_v0_13_R2.bat.
4. Selecciona la carpeta de v0.11.
5. Luego abre INSTALAR_Y_ABRIR.bat como siempre.

PRIMERA PRUEBA RECOMENDADA
--------------------------
Summer Anis Nude (normal, no 3DMigoto).
Abre el Preview Alpha: primero debe verse la textura habitual mientras prepara el mod y,
si el bundle contiene el set Spine completo, la misma zona debe cambiar al personaje armado.

NOTA
----
El motor auxiliar solo entrega los assets al mismo modal del Manager. No tiene una interfaz
web propia en esta revision. Se auto-cierra pocos segundos despues de que deja de recibir el
heartbeat del Manager.
