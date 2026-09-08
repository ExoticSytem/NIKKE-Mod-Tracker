from pathlib import Path
import shutil

ROOT = Path('extracted')
roots = [p.parent.parent for p in ROOT.rglob('web/app.js')]
if not roots:
    raise SystemExit('No encontré web/app.js dentro del artifact extraído')

PATCH = r'''

// --- NMM v0.14.8 Visible Diagnostic Top Button -----------------------------
(function () {
  if (window.__NMM_V0148_DIAG_TOP__) return;
  window.__NMM_V0148_DIAG_TOP__ = true;

  function diagText() {
    try {
      if (typeof window.__nmmRuntimeDiagnostic === 'function') {
        return window.__nmmRuntimeDiagnostic();
      }
    } catch (e) {}
    try {
      return 'NMM RUNTIME DIAGNOSTIC v0.14.8\n' + ((document.body && document.body.innerText) || '').slice(0, 8000);
    } catch (e) {
      return 'NMM RUNTIME DIAGNOSTIC v0.14.8\nNo pude leer diagnóstico: ' + String(e);
    }
  }

  function copy(txt, btn) {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(txt).then(function () {
          if (btn) btn.textContent = 'Diagnóstico copiado';
        }).catch(function () {
          window.prompt('Copia este diagnóstico completo:', txt);
        });
      } else {
        window.prompt('Copia este diagnóstico completo:', txt);
      }
    } catch (e) {
      window.prompt('Copia este diagnóstico completo:', txt);
    }
  }

  function ensureTopButton() {
    try {
      var btn = document.getElementById('nmm-diag-top-copy-button');
      if (!btn) {
        btn = document.createElement('button');
        btn.id = 'nmm-diag-top-copy-button';
        btn.textContent = 'Copiar diagnóstico';
        btn.style.cssText = [
          'position:fixed',
          'top:70px',
          'right:82px',
          'z-index:2147483647',
          'padding:10px 14px',
          'border-radius:10px',
          'border:2px solid #facc15',
          'background:#facc15',
          'color:#111827',
          'font-weight:900',
          'font-family:Segoe UI,Arial,sans-serif',
          'font-size:13px',
          'cursor:pointer',
          'box-shadow:0 6px 24px rgba(0,0,0,.45)'
        ].join(';');
        btn.onclick = function () { copy(diagText(), btn); };
        document.body.appendChild(btn);
      }

      var host = document.querySelector('#previewContent') ||
                 document.querySelector('.preview-content') ||
                 document.querySelector('#previewModal .modal-content') ||
                 document.querySelector('.modal-content');
      if (host && !document.getElementById('nmm-diag-top-panel')) {
        var panel = document.createElement('div');
        panel.id = 'nmm-diag-top-panel';
        panel.style.cssText = 'margin:10px 12px;padding:10px;border:2px solid #facc15;border-radius:10px;background:#0f172a;color:#e5e7eb;font:12px/1.35 Consolas,monospace;white-space:pre-wrap;max-height:240px;overflow:auto;position:relative;z-index:999999;';

        var title = document.createElement('div');
        title.textContent = 'DIAGNÓSTICO RUNTIME v0.14.8 — botón visible arriba a la derecha';
        title.style.cssText = 'font-weight:800;color:#facc15;margin-bottom:8px;font-family:Segoe UI,Arial,sans-serif;';

        var localBtn = document.createElement('button');
        localBtn.textContent = 'Copiar diagnóstico';
        localBtn.style.cssText = 'padding:7px 12px;margin:0 8px 8px 0;cursor:pointer;border-radius:7px;border:1px solid #94a3b8;background:#e5e7eb;color:#111827;font-weight:800;';
        localBtn.onclick = function () { copy(diagText(), localBtn); };

        var promptBtn = document.createElement('button');
        promptBtn.textContent = 'Abrir cuadro para copiar';
        promptBtn.style.cssText = 'padding:7px 12px;margin:0 0 8px 0;cursor:pointer;border-radius:7px;border:1px solid #94a3b8;background:#e5e7eb;color:#111827;font-weight:800;';
        promptBtn.onclick = function () { window.prompt('Copia este diagnóstico completo:', diagText()); };

        var pre = document.createElement('pre');
        pre.id = 'nmm-diag-top-text';
        pre.style.cssText = 'margin:0;white-space:pre-wrap;max-height:160px;overflow:auto;';
        pre.textContent = diagText();

        panel.appendChild(title);
        panel.appendChild(localBtn);
        panel.appendChild(promptBtn);
        panel.appendChild(pre);
        host.insertBefore(panel, host.firstChild);
      }

      var pre2 = document.getElementById('nmm-diag-top-text');
      if (pre2) pre2.textContent = diagText();
    } catch (e) {}
  }

  setInterval(ensureTopButton, 700);
  setTimeout(ensureTopButton, 100);
  setTimeout(ensureTopButton, 800);
  setTimeout(ensureTopButton, 1800);
})();
// --- end NMM v0.14.8 -------------------------------------------------------
'''

