"""Дымовой тест GUI на настоящем Tk (пропускается без tkinter или дисплея)."""
import os
import tempfile
import time

import pytest

from src.client.http_client import HttpClient
from src.server.handlers import build_router
from src.server.http_server import HttpServer

tk = pytest.importorskip("tkinter")


@pytest.fixture
def app():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("нет дисплея для Tk")
    from src.gui.app import App  # импорт после проверки tkinter
    with tempfile.TemporaryDirectory() as directory:
        application = App(root, os.path.join(directory, "app.log"),
                          os.path.join(directory, "history.json"))
        yield application
        application.close()
        from src.logging_setup import setup_logging
        setup_logging(os.devnull)


def wait_until(root, condition, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        root.update()
        if condition():
            return True
        time.sleep(0.01)
    return False


def test_client_tab_gets_response_from_server(app):
    server = HttpServer(build_router(), port=0)
    server.start()
    try:
        client = app.client_tab
        client.url_var.set(f"http://127.0.0.1:{server.port}/")
        client.send()
        assert wait_until(app.root, lambda: not client.busy)
        assert client.status_var.get() == "200 OK"
        assert "Hello" in client.response_body.get_text()
    finally:
        server.stop()


def test_client_tab_shows_error_in_response_area(app):
    client = app.client_tab
    client.url_var.set("http://")
    client.send()
    assert client.status_var.get() == "Ошибка ввода"
    assert client.response_body.get_text()


def test_server_tab_start_log_stop(app):
    probe = HttpServer(build_router(), port=0)
    probe.start()
    port = probe.port
    probe.stop()
    tab = app.server_tab
    tab.port_var.set(str(port))
    tab.start_server()
    try:
        assert tab.is_running and tab.indicator.running
        HttpClient(timeout=2).get(f"http://127.0.0.1:{port}/status/418")
        assert wait_until(app.root, lambda: tab.log_table.row_count == 1)
    finally:
        tab.stop_server()
    assert not tab.is_running and not tab.indicator.running


def test_theme_switch(app):
    app.apply_theme("dark")
    app.apply_theme("light")
