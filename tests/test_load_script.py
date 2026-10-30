"""Тест нагрузочного скрипта на настоящем сервере."""
import pytest

from scripts.load_test import run_load
from src.server.handlers import build_router
from src.server.http_server import HttpServer


@pytest.fixture
def server():
    srv = HttpServer(build_router(), port=0)
    srv.start()
    yield srv
    srv.stop()


def test_100_parallel_requests_all_ok(server):
    assert run_load(f"http://127.0.0.1:{server.port}/", total=100) == {"200": 100}


def test_errors_are_counted_not_raised():
    result = run_load("http://127.0.0.1:1/", total=3, timeout=1)
    assert result == {"ConnectionError": 3}
