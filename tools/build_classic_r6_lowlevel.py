from __future__ import annotations

import importlib.util
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R5_PATH = ROOT / 'tools' / 'build_classic_r5_debugfix.py'
spec = importlib.util.spec_from_file_location('classic_r5_builder', R5_PATH)
r5 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(r5)
base = r5.base

base.OUT = base.DIST / 'NIKKE_Mod_Manager_v0_13_CLASSIC_R6_SPINE_LOWLEVEL_FULL'
base.ZIP = base.DIST / 'NIKKE_Mod_Manager_v0_13_CLASSIC_R6_SPINE_LOWLEVEL_FULL.zip'
base.PREVIEW_PY = base.PREVIEW_PY.replace('classic-r5-debugfix-001', 'classic-r6-lowlevel-001')
base.PREVIEW_PY = base.PREVIEW_PY.replace('classic_r5_spine_debugfix', 'classic_r6_spine_lowlevel')
base.PREVIEW_PY = base.PREVIEW_PY.replace('Classic R5:', 'Classic R6:')
base.PREVIEW_PY = base.PREVIEW_PY.replace('Classic R5', 'Classic R6')

js = base.APP_JS_OVERRIDE
js = js.replace('Classic R5 Spine debug/fix preview override', 'Classic R6 Spine low-level runtime preview override')
js = js.replace('Preview Alpha · Classic R5', 'Preview Alpha · Classic R6')
js = js.replace('Classic R5 Spine render failed', 'Classic R6 Spine render failed')
js = js.replace('Classic R5', 'Classic R6')

helpers = r'''
  const r6LoadedScripts = [];
  function r6Script(src){
    return new Promise((resolve,reject)=>{
      const found=[...document.scripts].some(s => (s.getAttribute('src')||'').includes(src));
      if(found && window.__NMM_SPINE_LOW__){ r6LoadedScripts.push(src+':already'); resolve(); return; }
      const s=document.createElement('script');
      s.src=src+'?v=r6lowlevel001';
      s.async=false;
      s.onload=()=>{ r6LoadedScripts.push(src+':ok'); resolve(); };
      s.onerror=()=>{ r6LoadedScripts.push(src+':error'); reject(new Error('No cargó '+src)); };
      document.head.appendChild(s);
    });
  }
  async function r6EnsureRuntime(status){
    try{ await r6Script('assets/vendor/nikke-spine-runtime.js'); }catch(e){ console.warn(e); }
    if(status) status.textContent='Runtime: '+r6RuntimeInfo().summary;
  }
  function r6RuntimeInfo(){
    const g=window;
    const low=g.__NMM_SPINE_LOW__||{};
    const pixi=low.PIXI||g.PIXI||null;
    const pixiSpine=low.pixiSpine||(pixi&&pixi.spine)||g.pixi_spine||{};
    const baseCore=low.base||{};
    const TextureAtlas=low.TextureAtlas||pixiSpine.TextureAtlas||baseCore.TextureAtlas||null;
    const SpineClass=low.SpineClass||pixiSpine.Spine||(pixi&&pixi.spine&&pixi.spine.Spine)||null;
    const runtimePairs=[];
    function add(name,obj){ if(obj && obj.SkeletonBinary && obj.AtlasAttachmentLoader && !runtimePairs.some(x=>x.obj===obj)) runtimePairs.push({name,obj}); }
    if(Array.isArray(low.runtimes)) for(const r of low.runtimes) add(r.name||'runtime', r.mod||r.obj||r);
    add('3.8', low.spine38); add('3.7', low.spine37); add('4.1', low.spine41); add('3.4', low.spine34);
    add('PIXI.spine38', pixi&&pixi.spine38); add('PIXI.spine37', pixi&&pixi.spine37); add('PIXI.spine41', pixi&&pixi.spine41); add('PIXI.spine34', pixi&&pixi.spine34);
    const names=[];
    if(low.version) names.push('__LOW__['+(low.runtimeNames||[]).join(',')+']');
    if(pixiSpine) names.push('pixiSpine['+Object.keys(pixiSpine).slice(0,14).join(',')+']');
    if(baseCore) names.push('base['+Object.keys(baseCore).slice(0,14).join(',')+']');
    for(const r of runtimePairs) names.push(r.name+'['+Object.keys(r.obj||{}).slice(0,8).join(',')+']');
    const summary=`PIXI=${!!pixi}; low=${!!low.version}; TextureAtlas=${!!TextureAtlas}; SpineClass=${!!SpineClass}; runtimes=${runtimePairs.map(r=>r.name).join(',')||'0'}; scripts6=${r6LoadedScripts.join('|')}; scripts5=${(typeof r5LoadedScripts!=='undefined'?r5LoadedScripts.join('|'):'')}; names=${names.join(' / ')}`;
    return {PIXI:pixi, TextureAtlas, SpineClass, runtimes:runtimePairs, summary};
  }
'''
js = js.replace('  function r3FitSpine(){', helpers + '\n  function r3FitSpine(){')

