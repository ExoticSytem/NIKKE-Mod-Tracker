# NIKKE Mod Tracker

Aplicación para llevar un inventario de mods de **GODDESS OF VICTORY: NIKKE** por personaje/skin (`ID + Ver`), revisar qué acciones modifica cada mod, detectar duplicados/conflictos y sincronizar la biblioteca entre PC y Android.

## ES — Sobre el proyecto

Hice este proyecto rápido porque se me estaba haciendo incómodo recordar qué mods de NIKKE tenía, detectar cuáles estaban duplicados y revisar qué skin o acción modificaba cada uno. La idea y parte de la inspiración visual y de flujo vienen de [BD2ModManager de bruhnn](https://github.com/bruhnn/BD2ModManager), un excelente mod manager para Brown Dust 2; todo el crédito para ese proyecto por la inspiración. Este NIKKE Mod Tracker nació como un proyecto personal y lo desarrollé con ayuda de IA. No tenía idea de si ya existía algo parecido para NIKKE; si a alguien más le sirve, siéntase libre de usarlo, probarlo y compartir sugerencias.

## EN — About the project

I put this project together quickly because it was getting inconvenient to remember which NIKKE mods I had, spot duplicates, and check which skin or action each mod affected. The idea and part of the visual/workflow inspiration came from [bruhnn's BD2ModManager](https://github.com/bruhnn/BD2ModManager), an excellent Brown Dust 2 mod manager; full credit to that project for the inspiration. NIKKE Mod Tracker started as a personal project and was developed with AI assistance. I did not know whether something similar already existed for NIKKE; if it is useful to anyone else, feel free to use it, test it, and share suggestions.

## Funciones / Features

- Cada combinación `ID + Ver` se trata como una variante independiente.
- Inventario de `Aim`, `Cover` y `Standing` para personajes jugables; NPC / Extra usa solo `Standing`.
- Detección de mods duplicados/conflictos en PC.
- Nombres de mods visibles en Android después de sincronizar.
- Etiquetas compartidas PC ↔ Android.
- Sincronización local mediante Wi‑Fi/QR, sin cuentas ni base de datos central.
- Catálogo e imágenes con caché local y soporte para imágenes curadas por el proyecto.
- La clasificación NPC / Extra es compartida y la mantiene el proyecto; los jugadores no la editan localmente.

## Administración central

Solo el dueño/colaboradores con permiso de escritura del repositorio pueden cambiar datos globales.

- **NPC / Extra:** abre **Actions → Admin - Character classification**, escribe `ID_Ver` (por ejemplo `472_00`) y elige `npc_extra`, `playable` o `auto`.
- **Imagen global:** sube `c<ID>_<VER>.png` (o `.webp/.jpg/.jpeg`) a `assets/characters/manual/`. GitHub Actions regenera el manifiesto automáticamente.
- Android y Windows reciben esos cambios al pulsar **Actualizar**.

Guía completa: [ADMIN_GUIDE.md](./ADMIN_GUIDE.md)

## Imágenes

La aplicación puede usar imágenes externas como fallback y también admite imágenes alojadas por este proyecto. Las imágenes propias/curadas se buscan primero siguiendo la convención:

`assets/characters/manual/c<ID>_<VER>.png`

Ejemplo: `assets/characters/manual/c016_02.png`.

> No se deben copiar masivamente assets de terceros al repositorio sin comprobar antes que su licencia permita redistribuirlos. Los personajes, nombres, imágenes y demás assets de NIKKE pertenecen a sus respectivos titulares.

## APK

El APK se compila automáticamente con GitHub Actions. Ve a **Actions → Build Android APK → Artifacts** para descargar la versión más reciente.

## Créditos / Credits

- **Inspiración / Inspiration:** [bruhnn/BD2ModManager](https://github.com/bruhnn/BD2ModManager) — Brown Dust 2 Mod Manager (GPL-3.0).
- **Referencia de datos/imágenes / Data & image reference:** [Nikke-db/Nikke-db.github.io](https://github.com/Nikke-db/Nikke-db.github.io).
- Desarrollo asistido por IA / Development assisted by AI.
- GODDESS OF VICTORY: NIKKE y sus assets pertenecen a sus respectivos propietarios. Este proyecto no está afiliado con SHIFT UP, Level Infinite ni con los proyectos mencionados arriba.
