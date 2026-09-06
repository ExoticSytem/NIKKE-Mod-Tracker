NIKKE MOD MANAGER v0.12 PREVIEW BETA — FULL TEST BUILD
======================================================

ESTA ES UNA CARPETA COMPLETA.
No necesitas instalar v0.10 ni v0.11 antes y no tienes que ejecutar ningun actualizador.

USO
---
1. Extrae TODO el ZIP en una carpeta normal de Windows.
2. Ejecuta INSTALAR_Y_ABRIR.bat.
3. La primera vez eliges Español o English.
4. Selecciona la carpeta donde estan tus mods de NIKKE.
5. Entra a un personaje y pulsa "Vista previa" en cualquiera de sus mods.

PREVIEW BETA
------------
- Mods Unity/NKAB: intenta extraer .atlas + .skel + textura(s), detectar Spine 4.0/4.1 y abrir el viewer Beta.
- Busca automaticamente variantes Standing / Aim / Cover relacionadas en la misma carpeta.
- Mods 3DMigoto: se detectan antes de UnityPy para evitar el error "Invalid version string". Esta ruta sigue siendo experimental.
- El renderer/preview sigue en fase Beta: algunos mods pueden no reconstruirse o animarse correctamente todavia.

MANAGER
-------
- Catalogo completo por ID + Ver.
- Con mods / Sin mods / Conflictos / NPC-Extra.
- Conflicto = 2 o mas mods diferentes para el mismo ID + Ver + action.
- Aim / Cover / Standing.
- Etiquetas y notas guardadas localmente en la carpeta data/.
- Imagenes del repositorio publico de NIKKE Mod Tracker.
- Actualizar vuelve a escanear la carpeta y consulta el catalogo publico; si no hay Internet usa la copia local incluida.

PRIMER INICIO
-------------
INSTALAR_Y_ABRIR.bat crea un entorno Python local .venv e instala solo las dependencias del preview:
- UnityPy
- Pillow
- cryptography

Necesita Python 3 instalado en Windows. La configuracion y tus notas se guardan localmente; no se suben al repositorio.

IMPORTANTE
----------
Este paquete FULL se preparo especificamente para probar Preview Beta sin depender de una version anterior.
El sistema Android/sincronizacion movil no forma parte de esta compilacion de prueba del renderer; no cambia tu APK actual.

CREDITOS
--------
Proyecto personal creado con ayuda de IA.
La idea/interfaz y parte del flujo fueron inspirados por BD2ModManager de bruhnn para Brown Dust 2. Todo el credito a ese proyecto por la inspiracion.
NIKKE y sus personajes/recursos pertenecen a sus respectivos propietarios.