for root in roots:
    appjs = root / 'web' / 'app.js'
    js = appjs.read_text(encoding='utf-8', errors='ignore')
    appjs.with_suffix('.js.bak_v0148_diagtop').write_text(js, encoding='utf-8')
    js = js.replace('Classic v0.14.7 RuntimeDiagnostic', 'Classic v0.14.8 RuntimeDiagnosticTop')
    js = js.replace('Debug v0.14.7', 'Debug v0.14.8')
    js = js.replace('DEBUG v0.14.7', 'DEBUG v0.14.8')
    js = js.replace('NMM RUNTIME DIAGNOSTIC v0.14.7', 'NMM RUNTIME DIAGNOSTIC v0.14.8')
    js = js.replace('DIAGNÓSTICO RUNTIME v0.14.7', 'DIAGNÓSTICO RUNTIME v0.14.8')
    if 'NMM v0.14.8 Visible Diagnostic Top Button' not in js:
        js += '\n' + PATCH + '\n'
    appjs.write_text(js, encoding='utf-8')

    preview = root / 'src' / 'preview.py'
    if preview.exists():
        ps = preview.read_text(encoding='utf-8', errors='ignore')
        preview.with_suffix('.py.bak_v0148_diagtop').write_text(ps, encoding='utf-8')
        ps = ps.replace('Classic v0.14.7 RuntimeDiagnostic', 'Classic v0.14.8 RuntimeDiagnosticTop')
        ps = ps.replace('Debug v0.14.7', 'Debug v0.14.8')
        ps = ps.replace('DEBUG v0.14.7', 'DEBUG v0.14.8')
        compile(ps, str(preview), 'exec')
        preview.write_text(ps, encoding='utf-8')

    for rel in ['VERSION.txt', 'LEEME_PRIMERO.txt', 'DIAGNOSTICO_RUNTIME.md']:
        p = root / rel
        old = p.read_text(encoding='utf-8', errors='ignore') if p.exists() and rel != 'DIAGNOSTICO_RUNTIME.md' else ''
        p.write_text(
            'NIKKE Mod Manager v0.14.8 Classic Integrated Viewer RuntimeDiagnosticTop FULL\n\n'
            'Versión diagnóstico con botón amarillo fijo arriba a la derecha para copiar el diagnóstico.\n'
            'Abre c015_00_aim; cuando falle, pulsa Copiar diagnóstico y pega el texto completo en el chat.\n\n' + old,
            encoding='utf-8'
        )

    target = root.parent / 'NIKKE_Mod_Manager_v0_14_8_Classic_Integrated_Viewer_RUNTIME_DIAGNOSTIC_TOP_FULL'
    if root != target:
        if target.exists():
            shutil.rmtree(target)
        root.rename(target)
        root = target

    final_js = (root / 'web' / 'app.js').read_text(encoding='utf-8', errors='ignore')
    assert 'NMM v0.14.8 Visible Diagnostic Top Button' in final_js
    assert 'nmm-diag-top-copy-button' in final_js
    print('patched', root)
