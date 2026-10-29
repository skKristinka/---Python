"""Переиспользуемые виджеты: таблицы заголовков и лога, подсвеченный текст, индикатор."""
import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional, Tuple

from src.gui.formatting import tokenize
from src.server.http_server import LogEntry

MAX_HIGHLIGHT = 100_000
_TAG_COLORS = {
    "json_key": "key", "json_string": "string", "json_number": "number",
    "json_keyword": "keyword", "html_tag": "tag", "html_comment": "comment", "error": "error",
}


def style_text(text: tk.Text, palette: Dict[str, str]) -> None:
    """Раскрасить обычный tk.Text по палитре."""
    text.configure(background=palette["field"], foreground=palette["fg"],
                   insertbackground=palette["fg"], selectbackground=palette["select"],
                   highlightbackground=palette["muted"], highlightcolor=palette["muted"],
                   relief="flat", highlightthickness=1)


class HeaderTable(ttk.Frame):
    """Таблица заголовков «имя → значение»: добавить/удалить строку, правка двойным кликом."""

    def __init__(self, master: tk.Misc, height: int = 4):
        super().__init__(master)
        self._data: Dict[str, Tuple[str, str]] = {}
        self._editor: Optional[ttk.Entry] = None
        self.tree = ttk.Treeview(self, columns=("name", "value"), show="headings",
                                 height=height, selectmode="browse")
        self.tree.heading("name", text="Заголовок")
        self.tree.heading("value", text="Значение")
        self.tree.column("name", width=170, stretch=False)
        self.tree.column("value", width=360, stretch=True)
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        buttons = ttk.Frame(self)
        ttk.Button(buttons, text="Добавить", command=self._on_add).pack(fill="x", pady=(0, 4))
        ttk.Button(buttons, text="Удалить", command=self.remove_selected).pack(fill="x")
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        buttons.grid(row=0, column=2, sticky="n", padx=(8, 0))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.tree.bind("<Double-1>", self._on_double_click)

    def add_row(self, name: str = "", value: str = "") -> str:
        """Добавить строку и вернуть её идентификатор."""
        item = self.tree.insert("", "end", values=(name, value))
        self._data[item] = (name, value)
        self.tree.selection_set(item)
        return item

    def remove_selected(self) -> None:
        """Удалить выделенные строки."""
        self._close_editor()
        for item in self.tree.selection():
            self.tree.delete(item)
            self._data.pop(item, None)

    def clear(self) -> None:
        """Удалить все строки."""
        self._close_editor()
        for item in list(self._data):
            self.tree.delete(item)
        self._data.clear()

    def get_rows(self) -> List[Tuple[str, str]]:
        """Строки таблицы в порядке показа."""
        return [self._data[item] for item in self.tree.get_children() if item in self._data]

    def _on_add(self) -> None:
        item = self.add_row("X-Header", "value")
        self.tree.update_idletasks()
        self._edit(item, "#1")

    def _on_double_click(self, event: tk.Event) -> None:
        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if item and column in ("#1", "#2"):
            self._edit(item, column)

    def _edit(self, item: str, column: str) -> None:
        """Показать поле ввода поверх ячейки."""
        self._close_editor()
        box = self.tree.bbox(item, column)
        if not box:
            return
        x, y, width, height = box
        index = int(column[1:]) - 1
        entry = ttk.Entry(self.tree)
        entry.insert(0, self._data[item][index])
        entry.select_range(0, "end")
        entry.place(x=x, y=y, width=width, height=height)
        entry.focus_set()
        entry.bind("<Return>", lambda _e: self._commit(item, index, entry))
        entry.bind("<FocusOut>", lambda _e: self._commit(item, index, entry))
        entry.bind("<Escape>", lambda _e: self._close_editor())
        self._editor = entry

    def _commit(self, item: str, index: int, entry: ttk.Entry) -> None:
        if entry is not self._editor:
            return
        if item in self._data:
            values = list(self._data[item])
            values[index] = entry.get()
            self._data[item] = (values[0], values[1])
            self.tree.item(item, values=self._data[item])
        self._close_editor()

    def _close_editor(self) -> None:
        if self._editor is not None:
            editor, self._editor = self._editor, None
            editor.destroy()


