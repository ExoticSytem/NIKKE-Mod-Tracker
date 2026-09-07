# NIKKE Mod Tracker Android v0.1

Aplicación Android complementaria de NIKKE Mod Library. Está pensada para usar el teléfono como inventario/marcador, no como activador de mods.

## Funciones
- Catálogo completo incluido (548 entradas visibles; se omite Placeholder-chan).
- Orden predeterminado por ID + Ver.
- Cada ID + Ver se trata como personaje/skin independiente.
- Marcar Aim / Cover / Standing para entradas normales.
- NPC / Extra: solo Standing.
- Filtros Todos / Con mods / Sin mods / NPC-Extra.
- Etiquetas personalizadas y asignación masiva.
- Corrección manual de NPC/Extra.
- Notas por personaje para guardar nombre del mod, autor, enlace, etc.
- Imágenes remotas con varias fuentes de respaldo.
- Español / English; Aim, Cover y Standing no se traducen.
- Datos persistentes en el teléfono mediante localStorage.

## Compilación
El repositorio incluye `.github/workflows/build-apk.yml`. GitHub Actions compila `app-debug.apk` sin requerir Android Studio en el PC del usuario.
