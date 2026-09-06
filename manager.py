from pathlib import Path

# NIKKE Mod Manager v0.13
# El núcleo de escritorio se conserva desde v0.12 y aquí solo se actualiza
# la identidad/version de la aplicación. La administración de imágenes
# queda fuera de este paquete y pasa a la aplicación Admin separada.
BASE = Path(__file__).resolve().parent
CORE = BASE / "manager_core.py"
if not CORE.is_file():
    raise SystemExit("Falta manager_core.py. Vuelve a extraer el ZIP completo.")

src = CORE.read_text(encoding="utf-8")
replacements = {
    'APP_VERSION = "0.12 Preview Beta"': 'APP_VERSION = "0.13 Preview & Demo"',
    'Preview Beta · v0.12': 'Preview & Demo · v0.13',
    'NIKKE Mod Manager v0.12 Preview Beta': 'NIKKE Mod Manager v0.13 Preview & Demo',
    'NIKKE MOD MANAGER v0.12 PREVIEW BETA': 'NIKKE MOD MANAGER v0.13 PREVIEW & DEMO',
}
for old, new in replacements.items():
    src = src.replace(old, new)

ns = {
    "__name__": "__main__",
    "__file__": str(BASE / "manager.py"),
    "__package__": None,
}
exec(compile(src, str(CORE), "exec"), ns, ns)
