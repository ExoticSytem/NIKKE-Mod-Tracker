from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import webview
from src.api import AppAPI


def _first_run_setup() -> None:
    """Ask language and mods folder once, before opening the main UI."""
    settings_path = ROOT / 'data' / 'settings.json'
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        settings = json.loads(settings_path.read_text(encoding='utf-8')) if settings_path.exists() else {}
        if not isinstance(settings, dict):
            settings = {}
    except Exception:
        settings = {}

    if settings.get('onboarding_complete'):
        return

    import tkinter as tk
    from tkinter import filedialog

    choice = {'language': 'es'}
    w = tk.Tk()
    w.title('NIKKE Mod Manager — Idioma / Language')
    w.geometry('430x250')
    w.resizable(False, False)
    w.configure(bg='#0e1421')

    tk.Label(w, text='NIKKE  MOD LIBRARY', font=('Segoe UI', 18, 'bold'), fg='white', bg='#0e1421').pack(pady=(28, 8))
    tk.Label(w, text='Elige el idioma de la interfaz\nChoose the interface language', font=('Segoe UI', 11), fg='#b9c3d5', bg='#0e1421').pack(pady=(0, 22))

    row = tk.Frame(w, bg='#0e1421')
    row.pack()

    def choose(lang: str):
        choice['language'] = lang
        w.destroy()

    tk.Button(row, text='Español', width=16, height=2, command=lambda: choose('es'), bg='#ffcc33', fg='#14110a', relief='flat', font=('Segoe UI', 10, 'bold')).pack(side='left', padx=7)
    tk.Button(row, text='English', width=16, height=2, command=lambda: choose('en'), bg='#252d3b', fg='white', relief='flat', font=('Segoe UI', 10, 'bold')).pack(side='left', padx=7)
    w.protocol('WM_DELETE_WINDOW', lambda: choose('es'))
    w.mainloop()

    lang = choice['language']
    picker = tk.Tk()
    picker.withdraw()
    title = 'Selecciona la carpeta donde guardas tus mods de NIKKE' if lang == 'es' else 'Select the folder where you keep your NIKKE mods'
    folder = filedialog.askdirectory(title=title, mustexist=True)
    picker.destroy()

    settings['language'] = lang
    settings['mods_folder'] = str(folder or settings.get('mods_folder', ''))
    settings['onboarding_complete'] = True
    settings['settings_version'] = max(int(settings.get('settings_version', 0) or 0), 6)
    settings_path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding='utf-8')


def main() -> None:
    _first_run_setup()
    api = AppAPI(ROOT)
    window = webview.create_window(
        'NIKKE Mod Manager',
        url=str(ROOT / 'web' / 'index.html'),
        js_api=api,
        width=1460,
        height=900,
        min_size=(1050, 680),
        background_color='#0e1421',
    )
    api.attach_window(window)
    webview.start(debug=False)


if __name__ == '__main__':
    main()
