"""Настройка logging: вывод в файл и в очередь для GUI."""
import logging
import queue
from typing import Optional


class QueueLogHandler(logging.Handler):
    """Кладёт отформатированные записи в очередь; GUI забирает их через root.after."""

    def __init__(self, target: "queue.Queue[str]"):
        super().__init__()
        self.target = target

    def emit(self, record: logging.LogRecord) -> None:
        """Отправить запись в очередь."""
        try:
            self.target.put_nowait(self.format(record))
        except Exception:  # pylint: disable=broad-except
            self.handleError(record)


def setup_logging(log_file: str = "http_gui.log",
                  gui_queue: Optional["queue.Queue[str]"] = None) -> logging.Logger:
    """Настроить логгер http_gui (его дочерние логгеры наследуют обработчики)."""
    logger = logging.getLogger("http_gui")
    logger.setLevel(logging.INFO)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    if gui_queue is not None:
        gui_handler = QueueLogHandler(gui_queue)
        gui_handler.setFormatter(formatter)
        logger.addHandler(gui_handler)
    return logger