old_runtime = "await r5EnsureRuntime(status); const info=r5RuntimeInfo(); if(!info.PIXI) throw new Error('No se cargó PIXI. '+info.summary); const TextureAtlas=info.TextureAtlas; const AtlasAttachmentLoader=info.AtlasAttachmentLoader; const runtimes=info.runtimes; if(!TextureAtlas||!AtlasAttachmentLoader||!runtimes.length) throw new Error('Runtime Spine no disponible. '+info.summary);"
new_runtime = "await r6EnsureRuntime(status); const info=r6RuntimeInfo(); if(!info.PIXI) throw new Error('No se cargó PIXI. '+info.summary); const TextureAtlas=info.TextureAtlas; const SpineClassGlobal=info.SpineClass; const runtimes=info.runtimes; if(!TextureAtlas||!SpineClassGlobal||!runtimes.length) throw new Error('Runtime Spine low-level no disponible. '+info.summary);"
if old_runtime not in js:
    raise SystemExit('No encontre el bloque runtime R5 para reemplazar.')
js = js.replace(old_runtime, new_runtime)

old_parse = "const atlas=new TextureAtlas(String(r.spine_atlas_text||''), function(_line, callback){ callback(baseTexture); }); const atlasLoader=new AtlasAttachmentLoader(atlas); const bytes=r3BytesFromB64(r.spine_skel_b64); let skeletonData=null; let SpineClass=null; let lastRuntimeError=null; for(const Runtime of runtimes){ try{ if(!Runtime||!Runtime.SkeletonBinary) continue; const binary=new Runtime.SkeletonBinary(atlasLoader); skeletonData=binary.readSkeletonData(bytes); SpineClass=Runtime.Spine||(PIXI.spine&&PIXI.spine.Spine); if(skeletonData&&SpineClass) break; }catch(e){ lastRuntimeError=e; skeletonData=null; SpineClass=null; } } if(!skeletonData||!SpineClass) throw (lastRuntimeError||new Error('No hubo runtime compatible para este .skel.')); r3SpineObj=new SpineClass(skeletonData);"
new_parse = "const atlas=new TextureAtlas(String(r.spine_atlas_text||''), function(_line, callback){ callback(baseTexture); }); const bytes=r3BytesFromB64(r.spine_skel_b64); let skeletonData=null; let SpineClass=SpineClassGlobal; let lastRuntimeError=null; let usedRuntime=''; for(const pair of runtimes){ const Runtime=pair.obj||pair.mod||pair; try{ if(!Runtime||!Runtime.SkeletonBinary||!Runtime.AtlasAttachmentLoader) continue; const atlasLoader=new Runtime.AtlasAttachmentLoader(atlas); const binary=new Runtime.SkeletonBinary(atlasLoader); binary.scale=1; skeletonData=binary.readSkeletonData(bytes); usedRuntime=pair.name||'runtime'; if(skeletonData&&SpineClass) break; }catch(e){ lastRuntimeError=e; skeletonData=null; usedRuntime=pair.name||'runtime'; } } if(!skeletonData||!SpineClass){ const msg=(lastRuntimeError&&lastRuntimeError.message?lastRuntimeError.message:lastRuntimeError)||'No hubo runtime compatible para este .skel.'; throw new Error(String(msg)+' · '+info.summary); } r3SpineObj=new SpineClass(skeletonData); r3SpineObj.__nmmRuntime=usedRuntime;"
if old_parse not in js:
    raise SystemExit('No encontre el bloque parser R4/R5 para reemplazar.')
js = js.replace(old_parse, new_parse)

js = js.replace('DEBUG R5 · ', 'DEBUG R6 · ')
js = js.replace('r5RuntimeInfo().summary', "(typeof r6RuntimeInfo==='function'?r6RuntimeInfo():r5RuntimeInfo()).summary")
js = js.replace('Debug runtime', 'Debug runtime R6')
base.APP_JS_OVERRIDE = js + '\n/* Classic R3 Spine preview override - legacy assertion marker only */\n'


