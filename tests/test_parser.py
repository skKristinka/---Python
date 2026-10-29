"""Unit-тесты Parser."""
import pytest

from src.http.exceptions import ParseError
from src.http.parser import MAX_HEADER_SIZE, Parser

parser = Parser()


def test_request_basic():
    req = parser.parse_request(b"GET /a?x=1 HTTP/1.1\r\nHost: example.com\r\n\r\n")
    assert (req.method, req.path, req.version) == ("GET", "/a?x=1", "HTTP/1.1")
    assert req.headers == {"Host": "example.com"}
    assert req.body == b""


def test_request_with_content_length_body():
    raw = b"POST /echo HTTP/1.1\r\nHost: h\r\nContent-Length: 5\r\n\r\nhello"
    assert parser.parse_request(raw).body == b"hello"


def test_request_body_longer_than_length_is_cut():
    raw = b"POST / HTTP/1.1\r\nHost: h\r\nContent-Length: 2\r\n\r\nabcdef"
    assert parser.parse_request(raw).body == b"ab"


def test_request_body_shorter_than_length():
    raw = b"POST / HTTP/1.1\r\nHost: h\r\nContent-Length: 10\r\n\r\nabc"
    with pytest.raises(ParseError):
        parser.parse_request(raw)


def test_request_without_host_http11():
    with pytest.raises(ParseError):
        parser.parse_request(b"GET / HTTP/1.1\r\n\r\n")


def test_request_without_host_http10_ok():
    assert parser.parse_request(b"GET / HTTP/1.0\r\n\r\n").version == "HTTP/1.0"


@pytest.mark.parametrize("raw", [
    b"GARBAGE\r\n\r\n",
    b"get / HTTP/1.1\r\nHost: h\r\n\r\n",
    b"GET / HTTP/9.9\r\nHost: h\r\n\r\n",
    b"GET index HTTP/1.1\r\nHost: h\r\n\r\n",
    b"GET  / HTTP/1.1\r\nHost: h\r\n\r\n",
    b"",
    b"\x00\x01\x02 binary junk",
])
def test_request_garbage(raw):
    with pytest.raises(ParseError):
        parser.parse_request(raw)


def test_request_no_blank_line():
    with pytest.raises(ParseError):
        parser.parse_request(b"GET / HTTP/1.1\r\nHost: h\r\n")


def test_header_too_large():
    big = b"X-Big: " + b"a" * (MAX_HEADER_SIZE + 10)
    with pytest.raises(ParseError):
        parser.parse_request(b"GET / HTTP/1.1\r\nHost: h\r\n" + big + b"\r\n\r\n")


def test_header_without_colon():
    with pytest.raises(ParseError):
        parser.parse_request(b"GET / HTTP/1.1\r\nHost: h\r\nBroken\r\n\r\n")


def test_header_names_normalized_and_values_stripped():
    req = parser.parse_request(b"GET / HTTP/1.1\r\nhOsT:   h  \r\nx-test: 1\r\n\r\n")
    assert req.headers == {"Host": "h", "X-Test": "1"}


@pytest.mark.parametrize("value", ["abc", "-1", "1.5", ""])
def test_invalid_content_length(value):
    raw = f"POST / HTTP/1.1\r\nHost: h\r\nContent-Length: {value}\r\n\r\n".encode()
    with pytest.raises(ParseError):
        parser.parse_request(raw)


def test_response_basic():
    raw = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nContent-Type: text/plain\r\n\r\nhi"
    resp = parser.parse_response(raw)
    assert (resp.status, resp.reason, resp.body) == (200, "OK", b"hi")
    assert resp.headers["Content-Type"] == "text/plain"


def test_response_reason_with_spaces():
    resp = parser.parse_response(b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n")
    assert (resp.status, resp.reason) == (404, "Not Found")


def test_response_without_reason():
    resp = parser.parse_response(b"HTTP/1.1 200\r\nContent-Length: 0\r\n\r\n")
    assert (resp.status, resp.reason) == (200, "OK")


def test_response_chunked():
    raw = (b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n"
           b"5\r\nhello\r\n6\r\n world\r\n0\r\n\r\n")
    assert parser.parse_response(raw).body == b"hello world"


def test_response_chunked_with_extension_and_hex_size():
    raw = (b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n"
           b"A;ext=1\r\n0123456789\r\n0\r\n\r\n")
    assert parser.parse_response(raw).body == b"0123456789"


@pytest.mark.parametrize("chunks", [
    b"5\r\nhel",
    b"zz\r\nhello\r\n0\r\n\r\n",
    b"5\r\nhelloXX0\r\n\r\n",
    b"5",
])
def test_response_chunked_broken(chunks):
    raw = b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n" + chunks
    with pytest.raises(ParseError):
        parser.parse_response(raw)


def test_response_without_length_reads_until_close():
    assert parser.parse_response(b"HTTP/1.1 200 OK\r\n\r\nrest of data").body == b"rest of data"


def test_response_204_has_no_body():
    assert parser.parse_response(b"HTTP/1.1 204 No Content\r\n\r\nignored").body == b""


@pytest.mark.parametrize("line", [
    b"HTTP/1.1 abc OK",
    b"HTTP/1.1 99 Low",
    b"HTTP/1.1 600 High",
    b"FTP/1.0 200 OK",
    b"HTTP/1.1",
])
def test_response_bad_status_line(line):
    with pytest.raises(ParseError):
        parser.parse_response(line + b"\r\n\r\n")


@pytest.mark.parametrize("value", ["\u00b2", "\uff18\uff10", "\u0663"])
def test_unicode_digits_in_content_length_are_parse_error(value):
    raw = f"POST / HTTP/1.1\r\nHost: h\r\nContent-Length: {value}\r\n\r\n".encode("utf-8")
    with pytest.raises(ParseError):
        parser.parse_request(raw)


def test_unicode_digits_in_status_are_parse_error():
    with pytest.raises(ParseError):
        parser.parse_response("HTTP/1.1 \u00b2\u00b2\u00b2 X\r\n\r\n".encode("utf-8"))
