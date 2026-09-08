from pathlib import Path
import shutil
import zipfile

OUT_NAME = 'NIKKE_Mod_Manager_v0_14_8_Classic_Integrated_Viewer_RUNTIME_DIAGNOSTIC_TOP_FULL'
ROOT = Path('extracted')

JS_PATCH = r'''

// --- NMM v0.14.8 Visible Diagnostic Copy Patch -----------------------------
(function () {
  if (window.__NMM_V0148_VISIBLE_DIAG__) return;
  window.__NMM_V0148_VISIBLE_DIAG__ = true;

  function getDiagText() {
    try {
      if (typeof window.__nmmRuntimeDiagnostic === 'function') {
        return window.__nmmRuntimeDiagnostic();
      }
    } catch (e) {}
    try {
      var text = (document.body && document.body.innerText) || '';
      return 'NMM RUNTIME DIAGNOSTIC v0.14.8\n' + text.slice(0, 9000);
    } catch (e) {
      return 'NMM RUNTIME DIAGNOSTIC v0.14.8\nNo pude leer diagnóstico: ' + String(e);
    }
  }

  function copyText(txt, btn) {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(txt).then(function(){
          if (btn) btn.textContent = 'Diagnóstico copiado';
        }).catch(function(){ window.prompt('Copia este diagnóstico completo:', txt); });
      } else {
        window.prompt('Copia este diagnóstico completo:', txt);
      }
    } catch (e) {
      window.prompt('Copia este diagnóstico completo:', txt);
    }
  }

  function makePanel(host) {
    var panel = document.getElementById('nmm-visible-diagnostic-panel');
    if (panel) return panel;

    panel = document.createElement('div');
    panel.id = 'nmm-visible-diagnostic-panel';
    panel.style.cssText = [
      'margin:10px 12px',
      'padding:10px',
      'border:2px solid #facc15',
      'border-radius:10px',
      'background:#0f172a',
      'color:#e5e7eb',
      'font:12px/1.35 Consolas,monospace',
      'max-height:260px',
      'overflow:auto',
      'white-space:pre-wrap',
      'position:relative',
      'z-index:999999'
    ].join(';');

    var title = document.createElement('div');
    title.textContent = 'DIAGNÓSTICO RUNTIME v0.14.8 — botón visible arriba';
    title.style.cssText = 'font-weight:700;color:#facc15;margin-bottom:8px;font-family:system-ui,Segoe UI,sans-serif;';

    var btn = document.createElement('button');
    btn.textContent = 'Copiar diagnóstico';
    btn.style.cssText = 'padding:7px 12px;margin:0 8px 8px 0;cursor:pointer;border-radius:6px;border:1px solid #94a3b8;background:#e5e7eb;color:#111827;font-weight:700;';
    btn.onclick = function(){ copyText(getDiagText(), btn); };

    var btnPrompt = document.createElement('button');
    btnPrompt.textContent = 'Abrir cuadro para copiar';
    btnPrompt.style.cssText = 'padding:7px 12px;margin:0 0 8px 0;cursor:pointer;border-radius:6px;border:1px solid #94a3b8;background:#e5e7eb;color:#111827;font-weight:700;';
    btnPrompt.onclick = function(){ window.prompt('Copia este diagnóstico completo:', getDiagText()); };

    var pre = document.createElement('pre');
    pre.id = 'nmm-visible-diagnostic-text';
    pre.style.cssText = 'margin:0;white-space:pre-wrap;max-height:190px;overflow:auto;';
    pre.textContent = getDiagText();

    panel.appendChild(title);
    panel.appendChild(btn);
    panel.appendChild(btnPrompt);
    panel.appendChild(pre);
    host.insertBefore(panel, host.firstChild);
    return panel;
  }

  function injectVisibleDiag() {
    try {
      var bodyText = (document.body && document.body.innerText) || '';
      if (bodyText.indexOf('No se pudo armar') < 0 &&
          bodyText.indexOf('PointAttachment') < 0 &&
          bodyText.indexOf('MeshAttachment') < 0 &&
          bodyText.indexOf('DEBUG v0.14') < 0 &&
          bodyText.indexOf('Mostrando textura fallback') < 0) return;

      var host = document.querySelector('#previewContent') ||
                 document.querySelector('.preview-content') ||
                 document.querySelector('#previewModal .modal-content') ||
                 document.querySelector('.modal-content') ||
                 document.body;
      if (!host) return;

      var panel = makePanel(host);
      var pre = document.getElementById('nmm-visible-diagnostic-text');
      if (pre) pre.textContent = getDiagText();

      var floatBtn = document.getElementById('nmm-floating-copy-diagnostic');
      if (!floatBtn) {
        floatBtn = document.createElement('button');
        floatBtn.id = 'nmm-floating-copy-diagnostic';
        floatBtn.textContent = 'Copiar diagnóstico';
        floatBtn.style.cssText = 'position:fixed;right:72px;top:72px;z-index:2147483647;padding:9px 13px;border-radius:8px;border:2px solid #facc15;background:#facc15;color:#111827;font-weight:800;cursor:pointer;box-shadow:0 4px 18px rgba(0,0,0,.35);';
        floatBtn.onclick = function(){ copyText(getDiagText(), floatBtn); };
        document.body.appendChild(floatBtn);
      }
    } catch(e) {}
  }

  setInterval(injectVisibleDiag, 700);
  setTimeout(injectVisibleDiag, 400);
  setTimeout(injectVisibleDiag, 1200);
  setTimeout(injectVisibleDiag, 2500);
})();
// --- end NMM v0.14.8 --------------------------------------------------------
'''

