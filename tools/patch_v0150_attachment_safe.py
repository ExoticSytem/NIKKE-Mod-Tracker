from pathlib import Path
import shutil

ROOT = Path('extracted')
roots = [p.parent.parent for p in ROOT.rglob('web/app.js')]
if not roots:
    raise SystemExit('No encontré web/app.js dentro del artifact extraído')

PATCH = r'''

// --- NMM v0.15.0 Attachment Safe Constructor Patch -------------------------
(function () {
  if (window.__NMM_V0150_ATTACHMENT_SAFE__) return;
  window.__NMM_V0150_ATTACHMENT_SAFE__ = true;

  function safeName(name, path, fallback) {
    var n = name;
    if (n == null || n === '') n = path;
    if (n == null || n === '') n = fallback || 'attachment';
    return String(n);
  }

  function seqVariants(name) {
    var s = String(name == null ? '' : name);
    var out = [];
    function add(v) { if (v && v !== s && out.indexOf(v) < 0) out.push(v); }
    add(s.replace(/\d+$/, ''));
    add(s.replace(/[_-]?\d+$/, ''));
    add(s.replace(/t\d+$/, 't'));
    add(s.replace(/([a-z_]+)[0-9]+$/i, '$1'));
    return out;
  }

  function copyStatics(dst, src) {
    try {
      Object.getOwnPropertyNames(src).forEach(function(k) {
        if (k === 'length' || k === 'name' || k === 'prototype') return;
        try { Object.defineProperty(dst, k, Object.getOwnPropertyDescriptor(src, k)); } catch(e) {}
      });
    } catch(e) {}
  }

  function makeFallbackAttachment(ns, key, name) {
    var obj = { name: safeName(name, null, key || 'attachment'), type: key || 'Attachment' };
    obj.path = obj.name;
    obj.color = ns && typeof ns.Color === 'function' ? new ns.Color(1,1,1,1) : {r:1,g:1,b:1,a:1};
    obj.region = null;
    obj.bones = null;
    obj.vertices = [];
    obj.worldVerticesLength = 0;
    obj.timelineAttachment = obj;
    obj.lengths = [];
    obj.closed = false;
    obj.constantSpeed = false;
    obj.endSlot = null;
    obj.updateOffset = function(){};
    obj.setRegion = function(region){ this.region = region; };
    obj.computeWorldVertices = function(slot, start, count, out, offset, stride){
      out = out || []; offset = offset || 0; stride = stride || 2; count = count || 8;
      for (var i=0; i<count; i+=2) { out[offset] = 0; out[offset+1] = 0; offset += stride; }
      return out;
    };
    obj.computeWorldPosition = function(bone, point){ point = point || {x:0,y:0}; point.x = this.x || 0; point.y = this.y || 0; return point; };
    obj.computeWorldRotation = function(){ return this.rotation || 0; };
    return obj;
  }

  function wrapCtor(ns, key) {
    if (!ns || typeof ns[key] !== 'function') return false;
    var Orig = ns[key];
    if (Orig.__nmm_v0150_wrapped) return true;

    function WrappedAttachment(name) {
      var args = Array.prototype.slice.call(arguments);
      args[0] = safeName(args[0], args[1], key);
      try {
        return Reflect.construct(Orig, args, WrappedAttachment);
      } catch (err) {
        var msg = String((err && err.message) || err || '');
        if (/Attachment name must not be null|name must not be null|Cannot read properties of null/i.test(msg)) {
          try {
            return Reflect.construct(Orig, [safeName(args[0], args[1], key)], WrappedAttachment);
          } catch(e2) {
            return makeFallbackAttachment(ns, key, args[0]);
          }
        }
        throw err;
      }
    }
    try { Object.setPrototypeOf(WrappedAttachment, Orig); } catch(e) {}
    try { WrappedAttachment.prototype = Orig.prototype; } catch(e) {}
    try { WrappedAttachment.prototype.constructor = WrappedAttachment; } catch(e) {}
    copyStatics(WrappedAttachment, Orig);
    WrappedAttachment.__nmm_v0150_wrapped = true;
    WrappedAttachment.__nmm_v0150_original = Orig;
    ns[key] = WrappedAttachment;
    return true;
  }

  function ensureFallbackClasses(ns) {
    if (!ns) return false;
    if (!ns.AttachmentType) ns.AttachmentType = { Region:0, BoundingBox:1, Mesh:2, LinkedMesh:3, Path:4, Point:5, Clipping:6 };
    if (!ns.Color) ns.Color = function(r,g,b,a){ this.r=r==null?1:r; this.g=g==null?1:g; this.b=b==null?1:b; this.a=a==null?1:a; };

    function simple(key) {
      if (!ns[key]) ns[key] = function(name){ return makeFallbackAttachment(ns, key, safeName(name, null, key)); };
    }
    ['Attachment','RegionAttachment','MeshAttachment','PointAttachment','BoundingBoxAttachment','PathAttachment','ClippingAttachment'].forEach(simple);

    if (!ns.SequenceMode) ns.SequenceMode = { hold:0, once:1, loop:2, pingpong:3, onceReverse:4, loopReverse:5, pingpongReverse:6 };
    if (!ns.Sequence) ns.Sequence = function(count){ this.id=0; this.regions=new Array(count||0); this.start=0; this.digits=0; this.setupIndex=0; };
    if (ns.Sequence && ns.Sequence.prototype && !ns.Sequence.prototype.getPath) {
      ns.Sequence.prototype.getPath = function(basePath, index){ return String(basePath || '') + String(index || ''); };
    }
    return true;
  }

  function patchAtlas(ns) {
    if (!ns || !ns.TextureAtlas || !ns.TextureAtlas.prototype) return false;
    var p = ns.TextureAtlas.prototype;
    if (p.__nmm_v0150_findRegion) return true;
    var orig = p.findRegion;
    if (typeof orig !== 'function') return false;
    p.findRegion = function(name) {
      var r = orig.call(this, name);
      if (r) return r;
      var vars = seqVariants(name);
      for (var i=0; i<vars.length; i++) { try { r = orig.call(this, vars[i]); if (r) return r; } catch(e) {} }
      return null;
    };
    p.__nmm_v0150_findRegion = true;
    return true;
  }

  function patchLoader(ns) {
    if (!ns) return false;
    if (!ns.AtlasAttachmentLoader) {
      ns.AtlasAttachmentLoader = function(atlas){ this.atlas = atlas; };
    }
    var p = ns.AtlasAttachmentLoader.prototype;
    if (!p || p.__nmm_v0150_loader) return true;

    function find(atlas, name) {
      if (!atlas || typeof atlas.findRegion !== 'function') return null;
      var r = atlas.findRegion(name);
      if (r) return r;
      var vars = seqVariants(name);
      for (var i=0; i<vars.length; i++) { try { r = atlas.findRegion(vars[i]); if (r) return r; } catch(e) {} }
      return null;
    }

    p.newRegionAttachment = function(skin, name, path) {
      var n = safeName(name, path, 'region');
      var pp = safeName(path, name, n);
      var a = new ns.RegionAttachment(n);
      a.path = pp;
      a.region = find(this.atlas, pp) || find(this.atlas, n);
      if (typeof a.setRegion === 'function' && a.region) { try { a.setRegion(a.region); } catch(e) {} }
      return a;
    };
    p.newMeshAttachment = function(skin, name, path) {
      var n = safeName(name, path, 'mesh');
      var pp = safeName(path, name, n);
      var a = new ns.MeshAttachment(n);
      a.path = pp;
      a.region = find(this.atlas, pp) || find(this.atlas, n);
      if (typeof a.setRegion === 'function' && a.region) { try { a.setRegion(a.region); } catch(e) {} }
      return a;
    };
    p.newBoundingBoxAttachment = function(skin, name) { return new ns.BoundingBoxAttachment(safeName(name, null, 'bbox')); };
    p.newPathAttachment = function(skin, name) { return new ns.PathAttachment(safeName(name, null, 'path')); };
    p.newPointAttachment = function(skin, name) { return new ns.PointAttachment(safeName(name, null, 'point')); };
    p.newClippingAttachment = function(skin, name) { return new ns.ClippingAttachment(safeName(name, null, 'clip')); };
    p.__nmm_v0150_loader = true;
    return true;
  }

  function namespaces() {
    var out = [];
    function add(x) { if (x && out.indexOf(x) < 0) out.push(x); }
    add(window.pixi_spine);
    add(window.pixi_spine && window.pixi_spine.core);
    add(window.PIXI && window.PIXI.spine);
    add(window.PIXI && window.PIXI.spine && window.PIXI.spine.core);
    add(window.spine);
    add(window.spine && window.spine.core);
    add(window.spine38);
    add(window.spine41);
    return out;
  }

  window.__nmmV0150PatchRuntime = function(){
    var ok = false;
    var ns = namespaces();
    for (var i=0; i<ns.length; i++) {
      var n = ns[i];
      try { ok = ensureFallbackClasses(n) || ok; } catch(e) {}
      try { ['Attachment','RegionAttachment','MeshAttachment','PointAttachment','BoundingBoxAttachment','PathAttachment','ClippingAttachment'].forEach(function(k){ ok = wrapCtor(n,k) || ok; }); } catch(e) {}
      try { ok = patchAtlas(n) || ok; } catch(e) {}
      try { ok = patchLoader(n) || ok; } catch(e) {}
    }
    try { window.__nmmInstallRuntimeCompat && window.__nmmInstallRuntimeCompat(); } catch(e) {}
    try { window.__nmmPatchSpineAtlasSequences && window.__nmmPatchSpineAtlasSequences(); } catch(e) {}
    return ok;
  };

  // Captura stack para el próximo fallo.
  window.__nmmLastRuntimeErrorStack = '';
  window.addEventListener('error', function(e){ try { window.__nmmLastRuntimeErrorStack = (e.error && e.error.stack) || e.message || ''; } catch(x) {} });
  window.addEventListener('unhandledrejection', function(e){ try { window.__nmmLastRuntimeErrorStack = (e.reason && e.reason.stack) || String(e.reason || ''); } catch(x) {} });

  var tries = 0;
  var timer = setInterval(function(){ tries++; if (window.__nmmV0150PatchRuntime() || tries > 800) clearInterval(timer); }, 10);
  setTimeout(window.__nmmV0150PatchRuntime, 1);
  setTimeout(window.__nmmV0150PatchRuntime, 50);
  setTimeout(window.__nmmV0150PatchRuntime, 200);
  setTimeout(window.__nmmV0150PatchRuntime, 600);
})();
// --- end NMM v0.15.0 -------------------------------------------------------
'''

