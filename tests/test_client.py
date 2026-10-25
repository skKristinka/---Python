"""Тесты HttpClient на локальном тестовом сервере (см. conftest.py)."""
import socket

import pytest

from src.client.http_client import HttpClient
from src.http.exceptions import HttpError, ParseError

OK_HELLO = b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nhello"


def url(server, path="/"):
    return f"http://127.0.0.1:{server.port}{path}"


def test_get_returns_response(scripted_server):
    server = scripted_server([[OK_HELLO]])
    response = HttpClient(timeout=2).get(url(server, "/path?x=1"))
    assert (response.status, response.body) == (200, b"hello")
    request = server.requests[0]
    assert request.startswith(b"GET /path?x=1 HTTP/1.1\r\n")
    assert f"Host: 127.0.0.1:{server.port}".encode() in request


def test_post_sends_body_and_headers(scripted_server):
    server = scripted_server([[b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n"]])
    HttpClient(timeout=2).post(url(server, "/echo"), b"abc", "application/json")
    request = server.requests[0]
    assert request.startswith(b"POST /echo HTTP/1.1\r\n")
    assert b"Content-Type: application/json\r\n" in request
    assert b"Content-Length: 3\r\n" in request
    assert request.endswith(b"\r\n\r\nabc")


def test_custom_header_overrides_default(scripted_server):
    server = scripted_server([[OK_HELLO]])
    HttpClient(timeout=2).get(url(server), {"user-agent": "custom"})
    request = server.requests[0]
    assert b"user-agent: custom" in request
    assert b"User-Agent" not in request


def test_chunked_response_arriving_in_pieces(scripted_server):
    server = scripted_server([[
        b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n", 0.05,
        b"5\r\nhel", 0.05, b"lo\r\n0\r\n\r\n",
    ]])
    assert HttpClient(timeout=2).get(url(server)).body == b"hello"


def test_response_without_length_is_read_until_close(scripted_server):
    server = scripted_server([[b"HTTP/1.1 200 OK\r\n\r\npart1", 0.05, b"part2"]])
    assert HttpClient(timeout=2).get(url(server)).body == b"part1part2"


def test_timeout(scripted_server):
    server = scripted_server([[1.0]])
    with pytest.raises(TimeoutError):
        HttpClient(timeout=0.2).get(url(server))


def test_connection_refused():
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    with pytest.raises(ConnectionError):
        HttpClient(timeout=2).get(f"http://127.0.0.1:{port}/")


def test_unknown_host():
    with pytest.raises(ConnectionError):
        HttpClient(timeout=2).get("http://nonexistent.invalid/")


def test_server_closes_without_answer(scripted_server):
    server = scripted_server([[]])
    with pytest.raises(ConnectionError):
        HttpClient(timeout=2).get(url(server))


def test_garbage_response(scripted_server):
    server = scripted_server([[b"garbage garbage\r\n\r\n"]])
    with pytest.raises(ParseError):
        HttpClient(timeout=2).get(url(server))


def test_invalid_url():
    with pytest.raises(ParseError):
        HttpClient().get("garbage")


def test_header_injection_is_parse_error():
    with pytest.raises(ParseError):
        HttpClient().get("http://127.0.0.1:1/", {"X-Evil": "a\r\nb: c"})


def test_404_is_returned_by_default(scripted_server):
    server = scripted_server([[b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n"]])
    assert HttpClient(timeout=2).get(url(server)).status == 404


def test_raise_for_status(scripted_server):
    server = scripted_server([[b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n"]])
    with pytest.raises(HttpError) as info:
        HttpClient(timeout=2, raise_for_status=True).get(url(server))
    assert info.value.status == 404


REDIRECT = b"HTTP/1.1 302 Found\r\nLocation: /next\r\nContent-Length: 0\r\n\r\n"


def test_redirect_is_followed(scripted_server):
    server = scripted_server([[REDIRECT], [b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok"]])
    response = HttpClient(timeout=2, max_redirects=3).get(url(server, "/start"))
    assert response.body == b"ok"
    assert len(server.requests) == 2
    assert server.requests[1].startswith(b"GET /next ")


def test_redirect_is_not_followed_by_default(scripted_server):
    server = scripted_server([[REDIRECT]])
    assert HttpClient(timeout=2).get(url(server)).status == 302
    assert len(server.requests) == 1


def test_redirect_limit(scripted_server):
    server = scripted_server([[REDIRECT], [REDIRECT], [REDIRECT]])
    response = HttpClient(timeout=2, max_redirects=2).get(url(server))
    assert response.status == 302
    assert len(server.requests) == 3


def test_post_303_becomes_get(scripted_server):
    see_other = b"HTTP/1.1 303 See Other\r\nLocation: /r\r\nContent-Length: 0\r\n\r\n"
    server = scripted_server([[see_other], [OK_HELLO]])
    HttpClient(timeout=2, max_redirects=1).post(url(server), b"data")
    assert server.requests[1].startswith(b"GET /r ")
    assert server.requests[1].endswith(b"\r\n\r\n")
