"""Интеграционные тесты: HttpServer в потоке + HttpClient (клиент ↔ сервер)."""
import json
import socket
import threading
import time

import pytest

from src.client.http_client import HttpClient
from src.http.parser import Parser
from src.http.reader import read_message
from src.http.response import Response
from src.net.socket_wrapper import Socket
from src.server.handlers import build_router
from src.server.http_server import HttpServer


def slow_handler(_req):
    time.sleep(1)
    return Response(status=200, body=b"slow")


@pytest.fixture
def server():
    router = build_router()
    router.route("GET", "/sleep", slow_handler)
    srv = HttpServer(router, port=0)
    srv.start()
    yield srv
    srv.stop()


def url(srv, path="/"):
    return f"http://127.0.0.1:{srv.port}{path}"


def raw_exchange(port, data, half_close=True):
    """Отправить сырые байты и прочитать всё до закрытия соединения."""
    with socket.create_connection(("127.0.0.1", port), timeout=2) as sock:
        sock.sendall(data)
        if half_close:
            sock.shutdown(socket.SHUT_WR)
        chunks = []
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
    return b"".join(chunks)


def test_get_root_returns_hello(server):
    response = HttpClient(timeout=2).get(url(server))
    assert response.status == 200
    assert b"Hello" in response.body


def test_post_echo(server):
    response = HttpClient(timeout=2).post(url(server, "/echo"), b"abc", "text/plain")
    assert (response.status, response.body) == (200, b"abc")
    assert response.headers["Content-Type"] == "text/plain"


def test_post_echo_keeps_binary_and_unicode(server):
    body = "привет".encode("utf-8") + b"\x00\xff"
    response = HttpClient(timeout=2).post(url(server, "/echo"), body, "application/octet-stream")
    assert response.body == body


def test_status_404_and_unknown_path(server):
    client = HttpClient(timeout=2)
    assert client.get(url(server, "/status/404")).status == 404
    assert client.get(url(server, "/status/418")).status == 418
    assert client.get(url(server, "/nonexistent")).status == 404


def test_time_and_headers_json(server):
    client = HttpClient(timeout=2)
    assert "time" in json.loads(client.get(url(server, "/time")).body)
    data = json.loads(client.get(url(server, "/headers"), {"X-Test": "42"}).body)
    assert data["X-Test"] == "42"
    assert data["Host"] == f"127.0.0.1:{server.port}"


def test_100_sequential_requests(server):
    client = HttpClient(timeout=2)
    assert all(client.get(url(server)).status == 200 for _ in range(100))


def test_10_parallel_requests(server):
    statuses = []

    def worker():
        statuses.append(HttpClient(timeout=5).get(url(server)).status)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert statuses == [200] * 10


def test_client_timeout_when_server_sleeps(server):
    with pytest.raises(TimeoutError):
        HttpClient(timeout=0.1).get(url(server, "/sleep"))


def test_garbage_gets_400_and_server_survives(server):
    answer = raw_exchange(server.port, b"garbage garbage\r\n\r\n")
    assert answer.startswith(b"HTTP/1.1 400 Bad Request")
    assert HttpClient(timeout=2).get(url(server)).status == 200


def test_incomplete_request_gets_400(server):
    assert raw_exchange(server.port, b"GARBAGE").startswith(b"HTTP/1.1 400")


def test_missing_host_gets_400(server):
    assert raw_exchange(server.port, b"GET / HTTP/1.1\r\n\r\n").startswith(b"HTTP/1.1 400")


def test_huge_header_gets_400(server):
    data = b"GET / HTTP/1.1\r\nHost: h\r\nX-Big: " + b"a" * 9000 + b"\r\n\r\n"
    assert raw_exchange(server.port, data).startswith(b"HTTP/1.1 400")


def test_keep_alive_three_requests_on_one_connection(server):
    request = b"GET / HTTP/1.1\r\nHost: h\r\n\r\n"
    with socket.create_connection(("127.0.0.1", server.port), timeout=2) as raw:
        sock = Socket(raw)
        for _ in range(3):
            sock.send_all(request)
            response = Parser().parse_response(read_message(sock, is_response=True))
            assert response.status == 200
            assert response.headers["Connection"] == "keep-alive"


def test_connection_close_is_honored(server):
    answer = raw_exchange(server.port, b"GET / HTTP/1.1\r\nHost: h\r\nConnection: close\r\n\r\n",
                          half_close=False)
    assert b"Connection: close" in answer


def test_http10_closes_after_response(server):
    answer = raw_exchange(server.port, b"GET / HTTP/1.0\r\n\r\n", half_close=False)
    assert answer.startswith(b"HTTP/1.1 200") and b"Connection: close" in answer


def test_1000_requests_no_failures_and_no_leaks(server):
    client = HttpClient(timeout=2)
    for _ in range(1000):
        assert client.get(url(server)).status == 200
    deadline = time.time() + 2
    while server.active_connections and time.time() < deadline:
        time.sleep(0.05)
    assert server.active_connections == 0


def test_log_entry_is_queued(server):
    HttpClient(timeout=2).get(url(server, "/status/418"))
    entry = server.log_queue.get(timeout=2)
    assert (entry.method, entry.path, entry.status) == ("GET", "/status/418", 418)
    assert entry.ms >= 0


def test_handler_crash_gives_500_and_server_survives():
    router = build_router()
    router.route("GET", "/boom", lambda req: 1 / 0)
    srv = HttpServer(router, port=0)
    srv.start()
    try:
        client = HttpClient(timeout=2)
        assert client.get(url(srv, "/boom")).status == 500
        assert client.get(url(srv)).status == 200
    finally:
        srv.stop()


def test_stop_releases_port_and_restart_works():
    srv = HttpServer(build_router(), port=0)
    srv.start()
    port = srv.port
    assert HttpClient(timeout=2).get(f"http://127.0.0.1:{port}/").status == 200
    srv.stop()
    assert not srv.is_running
    with pytest.raises(ConnectionError):
        HttpClient(timeout=1).get(f"http://127.0.0.1:{port}/")
    again = HttpServer(build_router(), port=port)
    again.start()
    try:
        assert HttpClient(timeout=2).get(f"http://127.0.0.1:{port}/").status == 200
    finally:
        again.stop()


def test_stop_closes_idle_keep_alive_connection(server):
    raw = socket.create_connection(("127.0.0.1", server.port), timeout=3)
    try:
        raw.sendall(b"GET / HTTP/1.1\r\nHost: h\r\n\r\n")
        read_message(Socket(raw), is_response=True)
        started = time.time()
        server.stop()
        assert time.time() - started < 2
        assert raw.recv(10) == b""
    finally:
        raw.close()


def test_start_twice_is_error(server):
    with pytest.raises(RuntimeError):
        server.start()


def test_port_in_use_is_connection_error():
    blocker = socket.socket()
    blocker.bind(("127.0.0.1", 0))
    blocker.listen()
    try:
        with pytest.raises(ConnectionError):
            HttpServer(build_router(), port=blocker.getsockname()[1]).start()
    finally:
        blocker.close()


def test_stop_without_start_is_safe():
    HttpServer(build_router(), port=0).stop()
