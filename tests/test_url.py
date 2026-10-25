"""Unit-тесты разбора URL."""
import pytest

from src.http.exceptions import ParseError
from src.http.url import Url


def test_full_url():
    url = Url.parse("http://host:8080/path?q=1")
    assert (url.host, url.port, url.path, url.query) == ("host", 8080, "/path", "q=1")


def test_default_port_http():
    assert Url.parse("http://host/path").port == 80


def test_default_port_https():
    assert Url.parse("https://host/").port == 443


def test_default_path():
    assert Url.parse("http://host").path == "/"


def test_target_with_query():
    assert Url.parse("http://h/p?a=b").target == "/p?a=b"


@pytest.mark.parametrize("bad", [
    "garbage", "", "ftp://host/", "http://", "http://h:99999/", "http://h:0/",
])
def test_invalid(bad):
    with pytest.raises(ParseError):
        Url.parse(bad)


def test_query_without_path():
    url = Url.parse("http://host?x=1")
    assert (url.path, url.query) == ("/", "x=1")


def test_fragment_is_ignored():
    assert Url.parse("http://host/p#frag").path == "/p"


def test_scheme_case_insensitive():
    url = Url.parse("HTTP://Host/")
    assert (url.scheme, url.port) == ("http", 80)


def test_surrounding_spaces_are_stripped():
    assert Url.parse("  http://host/  ").host == "host"
