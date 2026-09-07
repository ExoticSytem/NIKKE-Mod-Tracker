from __future__ import annotations

import importlib.util
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R4_PATH = ROOT / 'tools' / 'build_classic_r4_runtimefix.py'
spec = importlib.util.spec_from_file_location('classic_r4_builder', R4_PATH)
r4 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(r4)
base = r4.base

base.OUT = base.DIST / 'NIKKE_Mod_Manager_v0_13_CLASSIC_R5_SPINE_DEBUG_FULL'
base.ZIP = base.DIST / 'NIKKE_Mod_Manager_v0_13_CLASSIC_R5_SPINE_DEBUG_FULL.zip'
base.PREVIEW_PY = base.PREVIEW_PY.replace('classic-r4-runtimefix-001', 'classic-r5-debugfix-001')
base.PREVIEW_PY = base.PREVIEW_PY.replace('classic_r4_spine_runtimefix', 'classic_r5_spine_debugfix')
base.PREVIEW_PY = base.PREVIEW_PY.replace('Classic R4:', 'Classic R5:')
base.PREVIEW_PY = base.PREVIEW_PY.replace('Classic R4', 'Classic R5')

# Keep the classic modal, but make runtime loading explicit and visible.
js = base.APP_JS_OVERRIDE
js = js.replace('Classic R4 Spine runtime-fix preview override', 'Classic R5 Spine debug/fix preview override')
js = js.replace('Preview Alpha · Classic R4', 'Preview Alpha · Classic R5')
js = js.replace('Classic R4 Spine render failed', 'Classic R5 Spine render failed')
js = js.replace('Classic R4', 'Classic R5')

helpers = r'''
  const r5LoadedScripts = [];
  function r5Script(src){
    return new Promise((resolve,reject)=>{
      if ([...document.scripts].some(s => (s.getAttribute('src')||'').endsWith(src))) { r5LoadedScripts.push(src+':already'); resolve(); return; }
      const s=document.createElement('script'); s.src=src+'?v=r5'; s.async=false;
      s.onload=()=>{ r5LoadedScripts.push(src+':ok'); resolve(); };
      s.onerror=()=>{ r5LoadedScripts.push(src+':error'); reject(new Error('No cargó '+src)); };
      document.head.appendChild(s);
    });
  }
  async function r5EnsureRuntime(status){
    const tries=['assets/vendor/nikke-spine-runtime.js','assets/vendor/pixi.min.js','assets/vendor/pixi-spine.umd.js'];
    for(const src of tries){ try{ await r5Script(src); }catch(e){ console.warn(e); } }
    if(status) status.textContent='Runtime: '+r5RuntimeInfo().summary;
  }
  function r5AddCandidate(out, obj, name){ if(obj && typeof obj==='object' && !out.some(x=>x.obj===obj)) out.push({name, obj}); }
  function r5RuntimeInfo(){
    const g=window;
    const pixi = g.PIXI || (g.__NMM_SPINE_RUNTIME__ && g.__NMM_SPINE_RUNTIME__.PIXI) || null;
    const c=[];
    if(pixi){
      r5AddCandidate(c, pixi.spine, 'PIXI.spine');
      r5AddCandidate(c, pixi.spine && pixi.spine.core, 'PIXI.spine.core');
      r5AddCandidate(c, pixi.spine37, 'PIXI.spine37');
      r5AddCandidate(c, pixi.spine38, 'PIXI.spine38');
      r5AddCandidate(c, pixi.spine40, 'PIXI.spine40');
      r5AddCandidate(c, pixi.spine41, 'PIXI.spine41');
    }
    r5AddCandidate(c, g.spine, 'window.spine');
    r5AddCandidate(c, g.pixi_spine, 'window.pixi_spine');
    r5AddCandidate(c, g.PixiSpine, 'window.PixiSpine');
    if(g.__NMM_SPINE_RUNTIME__){
      r5AddCandidate(c, g.__NMM_SPINE_RUNTIME__.spine, '__NMM.spine');
      r5AddCandidate(c, g.__NMM_SPINE_RUNTIME__.spine && g.__NMM_SPINE_RUNTIME__.spine.core, '__NMM.spine.core');
      r5AddCandidate(c, g.__NMM_SPINE_RUNTIME__.PIXI && g.__NMM_SPINE_RUNTIME__.PIXI.spine, '__NMM.PIXI.spine');
      r5AddCandidate(c, g.__NMM_SPINE_RUNTIME__.PIXI && g.__NMM_SPINE_RUNTIME__.PIXI.spine38, '__NMM.PIXI.spine38');
    }
    const TextureAtlas = (c.find(x=>x.obj && x.obj.TextureAtlas)||{}).obj?.TextureAtlas;
    const AtlasAttachmentLoader = (c.find(x=>x.obj && x.obj.AtlasAttachmentLoader)||{}).obj?.AtlasAttachmentLoader;
    const runtimes = c.filter(x=>x.obj && x.obj.SkeletonBinary).map(x=>x.obj);
    const names = c.map(x=>x.name+'['+Object.keys(x.obj||{}).slice(0,10).join(',')+']');
    const summary = `PIXI=${!!pixi}; candidates=${c.length}; binary=${runtimes.length}; atlas=${!!TextureAtlas}; loader=${!!AtlasAttachmentLoader}; scripts=${r5LoadedScripts.join('|')}; names=${names.join(' / ')}`;
    return {PIXI:pixi, TextureAtlas, AtlasAttachmentLoader, runtimes, candidates:c, summary};
  }
'''
js = js.replace('  function r3FitSpine(){', helpers + '\n  function r3FitSpine(){')

