from pathlib import Path
import shutil

ROOT = Path('extracted')
roots = [p.parent.parent for p in ROOT.rglob('web/app.js')]
if not roots:
    raise SystemExit('No encontré web/app.js dentro del artifact extraído')

PATCH = r'''

// --- NMM v0.14.9 Runtime Attachment Compatibility Polyfill -----------------
(function () {
  if (window.__NMM_V0149_RUNTIME_COMPAT__) return;
  window.__NMM_V0149_RUNTIME_COMPAT__ = true;

  function makeColor(ns) {
    if (ns && typeof ns.Color === 'function') return new ns.Color(1, 1, 1, 1);
    return { r: 1, g: 1, b: 1, a: 1, setFromColor: function(c){ if(c){this.r=c.r;this.g=c.g;this.b=c.b;this.a=c.a;} } };
  }

  function nameOf(name, path, fallback) {
    var n = name;
    if (n == null || n === '') n = path;
    if (n == null || n === '') n = fallback || 'attachment';
    return String(n);
  }

  function sequenceVariants(name) {
    var s = String(name == null ? '' : name);
    var out = [];
    function add(v) { if (v && v !== s && out.indexOf(v) < 0) out.push(v); }
    add(s.replace(/\d+$/, ''));
    add(s.replace(/[_-]?\d+$/, ''));
    add(s.replace(/t\d+$/, 't'));
    add(s.replace(/([a-z_]+)[0-9]+$/i, '$1'));
    return out;
  }

  function installOn(ns, label) {
    if (!ns || ns.__nmm_v0149_done) return false;

    if (!ns.AttachmentType) {
      ns.AttachmentType = { Region: 0, BoundingBox: 1, Mesh: 2, LinkedMesh: 3, Path: 4, Point: 5, Clipping: 6 };
    }

    if (!ns.Attachment) {
      ns.Attachment = function Attachment(name) { this.name = nameOf(name, null, 'attachment'); };
    }

    function Attachment(name) { this.name = nameOf(name, null, 'attachment'); }

    function VertexAttachment(name) {
      Attachment.call(this, name);
      this.id = (window.__nmm_v0149_va_id = (window.__nmm_v0149_va_id || 0) + 1);
      this.bones = null;
      this.vertices = [];
      this.worldVerticesLength = 0;
      this.timelineAttachment = this;
    }
    VertexAttachment.prototype.computeWorldVertices = function(slot, start, count, worldVertices, offset, stride) {
      worldVertices = worldVertices || [];
      stride = stride || 2;
      offset = offset || 0;
      for (var i = 0; i < count; i += 2) {
        worldVertices[offset] = 0;
        worldVertices[offset + 1] = 0;
        offset += stride;
      }
      return worldVertices;
    };
    if (!ns.VertexAttachment) ns.VertexAttachment = VertexAttachment;

    if (!ns.PointAttachment) {
      ns.PointAttachment = function PointAttachment(name) {
        Attachment.call(this, name);
        this.type = ns.AttachmentType.Point;
        this.x = 0; this.y = 0; this.rotation = 0; this.color = makeColor(ns);
      };
      ns.PointAttachment.prototype.computeWorldPosition = function(bone, point) {
        point = point || { x: 0, y: 0 };
        var x = this.x || 0, y = this.y || 0;
        if (bone && typeof bone.localToWorld === 'function') return bone.localToWorld({x:x,y:y});
        if (bone) {
          point.x = x * (bone.a || 1) + y * (bone.b || 0) + (bone.worldX || bone.x || 0);
          point.y = x * (bone.c || 0) + y * (bone.d || 1) + (bone.worldY || bone.y || 0);
        } else { point.x = x; point.y = y; }
        return point;
      };
      ns.PointAttachment.prototype.computeWorldRotation = function(bone) { return this.rotation || 0; };
    }

    if (!ns.BoundingBoxAttachment) {
      ns.BoundingBoxAttachment = function BoundingBoxAttachment(name) {
        VertexAttachment.call(this, name);
        this.type = ns.AttachmentType.BoundingBox;
        this.color = makeColor(ns);
      };
      ns.BoundingBoxAttachment.prototype = Object.create(VertexAttachment.prototype);
      ns.BoundingBoxAttachment.prototype.constructor = ns.BoundingBoxAttachment;
    }

    if (!ns.PathAttachment) {
      ns.PathAttachment = function PathAttachment(name) {
        VertexAttachment.call(this, name);
        this.type = ns.AttachmentType.Path;
        this.lengths = [];
        this.closed = false;
        this.constantSpeed = false;
        this.color = makeColor(ns);
      };
      ns.PathAttachment.prototype = Object.create(VertexAttachment.prototype);
      ns.PathAttachment.prototype.constructor = ns.PathAttachment;
    }

    if (!ns.ClippingAttachment) {
      ns.ClippingAttachment = function ClippingAttachment(name) {
        VertexAttachment.call(this, name);
        this.type = ns.AttachmentType.Clipping;
        this.endSlot = null;
        this.color = makeColor(ns);
      };
      ns.ClippingAttachment.prototype = Object.create(VertexAttachment.prototype);
      ns.ClippingAttachment.prototype.constructor = ns.ClippingAttachment;
    }

    if (!ns.RegionAttachment) {
      ns.RegionAttachment = function RegionAttachment(name) {
        Attachment.call(this, name);
        this.type = ns.AttachmentType.Region;
        this.path = this.name;
        this.x = 0; this.y = 0; this.scaleX = 1; this.scaleY = 1; this.rotation = 0;
        this.width = 0; this.height = 0; this.color = makeColor(ns);
        this.region = null; this.offset = [0,0,0,0,0,0,0,0]; this.uvs = [0,0,1,0,1,1,0,1];
      };
      ns.RegionAttachment.prototype.updateOffset = function() {};
      ns.RegionAttachment.prototype.setRegion = function(region) { this.region = region; };
      ns.RegionAttachment.prototype.computeWorldVertices = function(bone, worldVertices, offset, stride) {
        worldVertices = worldVertices || [];
        stride = stride || 2;
        offset = offset || 0;
        for (var i = 0; i < 4; i++) { worldVertices[offset] = 0; worldVertices[offset + 1] = 0; offset += stride; }
        return worldVertices;
      };
    }

    if (!ns.SequenceMode) ns.SequenceMode = { hold: 0, once: 1, loop: 2, pingpong: 3, onceReverse: 4, loopReverse: 5, pingpongReverse: 6 };
    if (!ns.Sequence) {
      ns.Sequence = function Sequence(count) { this.id = 0; this.regions = new Array(count || 0); this.start = 0; this.digits = 0; this.setupIndex = 0; };
      ns.Sequence.prototype.apply = function(slot, attachment) { return attachment; };
      ns.Sequence.prototype.getPath = function(basePath, index) { return String(basePath || '') + String(index || ''); };
    }

    if (!ns.AtlasAttachmentLoader) {
      ns.AtlasAttachmentLoader = function AtlasAttachmentLoader(atlas) { this.atlas = atlas; };
      ns.AtlasAttachmentLoader.prototype._find = function(path) {
        if (!this.atlas || typeof this.atlas.findRegion !== 'function') return null;
        var r = this.atlas.findRegion(path);
        if (r) return r;
        var vs = sequenceVariants(path);
        for (var i=0;i<vs.length;i++) { r = this.atlas.findRegion(vs[i]); if (r) return r; }
        return null;
      };
      ns.AtlasAttachmentLoader.prototype.newRegionAttachment = function(skin, name, path) {
        var n = nameOf(name, path, 'region');
        var p = nameOf(path, name, n);
        var a = new ns.RegionAttachment(n);
        a.path = p;
        a.region = this._find(p) || this._find(n);
        return a;
      };
      ns.AtlasAttachmentLoader.prototype.newMeshAttachment = function(skin, name, path) {
        var n = nameOf(name, path, 'mesh');
        var p = nameOf(path, name, n);
        var C = ns.MeshAttachment || ns.RegionAttachment;
        var a = new C(n);
        a.path = p;
        a.region = this._find(p) || this._find(n);
        return a;
      };
      ns.AtlasAttachmentLoader.prototype.newBoundingBoxAttachment = function(skin, name) { return new ns.BoundingBoxAttachment(nameOf(name, null, 'bbox')); };
      ns.AtlasAttachmentLoader.prototype.newPathAttachment = function(skin, name) { return new ns.PathAttachment(nameOf(name, null, 'path')); };
      ns.AtlasAttachmentLoader.prototype.newPointAttachment = function(skin, name) { return new ns.PointAttachment(nameOf(name, null, 'point')); };
      ns.AtlasAttachmentLoader.prototype.newClippingAttachment = function(skin, name) { return new ns.ClippingAttachment(nameOf(name, null, 'clip')); };
    }

    // Alias names used by different pixi-spine builds.
    if (!ns.AttachmentType.Point && ns.AttachmentType.point != null) ns.AttachmentType.Point = ns.AttachmentType.point;
    ns.__nmm_v0149_done = true;
    return true;
  }

  function patchAtlas(ns) {
    if (!ns || !ns.TextureAtlas || !ns.TextureAtlas.prototype) return false;
    var p = ns.TextureAtlas.prototype;
    if (p.__nmm_v0149_findRegion) return true;
    var original = p.findRegion;
    if (typeof original !== 'function') return false;
    p.findRegion = function(name) {
      var r = original.call(this, name);
      if (r) return r;
      var vs = sequenceVariants(name);
      for (var i=0;i<vs.length;i++) { try { r = original.call(this, vs[i]); if (r) return r; } catch(e){} }
      return null;
    };
    p.__nmm_v0149_findRegion = true;
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

  window.__nmmInstallRuntimeCompat = function() {
    var ok = false;
    var ns = namespaces();
    for (var i=0;i<ns.length;i++) {
      try { ok = installOn(ns[i], 'ns'+i) || ok; } catch(e) { console.warn('NMM v0.14.9 installOn failed', e); }
      try { ok = patchAtlas(ns[i]) || ok; } catch(e) { console.warn('NMM v0.14.9 patchAtlas failed', e); }
    }
    try { window.__nmmPatchSpineAtlasSequences && window.__nmmPatchSpineAtlasSequences(); } catch(e) {}
    return ok;
  };

  var tries = 0;
  var timer = setInterval(function(){
    tries++;
    if (window.__nmmInstallRuntimeCompat() || tries > 600) clearInterval(timer);
  }, 20);
  setTimeout(window.__nmmInstallRuntimeCompat, 10);
  setTimeout(window.__nmmInstallRuntimeCompat, 200);
  setTimeout(window.__nmmInstallRuntimeCompat, 800);
})();
// --- end NMM v0.14.9 -------------------------------------------------------
'''

