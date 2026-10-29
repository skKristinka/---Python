"""Тесты фонового запроса клиента (RequestWorker) на настоящем сервере."""
import queue
import socket

import pytest

from src.gui.request_worker import RequestSpec, RequestWorker
from src.server.handlers import build_router
from src.server.http_server import HttpServer


@pytest.fixture
def server():
    srv = HttpServer(build_router(), port=0)
    srv.start()
    yield srv
    srv.stop()


def spec_for(url, method="GET", body=b"", headers=None, timeout=2.0):
    return RequestSpec(method, url, headers or {}, body, timeout, 0)


def run(spec, factory=None):
    results = queue.Queue()
    worker = RequestWorker(factory) if factory else RequestWorker()
    worker.submit(spec, results).join(timeout=10)
    return results.get(timeout=1)


def test_successful_request(server):
    result = run(spec_for(f"http://127.0.0.1:{server.port}/"))
    assert result.error is None
    assert result.response.status == 200 and b"Hello" in result.response.body
    assert result.elapsed_ms >= 0


def test_post_echo(server):
    spec = spec_for(f"http://127.0.0.1:{server.port}/echo", "POST", b"hello",
                    {"Content-Type": "text/plain"})
    assert run(spec).response.body == b"hello"


def test_404_is_a_response_not_an_error(server):
    result = run(spec_for(f"http://127.0.0.1:{server.port}/nope"))
    assert result.error is None and result.response.status == 404


def test_connection_refused_becomes_error_text():
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    result = run(spec_for(f"http://127.0.0.1:{port}/"))
    assert result.response is None
    assert result.error.startswith("ConnectionError")


def test_invalid_url_becomes_error_text():
    result = run(spec_for("garbage"))
    assert result.response is None and result.error.startswith("ParseError")


def test_timeout_becomes_error_text():
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    try:
        result = run(spec_for(f"http://127.0.0.1:{listener.getsockname()[1]}/", timeout=0.2))
    finally:
        listener.close()
    assert result.error.startswith("TimeoutError")


def test_unexpected_exception_does_not_kill_the_thread():
    def broken_factory(**_kwargs):
        raise RuntimeError("boom")

    result = run(spec_for("http://127.0.0.1:1/"), broken_factory)
    assert result.response is None
    assert "Непредвиденная ошибка" in result.error and "boom" in result.error
