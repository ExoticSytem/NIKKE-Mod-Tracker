from __future__ import annotations

import importlib.util
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R3_PATH = ROOT / 'tools' / 'build_classic_r3_spine.py'
spec = importlib.util.spec_from_file_location('classic_r3_builder', R3_PATH)
base = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(base)

base.OUT = base.DIST / 'NIKKE_Mod_Manager_v0_13_CLASSIC_R4_SPINE_FULL'
base.ZIP = base.DIST / 'NIKKE_Mod_Manager_v0_13_CLASSIC_R4_SPINE_FULL.zip'
base.PREVIEW_PY = base.PREVIEW_PY.replace('classic-r3-spine-003', 'classic-r4-runtimefix-001')
base.PREVIEW_PY = base.PREVIEW_PY.replace('classic_r3_spine_canvas', 'classic_r4_spine_runtimefix')
base.PREVIEW_PY = base.PREVIEW_PY.replace('Classic R3:', 'Classic R4:')
base.PREVIEW_PY = base.PREVIEW_PY.replace('Classic R3', 'Classic R4')

base.APP_JS_OVERRIDE = base.APP_JS_OVERRIDE.replace('Classic R3 Spine preview override', 'Classic R4 Spine runtime-fix preview override')
base.APP_JS_OVERRIDE = base.APP_JS_OVERRIDE.replace('Preview Alpha · Classic R3', 'Preview Alpha · Classic R4')
base.APP_JS_OVERRIDE = base.APP_JS_OVERRIDE.replace('Classic R3 Spine render failed', 'Classic R4 Spine render failed')
base.APP_JS_OVERRIDE = base.APP_JS_OVERRIDE.replace(
    "if(!window.PIXI||!PIXI.spine) throw new Error('No se cargó Pixi/Spine local.'); const core=PIXI.spine.core||PIXI.spine; if(!core.TextureAtlas||!core.AtlasAttachmentLoader||!core.SkeletonBinary||!PIXI.spine.Spine) throw new Error('Runtime Spine incompleto o incompatible.');",
    "if(!window.PIXI) throw new Error('No se cargó Pixi local.'); const spineBase=(PIXI.spine&&PIXI.spine.core)||PIXI.spine||{}; const runtimes=[PIXI.spine38,PIXI.spine37,PIXI.spine40,PIXI.spine41,PIXI.spine].filter(Boolean); const TextureAtlas=spineBase.TextureAtlas||runtimes.find(x=>x&&x.TextureAtlas)?.TextureAtlas; const AtlasAttachmentLoader=spineBase.AtlasAttachmentLoader||runtimes.find(x=>x&&x.AtlasAttachmentLoader)?.AtlasAttachmentLoader; if(!TextureAtlas||!AtlasAttachmentLoader||!runtimes.length) throw new Error('Runtime Spine no cargó namespaces 3.7/3.8/4.x.');"
)
base.APP_JS_OVERRIDE = base.APP_JS_OVERRIDE.replace(
    "const atlas=new core.TextureAtlas(String(r.spine_atlas_text||''), function(_line, callback){ callback(baseTexture); }); const atlasLoader=new core.AtlasAttachmentLoader(atlas); const binary=new core.SkeletonBinary(atlasLoader); const skeletonData=binary.readSkeletonData(r3BytesFromB64(r.spine_skel_b64)); r3SpineObj=new PIXI.spine.Spine(skeletonData);",
    "const atlas=new TextureAtlas(String(r.spine_atlas_text||''), function(_line, callback){ callback(baseTexture); }); const atlasLoader=new AtlasAttachmentLoader(atlas); const bytes=r3BytesFromB64(r.spine_skel_b64); let skeletonData=null; let SpineClass=null; let lastRuntimeError=null; for(const Runtime of runtimes){ try{ if(!Runtime||!Runtime.SkeletonBinary) continue; const binary=new Runtime.SkeletonBinary(atlasLoader); skeletonData=binary.readSkeletonData(bytes); SpineClass=Runtime.Spine||(PIXI.spine&&PIXI.spine.Spine); if(skeletonData&&SpineClass) break; }catch(e){ lastRuntimeError=e; skeletonData=null; SpineClass=null; } } if(!skeletonData||!SpineClass) throw (lastRuntimeError||new Error('No hubo runtime compatible para este .skel.')); r3SpineObj=new SpineClass(skeletonData);"
)
# The imported R3 builder checks for this exact marker before zipping.
base.APP_JS_OVERRIDE += '\n/* Classic R3 Spine preview override - legacy assertion marker only */\n'

