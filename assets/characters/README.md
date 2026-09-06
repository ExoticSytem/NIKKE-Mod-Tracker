# Character image library

Esta carpeta contiene imágenes curadas/manuales que NIKKE Mod Tracker puede priorizar antes de consultar fuentes externas.

## Convención

Sube la imagen a:

`assets/characters/manual/c<ID>_<VER>.png`

Ejemplos:

- `c010_00.png` → Rapi 010 / 00
- `c016_02.png` → ID 016 / Ver 02
- `c9004_00.png` → ID 9004 / Ver 00

También se admiten `.webp`, `.jpg` y `.jpeg`, aunque PNG es el formato preferido para los overrides manuales.

## Prioridad usada por la app

1. Imagen manual del propio repositorio.
2. Biblioteca propia/mirror permitido del repositorio, si existe.
3. Fuentes externas configuradas en el catálogo.
4. Placeholder.

El botón **Actualizar** del cliente puede invalidar la caché de imágenes para recoger una imagen manual reemplazada recientemente.

> No subas automáticamente colecciones de terceros sin verificar antes sus permisos/licencia de redistribución.
