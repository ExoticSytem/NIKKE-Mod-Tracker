from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from collections import defaultdict
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_VERSION = "0.12 Preview Beta FULL"
APP_DIR = Path(__file__).resolve().parent
CONFIG_FILE = APP_DIR / "config.json"
USER_FILE = APP_DIR / "user_data.json"
CATALOG_FILE = APP_DIR / "catalog" / "base_catalog.json"
PREVIEW_SERVER = APP_DIR / "tools" / "preview_beta_server.py"
PREVIEW_PORT = 8137
MOD_RE = re.compile(r"c(?P<id>\d{3,4})_(?P<ver>\d{2})_(?P<action>standing|aim|cover)(?:_(?P<rest>.*))?$", re.I)

TEXT = {
    "es": {
        "title": "NIKKE Mod Manager",
        "choose_lang": "Elige el idioma / Choose language",
        "choose_folder": "Selecciona la carpeta donde guardas tus mods de NIKKE",
        "mods_folder": "Carpeta de mods",
        "change_folder": "Cambiar carpeta",
        "refresh": "↻ Actualizar",
        "search": "Buscar personaje, ID o mod…",
        "all": "Todos",
        "with_mods": "Con mods",
        "without_mods": "Sin mods",
        "conflicts": "Conflictos",
        "characters": "Personajes / skins",
        "name": "Nombre",
        "mods": "Mods",
        "conflict": "Conflicto",
        "npc": "NPC / Extra",
        "details": "Selecciona un personaje o skin",
        "no_mods": "Sin mods instalados para esta acción",
        "preview": "👁 Vista previa",
        "open_folder": "Abrir ubicación",
        "delete": "Enviar a Papelera",
        "tags": "Etiquetas",
        "add_tag": "Agregar",
        "remove_tag": "Quitar",
        "notes": "Notas",
        "save": "Guardar",
        "scanning": "Escaneando mods…",
        "ready": "Listo",
        "found": "{chars} variantes · {mods} mods detectados · {conflicts} conflictos",
        "bad_folder": "La carpeta configurada ya no existe. Selecciona otra.",
        "preview_error": "No pude iniciar el motor de vista previa.",
        "select_mod": "Selecciona primero un mod de la lista.",
        "confirm_delete": "¿Enviar este mod a la Papelera de reciclaje?\n\n{path}",
        "delete_error": "No pude enviar el mod a la Papelera:\n{error}",
        "lang": "Idioma",
        "spanish": "Español",
        "english": "English",
        "settings": "Configuración",
        "current_folder": "Carpeta actual",
    },
    "en": {
        "title": "NIKKE Mod Manager",
        "choose_lang": "Choose language / Elige el idioma",
        "choose_folder": "Select the folder where you keep your NIKKE mods",
        "mods_folder": "Mods folder",
        "change_folder": "Change folder",
        "refresh": "↻ Refresh",
        "search": "Search character, ID or mod…",
        "all": "All",
        "with_mods": "With mods",
        "without_mods": "Without mods",
        "conflicts": "Conflicts",
        "characters": "Characters / skins",
        "name": "Name",
        "mods": "Mods",
        "conflict": "Conflict",
        "npc": "NPC / Extra",
        "details": "Select a character or skin",
        "no_mods": "No installed mods for this action",
        "preview": "👁 Preview",
        "open_folder": "Open location",
        "delete": "Send to Recycle Bin",
        "tags": "Tags",
        "add_tag": "Add",
        "remove_tag": "Remove",
        "notes": "Notes",
        "save": "Save",
        "scanning": "Scanning mods…",
        "ready": "Ready",
        "found": "{chars} variants · {mods} mods detected · {conflicts} conflicts",
        "bad_folder": "The configured folder no longer exists. Select another one.",
        "preview_error": "Could not start the preview engine.",
        "select_mod": "Select a mod first.",
        "confirm_delete": "Send this mod to the Recycle Bin?\n\n{path}",
        "delete_error": "Could not send the mod to the Recycle Bin:\n{error}",
        "lang": "Language",
        "spanish": "Español",
        "english": "English",
        "settings": "Settings",
        "current_folder": "Current folder",
    },
}


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_mod_path(path: Path):
    m = MOD_RE.match(path.name)
    if not m:
        return None
    d = {k: (v or "") for k, v in m.groupdict().items()}
    d["action"] = d["action"].lower()
    d["path"] = str(path)
    d["name"] = d["rest"].replace("_", " ").replace("-", " ").strip() or path.name
    return d


