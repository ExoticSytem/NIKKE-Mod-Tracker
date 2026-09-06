NIKKE MOD MANAGER v0.12 — PREVIEW BETA
======================================

Esta es una actualización sobre NIKKE Mod Manager v0.11 Preview Alpha.
No borra el Preview Alpha: lo conserva como respaldo y agrega un segundo motor Beta.

INSTALACIÓN
-----------
1. Descomprime este ZIP.
2. Ejecuta ACTUALIZAR_A_V0_12.bat.
3. Selecciona la carpeta donde tienes NIKKE Mod Manager v0.11 si el actualizador no la encuentra solo.
4. Desde entonces abre ABRIR_NIKKE_MOD_MANAGER_v0_12.bat, que quedará creado dentro del Manager.

QUÉ PRUEBA ESTA BETA
--------------------
- Los mods Unity/NKAB se extraen localmente igual que en la Alpha, pero ahora el Beta entrega .skel + .atlas + todas las texturas necesarias a un reproductor Spine/Pixi dentro de la app.
- Intenta montar el personaje y reproducir sus animaciones, en vez de mostrar solo la plancha/atlas.
- Standing, Aim y Cover del mismo ID + Ver se detectan como pestañas cuando los archivos están en la misma carpeta.
- Selector de animación, pausa/reanudar, loop, zoom, arrastre y reset.
- Detecta mods 3DMigoto ANTES de UnityPy. Ya no deberían caer en “Invalid version string”.
- En 3DMigoto esta beta muestra las texturas DDS/PNG y los identifica correctamente. El ensamblado del mesh 3D todavía no está implementado.
- El Preview Alpha original queda intacto. Cuando abras una vista previa aparecerá el botón “▶ Preview Beta”.

IMPORTANTE SOBRE EL RENDERER
----------------------------
Esta beta NO copia el PreviewEngine del NMM V3.28 y NO usa el archivo .jwe del otro instalador.
La extracción es nuestra (UnityPy/NKAB) y la ventana Beta usa PixiJS + pixi-spine 4.0.4 desde CDN para probar compatibilidad con los esqueletos 4.0/4.1 encontrados en NIKKE.
Por eso, para montar la animación Beta hace falta conexión a Internet en esta prueba. Si el enfoque funciona bien con tus mods, la siguiente etapa puede reemplazar/encapsular mejor esa dependencia.

ARCHIVOS DE PRUEBA USADOS PARA DEFINIR LA BETA
-----------------------------------------------
- c015_00_standing_Na0h_Summer-Anis-Nude
- c015_00_aim_Na0h_Summer-Anis-Nude
- c015_00_cover_Na0h_Summer-Anis-Nude
- c043_02_standing / cover 3DMigoto como caso de formato alternativo

SI ALGO FALLA
-------------
Mándame captura de la ventana Preview Beta y, si aparece texto rojo, el mensaje completo.
Los fallos más útiles ahora son:
- modelo totalmente desarmado;
- textura negra/transparentada;
- animación incorrecta;
- “Unsupported version”;
- atlas con varias páginas/texturas;
- 3DMigoto que no sea detectado.
