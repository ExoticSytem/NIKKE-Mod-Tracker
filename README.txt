NIKKE MOD MANAGER v0.13 FULL — Preview & Demo
================================================

Esta es una instalación completa. Extrae el ZIP en una carpeta nueva y ejecuta:

    INSTALAR_Y_ABRIR.bat

CAMBIOS PRINCIPALES
-------------------
- Nombre unificado: NIKKE Mod Manager.
- La administración/agregado de imágenes de personajes ya no forma parte del Manager.
  Esa función queda reservada para la aplicación NIKKE Admin separada.
- Nuevo Preview & Demo v0.13.
- Los mods detectados como 3DMigoto intentan primero reconstruirse como Spine/Unity.
- Si UnityPy devuelve "Invalid version string", v0.13 intenta reparar únicamente en
  memoria la cadena inválida y vuelve a cargar el bundle. Nunca modifica el mod original.
- Si no es posible reconstruir el personaje, las texturas se muestran claramente como
  VISTA TÉCNICA DE RESPALDO, no como preview final.
- Demo Idle: busca Idle / Standing / Wait.
- Demo Acción: busca Attack / Skill / Burst / Fire / Action.
- Demo Auto: recorre automáticamente animaciones reales detectadas en el mod.
- Continúan disponibles Pausa, Loop, selector de animación, zoom, arrastre, Reset y
  las variantes Standing / Aim / Cover cuando existen.
- Caché nueva .nikke_preview_v013_cache para no reutilizar previews de v0.12.

3DMIGOTO — CASOS DE PRUEBA PRIORITARIOS
---------------------------------------
La lógica nueva está pensada especialmente para los casos reportados en D: Killer Wife,
Milk Blooming Bunny, Nayuta, Ade Agent Bunny, Crown Glorious Flower y Bay.

NOTA IMPORTANTE
---------------
No todos los mods 3DMigoto contienen un set Spine reproducible. Cuando el mod solo trae
texturas o datos de sustitución, el Manager puede mostrar una vista técnica pero no puede
inventar una animación que no exista dentro del mod.

La reparación de versiones Unity es conservadora: solo se aplica sobre una copia en
memoria durante el preview. Los archivos originales permanecen intactos.