for root in roots:
    appjs = root / 'web' / 'app.js'
    js = appjs.read_text(encoding='utf-8', errors='ignore')
    appjs.with_suffix('.js.bak_v0149_runtimecompat').write_text(js, encoding='utf-8')

    js = js.replace('Classic v0.14.8 RuntimeDiagnosticTop', 'Classic v0.14.9 RuntimeCompat')
    js = js.replace('Classic v0.14.7 RuntimeDiagnostic', 'Classic v0.14.9 RuntimeCompat')
    js = js.replace('Debug v0.14.8', 'Debug v0.14.9')
    js = js.replace('DEBUG v0.14.8', 'DEBUG v0.14.9')
    js = js.replace('Debug v0.14.7', 'Debug v0.14.9')
    js = js.replace('DEBUG v0.14.7', 'DEBUG v0.14.9')
    js = js.replace('NMM RUNTIME DIAGNOSTIC v0.14.8', 'NMM RUNTIME DIAGNOSTIC v0.14.9')
    js = js.replace('DIAGNÓSTICO RUNTIME v0.14.8', 'DIAGNÓSTICO RUNTIME v0.14.9')

    if 'NMM v0.14.9 Runtime Attachment Compatibility Polyfill' not in js:
        lines = js.splitlines()
        out = []
        for line in lines:
            trigger = (
                ('readSkeletonData' in line or 'new ' in line)
                and any(k in line for k in ['TextureAtlas', 'AtlasAttachmentLoader', 'SkeletonBinary', 'SkeletonJson', 'readSkeletonData'])
                and '__nmmInstallRuntimeCompat' not in line
            )
            if trigger:
                out.append('      try { window.__nmmInstallRuntimeCompat && window.__nmmInstallRuntimeCompat(); } catch(e) {}')
            out.append(line)
        js = '\n'.join(out) + '\n' + PATCH + '\n'
    appjs.write_text(js, encoding='utf-8')

    preview = root / 'src' / 'preview.py'
    if preview.exists():
        ps = preview.read_text(encoding='utf-8', errors='ignore')
        preview.with_suffix('.py.bak_v0149_runtimecompat').write_text(ps, encoding='utf-8')
        ps = ps.replace('Classic v0.14.8 RuntimeDiagnosticTop', 'Classic v0.14.9 RuntimeCompat')
        ps = ps.replace('Classic v0.14.7 RuntimeDiagnostic', 'Classic v0.14.9 RuntimeCompat')
        ps = ps.replace('Debug v0.14.8', 'Debug v0.14.9')
        ps = ps.replace('DEBUG v0.14.8', 'DEBUG v0.14.9')
        ps = ps.replace('Debug v0.14.7', 'Debug v0.14.9')
        ps = ps.replace('DEBUG v0.14.7', 'DEBUG v0.14.9')
        compile(ps, str(preview), 'exec')
        preview.write_text(ps, encoding='utf-8')

    for rel in ['VERSION.txt', 'LEEME_PRIMERO.txt', 'DIAGNOSTICO_RUNTIME.md']:
        p = root / rel
        old = p.read_text(encoding='utf-8', errors='ignore') if p.exists() and rel != 'DIAGNOSTICO_RUNTIME.md' else ''
        p.write_text(
            'NIKKE Mod Manager v0.14.9 Classic Integrated Viewer RuntimeCompat FULL\n\n'
            'Agrega polyfill de attachments Spine faltantes: Point, BoundingBox, Path, Clipping, Region y AtlasAttachmentLoader.\n'
            'Mantiene diagnóstico visible y botón Copiar diagnóstico.\n\n' + old,
            encoding='utf-8'
        )

    target = root.parent / 'NIKKE_Mod_Manager_v0_14_9_Classic_Integrated_Viewer_RUNTIMECOMPAT_FULL'
    if root != target:
        if target.exists():
            shutil.rmtree(target)
        root.rename(target)
        root = target

    final_js = (root / 'web' / 'app.js').read_text(encoding='utf-8', errors='ignore')
    assert 'NMM v0.14.9 Runtime Attachment Compatibility Polyfill' in final_js
    print('patched', root)
