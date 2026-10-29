"""Вкладка «Сервер»."""
import queue
import tkinter as tk
import webbrowser
from tkinter import ttk
from typing import Callable, Dict, Optional

from src.gui.validation import ValidationError, validate_port
from src.gui.widgets import LogTable, StatusIndicator
from src.server.handlers import build_router
from src.server.http_server import HttpServer

POLL_MS = 100
MAX_PER_TICK = 200


def default_server_factory(port: int) -> HttpServer:
    """Сервер со стандартными маршрутами."""
    return HttpServer(build_router(), port=port)


class ServerTab(ttk.Frame):
    """Порт, Запустить/Остановить, индикатор состояния, лог запросов.

    Сервер работает в своих потоках; лог забирается из его очереди через root.after.
    """

    def __init__(self, master: tk.Misc,
                 server_factory: Callable[[int], HttpServer] = default_server_factory):
        super().__init__(master)
        self._factory = server_factory
        self._server: Optional[HttpServer] = None
        self._palette: Dict[str, str] = {"ok": "#1a8f3c", "error": "#c62828", "fg": "#000000"}
        self.port_var = tk.StringVar(value="8080")
        self.message_var = tk.StringVar(value="")
        self._build()
        self._update_controls()
        self._poll_id: Optional[str] = self.after(POLL_MS, self._poll_log)

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))
        ttk.Label(top, text="Порт:").pack(side="left")
        self.port_entry = ttk.Entry(top, textvariable=self.port_var, width=8)
        self.port_entry.pack(side="left", padx=6)
        self.start_button = ttk.Button(top, text="Запустить", command=self.start_server)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(top, text="Остановить", command=self.stop_server)
        self.stop_button.pack(side="left", padx=6)
        self.indicator = StatusIndicator(top)
        self.indicator.pack(side="left", padx=16)
        ttk.Button(top, text="Открыть в браузере", command=self.open_browser).pack(side="right")

        self.message_label = ttk.Label(self, textvariable=self.message_var)
        self.message_label.grid(row=1, column=0, sticky="w", padx=10)

        self.log_table = LogTable(self)
        self.log_table.grid(row=2, column=0, sticky="nsew", padx=10, pady=4)
        bottom = ttk.Frame(self)
        bottom.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        ttk.Button(bottom, text="Очистить лог", command=self.log_table.clear).pack(side="left")

    # ----- действия -----

    @property
    def is_running(self) -> bool:
        """Запущен ли сервер."""
        return self._server is not None

    @property
    def port(self) -> Optional[int]:
        """Порт работающего сервера."""
        return self._server.port if self._server else None

    def start_server(self) -> None:
        """Проверить порт и запустить сервер."""
        if self._server is not None:
            return
        try:
            port = validate_port(self.port_var.get())
        except ValidationError as exc:
            self._set_message(str(exc), error=True)
            return
        server = self._factory(port)
        try:
            server.start()
        except (ConnectionError, OSError) as exc:
            self._set_message(str(exc), error=True)
            return
        self._server = server
        self._set_message(f"Сервер запущен: http://localhost:{server.port}/", error=False)
        self._update_controls()

    def stop_server(self) -> None:
        """Остановить сервер и освободить порт."""
        server, self._server = self._server, None
        if server is None:
            return
        server.stop()
        self._drain(server)
        self._set_message("Сервер остановлен", error=False)
        self._update_controls()

    def shutdown(self) -> None:
        """Остановить сервер при закрытии окна."""
        self.stop_server()

    def open_browser(self) -> None:
        """Открыть http://localhost:<порт>/ в браузере."""
        if self._server is not None:
            port = self._server.port
        else:
            try:
                port = validate_port(self.port_var.get())
            except ValidationError as exc:
                self._set_message(str(exc), error=True)
                return
        webbrowser.open(f"http://localhost:{port}/")

    # ----- лог из потока сервера -----

    def _poll_log(self) -> None:
        if self._server is not None:
            self._drain(self._server)
        self._poll_id = self.after(POLL_MS, self._poll_log)

    def _drain(self, server: HttpServer) -> None:
        for _ in range(MAX_PER_TICK):
            try:
                entry = server.log_queue.get_nowait()
            except queue.Empty:
                return
            self.log_table.append(entry)

    # ----- оформление -----

    def _update_controls(self) -> None:
        running = self._server is not None
        self.indicator.set_running(running)
        self.start_button.state(["disabled" if running else "!disabled"])
        self.stop_button.state(["!disabled" if running else "disabled"])
        self.port_entry.state(["disabled" if running else "!disabled"])

    def _set_message(self, text: str, error: bool) -> None:
        self.message_var.set(text)
        self.message_label.configure(foreground=self._palette["error" if error else "fg"])

    def apply_palette(self, palette: Dict[str, str]) -> None:
        """Применить тему."""
        self._palette = palette
        self.indicator.configure_palette(palette)
        self.log_table.configure_palette(palette)
        self.message_label.configure(foreground=palette["fg"])

    def destroy(self) -> None:
        """Остановить сервер и опрос очереди."""
        if self._poll_id is not None:
            self.after_cancel(self._poll_id)
            self._poll_id = None
        self.stop_server()
        super().destroy()
