from __future__ import annotations

import importlib.util
import shutil
import threading
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

APP_DIR = Path(__file__).resolve().parent
ENGINE_FILE = APP_DIR / "tools" / "preview_beta_server.py"
CACHE_DIR = APP_DIR / ".nikke_preview_native_cache"

_ENGINE = None


def _load_engine():
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE
    if not ENGINE_FILE.exists():
        raise FileNotFoundError(f"Falta el motor de preview: {ENGINE_FILE}")
    spec = importlib.util.spec_from_file_location("nmt_preview_engine", ENGINE_FILE)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar el motor de vista previa.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.APP_ROOT = APP_DIR
    module.CACHE_ROOT = CACHE_DIR
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _ENGINE = module
    return module


class NativePreviewWindow(tk.Toplevel):
    BG = "#08101c"
    PANEL = "#0b1220"
    PANEL2 = "#0f1725"
    FIELD = "#172033"
    BORDER = "#334155"
    TEXT = "#e5e7eb"
    MUTED = "#94a3b8"
    ACCENT = "#facc15"
    ERROR = "#fecaca"

    def __init__(self, master, path: Path):
        super().__init__(master)
        self.current_path = Path(path)
        self.engine = None
        self.token = None
        self.manifest = None
        self.image_entries = []
        self.image_cache = {}
        self.current_pil = None
        self.current_photo = None
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.drag_start = None
        self.load_generation = 0

        self.title(f"Vista previa · {self.current_path.name}")
        self.geometry("1040x760")
        self.minsize(760, 560)
        self.configure(bg=self.BG)
        self.transient(master)

        self._build_ui()
        self.after(50, lambda: self.load_path(self.current_path))

    def _build_ui(self):
        header = tk.Frame(self, bg=self.PANEL, height=88)
        header.pack(fill="x")
        header.pack_propagate(False)

        brand = tk.Frame(header, bg=self.PANEL)
        brand.pack(side="left", fill="y", padx=18, pady=12)
        tk.Label(brand, text="NIKKE PREVIEW · NATIVE", bg=self.PANEL, fg=self.ACCENT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.title_label = tk.Label(brand, text=self.current_path.name, bg=self.PANEL, fg="#f8fafc",
                                    font=("Segoe UI", 17, "bold"))
        self.title_label.pack(anchor="w")
        self.meta_label = tk.Label(brand, text="Preparando…", bg=self.PANEL, fg=self.MUTED,
                                   font=("Segoe UI", 9))
        self.meta_label.pack(anchor="w", pady=(3, 0))

        self.related_bar = tk.Frame(header, bg=self.PANEL)
        self.related_bar.pack(side="right", padx=18, pady=22)

        body = tk.Frame(self, bg=self.BG)
        body.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(body, bg="#05080d", highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True, padx=12, pady=12)
        self.canvas.bind("<Configure>", lambda _e: self._render())
        self.canvas.bind("<MouseWheel>", self._wheel)
        self.canvas.bind("<ButtonPress-1>", self._drag_begin)
        self.canvas.bind("<B1-Motion>", self._drag_move)
        self.canvas.bind("<ButtonRelease-1>", lambda _e: setattr(self, "drag_start", None))

        footer = tk.Frame(self, bg=self.PANEL, height=72)
        footer.pack(fill="x")
        footer.pack_propagate(False)

        row = tk.Frame(footer, bg=self.PANEL)
        row.pack(fill="both", expand=True, padx=14, pady=12)

        tk.Label(row, text="Textura:", bg=self.PANEL, fg=self.MUTED,
                 font=("Segoe UI", 9)).pack(side="left")
        self.texture_var = tk.StringVar()
        self.texture_combo = ttk.Combobox(row, textvariable=self.texture_var, state="readonly", width=34)
        self.texture_combo.pack(side="left", padx=(7, 10))
        self.texture_combo.bind("<<ComboboxSelected>>", lambda _e: self._select_texture())

        self._button(row, "−", lambda: self._set_zoom(self.zoom / 1.15), width=3).pack(side="left", padx=3)
        self._button(row, "+", lambda: self._set_zoom(self.zoom * 1.15), width=3).pack(side="left", padx=3)
        self._button(row, "↺ Ajustar", self.reset_view).pack(side="left", padx=3)

        self.status_label = tk.Label(row, text="", bg=self.PANEL, fg=self.MUTED,
                                     font=("Segoe UI", 8), anchor="e")
        self.status_label.pack(side="right", fill="x", expand=True, padx=(12, 0))

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TCombobox", fieldbackground=self.FIELD, background=self.FIELD,
                        foreground=self.TEXT, arrowcolor=self.TEXT)

    def _button(self, parent, text, command, width=None, accent=False):
        return tk.Button(parent, text=text, command=command, width=width,
                         bg="#3a2d08" if accent else self.FIELD,
                         fg="#fde68a" if accent else self.TEXT,
                         activebackground="#5a450b" if accent else "#27364d",
                         activeforeground="#ffffff", relief="flat", bd=0,
                         padx=10, pady=7, font=("Segoe UI", 9, "bold"), cursor="hand2")

    def _show_center_text(self, text: str, color=None):
        self.canvas.delete("all")
        self.canvas.create_text(max(10, self.canvas.winfo_width() / 2),
                                max(10, self.canvas.winfo_height() / 2),
                                text=text, fill=color or self.MUTED,
                                font=("Segoe UI", 12, "bold"), width=max(300, self.canvas.winfo_width() - 100),
                                justify="center")

    def load_path(self, path: Path):
        self.current_path = Path(path)
        self.load_generation += 1
        generation = self.load_generation
        self.title(f"Vista previa · {self.current_path.name}")
        self.title_label.config(text=self.current_path.name)
        self.meta_label.config(text="Extrayendo recursos del mod…", fg=self.MUTED)
        self.status_label.config(text=str(self.current_path))
        self.texture_combo["values"] = ()
        self.texture_var.set("")
        self.current_pil = None
        self.current_photo = None
        self.image_entries = []
        self._show_center_text("Cargando vista previa…")
        self._clear_related()

        def worker():
            try:
                engine = _load_engine()
                token, manifest = engine.prepare(str(self.current_path))
                result = (engine, token, manifest, None)
            except Exception as exc:
                result = (None, None, None, f"{exc}\n\n{traceback.format_exc(limit=4)}")
            self.after(0, lambda: self._finish_load(generation, result))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_load(self, generation, result):
        if generation != self.load_generation or not self.winfo_exists():
            return
        engine, token, manifest, error = result
        if error:
            self.meta_label.config(text="No se pudo preparar el mod", fg=self.ERROR)
            short = error.split("\n\n", 1)[0]
            self._show_center_text("No se pudo mostrar la vista previa.\n\n" + short, self.ERROR)
            return

        self.engine = engine
        self.token = token
        self.manifest = manifest
        self._build_related(manifest.get("related") or {})

        kind = manifest.get("type", "")
        if kind == "spine":
            self.image_entries = list(manifest.get("textures") or [])
            version = manifest.get("spineVersion", "?")
            action = manifest.get("action", "")
            bundle = manifest.get("bundleKind", "")
            self.meta_label.config(text=f"Spine {version} · {action} · {bundle}", fg=self.MUTED)
        elif kind == "3dmigoto":
            self.image_entries = list(manifest.get("images") or [])
            action = manifest.get("action", "")
            self.meta_label.config(text=f"3DMigoto · {action} · vista de texturas", fg=self.MUTED)
        else:
            self.image_entries = []
            self.meta_label.config(text=f"Formato: {kind or 'desconocido'}", fg=self.MUTED)

        names = [x.get("sourceName") or x.get("name") or f"Textura {i+1}" for i, x in enumerate(self.image_entries)]
        self.texture_combo["values"] = names
        if names:
            self.texture_combo.current(0)
            self._select_texture()
        else:
            self._show_center_text("El mod fue reconocido, pero no encontré una textura que pueda mostrar.")

    def _clear_related(self):
        for child in self.related_bar.winfo_children():
            child.destroy()

    def _build_related(self, related):
        self._clear_related()
        for action in ("standing", "aim", "cover"):
            raw = related.get(action)
            if not raw:
                continue
            p = Path(raw)
            active = p == self.current_path
            text = action.capitalize()
            self._button(self.related_bar, text, lambda p=p: self.load_path(p), accent=active).pack(side="left", padx=3)

    def _asset_path(self, entry):
        if not self.token:
            return None
        name = entry.get("name")
        if not name:
            return None
        return CACHE_DIR / str(self.token) / str(name)

    def _select_texture(self):
        idx = self.texture_combo.current()
        if idx < 0 or idx >= len(self.image_entries):
            return
        entry = self.image_entries[idx]
        p = self._asset_path(entry)
        if p is None or not p.exists():
            self._show_center_text("No encuentro la textura extraída.", self.ERROR)
            return
        try:
            self.current_pil = Image.open(p).convert("RGBA")
            self.zoom = 1.0
            self.pan_x = 0.0
            self.pan_y = 0.0
            self._render()
            src = entry.get("sourceName") or entry.get("name") or p.name
            self.status_label.config(text=f"{src} · {self.current_pil.width}×{self.current_pil.height}")
        except Exception as exc:
            self._show_center_text(f"No pude abrir la textura:\n{exc}", self.ERROR)

    def _render(self):
        if self.current_pil is None or not self.winfo_exists():
            return
        cw = max(20, self.canvas.winfo_width())
        ch = max(20, self.canvas.winfo_height())
        iw, ih = self.current_pil.size
        fit = min((cw - 36) / max(1, iw), (ch - 36) / max(1, ih))
        scale = max(0.03, fit * self.zoom)
        nw = max(1, int(iw * scale))
        nh = max(1, int(ih * scale))
        key = (id(self.current_pil), nw, nh)
        photo = self.image_cache.get(key)
        if photo is None:
            resized = self.current_pil.resize((nw, nh), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(resized)
            self.image_cache = {key: photo}
        self.current_photo = photo
        self.canvas.delete("all")
        x = cw / 2 + self.pan_x
        y = ch / 2 + self.pan_y
        self.canvas.create_image(x, y, image=photo, anchor="center")

    def _set_zoom(self, value):
        self.zoom = min(8.0, max(0.15, float(value)))
        self._render()

    def reset_view(self):
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self._render()

    def _wheel(self, event):
        if event.delta > 0:
            self._set_zoom(self.zoom * 1.10)
        elif event.delta < 0:
            self._set_zoom(self.zoom / 1.10)

    def _drag_begin(self, event):
        self.drag_start = (event.x, event.y, self.pan_x, self.pan_y)

    def _drag_move(self, event):
        if not self.drag_start:
            return
        sx, sy, px, py = self.drag_start
        self.pan_x = px + (event.x - sx)
        self.pan_y = py + (event.y - sy)
        self._render()


def install_native_preview(app_class):
    def open_preview(self, path: Path):
        try:
            NativePreviewWindow(self, Path(path))
            if hasattr(self, "status_var"):
                self.status_var.set(self.t("ready"))
        except Exception as exc:
            try:
                from tkinter import messagebox
                messagebox.showerror(self.t("title"), f"No pude abrir la vista previa nativa.\n\n{exc}")
            except Exception:
                pass

    app_class.open_preview = open_preview
    return app_class
