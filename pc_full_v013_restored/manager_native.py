from __future__ import annotations

import tkinter as tk

import manager
from native_preview import install_native_preview

manager.APP_VERSION = "0.13 Restored Native Preview"
install_native_preview(manager.App)


def _retitle_widgets(widget):
    try:
        if isinstance(widget, tk.Label):
            text = str(widget.cget("text"))
            if text == "Preview Beta · v0.12":
                widget.config(text="Preview Native · v0.13")
    except Exception:
        pass
    try:
        for child in widget.winfo_children():
            _retitle_widgets(child)
    except Exception:
        pass


def main():
    app = manager.App()
    try:
        _retitle_widgets(app)
        app.title("NIKKE Mod Manager · 0.13 Restored Native Preview")
    except Exception:
        pass
    app.mainloop()


if __name__ == "__main__":
    main()
