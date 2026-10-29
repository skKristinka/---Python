"""Светлая и тёмная темы."""
import tkinter as tk
from tkinter import ttk
from typing import Dict

PALETTES: Dict[str, Dict[str, str]] = {
    "light": {
        "bg": "#f2f2f2", "fg": "#1d1d1f", "field": "#ffffff", "select": "#cfe3ff",
        "ok": "#1a8f3c", "error": "#c62828", "warn": "#b26a00", "muted": "#6b6b6b",
        "key": "#0b5cad", "string": "#1a7f37", "number": "#b5530d", "keyword": "#8250df",
        "tag": "#0b5cad", "comment": "#6e7781",
    },
    "dark": {
        "bg": "#1e1f22", "fg": "#e6e6e6", "field": "#2b2d30", "select": "#3a4f73",
        "ok": "#4cc16a", "error": "#ff6b6b", "warn": "#e0a030", "muted": "#9a9a9a",
        "key": "#7cb7ff", "string": "#8fd48f", "number": "#f0a060", "keyword": "#c792ea",
        "tag": "#7cb7ff", "comment": "#8b949e",
    },
}
THEME_LABELS = {"Светлая": "light", "Тёмная": "dark"}


def get_palette(name: str) -> Dict[str, str]:
    """Палитра по имени (неизвестное имя — светлая)."""
    return PALETTES.get(name, PALETTES["light"])


def apply_ttk_style(root: tk.Misc, palette: Dict[str, str]) -> None:
    """Применить палитру к ttk-виджетам и окну."""
    style = ttk.Style(root)
    style.theme_use("clam")
    bg, fg, field, select = palette["bg"], palette["fg"], palette["field"], palette["select"]
    root.configure(background=bg)
    style.configure(".", background=bg, foreground=fg, fieldbackground=field)
    style.configure("TFrame", background=bg)
    style.configure("TLabel", background=bg, foreground=fg)
    style.configure("TLabelframe", background=bg, foreground=fg)
    style.configure("TLabelframe.Label", background=bg, foreground=fg)
    style.configure("TCheckbutton", background=bg, foreground=fg)
    style.configure("TButton", background=field, foreground=fg, padding=(10, 4))
    style.map("TButton", background=[("active", select), ("disabled", bg)],
              foreground=[("disabled", palette["muted"])])
    style.configure("TEntry", fieldbackground=field, foreground=fg)
    style.configure("TCombobox", fieldbackground=field, foreground=fg, background=field)
    style.configure("TSpinbox", fieldbackground=field, foreground=fg, background=field)
    style.map("TCombobox", fieldbackground=[("readonly", field)],
              foreground=[("readonly", fg)], selectbackground=[("readonly", field)],
              selectforeground=[("readonly", fg)])
    style.configure("Treeview", background=field, fieldbackground=field, foreground=fg)
    style.configure("Treeview.Heading", background=bg, foreground=fg)
    style.map("Treeview", background=[("selected", select)], foreground=[("selected", fg)])
    style.configure("TNotebook", background=bg)
    style.configure("TNotebook.Tab", background=bg, foreground=fg, padding=(14, 6))
    style.map("TNotebook.Tab", background=[("selected", field)])
    root.option_add("*TCombobox*Listbox.background", field)
    root.option_add("*TCombobox*Listbox.foreground", fg)
    root.option_add("*TCombobox*Listbox.selectBackground", select)
    root.option_add("*TCombobox*Listbox.selectForeground", fg)
