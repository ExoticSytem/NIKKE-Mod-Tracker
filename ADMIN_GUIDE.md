# Administración central / Central administration

Los jugadores no cambian la clasificación NPC / Extra desde Android ni Windows. La clasificación compartida se controla desde este repositorio y se aplica al actualizar.

## Cambiar NPC / Extra

Ruta rápida para el dueño/colaboradores con permisos de escritura:

1. Abre **Actions**.
2. Ejecuta **Admin - Character classification**.
3. Escribe la clave `ID_Ver`, por ejemplo `472_00`.
4. Elige:
   - `npc_extra` → solo Standing.
   - `playable` → Aim, Cover y Standing.
   - `auto` → elimina el override y vuelve a la clasificación base.
5. Ejecuta el workflow. El cambio queda en `admin/catalog_overrides.json` y los clientes lo reciben al pulsar **Actualizar**.

## Agregar o reemplazar una imagen global

1. Entra a `assets/characters/manual/`.
2. Pulsa **Add file → Upload files**.
3. Sube la imagen con nombre `c<ID>_<VER>.png` (también `.webp`, `.jpg` o `.jpeg`).
   - `c010_00.png`
   - `c016_02.png`
   - `c9004_00.png`
4. Haz commit.
5. GitHub Actions regenera `assets/characters/manifest.json` automáticamente.
6. Los clientes reciben la imagen al pulsar **Actualizar**.

Las imágenes de `manual/` tienen prioridad sobre cualquier fuente externa. Solo usuarios con permisos de escritura del repositorio pueden cambiar estos datos globales.

> Usa imágenes propias o que tengas permiso para redistribuir. El proyecto puede enlazar recursos externos como fallback, pero no conviene copiar en masa artwork de terceros sin permiso claro.

---

# Central administration

Players cannot change NPC / Extra classification from Android or Windows. Shared classification is controlled by this repository and picked up on refresh.

## Change NPC / Extra

1. Open **Actions**.
2. Run **Admin - Character classification**.
3. Enter the `ID_Ver` key, e.g. `472_00`.
4. Choose `npc_extra`, `playable`, or `auto`.
5. Run the workflow. The change is stored in `admin/catalog_overrides.json` and clients receive it when they press **Refresh**.

## Add or replace a global image

Upload an image to `assets/characters/manual/` using the filename `c<ID>_<VER>.png` (or `.webp/.jpg/.jpeg`) and commit it. The manifest is rebuilt automatically and clients pick it up on **Refresh**.
