# Preview Alpha — notas técnicas

Esta versión agrega una primera vista previa **propia** al NIKKE Mod Library.

## Qué hace v0.11

1. Lee el mod seleccionado sin ejecutarlo.
2. Si detecta el contenedor `NKAB`, intenta abrir v1/v2 localmente.
3. Carga el Unity bundle mediante **UnityPy**.
4. Busca `Texture2D`, `.atlas` y `.skel`.
5. Muestra la textura real de mayor tamaño y algunos metadatos detectados.

Todavía **no reconstruye la animación Spine**. El objetivo de esta alpha es comprobar primero qué tan compatibles son los mods reales de distintos autores con nuestro lector.

## Independencia respecto de otros Mod Managers

- No se incluye ni se llama al visualizador de NMM V3.28 SWAP.
- No se incluye el archivo `.jwe` enviado para estudiar ese programa.
- No se incluye Spine Runtime de terceros.
- No se copia el `PreviewEngine` de otros proyectos.

Durante la investigación se consultó el proyecto público `No1syB0y/NikkeModManager` para entender qué tipos de datos suelen contener los bundles de NIKKE y qué generaciones de Spine aparecen en la comunidad. Su repositorio está publicado con licencia MIT, pero su runtime de Spine tiene condiciones separadas; por eso esta alpha no reutiliza ese renderer.

UnityPy: https://github.com/K0lb3/UnityPy
Referencia de investigación: https://github.com/No1syB0y/NikkeModManager