class LogTable(ttk.Frame):
    """Таблица лога сервера: время, метод, путь, статус, мс."""

    MAX_ROWS = 5000

    def __init__(self, master: tk.Misc):
        super().__init__(master)
        self._count = 0
        columns = ("time", "method", "path", "status", "ms")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")
        for name, title, width in (("time", "Время", 80), ("method", "Метод", 70),
                                   ("path", "Путь", 320), ("status", "Статус", 70),
                                   ("ms", "мс", 70)):
            self.tree.heading(name, text=title)
            self.tree.column(name, width=width, stretch=(name == "path"))
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

    @property
    def row_count(self) -> int:
        """Сколько строк в таблице."""
        return self._count

    def append(self, entry: LogEntry) -> None:
        """Добавить запись лога и прокрутить вниз."""
        tag = "ok" if entry.status < 400 else "error"
        self.tree.insert("", "end", tags=(tag,),
                         values=(entry.time, entry.method, entry.path, entry.status,
                                 f"{entry.ms:.1f}"))
        self._count += 1
        if self._count > self.MAX_ROWS:
            oldest = self.tree.get_children()[:self._count - self.MAX_ROWS]
            self.tree.delete(*oldest)
            self._count -= len(oldest)
        self.tree.yview_moveto(1.0)

    def clear(self) -> None:
        """Очистить лог."""
        self.tree.delete(*self.tree.get_children())
        self._count = 0

    def configure_palette(self, palette: Dict[str, str]) -> None:
        """Цвета строк по статусу."""
        self.tree.tag_configure("ok", foreground=palette["ok"])
        self.tree.tag_configure("error", foreground=palette["error"])


class HighlightedText(ttk.Frame):
    """Текст только для чтения с подсветкой JSON/HTML и сообщениями об ошибках."""

    def __init__(self, master: tk.Misc, height: int = 8):
        super().__init__(master)
        self.text = tk.Text(self, height=height, wrap="none", font="TkFixedFont",
                            state="disabled")
        vertical = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        horizontal = ttk.Scrollbar(self, orient="horizontal", command=self.text.xview)
        self.text.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

    def set_text(self, content: str, kind: str = "text") -> None:
        """Показать текст; kind = json / html / text."""
        self._replace(content)
        if kind in ("json", "html"):
            for start, end, name in tokenize(content[:MAX_HIGHLIGHT], kind):
                self.text.tag_add(f"{kind}_{name}", f"1.0+{start}c", f"1.0+{end}c")

    def set_error(self, message: str) -> None:
        """Показать сообщение об ошибке красным."""
        self._replace(message)
        self.text.tag_add("error", "1.0", "end-1c")

    def clear(self) -> None:
        """Очистить."""
        self._replace("")

    def get_text(self) -> str:
        """Текущее содержимое."""
        return self.text.get("1.0", "end-1c")

    def configure_palette(self, palette: Dict[str, str]) -> None:
        """Цвета фона, текста и подсветки."""
        style_text(self.text, palette)
        for tag, color in _TAG_COLORS.items():
            self.text.tag_configure(tag, foreground=palette[color])

    def _replace(self, content: str) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self.text.configure(state="disabled")


class StatusIndicator(ttk.Frame):
    """Индикатор состояния: зелёный (работает) / красный (остановлен)."""

    def __init__(self, master: tk.Misc):
        super().__init__(master)
        self._running = False
        self._palette: Dict[str, str] = {"ok": "#1a8f3c", "error": "#c62828", "bg": "#f2f2f2"}
        self._canvas = tk.Canvas(self, width=18, height=18, highlightthickness=0)
        self._dot = self._canvas.create_oval(2, 2, 16, 16, outline="")
        self._label = ttk.Label(self, text="Остановлен")
        self._canvas.pack(side="left")
        self._label.pack(side="left", padx=(6, 0))
        self._redraw()

    @property
    def running(self) -> bool:
        """Показывает ли индикатор «работает»."""
        return self._running

    def set_running(self, running: bool) -> None:
        """Переключить состояние."""
        self._running = running
        self._redraw()

    def configure_palette(self, palette: Dict[str, str]) -> None:
        """Применить палитру темы."""
        self._palette = palette
        self._redraw()

    def _redraw(self) -> None:
        color = self._palette["ok"] if self._running else self._palette["error"]
        self._canvas.configure(background=self._palette["bg"])
        self._canvas.itemconfigure(self._dot, fill=color)
        self._label.configure(text="Запущен" if self._running else "Остановлен")
