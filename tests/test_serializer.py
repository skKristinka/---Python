"""Unit-тесты Serializer (включая обратное преобразование через Parser)."""
import pytest

from src.http.parser import Parser
from src.http.request import Request
from src.http.response import Response
from src.http.serializer import Serializer

serializer = Serializer()
parser = Parser()


def test_request_ends_headers_with_blank_line():
    raw = serializer.serialize_request(Request("GET", "/", headers={"Host": "h"}))
    assert raw == b"GET / HTTP/1.1\r\nHost: h\r\n\r\n"


def test_request_adds_content_length_for_body():
    raw = serializer.serialize_request(Request("POST", "/x", headers={"Host": "h"}, body=b"abc"))
    assert b"Content-Length: 3\r\n" in raw
    assert raw.endswith(b"\r\n\r\nabc")


def test_request_keeps_existing_content_length():
    req = Request("POST", "/", headers={"content-length": "3"}, body=b"abc")
    assert serializer.serialize_request(req).count(b"ontent-") == 1


def test_response_has_content_length_and_date():
    raw = serializer.serialize_response(Response(status=200, body=b"Hello"))
    assert raw.startswith(b"HTTP/1.1 200 OK\r\n")
    assert b"Content-Length: 5\r\n" in raw
    assert b"Date: " in raw
    assert raw.endswith(b"\r\n\r\nHello")


def test_response_overrides_wrong_content_length_and_drops_chunked():
    resp = Response(headers={"Content-Length": "999", "Transfer-Encoding": "chunked"}, body=b"ab")
    raw = serializer.serialize_response(resp)
    assert b"Content-Length: 2\r\n" in raw
    assert b"Transfer-Encoding" not in raw


def test_response_keeps_custom_headers():
    resp = Response(status=404, headers={"Content-Type": "text/plain"}, body=b"x")
    raw = serializer.serialize_response(resp)
    assert b"HTTP/1.1 404 Not Found\r\n" in raw
    assert b"Content-Type: text/plain\r\n" in raw


def test_serialize_does_not_mutate_original():
    resp = Response(headers={"X-A": "1"}, body=b"x")
    serializer.serialize_response(resp)
    assert resp.headers == {"X-A": "1"}


def test_roundtrip_request():
    req = Request("POST", "/echo?a=1", headers={"Host": "h", "Content-Type": "text/plain"},
                  body=b"hello")
    parsed = parser.parse_request(serializer.serialize_request(req))
    assert (parsed.method, parsed.path, parsed.body) == ("POST", "/echo?a=1", b"hello")
    assert parsed.headers["Content-Type"] == "text/plain"


def test_roundtrip_response():
    resp = Response(status=418, headers={"Content-Type": "text/plain"}, body="чайник".encode())
    parsed = parser.parse_response(serializer.serialize_response(resp))
    assert (parsed.status, parsed.reason, parsed.body) == (418, "I'm a teapot", "чайник".encode())


def test_header_injection_is_rejected():
    with pytest.raises(ValueError):
        serializer.serialize_response(Response(headers={"X-Evil": "a\r\nSet-Cookie: b=1"}))
