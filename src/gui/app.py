"""Главное окно приложения."""
import queue
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Optional

from src.gui.client_tab import ClientTab
from src.gui.history import HistoryStore
from src.gui.server_tab import ServerTab
from src.gui.settings import Settings
from src.gui.settings_tab import SettingsTab
from src.gui.theme import apply_ttk_style, get_palette
from src.logging_setup import setup_logging

LOG_POLL_MS = 200


class App:
    """Окно с вкладками Клиент / Сервер / Настройки."""

    def __init__(self, root: Optional[tk.Tk] = None, log_file: str = "http_gui.log",
                 history_path: str = "history.json"):
        self.root = root or tk.Tk()
        self.root.title("HTTP-клиент и сервер")
        self.root.geometry("980x780")
        self.root.minsize(820, 620)
        self.settings = Settings()
        self.log_queue: "queue.Queue[str]" = queue.Queue()
        setup_logging(log_file, self.log_queue)
        self.notebook = ttk.Notebook(self.root)
        self.client_tab = ClientTab(self.notebook, self.settings, HistoryStore(Path(history_path)))
        self.server_tab = ServerTab(self.notebook)
        self.settings_tab = SettingsTab(self.notebook, self.settings, self.apply_theme)
        self.notebook.add(self.client_tab, text="Клиент")
        self.notebook.add(self.server_tab, text="Сервер")
        self.notebook.add(self.settings_tab, text="Настройки")
        self.notebook.pack(fill="both", expand=True)
        self.apply_theme(self.settings.theme)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self._poll_id: Optional[str] = self.root.after(LOG_POLL_MS, self._poll_logs)

    def run(self) -> None:
        """Запустить главный цикл."""
        self.root.mainloop()

    def close(self) -> None:
        """Остановить сервер и закрыть окно."""
        if self._poll_id is not None:
            self.root.after_cancel(self._poll_id)
            self._poll_id = None
        self.server_tab.shutdown()
        self.root.destroy()

    def apply_theme(self, name: str) -> None:
        """Применить тему ко всем вкладкам."""
        palette = get_palette(name)
        apply_ttk_style(self.root, palette)
        for tab in (self.client_tab, self.server_tab, self.settings_tab):
            tab.apply_palette(palette)

    def _poll_logs(self) -> None:
        """Перенести записи logging из очереди в журнал (только главный поток)."""
        for _ in range(200):
            try:
                line = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self.settings_tab.append_log(line)
        self._poll_id = self.root.after(LOG_POLL_MS, self._poll_logs)
