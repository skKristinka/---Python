"""Вкладка «Клиент»."""
import queue
import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Dict, Optional

from src.gui.formatting import format_body
from src.gui.history import HistoryStore
from src.gui.request_worker import RequestResult, RequestSpec, RequestWorker
from src.gui.settings import Settings
from src.gui.validation import ValidationError, normalize_url, validate_headers
from src.gui.widgets import HeaderTable, HighlightedText, style_text

POLL_MS = 50


class ClientTab(ttk.Frame):
    """URL, метод, заголовки, тело, кнопки, область ответа, индикатор загрузки.

    Запрос идёт в фоновом потоке, результат приходит через queue.Queue и root.after.
    """

    METHODS = ("GET", "POST")

    def __init__(self, master: tk.Misc, settings: Settings,
                 history: Optional[HistoryStore] = None,
                 worker: Optional[RequestWorker] = None):
        super().__init__(master)
        self.settings = settings
        self._history = history
        self._worker = worker or RequestWorker()
        self._results: "queue.Queue[RequestResult]" = queue.Queue()
        self._palette: Dict[str, str] = {"ok": "#1a8f3c", "error": "#c62828", "warn": "#b26a00",
                                         "fg": "#000000"}
        self._poll_id: Optional[str] = None
        self.busy = False
        self.url_var = tk.StringVar(value="http://localhost:8080/")
        self.method_var = tk.StringVar(value="GET")
        self.status_var = tk.StringVar(value="—")
        self.time_var = tk.StringVar(value="")
        self._build()
        self._update_body_state()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))
        top.columnconfigure(1, weight=1)
        ttk.Label(top, text="URL:").grid(row=0, column=0, padx=(0, 6))
        url_entry = ttk.Entry(top, textvariable=self.url_var)
        url_entry.grid(row=0, column=1, sticky="ew")
        url_entry.bind("<Return>", lambda _e: self.send())
        method_box = ttk.Combobox(top, textvariable=self.method_var, values=self.METHODS,
                                  state="readonly", width=7)
        method_box.grid(row=0, column=2, padx=6)
        method_box.bind("<<ComboboxSelected>>", lambda _e: self._update_body_state())
        self.send_button = ttk.Button(top, text="Отправить", command=self.send)
        self.send_button.grid(row=0, column=3)
        ttk.Button(top, text="Очистить", command=self.clear).grid(row=0, column=4, padx=(6, 0))

        headers_frame = ttk.LabelFrame(self, text="Заголовки запроса")
        headers_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=4)
        headers_frame.columnconfigure(0, weight=1)
        self.header_table = HeaderTable(headers_frame, height=3)
        self.header_table.grid(row=0, column=0, sticky="ew", padx=6, pady=6)

        body_frame = ttk.LabelFrame(self, text="Тело запроса (только для POST)")
        body_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=4)
        body_frame.columnconfigure(0, weight=1)
        self.body_text = tk.Text(body_frame, height=4, wrap="word", font="TkFixedFont")
        self.body_text.grid(row=0, column=0, sticky="ew", padx=6, pady=6)

        status_row = ttk.Frame(self)
        status_row.grid(row=3, column=0, sticky="ew", padx=10, pady=(6, 0))
        ttk.Label(status_row, text="Статус:").pack(side="left")
        self.status_label = ttk.Label(status_row, textvariable=self.status_var)
        self.status_label.pack(side="left", padx=(6, 16))
        ttk.Label(status_row, textvariable=self.time_var).pack(side="left")
        self.spinner_label = ttk.Label(status_row, text="Отправка…")
        self.spinner = ttk.Progressbar(status_row, mode="indeterminate", length=110)

        response = ttk.Frame(self)
        response.grid(row=4, column=0, sticky="nsew", padx=10, pady=(4, 10))
        response.columnconfigure(0, weight=1)
        response.rowconfigure(1, weight=1)
        response.rowconfigure(3, weight=3)
        ttk.Label(response, text="Заголовки ответа").grid(row=0, column=0, sticky="w")
        self.response_headers = HighlightedText(response, height=5)
        self.response_headers.grid(row=1, column=0, sticky="nsew", pady=(0, 6))
        ttk.Label(response, text="Тело ответа").grid(row=2, column=0, sticky="w")
        self.response_body = HighlightedText(response, height=10)
        self.response_body.grid(row=3, column=0, sticky="nsew")

    # ----- действия пользователя -----

    def send(self) -> None:
        """Проверить ввод и отправить запрос в фоне."""
        if self.busy:
            return
        try:
            spec = self._build_spec()
        except ValidationError as exc:
            self._show_error(str(exc))
            return
        self._set_busy(True)
        self.status_var.set("…")
        self.time_var.set("")
        self.response_headers.clear()
        self.response_body.clear()
        self._worker.submit(spec, self._results)
        self._poll_id = self.after(POLL_MS, self._poll)

    def clear(self) -> None:
        """Очистить поля ввода и область ответа."""
        self.url_var.set("")
        self.method_var.set("GET")
        self.header_table.clear()
        self.body_text.configure(state="normal")
        self.body_text.delete("1.0", "end")
        self._update_body_state()
        self.response_headers.clear()
        self.response_body.clear()
        self.status_var.set("—")
        self.time_var.set("")
        self._set_status_color(None)

    def _build_spec(self) -> RequestSpec:
        url = normalize_url(self.url_var.get())
        self.url_var.set(url)
        headers = validate_headers(self.header_table.get_rows())
        method = self.method_var.get()
        body = b""
        if method == "POST":
            body = self.body_text.get("1.0", "end-1c").encode("utf-8")
            if not any(name.lower() == "content-type" for name in headers):
                headers["Content-Type"] = "text/plain; charset=utf-8"
        return RequestSpec(method, url, headers, body, self.settings.timeout,
                           self.settings.max_redirects)

    # ----- результат из фонового потока -----

    def _poll(self) -> None:
        try:
            result = self._results.get_nowait()
        except queue.Empty:
            self._poll_id = self.after(POLL_MS, self._poll)
            return
        self._poll_id = None
        self._set_busy(False)
        self._show_result(result)

    def _show_result(self, result: RequestResult) -> None:
        self.time_var.set(f"{result.elapsed_ms:.0f} мс")
        if result.error is not None:
            self.status_var.set("Ошибка")
            self._set_status_color("error")
            self.response_headers.clear()
            self.response_body.set_error(result.error)
        else:
            response = result.response
            self.status_var.set(f"{response.status} {response.reason}")
            self._set_status_color("ok" if response.status < 400 else "error")
            self.response_headers.set_text(
                "\n".join(f"{name}: {value}" for name, value in response.headers.items()))
            text, kind = format_body(response.body, response.headers.get("Content-Type", ""))
            self.response_body.set_text(text, kind)
        self._save_history(result)

    def _save_history(self, result: RequestResult) -> None:
        if not (self.settings.save_history and self._history):
            return
        self._history.add({
            "time": datetime.now().isoformat(timespec="seconds"),
            "method": result.spec.method,
            "url": result.spec.url,
            "status": result.response.status if result.response else None,
            "error": result.error,
            "ms": round(result.elapsed_ms),
        })

    def _show_error(self, message: str) -> None:
        """Ошибка проверки ввода — в области ответа, не в консоли."""
        self.status_var.set("Ошибка ввода")
        self.time_var.set("")
        self._set_status_color("error")
        self.response_headers.clear()
        self.response_body.set_error(message)

    # ----- оформление -----

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        if busy:
            self.send_button.state(["disabled"])
            self.spinner_label.pack(side="right")
            self.spinner.pack(side="right", padx=(0, 6))
            self.spinner.start(12)
        else:
            self.spinner.stop()
            self.spinner.pack_forget()
            self.spinner_label.pack_forget()
            self.send_button.state(["!disabled"])

    def _update_body_state(self) -> None:
        """Тело запроса доступно только для POST."""
        self.body_text.configure(state="normal" if self.method_var.get() == "POST" else "disabled")

    def _set_status_color(self, kind: Optional[str]) -> None:
        color = self._palette.get(kind) if kind else self._palette["fg"]
        self.status_label.configure(foreground=color)

    def apply_palette(self, palette: Dict[str, str]) -> None:
        """Применить тему."""
        self._palette = palette
        style_text(self.body_text, palette)
        self.response_headers.configure_palette(palette)
        self.response_body.configure_palette(palette)
        self._set_status_color(None)

    def destroy(self) -> None:
        """Отменить отложенный опрос очереди."""
        if self._poll_id is not None:
            self.after_cancel(self._poll_id)
            self._poll_id = None
        super().destroy()