for root in roots:
    appjs = root / 'web' / 'app.js'
    js = appjs.read_text(encoding='utf-8', errors='ignore')
    appjs.with_suffix('.js.bak_v0150_attachment_safe').write_text(js, encoding='utf-8')

    for old in ['Classic v0.14.9 RuntimeCompat','Classic v0.14.8 RuntimeDiagnosticTop','Classic v0.14.7 RuntimeDiagnostic']:
        js = js.replace(old, 'Classic v0.15.0 AttachmentSafe')
    for old in ['Debug v0.14.9','Debug v0.14.8','Debug v0.14.7']:
        js = js.replace(old, 'Debug v0.15.0')
    for old in ['DEBUG v0.14.9','DEBUG v0.14.8','DEBUG v0.14.7']:
        js = js.replace(old, 'DEBUG v0.15.0')
    for old in ['NMM RUNTIME DIAGNOSTIC v0.14.9','NMM RUNTIME DIAGNOSTIC v0.14.8','NMM RUNTIME DIAGNOSTIC v0.14.7']:
        js = js.replace(old, 'NMM RUNTIME DIAGNOSTIC v0.15.0')
    for old in ['DIAGNÓSTICO RUNTIME v0.14.9','DIAGNÓSTICO RUNTIME v0.14.8','DIAGNÓSTICO RUNTIME v0.14.7']:
        js = js.replace(old, 'DIAGNÓSTICO RUNTIME v0.15.0')

    if 'NMM v0.15.0 Attachment Safe Constructor Patch' not in js:
        lines = js.splitlines()
        out = []
        for line in lines:
            trigger = (
                ('readSkeletonData' in line or 'new ' in line)
                and any(k in line for k in ['TextureAtlas', 'AtlasAttachmentLoader', 'SkeletonBinary', 'SkeletonJson', 'readSkeletonData','Spine'])
                and '__nmmV0150PatchRuntime' not in line
            )
            if trigger:
                out.append('      try { window.__nmmV0150PatchRuntime && window.__nmmV0150PatchRuntime(); } catch(e) {}')
            out.append(line)
        js = '\n'.join(out) + '\n' + PATCH + '\n'

    # augment diagnostic with last stack if function exists as text marker
    if 'LAST_RUNTIME_STACK=' not in js:
        js += "\n(function(){try{var old=window.__nmmRuntimeDiagnostic;if(typeof old==='function'){window.__nmmRuntimeDiagnostic=function(){var t=old();try{t+='\\nLAST_RUNTIME_STACK='+(window.__nmmLastRuntimeErrorStack||'');}catch(e){}return t;};}}catch(e){}})();\n"

    appjs.write_text(js, encoding='utf-8')

    preview = root / 'src' / 'preview.py'
    if preview.exists():
        ps = preview.read_text(encoding='utf-8', errors='ignore')
        preview.with_suffix('.py.bak_v0150_attachment_safe').write_text(ps, encoding='utf-8')
        for old in ['Classic v0.14.9 RuntimeCompat','Classic v0.14.8 RuntimeDiagnosticTop','Classic v0.14.7 RuntimeDiagnostic']:
            ps = ps.replace(old, 'Classic v0.15.0 AttachmentSafe')
        for old in ['Debug v0.14.9','Debug v0.14.8','Debug v0.14.7']:
            ps = ps.replace(old, 'Debug v0.15.0')
        for old in ['DEBUG v0.14.9','DEBUG v0.14.8','DEBUG v0.14.7']:
            ps = ps.replace(old, 'DEBUG v0.15.0')
        compile(ps, str(preview), 'exec')
        preview.write_text(ps, encoding='utf-8')

    for rel in ['VERSION.txt', 'LEEME_PRIMERO.txt', 'DIAGNOSTICO_RUNTIME.md']:
        p = root / rel
        old = p.read_text(encoding='utf-8', errors='ignore') if p.exists() and rel != 'DIAGNOSTICO_RUNTIME.md' else ''
        p.write_text(
            'NIKKE Mod Manager v0.15.0 Classic Integrated Viewer AttachmentSafe FULL\n\n'
            'Parche más agresivo para Attachment name must not be null: envuelve constructores y loader de attachments.\n'
            'Mantiene botón Copiar diagnóstico e incluye LAST_RUNTIME_STACK si vuelve a fallar.\n\n' + old,
            encoding='utf-8'
        )

    target = root.parent / 'NIKKE_Mod_Manager_v0_15_0_Classic_Integrated_Viewer_ATTACHMENTSAFE_FULL'
    if root != target:
        if target.exists():
            shutil.rmtree(target)
        root.rename(target)
        root = target

    final_js = (root / 'web' / 'app.js').read_text(encoding='utf-8', errors='ignore')
    assert 'NMM v0.15.0 Attachment Safe Constructor Patch' in final_js
    print('patched', root)
