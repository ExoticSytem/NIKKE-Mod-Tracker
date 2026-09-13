# NIKKE Mod Tracker Android v0.3.0

Companion Android actualizado para NIKKE Mod Manager.

- Catálogo central desde `catalog/admin/characters.json`.
- Imágenes oficiales publicadas por Admin; miniaturas `__card.png` en tarjetas y cuerpo completo en detalle.
- Sincronización LAN con el Mod Manager actual mediante `nikkemodtracker://pair` y protocolo `/v1/sync`.
- Inventario y etiquetas quedan guardados en el teléfono para consulta offline.
- Etiquetas sincronizadas en ambos sentidos por `updated_at`.
- Caché LRU de miniaturas limitado a ~80 MB.
- No se transfieren archivos de mods y no requiere cuentas ni servidor privado.
