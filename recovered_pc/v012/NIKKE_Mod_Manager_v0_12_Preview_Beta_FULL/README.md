# NIKKE Mod Manager v0.12 — Preview Beta FULL

Inventario local de mods de NIKKE para Windows. **No activa ni desactiva mods**: escanea la carpeta que ya usas con tu activador externo.

## Qué incluye esta versión completa

Esta ZIP ya contiene toda la aplicación; **no necesitas instalar primero v0.11 ni aplicar un actualizador**.

- Catálogo de personajes/skins por **ID + Ver**.
- Escaneo de mods y detección Aim / Cover / Standing.
- Conflictos, nombres de mods y autor detectado.
- Etiquetas personales.
- Sincronización local con Android por Wi‑Fi/QR, sin cuentas ni nube.
- Clasificación central NPC / Extra; NPC / Extra usa solo Standing.
- Actualización del catálogo y clasificaciones publicadas.
- Preview Alpha v0.11 conservado como respaldo.
- **Preview Beta v0.12** para probar animaciones Spine y compatibilidad 3DMigoto.

## Preview Beta v0.12

### Unity / NKAB
- Descifra NKAB v1/v2 localmente.
- Extrae `.skel`, `.atlas` y texturas.
- Intenta montar y animar el personaje en un visor Pixi/Spine.
- Standing / Aim / Cover del mismo ID + Ver aparecen como pestañas cuando están juntos.
- Selector de animación, pausa/reanudar, loop, zoom, arrastre y reset.

### 3DMigoto
- Se detecta antes de UnityPy, por lo que no debería caer en `Invalid version string`.
- Por ahora muestra las texturas DDS/PNG detectadas.
- El mesh 3D todavía no se ensambla en esta Beta.

### Internet
La extracción y lectura del mod es local. El renderer Beta carga PixiJS + pixi-spine desde CDN, así que **la vista animada Beta necesita conexión a Internet** en esta prueba.

## Instalación limpia

1. Descomprime la carpeta completa.
2. Ejecuta **`INSTALAR_Y_ABRIR.bat`** la primera vez.
3. Elige Español / English y selecciona tu carpeta de mods.
4. En un mod pulsa **👁 Vista previa** para abrir Preview Alpha.
5. Dentro de esa vista aparecerá **▶ Preview Beta**.

Después puedes abrir normalmente con **`ABRIR.bat`** o **`ABRIR_NIKKE_MOD_MANAGER_v0_12.bat`**.

## Android

El PC continúa siendo la fuente real del inventario. Desde Configuración → Sincronización con Android puedes vincular el tracker por QR en la misma Wi‑Fi. Las etiquetas se sincronizan en ambos sentidos y el móvil conserva el último inventario sincronizado para consultarlo aunque el PC esté apagado.

## Seguridad / alcance

- La app no ejecuta los archivos de los mods.
- La eliminación usa la Papelera de reciclaje, no borrado permanente.
- La sincronización local solo expone un resumen del inventario, no los archivos de los mods.
- No se incluye ni se usa el `.jwe` de NMM V3.28 SWAP.
- No se copia el PreviewEngine de NMM V3.28.

## Créditos

La idea y parte de la inspiración visual/de flujo vienen de **BD2ModManager de bruhnn** para Brown Dust 2. NIKKE Mod Manager/Tracker fue desarrollado con ayuda de IA.

BD2ModManager: https://github.com/bruhnn/BD2ModManager
