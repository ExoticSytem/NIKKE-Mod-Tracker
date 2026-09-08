from pathlib import Path

JS_DIAG = r'''

// --- NMM v0.14.7 Runtime Diagnostic SIMPLE ---------------------------------
(function () {
  if (window.__NMM_V0147_RUNTIME_DIAG_SIMPLE__) return;
  window.__NMM_V0147_RUNTIME_DIAG_SIMPLE__ = true;
  window.__nmmDiagErrors = window.__nmmDiagErrors || [];

  function errText(err) {
    try {
      if (!err) return '';
      if (err.message) return err.message;
      if (err.reason && err.reason.message) return err.reason.message;
      return String(err);
    } catch(e) { return 'error converting error'; }
  }
  function pushErr(type, err) {
    try {
      window.__nmmDiagErrors.push({
        time: new Date().toISOString(),
        type: type,
        message: errText(err),
        stack: String((err && err.stack) || (err && err.error && err.error.stack) || '').slice(0, 1500)
      });
      if (window.__nmmDiagErrors.length > 30) window.__nmmDiagErrors.shift();
    } catch(e) {}
  }
  window.addEventListener('error', function(e){ pushErr('window.error', e.error || e.message || e); });
  window.addEventListener('unhandledrejection', function(e){ pushErr('unhandledrejection', e.reason || e); });

  function add(arr, label, obj) {
    if (obj && arr.every(function(x){ return x.obj !== obj; })) arr.push({label: label, obj: obj});
  }
  function namespaces() {
    var P = window.PIXI, a = [];
    add(a, 'window.spine', window.spine);
    add(a, 'window.spine.core', window.spine && window.spine.core);
    add(a, 'window.spine38', window.spine38);
    add(a, 'window.spine41', window.spine41);
    add(a, 'window.pixi_spine', window.pixi_spine);
    add(a, 'window.pixi_spine.core', window.pixi_spine && window.pixi_spine.core);
    add(a, 'window.pixi_spine.base', window.pixi_spine && window.pixi_spine.base);
    add(a, 'window.pixi_spine.spine37', window.pixi_spine && window.pixi_spine.spine37);
    add(a, 'window.pixi_spine.spine38', window.pixi_spine && window.pixi_spine.spine38);
    add(a, 'window.pixi_spine.spine40', window.pixi_spine && window.pixi_spine.spine40);
    add(a, 'window.pixi_spine.spine41', window.pixi_spine && window.pixi_spine.spine41);
    add(a, 'PIXI.spine', P && P.spine);
    add(a, 'PIXI.spine.core', P && P.spine && P.spine.core);
    add(a, 'PIXI.spine.base', P && P.spine && P.spine.base);
    add(a, 'PIXI.spine.spine37', P && P.spine && P.spine.spine37);
    add(a, 'PIXI.spine.spine38', P && P.spine && P.spine.spine38);
    add(a, 'PIXI.spine.spine40', P && P.spine && P.spine.spine40);
    add(a, 'PIXI.spine.spine41', P && P.spine && P.spine.spine41);
    return a;
  }
  var classes = [
    'TextureAtlas','TextureAtlasPage','TextureAtlasRegion','AtlasAttachmentLoader',
    'SkeletonBinary','SkeletonJson','Skeleton','Spine','Skin','Slot','SlotData','Bone','BoneData',
    'RegionAttachment','MeshAttachment','PointAttachment','BoundingBoxAttachment','PathAttachment','ClippingAttachment',
    'Attachment','AttachmentType','Sequence','SequenceMode','Animation','AnimationState','AnimationStateData',
    'IkConstraint','TransformConstraint','PathConstraint','Event','EventData','Color','Vector2','Utils','BinaryInput'
  ];
  function classLine(ns) {
    var ok = [], missing = [];
    classes.forEach(function(k){
      var v = ns && ns[k];
      ((typeof v === 'function' || (typeof v === 'object' && v !== null)) ? ok : missing).push(k);
    });
    return {ok: ok, missing: missing};
  }
  function scripts() {
    try {
      return Array.prototype.slice.call(document.scripts).map(function(s){ return s.getAttribute('src') || '[inline]'; }).filter(Boolean);
    } catch(e) { return []; }
  }
  function previewText() {
    try {
      var best = '';
      Array.prototype.slice.call(document.querySelectorAll('div,section,main,article')).forEach(function(el){
        var t = el.innerText || '';
        if ((t.indexOf('No se pudo armar') >= 0 || t.indexOf('DEBUG v0.14') >= 0) && (best === '' || t.length < best.length)) best = t;
      });
      return (best || (document.body && document.body.innerText) || '').replace(/\s+/g, ' ').slice(0, 2500);
    } catch(e) { return ''; }
  }
  function diag() {
    var P = window.PIXI;
    var ns = namespaces();
    var lines = [];
    lines.push('NMM RUNTIME DIAGNOSTIC v0.14.7');
    lines.push('PIXI=' + (!!P) + (P && P.VERSION ? ' version=' + P.VERSION : ''));
    lines.push('href=' + location.href);
    lines.push('userAgent=' + navigator.userAgent);
    lines.push('scripts=' + scripts().join(' | '));
    lines.push('namespaces=' + ns.map(function(x){ return x.label; }).join(', '));
    ns.forEach(function(x){
      var m = classLine(x.obj);
      lines.push('[' + x.label + '] OK=' + m.ok.join(','));
      lines.push('[' + x.label + '] MISSING=' + m.missing.join(','));
    });
    if (window.__nmmDiagErrors && window.__nmmDiagErrors.length) lines.push('ERRORS=' + JSON.stringify(window.__nmmDiagErrors.slice(-10)));
    lines.push('VISIBLE_PREVIEW=' + previewText());
    return lines.join('\n');
  }
  window.__nmmRuntimeDiagnostic = diag;

  function findHost() {
    var candidates = ['#previewContent', '#previewModal', '.preview-content', '.preview-modal', '.modal-content'];
    for (var i=0;i<candidates.length;i++) {
      var el = document.querySelector(candidates[i]);
      if (el) return el;
    }
    var nodes = Array.prototype.slice.call(document.querySelectorAll('div,section,main,article'));
    var found = null;
    nodes.forEach(function(el){
      if (found) return;
      var t = el.innerText || '';
      if (t.indexOf('No se pudo armar') >= 0 || t.indexOf('DEBUG v0.14') >= 0 || t.indexOf('Mostrando textura fallback') >= 0) found = el;
    });
    return found || document.body;
  }
  function inject() {
    try {
      var t = (document.body && document.body.innerText) || '';
      if (t.indexOf('No se pudo armar') < 0 && t.indexOf('DEBUG v0.14') < 0 && t.indexOf('Mostrando textura fallback') < 0) return;
      var host = findHost();
      if (!host) return;
      var wrap = document.getElementById('nmm-runtime-diagnostic-wrap');
      var box;
      if (!wrap) {
        wrap = document.createElement('div');
        wrap.id = 'nmm-runtime-diagnostic-wrap';
        wrap.style.cssText = 'margin:12px;padding:12px;border:1px solid #facc15;border-radius:8px;background:#0b1220;color:#e5e7eb;font:12px/1.35 Consolas,monospace;white-space:pre-wrap;max-height:380px;overflow:auto;';
        var title = document.createElement('div');
        title.textContent = 'DIAGNÓSTICO RUNTIME v0.14.7 — copiar y enviar este bloque completo';
        title.style.cssText = 'font-weight:bold;color:#facc15;margin-bottom:8px;';
        var btn = document.createElement('button');
        btn.textContent = 'Copiar diagnóstico';
        btn.style.cssText = 'margin-bottom:8px;padding:6px 10px;cursor:pointer;';
        box = document.createElement('pre');
        box.id = 'nmm-runtime-diagnostic-box';
        box.style.cssText = 'margin:0;white-space:pre-wrap;';
        btn.onclick = function(){ try { navigator.clipboard.writeText(box.textContent); btn.textContent = 'Copiado'; } catch(e) { alert(box.textContent); } };
        wrap.appendChild(title); wrap.appendChild(btn); wrap.appendChild(box);
        host.appendChild(wrap);
      }
      box = document.getElementById('nmm-runtime-diagnostic-box');
      if (box) box.textContent = diag();
    } catch(e) {}
  }
  setInterval(inject, 1000);
  setTimeout(inject, 1200);
  setTimeout(inject, 3000);
})();
// --- end NMM v0.14.7 --------------------------------------------------------
'''

