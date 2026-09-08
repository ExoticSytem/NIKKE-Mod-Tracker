from pathlib import Path
import re
import shutil

ROOT = Path('extracted')
roots = [p.parent.parent for p in ROOT.rglob('web/app.js')]
if not roots:
    raise SystemExit('No encontré web/app.js dentro del artifact extraído')

AUTO_EXPR = '"__nmm_auto_attachment_" + ((typeof window !== "undefined" && (window.__nmm_auto_attachment_id = (window.__nmm_auto_attachment_id || 0) + 1)) || Math.floor(Math.random()*1000000))'

def patch_attachment_throw(text: str) -> tuple[str, int]:
    before = text

    # Caso multilinea típico del runtime Spine:
    # if (name == null)
    #     throw new Error("Attachment name must not be null");
    patterns = [
        (r'if\s*\(\s*name\s*==\s*null\s*\)\s*\{\s*throw\s+new\s+Error\(\s*["\']Attachment name must not be null["\']\s*\)\s*;\s*\}',
         'if (name == null) { name = ' + AUTO_EXPR + '; }'),
        (r'if\s*\(\s*name\s*==\s*null\s*\)\s*throw\s+new\s+Error\(\s*["\']Attachment name must not be null["\']\s*\)\s*;',
         'if (name == null) name = ' + AUTO_EXPR + ';'),
        (r'if\s*\(\s*name\s*==\s*null\s*\)\s*\n\s*throw\s+new\s+Error\(\s*["\']Attachment name must not be null["\']\s*\)\s*;',
         'if (name == null) name = ' + AUTO_EXPR + ';'),
    ]
    count = 0
    for pat, repl in patterns:
        text, n = re.subn(pat, repl, text, flags=re.M)
        count += n

    # Fallback extra: reemplaza únicamente el throw literal cuando sigue quedando.
    literal = 'throw new Error("Attachment name must not be null");'
    if literal in text:
        text = text.replace(literal, 'name = ' + AUTO_EXPR + ';')
        count += before.count(literal)
    literal2 = "throw new Error('Attachment name must not be null');"
    if literal2 in text:
        text = text.replace(literal2, 'name = ' + AUTO_EXPR + ';')
        count += before.count(literal2)

    return text, count

for root in roots:
    print('root', root)

    changed_total = 0
    for rel in [
        'web/assets/vendor/nikke-spine-runtime.js',
        'web/assets/vendor/viewer/pixi-spine.js',
        'web/assets/vendor/pixi-spine.umd.js',
        'web/app.js',
    ]:
        p = root / rel
        if not p.exists():
            print('missing', rel)
            continue
        s = p.read_text(encoding='utf-8', errors='ignore')
        p.with_suffix(p.suffix + '.bak_v0151_vendor_attachment').write_text(s, encoding='utf-8')
        ns, n = patch_attachment_throw(s)
        ns = ns.replace('v0.15.0', 'v0.15.1')
        ns = ns.replace('DEBUG v0.15.0', 'DEBUG v0.15.1')
        ns = ns.replace('Debug v0.15.0', 'Debug v0.15.1')
        ns = ns.replace('NMM RUNTIME DIAGNOSTIC v0.15.0', 'NMM RUNTIME DIAGNOSTIC v0.15.1')
        ns = ns.replace('Classic v0.15.0 AttachmentSafe', 'Classic v0.15.1 VendorAttachmentFix')
        p.write_text(ns, encoding='utf-8')
        changed_total += n
        print(rel, 'attachment_throw_replacements=', n)

    if changed_total <= 0:
        raise SystemExit('No se reemplazó ningún throw de Attachment name must not be null')

    # Marker and version notes
    marker_js = root / 'web' / 'app.js'
    js = marker_js.read_text(encoding='utf-8', errors='ignore')
    marker = "\n// NMM v0.15.1 marker: vendor attachment constructor throw patched\nwindow.__NMM_VENDOR_ATTACHMENT_THROW_PATCH__ = true;\n"
    if '__NMM_VENDOR_ATTACHMENT_THROW_PATCH__' not in js:
        js += marker
    marker_js.write_text(js, encoding='utf-8')

    for rel in ['VERSION.txt', 'LEEME_PRIMERO.txt', 'DIAGNOSTICO_RUNTIME.md']:
        p = root / rel
        old = p.read_text(encoding='utf-8', errors='ignore') if p.exists() and rel != 'DIAGNOSTICO_RUNTIME.md' else ''
        p.write_text(
            'NIKKE Mod Manager v0.15.1 Classic Integrated Viewer VendorAttachmentFix FULL\n\n'
            'Parche directo a los runtimes vendor: el constructor Attachment ya no lanza error si name viene null; asigna un nombre seguro automático.\n'
            'Mantiene diagnóstico visible, atlas preserve, canvas expandido y fixes anteriores.\n\n' + old,
            encoding='utf-8'
        )

    target = root.parent / 'NIKKE_Mod_Manager_v0_15_1_Classic_Integrated_Viewer_VENDOR_ATTACHMENT_FIX_FULL'
    if root != target:
        if target.exists():
            shutil.rmtree(target)
        root.rename(target)
        root = target

    # Verificación: no debe quedar el throw literal en los runtimes vendor.
    for rel in ['web/assets/vendor/nikke-spine-runtime.js','web/assets/vendor/viewer/pixi-spine.js','web/assets/vendor/pixi-spine.umd.js']:
        p = root / rel
        if p.exists():
            txt = p.read_text(encoding='utf-8', errors='ignore')
            if 'throw new Error("Attachment name must not be null")' in txt or 'throw new Error("Attachment name must not be null");' in txt:
                raise SystemExit('Sigue quedando throw literal en ' + rel)

    print('patched OK', root, 'total replacements', changed_total)
