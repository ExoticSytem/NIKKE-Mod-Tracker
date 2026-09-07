# Preview Beta v0.12

Esta build completa agrega un segundo motor de vista previa sobre el Preview Alpha de v0.11.

## Unity / NKAB

- Lee y descifra localmente NKAB v1/v2.
- Extrae `.skel`, `.atlas` y las texturas necesarias con UnityPy.
- Intenta montar el personaje con PixiJS + pixi-spine 4.0.4.
- Detecta versiones Spine 4.0/4.1 cuando aparecen en el esqueleto.
- Si Standing, Aim y Cover del mismo ID + Ver están en la misma carpeta, aparecen como pestañas.
- Incluye selector de animación, loop, pausa/reanudar, zoom, arrastre y reset.

## 3DMigoto

- Se detecta antes de intentar UnityPy, evitando el error `Invalid version string` de la Alpha.
- La Beta identifica el mod y muestra las texturas DDS/PNG encontradas.
- El ensamblado del mesh 3D todavía no está implementado.

## Renderer web

Esta Beta usa PixiJS y pixi-spine desde CDN, por lo que el Preview Beta requiere Internet para cargar el runtime web. La extracción del mod sigue ocurriendo localmente.

## Casos usados al preparar v0.12

- Summer Anis: Aim / Cover / Standing.
- D: Killer Wife: caso 3DMigoto.

El Preview Alpha permanece disponible como respaldo.
