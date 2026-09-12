from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

PATCH_ROOT = Path(__file__).resolve().parent
MARKER = "/* NMM v0.34.8: silent character-name clipboard copy */"
JS_BLOCK = r'''

/* NMM v0.34.8: silent character-name clipboard copy */
(function(){
  function silentCopy(text){
    const value=(text||'').trim();
    if(!value) return;
    try{
      if(navigator.clipboard && navigator.clipboard.writeText){
        navigator.clipboard.writeText(value).catch(()=>fallbackCopy(value));
        return;
      }
    }catch(e){}
    fallbackCopy(value);
  }
  function fallbackCopy(value){
    try{
      const ta=document.createElement('textarea');
      ta.value=value;
      ta.setAttribute('readonly','');
      ta.style.position='fixed';
      ta.style.left='-9999px';
      ta.style.top='-9999px';
      ta.style.opacity='0';
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      document.execCommand('copy');
      ta.remove();
    }catch(e){}
  }
  document.addEventListener('click',(ev)=>{
    const target=ev.target && ev.target.closest ? ev.target.closest(
      '.detail-info h1, .detail-info h2, .detail-main h1, .detail-main h2, .detail-head h1, .detail-head h2, .detail-name, .character-detail-name, [data-character-name]'
    ) : null;
    if(!target) return;
    if(!target.closest('.detail-layout, .detail-main, .detail-head')) return;
    const value=(target.dataset && target.dataset.characterName) ? target.dataset.characterName : target.textContent;
    silentCopy(value);
  }, false);
})();
'''

def looks_like_manager(p: Path) -> bool:
    return (p/'app.py').exists() and (p/'web'/'app.js').exists() and (p/'src'/'api.py').exists()

def choose_folder() -> Path | None:
    if looks_like_manager(PATCH_ROOT.parent):
        return PATCH_ROOT.parent
    try:
        import tkinter as tk
        from tkinter import filedialog
        root=tk.Tk(); root.withdraw()
        path=filedialog.askdirectory(title='Selecciona la carpeta raiz de NIKKE Mod Manager')
        root.destroy()
        return Path(path) if path else None
    except Exception:
        raw=input('Ruta de NIKKE Mod Manager: ').strip().strip('"')
        return Path(raw) if raw else None

def main() -> int:
    target=choose_folder()
    if not target:
        print('Parche cancelado.')
        return 1
    target=target.resolve()
    if not looks_like_manager(target):
        print('ERROR: carpeta invalida:', target)
        input('Enter para salir...')
        return 2

    appjs=target/'web'/'app.js'
    version=target/'VERSION.txt'
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
    backup=target/'Backups'/'Patches'/f'pre_v0_34_8_{stamp}'
    backup.mkdir(parents=True, exist_ok=True)

    shutil.copy2(appjs, backup/'app.js')
    if version.exists():
        shutil.copy2(version, backup/'VERSION.txt')

    text=appjs.read_text(encoding='utf-8')
    if MARKER not in text:
        appjs.write_text(text.rstrip()+JS_BLOCK+'\n', encoding='utf-8')

    version.write_text('v0.34.8\n', encoding='utf-8')

    print('Parche v0.34.8 aplicado correctamente.')
    print('Ahora, al tocar el nombre del personaje en la ficha abierta, se copia silenciosamente al portapapeles.')
    print('No agrega mensajes, iconos, animaciones ni cambios visuales.')
    print('Respaldo:', backup)
    input('Enter para cerrar...')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
