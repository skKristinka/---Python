"""Вкладка «Настройки»: таймаут, редиректы, тема, история, журнал приложения."""
import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict

from src.gui.settings import Settings
from src.gui.theme import THEME_LABELS
from src.gui.validation import ValidationError, validate_redirects, validate_timeout
from src.gui.widgets import HighlightedText

_LABEL_BY_THEME = {value: label for label, value in THEME_LABELS.items()}
MAX_LOG_LINES = 1000


class SettingsTab(ttk.Frame):
    """Настройки приложения и просмотр журнала (logging → GUI)."""

    def __init__(self, master: tk.Misc, settings: Settings,
                 on_apply: Callable[[str], None]):
        super().__init__(master)
        self.settings = settings
        self._on_apply = on_apply
        self._palette: Dict[str, str] = {"ok": "#1a8f3c", "error": "#c62828", "fg": "#000000"}
        self._log_lines = 0
        self.timeout_var = tk.StringVar(value=str(settings.timeout))
        self.redirects_var = tk.StringVar(value=str(settings.max_redirects))
        self.theme_var = tk.StringVar(value=_LABEL_BY_THEME.get(settings.theme, "Светлая"))
        self.history_var = tk.BooleanVar(value=settings.save_history)
        self.message_var = tk.StringVar(value="")
        self._build()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        form = ttk.LabelFrame(self, text="Параметры")
        form.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        timeout_label = ttk.Label(form, text="Таймаут по умолчанию, с:")
        timeout_label.grid(row=0, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(form, textvariable=self.timeout_var, width=8).grid(row=0, column=1, sticky="w")
        ttk.Label(form, text="Следовать за редиректами 3xx (макс.):").grid(
            row=1, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(form, textvariable=self.redirects_var, width=8).grid(row=1, column=1,
                                                                        sticky="w")
        ttk.Label(form, text="Тема:").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        ttk.Combobox(form, textvariable=self.theme_var, values=list(THEME_LABELS),
                     state="readonly", width=10).grid(row=2, column=1, sticky="w")
        ttk.Checkbutton(form, text="Сохранять историю запросов в history.json",
                        variable=self.history_var).grid(row=3, column=0, columnspan=2,
                                                        sticky="w", padx=8, pady=4)
        actions = ttk.Frame(form)
        actions.grid(row=4, column=0, columnspan=2, sticky="w", padx=8, pady=(4, 8))
        ttk.Button(actions, text="Применить", command=self.apply).pack(side="left")
        self.message_label = ttk.Label(actions, textvariable=self.message_var)
        self.message_label.pack(side="left", padx=10)

        log_frame = ttk.LabelFrame(self, text="Журнал приложения (также пишется в http_gui.log)")
        log_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log_view = HighlightedText(log_frame, height=10)
        self.log_view.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

    def apply(self) -> None:
        """Проверить значения, сохранить их и применить тему."""
        try:
            timeout = validate_timeout(self.timeout_var.get())
            redirects = validate_redirects(self.redirects_var.get())
        except ValidationError as exc:
            self._set_message(str(exc), error=True)
            return
        self.settings.timeout = timeout
        self.settings.max_redirects = redirects
        self.settings.save_history = bool(self.history_var.get())
        self.settings.theme = THEME_LABELS.get(self.theme_var.get(), "light")
        self._on_apply(self.settings.theme)
        self._set_message("Настройки применены", error=False)

    def append_log(self, line: str) -> None:
        """Добавить строку в журнал (вызывать из главного потока)."""
        text = self.log_view.get_text()
        lines = (text + "\n" + line).strip("\n").split("\n")[-MAX_LOG_LINES:]
        self.log_view.set_text("\n".join(lines))
        self.log_view.text.see("end")

    def _set_message(self, text: str, error: bool) -> None:
        self.message_var.set(text)
        self.message_label.configure(foreground=self._palette["error" if error else "ok"])

    def apply_palette(self, palette: Dict[str, str]) -> None:
        """Применить тему."""
        self._palette = palette
        self.log_view.configure_palette(palette)