def patch_file_text(path: Path, is_js: bool) -> None:
    text = path.read_text(encoding='utf-8', errors='ignore')
    path.with_suffix(path.suffix + '.bak_v0148_diag_top').write_text(text, encoding='utf-8')
    replacements = {
        'Classic v0.14.7 RuntimeDiagnostic': 'Classic v0.14.8 RuntimeDiagnosticTop',
        'Classic v0.14.6 MeshFallback': 'Classic v0.14.8 RuntimeDiagnosticTop',
        'Debug v0.14.7': 'Debug v0.14.8',
        'DEBUG v0.14.7': 'DEBUG v0.14.8',
        'Debug v0.14.6': 'Debug v0.14.8',
        'DEBUG v0.14.6': 'DEBUG v0.14.8',
        'NMM RUNTIME DIAGNOSTIC v0.14.7': 'NMM RUNTIME DIAGNOSTIC v0.14.8',
        'DIAGNÓSTICO RUNTIME v0.14.7': 'DIAGNÓSTICO RUNTIME v0.14.8',
        'DIAGNOSTICO RUNTIME v0.14.7': 'DIAGNOSTICO RUNTIME v0.14.8',
    }
    for a, b in replacements.items():
        text = text.replace(a, b)
    if is_js and 'NMM v0.14.8 Visible Diagnostic Copy Patch' not in text:
        text += '\n' + JS_PATCH + '\n'
    if path.name == 'preview.py':
        compile(text, str(path), 'exec')
    path.write_text(text, encoding='utf-8')

def main():
    roots = [p.parent.parent for p in ROOT.rglob('web/app.js')]
    if not roots:
        raise SystemExit('No app roots found')

    for root in roots:
        appjs = root / 'web' / 'app.js'
        patch_file_text(appjs, True)
        preview = root / 'src' / 'preview.py'
        if preview.exists():
            patch_file_text(preview, False)

        for rel in ['VERSION.txt', 'LEEME_PRIMERO.txt', 'DIAGNOSTICO_RUNTIME.md']:
            p = root / rel
            old = p.read_text(encoding='utf-8', errors='ignore') if p.exists() and rel != 'DIAGNOSTICO_RUNTIME.md' else ''
            p.write_text(
                'NIKKE Mod Manager v0.14.8 Classic Integrated Viewer RuntimeDiagnosticTop FULL\n\n'
                'Version diagnostico con boton flotante visible para copiar el diagnostico. '\
                'Cuando falle el preview, pulsa el boton amarillo Copiar diagnostico arriba a la derecha.\n\n' + old,
                encoding='utf-8',
            )

        target = root.parent / OUT_NAME
        if root != target:
            if target.exists():
                shutil.rmtree(target)
            root.rename(target)

    out = Path('dist')
    out.mkdir(exist_ok=True)
    zip_path = out / (OUT_NAME + '.zip')
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for p in Path('extracted').rglob('*'):
            if p.is_file():
                z.write(p, p.relative_to(Path('extracted')))
    with zipfile.ZipFile(zip_path) as z:
        bad = z.testzip()
        if bad:
            raise RuntimeError('zip corrupto: ' + bad)
    print(zip_path, zip_path.stat().st_size)

if __name__ == '__main__':
    main()