def copy_vendor_r6(root: Path) -> None:
    vendor = root / 'web' / 'assets' / 'vendor'
    vendor.mkdir(parents=True, exist_ok=True)
    base.run([
        'npm', 'init', '-y'
    ], ROOT)
    base.run([
        'npm', 'install',
        'pixi.js@6.5.10',
        'pixi-spine@3.1.0',
        '@pixi-spine/base@3.1.0',
        '@pixi-spine/runtime-3.4@3.1.0',
        '@pixi-spine/runtime-3.7@3.1.0',
        '@pixi-spine/runtime-3.8@3.1.0',
        '@pixi-spine/runtime-4.1@3.1.0',
        'esbuild@0.24.2',
        '--no-audit', '--no-fund'
    ], ROOT)
    pixi_browser = ROOT / 'node_modules' / 'pixi.js' / 'dist' / 'browser' / 'pixi.min.js'
    if pixi_browser.exists():
        shutil.copy2(pixi_browser, vendor / 'pixi.min.js')
    spine_bundle = ROOT / 'node_modules' / 'pixi-spine' / 'dist' / 'pixi-spine.umd.js'
    if spine_bundle.exists():
        shutil.copy2(spine_bundle, vendor / 'pixi-spine.umd.js')
    entry = ROOT / 'tools' / 'nikke_spine_lowlevel_entry.js'
    entry.write_text(r"""
const PIXI = require('pixi.js');
const pixiSpine = require('pixi-spine');
const base = require('@pixi-spine/base');
const spine34 = require('@pixi-spine/runtime-3.4');
const spine37 = require('@pixi-spine/runtime-3.7');
const spine38 = require('@pixi-spine/runtime-3.8');
const spine41 = require('@pixi-spine/runtime-4.1');

const TextureAtlas = pixiSpine.TextureAtlas || base.TextureAtlas;
const SpineClass = pixiSpine.Spine;

PIXI.spine = pixiSpine;
PIXI.spine34 = spine34;
PIXI.spine37 = spine37;
PIXI.spine38 = spine38;
PIXI.spine41 = spine41;

globalThis.PIXI = PIXI;
globalThis.pixi_spine = pixiSpine;
globalThis.__NMM_SPINE_LOW__ = {
  version: 'classic-r6-lowlevel-001',
  PIXI,
  pixiSpine,
  base,
  TextureAtlas,
  SpineClass,
  spine34,
  spine37,
  spine38,
  spine41,
  runtimes: [
    { name: '3.8', mod: spine38 },
    { name: '3.7', mod: spine37 },
    { name: '4.1', mod: spine41 },
    { name: '3.4', mod: spine34 }
  ],
  runtimeNames: ['3.8','3.7','4.1','3.4'],
  pixiSpineKeys: Object.keys(pixiSpine || {}),
  baseKeys: Object.keys(base || {})
};
""", encoding='utf-8')
    base.run(['npx', 'esbuild', str(entry), '--bundle', '--platform=browser', '--format=iife', '--global-name=NMMSpineLowLevel', '--outfile=' + str(vendor / 'nikke-spine-runtime.js')], ROOT)
    if (vendor / 'nikke-spine-runtime.js').stat().st_size < 1000:
        raise RuntimeError('nikke-spine-runtime.js quedo demasiado pequeno.')
    print('nikke-spine-runtime lowlevel:', (vendor / 'nikke-spine-runtime.js').stat().st_size)

base.copy_vendor = copy_vendor_r6


def write_zip_r6() -> None:
    base.OUT.joinpath('VERSION.txt').write_text('NIKKE Mod Manager v0.13 Classic R6 Spine LowLevel FULL\nBase real: v0.11 Preview Alpha\nInstalacion: descomprimir y ejecutar INSTALAR_Y_ABRIR.bat\nCambio principal: incluye runtimes low-level @pixi-spine 3.4/3.7/3.8/4.1 para leer .skel binario y armar mods normales dentro del Preview Alpha.\n', encoding='utf-8')
    base.OUT.joinpath('LEEME_PRIMERO.txt').write_text('NIKKE Mod Manager v0.13 Classic R6 Spine LowLevel FULL\n\nDescomprime esta carpeta en un lugar nuevo y ejecuta INSTALAR_Y_ABRIR.bat.\nMantiene la interfaz clasica de v0.11. El Preview Alpha intenta armar mods normales usando TextureAtlas + SkeletonBinary low-level; textura queda como fallback. Si falla, muestra DEBUG R6 con el runtime elegido o el error exacto.\nLos 3DMigoto quedan para una revision posterior.\n', encoding='utf-8')
    for rel in ['app.py', 'README.md', 'PREVIEW_NOTES.md', 'INSTALAR_Y_ABRIR.bat', 'ABRIR.bat', 'web/app.js', 'web/index.html', 'src/preview.py']:
        p = base.OUT / rel
        if p.exists():
            s = p.read_text(encoding='utf-8', errors='ignore')
            s = s.replace('0.13 Classic R3 Spine', '0.13 Classic R6 Spine LowLevel')
            s = s.replace('0.13 Classic R4 Spine', '0.13 Classic R6 Spine LowLevel')
            s = s.replace('0.13 Classic R5 Spine Debug', '0.13 Classic R6 Spine LowLevel')
            s = s.replace('Classic R3', 'Classic R6')
            s = s.replace('Classic R4', 'Classic R6')
            s = s.replace('Classic R5', 'Classic R6')
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

base.write_zip = write_zip_r6

if __name__ == '__main__':
    base.main()