for root in [p.parent.parent for p in Path('extracted').rglob('web/app.js')]:
    appjs = root / 'web' / 'app.js'
    js = appjs.read_text(encoding='utf-8', errors='ignore')
    appjs.with_suffix('.js.bak_v0147diag').write_text(js, encoding='utf-8')
    for old in ['Classic v0.14.6 MeshFallback', 'Classic v0.14.5 AttachmentNullFix', 'Classic v0.14.4 SequenceAttachFix', 'Classic v0.14.3 AtlasPreserveFix', 'Classic v0.14 Integrated Viewer']:
        js = js.replace(old, 'Classic v0.14.7 RuntimeDiagnostic')
    for old in ['Debug v0.14.6','DEBUG v0.14.6','Debug v0.14.5','DEBUG v0.14.5','Debug v0.14.4','DEBUG v0.14.4','Debug R8','DEBUG R8']:
        js = js.replace(old, 'Debug v0.14.7' if old.startswith('Debug') else 'DEBUG v0.14.7')
    if 'NMM v0.14.7 Runtime Diagnostic SIMPLE' not in js:
        js += '\n' + JS_DIAG + '\n'
    appjs.write_text(js, encoding='utf-8')

    preview = root / 'src' / 'preview.py'
    if preview.exists():
        ps = preview.read_text(encoding='utf-8', errors='ignore')
        preview.with_suffix('.py.bak_v0147diag').write_text(ps, encoding='utf-8')
        for old in ['Classic v0.14.6 MeshFallback', 'Classic v0.14.5 AttachmentNullFix', 'Classic v0.14.4 SequenceAttachFix', 'Classic v0.14.3 AtlasPreserveFix', 'Classic v0.14 Integrated Viewer']:
            ps = ps.replace(old, 'Classic v0.14.7 RuntimeDiagnostic')
        compile(ps, str(preview), 'exec')
        preview.write_text(ps, encoding='utf-8')

    note = ('NIKKE Mod Manager v0.14.7 Classic Integrated Viewer RuntimeDiagnostic FULL\n\n'
            'Esta version es diagnostico, no fix final. En Preview Alpha aparece un bloque amarillo llamado DIAGNOSTICO RUNTIME v0.14.7.\n'
            'Abre c015_00_aim, pulsa Copiar diagnostico y envia ese bloque completo.\n')
    for rel in ['VERSION.txt','LEEME_PRIMERO.txt','DIAGNOSTICO_RUNTIME.md']:
        p = root / rel
        old = p.read_text(encoding='utf-8', errors='ignore') if p.exists() and rel != 'DIAGNOSTICO_RUNTIME.md' else ''
        p.write_text(note + '\n' + old, encoding='utf-8')
    print('patched runtime diagnostic', root)
