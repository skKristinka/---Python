"""Тесты настройки logging (файл + очередь для GUI)."""
import logging
import os
import queue
import tempfile

from src.logging_setup import setup_logging


def test_records_go_to_file_and_queue():
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "app.log")
        gui_queue = queue.Queue()
        logger = setup_logging(path, gui_queue)
        try:
            logging.getLogger("http_gui.server").info("запрос обработан")
            line = gui_queue.get(timeout=1)
            assert "запрос обработан" in line and "INFO" in line
            for handler in logger.handlers:
                handler.flush()
            with open(path, encoding="utf-8") as file:
                assert "запрос обработан" in file.read()
        finally:
            setup_logging(os.devnull)


def test_repeated_setup_does_not_duplicate_handlers():
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "app.log")
        gui_queue = queue.Queue()
        setup_logging(path, gui_queue)
        logger = setup_logging(path, gui_queue)
        try:
            assert len(logger.handlers) == 2
        finally:
            setup_logging(os.devnull)