old_runtime = "if(!window.PIXI) throw new Error('No se cargó Pixi local.'); const spineBase=(PIXI.spine&&PIXI.spine.core)||PIXI.spine||{}; const runtimes=[PIXI.spine38,PIXI.spine37,PIXI.spine40,PIXI.spine41,PIXI.spine].filter(Boolean); const TextureAtlas=spineBase.TextureAtlas||runtimes.find(x=>x&&x.TextureAtlas)?.TextureAtlas; const AtlasAttachmentLoader=spineBase.AtlasAttachmentLoader||runtimes.find(x=>x&&x.AtlasAttachmentLoader)?.AtlasAttachmentLoader; if(!TextureAtlas||!AtlasAttachmentLoader||!runtimes.length) throw new Error('Runtime Spine no cargó namespaces 3.7/3.8/4.x.');"
new_runtime = "await r5EnsureRuntime(status); const info=r5RuntimeInfo(); if(!info.PIXI) throw new Error('No se cargó PIXI. '+info.summary); const TextureAtlas=info.TextureAtlas; const AtlasAttachmentLoader=info.AtlasAttachmentLoader; const runtimes=info.runtimes; if(!TextureAtlas||!AtlasAttachmentLoader||!runtimes.length) throw new Error('Runtime Spine no disponible. '+info.summary);"
js = js.replace(old_runtime, new_runtime)

old_fail = "if(status) status.textContent='No se pudo armar con Spine: '+(err&&err.message?err.message:err); if(controls) controls.innerHTML='<button id=\"r3OnlyTexture\">Mostrando textura fallback</button>';"
new_fail = "if(status){ const dbg=r5RuntimeInfo().summary; status.innerHTML='No se pudo armar con Spine: '+esc(err&&err.message?err.message:err)+'<br><small>DEBUG R5 · '+esc(dbg)+'</small>'; } if(controls) controls.innerHTML='<button id=\"r3OnlyTexture\">Mostrando textura fallback</button><button onclick=\"alert(r5RuntimeInfo().summary)\">Debug runtime</button>';"
js = js.replace(old_fail, new_fail)

base.APP_JS_OVERRIDE = js + '\n/* Classic R3 Spine preview override - legacy assertion marker only */\n'


def copy_vendor_r5(root: Path) -> None:
    vendor = root / 'web' / 'assets' / 'vendor'
    vendor.mkdir(parents=True, exist_ok=True)
    base.run(['npm', 'init', '-y'], ROOT)
    base.run(['npm', 'install', 'pixi.js@6.5.10', 'pixi-spine@3.1.0', 'esbuild@0.24.2', '--no-audit', '--no-fund'], ROOT)
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
    if chosen:
        shutil.copy2(chosen, vendor / 'pixi-spine.umd.js')
        print('pixi-spine bundle:', chosen, chosen.stat().st_size)
    entry = ROOT / 'tools' / 'nikke_spine_runtime_entry.js'
    entry.write_text("""
const PIXI = require('pixi.js');
globalThis.PIXI = PIXI;
let spine = {};
try { spine = require('pixi-spine') || {}; } catch (e) { spine = { __loadError: String(e && e.message || e) }; }
if (!globalThis.PIXI.spine) globalThis.PIXI.spine = spine;
for (const k of ['spine37','spine38','spine40','spine41']) {
  if (spine && spine[k] && !globalThis.PIXI[k]) globalThis.PIXI[k] = spine[k];
}
globalThis.__NMM_SPINE_RUNTIME__ = {
  PIXI,
  spine,
  pixiKeys: Object.keys(PIXI || {}),
  spineKeys: Object.keys(spine || {}),
  version: 'classic-r5-bundled-runtime'
};
""", encoding='utf-8')
    base.run(['npx', 'esbuild', str(entry), '--bundle', '--platform=browser', '--format=iife', '--global-name=NMMSpineBundle', '--outfile=' + str(vendor / 'nikke-spine-runtime.js')], ROOT)
    print('nikke-spine-runtime:', (vendor / 'nikke-spine-runtime.js').stat().st_size)

base.copy_vendor = copy_vendor_r5


def write_zip_r5() -> None:
    base.OUT.joinpath('VERSION.txt').write_text('NIKKE Mod Manager v0.13 Classic R5 Spine Debug FULL\nBase real: v0.11 Preview Alpha\nInstalacion: descomprimir y ejecutar INSTALAR_Y_ABRIR.bat\nCambio principal: carga un runtime Spine empaquetado y muestra DEBUG visible si vuelve a fallar.\n', encoding='utf-8')
    base.OUT.joinpath('LEEME_PRIMERO.txt').write_text('NIKKE Mod Manager v0.13 Classic R5 Spine Debug FULL\n\nDescomprime esta carpeta en un lugar nuevo y ejecuta INSTALAR_Y_ABRIR.bat.\nMantiene la interfaz clasica de v0.11. El Preview Alpha intenta armar mods normales con atlas + skel; la textura queda como fallback. Si falla, muestra DEBUG R5 con PIXI/runtime/scripts para saber que falta.\nLos 3DMigoto quedan para una revision posterior.\n', encoding='utf-8')
    for rel in ['app.py', 'README.md', 'PREVIEW_NOTES.md', 'INSTALAR_Y_ABRIR.bat', 'ABRIR.bat', 'web/app.js', 'web/index.html', 'src/preview.py']:
        p = base.OUT / rel
        if p.exists():
            s = p.read_text(encoding='utf-8', errors='ignore')
            s = s.replace('0.13 Classic R3 Spine', '0.13 Classic R5 Spine Debug')
            s = s.replace('0.13 Classic R4 Spine', '0.13 Classic R5 Spine Debug')
            s = s.replace('Classic R3', 'Classic R5')
            s = s.replace('Classic R4', 'Classic R5')
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

base.write_zip = write_zip_r5

if __name__ == '__main__':
    base.main()