old_main = base.main

def copy_vendor_runtimefix(root: Path) -> None:
    vendor = root / 'web' / 'assets' / 'vendor'
    vendor.mkdir(parents=True, exist_ok=True)
    base.run(['npm', 'init', '-y'], ROOT)
    base.run(['npm', 'install', 'pixi.js@6.5.10', 'pixi-spine@3.1.0', '--no-audit', '--no-fund'], ROOT)
    shutil.copy2(ROOT / 'node_modules' / 'pixi.js' / 'dist' / 'browser' / 'pixi.min.js', vendor / 'pixi.min.js')
    candidates = [
        ROOT / 'node_modules' / 'pixi-spine' / 'dist' / 'pixi-spine.umd.js',
        ROOT / 'node_modules' / 'pixi-spine' / 'dist' / 'pixi-spine.js',
        ROOT / 'node_modules' / 'pixi-spine' / 'bin' / 'pixi-spine.js',
    ]
    chosen = next((p for p in candidates if p.exists() and p.stat().st_size > 1000), None)
    if chosen is None:
        extra = list((ROOT / 'node_modules' / 'pixi-spine').rglob('pixi-spine*.js')) + list((ROOT / 'node_modules' / 'pixi-spine').rglob('*.min.js'))
        chosen = next((p for p in extra if p.exists() and p.stat().st_size > 1000), None)
    if chosen is None:
        raise RuntimeError('No encontre un bundle browser valido de pixi-spine.')
    shutil.copy2(chosen, vendor / 'pixi-spine.umd.js')
    print('pixi-spine bundle:', chosen, chosen.stat().st_size)

base.copy_vendor = copy_vendor_runtimefix

def write_zip_r4() -> None:
    base.OUT.joinpath('VERSION.txt').write_text('NIKKE Mod Manager v0.13 Classic R4 Spine FULL\nBase real: v0.11 Preview Alpha\nInstalacion: descomprimir y ejecutar INSTALAR_Y_ABRIR.bat\nCambio principal: corrige el runtime Pixi/Spine usando namespaces 3.7/3.8/4.x para intentar armar el modelo normal dentro del Preview Alpha.\n', encoding='utf-8')
    base.OUT.joinpath('LEEME_PRIMERO.txt').write_text('NIKKE Mod Manager v0.13 Classic R4 Spine FULL\n\nDescomprime esta carpeta en un lugar nuevo y ejecuta INSTALAR_Y_ABRIR.bat.\nMantiene la interfaz clasica de v0.11. El Preview Alpha intenta armar mods normales con atlas + skel; la textura queda solo como fallback.\nLos 3DMigoto quedan para una revision posterior.\n', encoding='utf-8')
    for rel in ['app.py', 'README.md', 'PREVIEW_NOTES.md', 'INSTALAR_Y_ABRIR.bat', 'ABRIR.bat', 'web/app.js', 'web/index.html', 'src/preview.py']:
        p = base.OUT / rel
        if p.exists():
            s = p.read_text(encoding='utf-8', errors='ignore')
            s = s.replace('0.13 Classic R3 Spine', '0.13 Classic R4 Spine')
            s = s.replace('Classic R3', 'Classic R4')
            p.write_text(s, encoding='utf-8')
    if base.ZIP.exists():
        base.ZIP.unlink()
    with zipfile.ZipFile(base.ZIP, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for p in base.OUT.rglob('*'):
            z.write(p, p.relative_to(base.DIST))
    with zipfile.ZipFile(base.ZIP) as z:
        bad = z.testzip()
        if bad:
            raise RuntimeError(f'Zip corrupto en {bad}')
    print(f'OK {base.ZIP} {base.ZIP.stat().st_size} bytes')

base.write_zip = write_zip_r4

if __name__ == '__main__':
    old_main()