def scan_mods(root: Path):
    result = []
    if not root.is_dir():
        return result
    # Most NIKKE mods are top-level folders/files. We also inspect one nested level
    # so collections grouped by author still work without crawling huge trees.
    try:
        entries = list(root.iterdir())
    except Exception:
        return result
    for p in entries:
        info = parse_mod_path(p)
        if info:
            result.append(info)
            continue
        if p.is_dir() and not p.name.startswith("."):
            try:
                for c in p.iterdir():
                    info = parse_mod_path(c)
                    if info:
                        result.append(info)
            except Exception:
                pass
    return result


def startfile(path: Path):
    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", str(path)])


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.config_data = load_json(CONFIG_FILE, {})
        self.user_data = load_json(USER_FILE, {})
        self.lang = self.config_data.get("language")
        self.mods_root = Path(self.config_data.get("mods_folder", "")) if self.config_data.get("mods_folder") else None
        self.catalog = []
        self.catalog_by_key = {}
        self.mods = []
        self.mods_by_key_action = defaultdict(list)
        self.filtered_keys = []
        self.selected_key = None
        self.selected_mod_path = None
        self.preview_proc = None

        if self.lang not in ("es", "en"):
            self.withdraw()
            self.lang = self.ask_language()
            if not self.lang:
                self.destroy(); return
            self.config_data["language"] = self.lang
            save_json(CONFIG_FILE, self.config_data)

        if not self.mods_root or not self.mods_root.is_dir():
            self.withdraw()
            folder = filedialog.askdirectory(title=TEXT[self.lang]["choose_folder"])
            if not folder:
                self.destroy(); return
            self.mods_root = Path(folder)
            self.config_data["mods_folder"] = str(self.mods_root)
            save_json(CONFIG_FILE, self.config_data)

        self.deiconify()
        self.load_catalog()
        self.build_ui()
        self.after(150, self.refresh_async)

    def t(self, key):
        return TEXT[self.lang].get(key, key)

    def ask_language(self):
        dlg = tk.Toplevel(self)
        dlg.title("NIKKE Mod Manager")
        dlg.geometry("430x245")
        dlg.resizable(False, False)
        dlg.configure(bg="#0b1220")
        dlg.grab_set()
        out = {"value": None}
        tk.Label(dlg, text="NIKKE MOD MANAGER", bg="#0b1220", fg="#facc15", font=("Segoe UI", 11, "bold")).pack(pady=(28, 6))
        tk.Label(dlg, text="Elige el idioma / Choose language", bg="#0b1220", fg="#f8fafc", font=("Segoe UI", 16, "bold")).pack(pady=(0, 24))
        row = tk.Frame(dlg, bg="#0b1220"); row.pack()
        def choose(v): out["value"] = v; dlg.destroy()
        for text, value in (("🇪🇸  Español", "es"), ("🇬🇧  English", "en")):
            tk.Button(row, text=text, command=lambda v=value: choose(v), width=16, height=2,
                      bg="#172033", fg="#f8fafc", activebackground="#27364d", activeforeground="#fff",
                      relief="flat", font=("Segoe UI", 11, "bold"), cursor="hand2").pack(side="left", padx=8)
        dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)
        self.wait_window(dlg)
        return out["value"]

    def load_catalog(self):
        raw = load_json(CATALOG_FILE, {})
        chars = raw.get("characters", raw if isinstance(raw, list) else [])
        self.catalog = chars
        self.catalog_by_key = {f"{str(c.get('id','')).zfill(3)}_{str(c.get('version', c.get('ver','00'))).zfill(2)}": c for c in chars}

    def build_ui(self):
        self.title(f"NIKKE Mod Manager · {APP_VERSION}")
        self.geometry("1320x820")
        self.minsize(1050, 680)
        self.configure(bg="#08101c")
        style = ttk.Style(self)
        try: style.theme_use("clam")
        except Exception: pass
        style.configure("Treeview", background="#0f1725", fieldbackground="#0f1725", foreground="#e5e7eb", rowheight=29, borderwidth=0)
        style.configure("Treeview.Heading", background="#172033", foreground="#e5e7eb", relief="flat", font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#334155")], foreground=[("selected", "#ffffff")])
        style.configure("TCombobox", fieldbackground="#172033", background="#172033", foreground="#e5e7eb")

        header = tk.Frame(self, bg="#0b1220", height=86); header.pack(fill="x"); header.pack_propagate(False)
        brand = tk.Frame(header, bg="#0b1220"); brand.pack(side="left", padx=20, pady=13)
        tk.Label(brand, text="NIKKE MOD MANAGER", bg="#0b1220", fg="#facc15", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(brand, text="Preview Beta · v0.12", bg="#0b1220", fg="#f8fafc", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        self.folder_label = tk.Label(brand, text=str(self.mods_root), bg="#0b1220", fg="#64748b", font=("Segoe UI", 8))
        self.folder_label.pack(anchor="w")
        actions = tk.Frame(header, bg="#0b1220"); actions.pack(side="right", padx=18)
        self.dark_button(actions, self.t("change_folder"), self.change_folder).pack(side="left", padx=5)
        self.dark_button(actions, self.t("refresh"), self.refresh_async, accent=True).pack(side="left", padx=5)
        lang_btn = self.dark_button(actions, "ES / EN", self.toggle_language); lang_btn.pack(side="left", padx=5)

        filterbar = tk.Frame(self, bg="#0d1624", height=58); filterbar.pack(fill="x"); filterbar.pack_propagate(False)
        self.search_var = tk.StringVar()
        search = tk.Entry(filterbar, textvariable=self.search_var, bg="#172033", fg="#e5e7eb", insertbackground="#fff", relief="flat", font=("Segoe UI", 10))
        search.insert(0, "")
        search.pack(side="left", fill="x", expand=True, padx=(18, 10), pady=13, ipady=7)
        search.bind("<KeyRelease>", lambda e: self.apply_filter())
        self.filter_var = tk.StringVar(value="all")
        for value, label in (("all", self.t("all")), ("with", self.t("with_mods")), ("without", self.t("without_mods")), ("conflict", self.t("conflicts"))):
            rb = tk.Radiobutton(filterbar, text=label, variable=self.filter_var, value=value, command=self.apply_filter,
                                indicatoron=False, bg="#172033", fg="#cbd5e1", selectcolor="#334155", activebackground="#27364d", activeforeground="#fff",
                                relief="flat", padx=10, pady=7, font=("Segoe UI", 9, "bold"), cursor="hand2")
            rb.pack(side="left", padx=3)
        tk.Frame(filterbar, bg="#0d1624", width=14).pack(side="left")

        body = tk.PanedWindow(self, orient="horizontal", bg="#08101c", sashwidth=5, sashrelief="flat")
        body.pack(fill="both", expand=True, padx=12, pady=12)
        left = tk.Frame(body, bg="#0f1725"); right = tk.Frame(body, bg="#0f1725")
        body.add(left, minsize=500, width=670); body.add(right, minsize=430)

        tk.Label(left, text=self.t("characters"), bg="#0f1725", fg="#f8fafc", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(11, 6))
        tree_frame = tk.Frame(left, bg="#0f1725"); tree_frame.pack(fill="both", expand=True, padx=10, pady=(0,10))
        cols = ("id", "ver", "mods", "conflict", "type")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="tree headings", selectmode="browse")
        self.tree.heading("#0", text=self.t("name")); self.tree.column("#0", width=280, stretch=True)
        self.tree.heading("id", text="ID"); self.tree.column("id", width=55, anchor="center", stretch=False)
        self.tree.heading("ver", text="Ver"); self.tree.column("ver", width=45, anchor="center", stretch=False)
        self.tree.heading("mods", text=self.t("mods")); self.tree.column("mods", width=55, anchor="center", stretch=False)
        self.tree.heading("conflict", text="⚠"); self.tree.column("conflict", width=45, anchor="center", stretch=False)
        self.tree.heading("type", text=self.t("npc")); self.tree.column("type", width=85, anchor="center", stretch=False)
        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_character_select)

        self.detail = tk.Frame(right, bg="#0f1725"); self.detail.pack(fill="both", expand=True, padx=14, pady=14)
        self.render_empty_detail()

        status = tk.Frame(self, bg="#0b1220", height=32); status.pack(fill="x"); status.pack_propagate(False)
        self.status_var = tk.StringVar(value=self.t("ready"))
        tk.Label(status, textvariable=self.status_var, bg="#0b1220", fg="#94a3b8", font=("Segoe UI", 9)).pack(side="left", padx=18)
        tk.Label(status, text=APP_VERSION, bg="#0b1220", fg="#475569", font=("Segoe UI", 8)).pack(side="right", padx=18)

    def dark_button(self, parent, text, command, accent=False):
        return tk.Button(parent, text=text, command=command, relief="flat", bd=0, cursor="hand2", padx=12, pady=7,
                         bg="#3a2d08" if accent else "#172033", fg="#fde68a" if accent else "#e5e7eb",
                         activebackground="#5a4308" if accent else "#27364d", activeforeground="#fff", font=("Segoe UI", 9, "bold"))

    def refresh_async(self):
        if not self.mods_root or not self.mods_root.is_dir():
            messagebox.showwarning(self.t("title"), self.t("bad_folder")); self.change_folder(); return
        self.status_var.set(self.t("scanning"))
        def worker():
            mods = scan_mods(self.mods_root)
            self.after(0, lambda: self.finish_scan(mods))
        threading.Thread(target=worker, daemon=True).start()

    def finish_scan(self, mods):
        self.mods = mods
        self.mods_by_key_action = defaultdict(list)
        for m in mods:
            key = f"{m['id'].zfill(3)}_{m['ver'].zfill(2)}"
            self.mods_by_key_action[(key, m["action"])].append(m)
        # Unknown ID/Ver found in the user's folder is still shown instead of being dropped.
        for m in mods:
            key = f"{m['id'].zfill(3)}_{m['ver'].zfill(2)}"
            if key not in self.catalog_by_key:
                self.catalog_by_key[key] = {"id": m['id'].zfill(3), "version": m['ver'].zfill(2), "key": key, "name": f"Unknown {key}", "npcExtra": False}
        self.apply_filter()
        conflicts = sum(1 for (key, action), items in self.mods_by_key_action.items() if len(items) > 1)
        self.status_var.set(self.t("found").format(chars=len(self.catalog_by_key), mods=len(mods), conflicts=conflicts))
        if self.selected_key:
            self.render_detail(self.selected_key)

    def key_stats(self, key):
        counts = {a: len(self.mods_by_key_action.get((key, a), [])) for a in ("standing", "aim", "cover")}
        total = sum(counts.values())
        conflicts = sum(1 for n in counts.values() if n > 1)
        return counts, total, conflicts

    def apply_filter(self):
        if not hasattr(self, "tree"): return
        q = self.search_var.get().strip().lower()
        mode = self.filter_var.get()
        self.tree.delete(*self.tree.get_children())
        keys = sorted(self.catalog_by_key.keys(), key=lambda k: tuple(int(x) for x in k.split("_")))
        for key in keys:
            c = self.catalog_by_key[key]
            counts, total, conflicts = self.key_stats(key)
            blob = " ".join([str(c.get("name", "")), key] + [m.get("rest", "") for a in ("standing","aim","cover") for m in self.mods_by_key_action.get((key,a),[])]).lower()
            if q and q not in blob: continue
            if mode == "with" and total == 0: continue
            if mode == "without" and total > 0: continue
            if mode == "conflict" and conflicts == 0: continue
            npc = "NPC / Extra" if c.get("npcExtra") else ""
            warn = "⚠" if conflicts else ""
            self.tree.insert("", "end", iid=key, text=c.get("name", key), values=(c.get("id",""), c.get("version",c.get("ver","")), total, warn, npc))

    def on_character_select(self, _event=None):
        sel = self.tree.selection()
        if not sel: return
        self.selected_key = sel[0]
        self.render_detail(self.selected_key)

    def clear_detail(self):
        for w in self.detail.winfo_children(): w.destroy()

    def render_empty_detail(self):
        self.clear_detail()
        tk.Label(self.detail, text=self.t("details"), bg="#0f1725", fg="#64748b", font=("Segoe UI", 14, "bold")).pack(expand=True)

    def render_detail(self, key):
        self.clear_detail()
        c = self.catalog_by_key.get(key, {})
        counts, total, conflicts = self.key_stats(key)
        top = tk.Frame(self.detail, bg="#0f1725"); top.pack(fill="x")
        tk.Label(top, text=c.get("name", key), bg="#0f1725", fg="#f8fafc", font=("Segoe UI", 18, "bold"), wraplength=520, justify="left").pack(anchor="w")
        meta = f"ID {c.get('id','')} · Ver {c.get('version',c.get('ver',''))}"
        if c.get("npcExtra"): meta += " · NPC / Extra"
        tk.Label(top, text=meta, bg="#0f1725", fg="#94a3b8", font=("Segoe UI", 9)).pack(anchor="w", pady=(3, 12))

        self.action_lists = {}
        for action in ("standing", "aim", "cover"):
            if c.get("npcExtra") and action != "standing":
                continue
            frame = tk.LabelFrame(self.detail, text=f" {action.title()}  ·  {counts[action]} ", bg="#0f1725", fg="#cbd5e1", bd=1, relief="solid", font=("Segoe UI", 9, "bold"))
            frame.pack(fill="x", pady=5)
            items = self.mods_by_key_action.get((key, action), [])
            if not items:
                tk.Label(frame, text=self.t("no_mods"), bg="#0f1725", fg="#64748b", font=("Segoe UI", 9)).pack(anchor="w", padx=9, pady=9)
                continue
            listbox = tk.Listbox(frame, height=min(4, max(1,len(items))), bg="#0b1220", fg="#e5e7eb", selectbackground="#334155", relief="flat", exportselection=False, font=("Segoe UI", 9))
            for m in items:
                prefix = "⚠  " if len(items) > 1 else ""
                listbox.insert("end", prefix + (m.get("rest") or Path(m["path"]).name))
            listbox.pack(fill="x", padx=8, pady=(7,5))
            self.action_lists[action] = (listbox, items)
            row = tk.Frame(frame, bg="#0f1725"); row.pack(fill="x", padx=8, pady=(0,8))
            self.dark_button(row, self.t("preview"), lambda a=action: self.preview_from_action(a), accent=True).pack(side="left", padx=(0,5))
            self.dark_button(row, self.t("open_folder"), lambda a=action: self.open_from_action(a)).pack(side="left", padx=5)
            self.dark_button(row, self.t("delete"), lambda a=action: self.delete_from_action(a)).pack(side="left", padx=5)
            listbox.bind("<Double-Button-1>", lambda e, a=action: self.preview_from_action(a))

        sep = tk.Frame(self.detail, bg="#263449", height=1); sep.pack(fill="x", pady=12)
        meta_data = self.user_data.setdefault(key, {"tags": [], "notes": ""})
        tag_row = tk.Frame(self.detail, bg="#0f1725"); tag_row.pack(fill="x")
        tk.Label(tag_row, text=self.t("tags"), bg="#0f1725", fg="#cbd5e1", font=("Segoe UI", 9, "bold")).pack(side="left")
        self.tag_var = tk.StringVar()
        tag_entry = tk.Entry(tag_row, textvariable=self.tag_var, bg="#172033", fg="#e5e7eb", insertbackground="#fff", relief="flat")
        tag_entry.pack(side="left", fill="x", expand=True, padx=8, ipady=5)
        self.dark_button(tag_row, self.t("add_tag"), self.add_tag).pack(side="left", padx=3)
        self.dark_button(tag_row, self.t("remove_tag"), self.remove_tag).pack(side="left", padx=3)
        self.tags_list = tk.Listbox(self.detail, height=2, bg="#0b1220", fg="#fde68a", selectbackground="#334155", relief="flat", exportselection=False)
        for tag in meta_data.get("tags", []): self.tags_list.insert("end", tag)
        self.tags_list.pack(fill="x", pady=(6,10))
        tk.Label(self.detail, text=self.t("notes"), bg="#0f1725", fg="#cbd5e1", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.notes_text = tk.Text(self.detail, height=4, bg="#0b1220", fg="#e5e7eb", insertbackground="#fff", relief="flat", wrap="word")
        self.notes_text.insert("1.0", meta_data.get("notes", "")); self.notes_text.pack(fill="x", pady=(5,6))
        self.dark_button(self.detail, self.t("save"), self.save_notes).pack(anchor="e")

    def selected_mod_for_action(self, action):
        data = getattr(self, "action_lists", {}).get(action)
        if not data: return None
        lb, items = data
        idx = lb.curselection()
        i = idx[0] if idx else 0
        return items[i] if items else None

    def preview_from_action(self, action):
        mod = self.selected_mod_for_action(action)
        if not mod:
            messagebox.showinfo(self.t("title"), self.t("select_mod")); return
        self.open_preview(Path(mod["path"]))

    def ensure_preview_server(self):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PREVIEW_PORT}/health", timeout=0.7) as r:
                if r.status == 200: return True
        except Exception:
            pass
        if not PREVIEW_SERVER.exists(): return False
        kwargs = {"cwd": str(APP_DIR)}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
        try:
            self.preview_proc = subprocess.Popen([sys.executable, str(PREVIEW_SERVER), "--root", str(APP_DIR), "--port", str(PREVIEW_PORT)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)
        except Exception:
            return False
        for _ in range(25):
            time.sleep(0.12)
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{PREVIEW_PORT}/health", timeout=0.5) as r:
                    if r.status == 200: return True
            except Exception:
                pass
        return False

    def open_preview(self, path: Path):
        self.status_var.set("Preview…")
        def worker():
            ok = self.ensure_preview_server()
            if ok:
                url = f"http://127.0.0.1:{PREVIEW_PORT}/viewer?path=" + urllib.parse.quote(str(path), safe="")
                webbrowser.open(url)
                self.after(0, lambda: self.status_var.set(self.t("ready")))
            else:
                self.after(0, lambda: messagebox.showerror(self.t("title"), self.t("preview_error")))
        threading.Thread(target=worker, daemon=True).start()

    def open_from_action(self, action):
        mod = self.selected_mod_for_action(action)
        if not mod: return
        p = Path(mod["path"])
        try:
            if p.is_dir(): startfile(p)
            else: startfile(p.parent)
        except Exception as exc: messagebox.showerror(self.t("title"), str(exc))

    def delete_from_action(self, action):
        mod = self.selected_mod_for_action(action)
        if not mod: return
        p = Path(mod["path"])
        if not messagebox.askyesno(self.t("delete"), self.t("confirm_delete").format(path=p)): return
        try:
            from send2trash import send2trash
            send2trash(str(p))
            self.refresh_async()
        except Exception as exc:
            messagebox.showerror(self.t("title"), self.t("delete_error").format(error=exc))

    def add_tag(self):
        if not self.selected_key: return
        tag = self.tag_var.get().strip()
        if not tag: return
        d = self.user_data.setdefault(self.selected_key, {"tags": [], "notes": ""})
        if tag not in d["tags"]:
            d["tags"].append(tag); save_json(USER_FILE, self.user_data); self.tags_list.insert("end", tag)
        self.tag_var.set("")

    def remove_tag(self):
        if not self.selected_key: return
        idx = self.tags_list.curselection()
        if not idx: return
        tag = self.tags_list.get(idx[0])
        d = self.user_data.setdefault(self.selected_key, {"tags": [], "notes": ""})
        d["tags"] = [x for x in d.get("tags", []) if x != tag]
        save_json(USER_FILE, self.user_data); self.tags_list.delete(idx[0])

    def save_notes(self):
        if not self.selected_key: return
        d = self.user_data.setdefault(self.selected_key, {"tags": [], "notes": ""})
        d["notes"] = self.notes_text.get("1.0", "end-1c")
        save_json(USER_FILE, self.user_data)
        self.status_var.set(self.t("ready"))

    def change_folder(self):
        folder = filedialog.askdirectory(title=self.t("choose_folder"), initialdir=str(self.mods_root) if self.mods_root else None)
        if not folder: return
        self.mods_root = Path(folder)
        self.config_data["mods_folder"] = str(self.mods_root); save_json(CONFIG_FILE, self.config_data)
        if hasattr(self, "folder_label"): self.folder_label.config(text=str(self.mods_root))
        self.refresh_async()

    def toggle_language(self):
        self.config_data["language"] = "en" if self.lang == "es" else "es"
        save_json(CONFIG_FILE, self.config_data)
        messagebox.showinfo("NIKKE Mod Manager", "Idioma guardado. Reinicia la aplicación para aplicar todos los textos.\nLanguage saved. Restart the app to apply all text.")


if __name__ == "__main__":
    app = App()
    try:
        app.mainloop()
    except tk.TclError:
        pass
