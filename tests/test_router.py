"""Unit-тесты Router и обработчиков."""
import json

import pytest

from src.http.request import Request
from src.server.handlers import build_router
from src.server.router import Router
from src.http.response import Response

router = build_router()


def get(path):
    return router.dispatch(Request("GET", path))


def test_index_is_html_hello():
    response = get("/")
    assert response.status == 200
    assert b"Hello" in response.body
    assert response.headers["Content-Type"].startswith("text/html")


def test_echo_keeps_body_and_content_type():
    request = Request("POST", "/echo", headers={"Content-Type": "text/plain"}, body=b"abc")
    response = router.dispatch(request)
    assert (response.body, response.headers["Content-Type"]) == (b"abc", "text/plain")


def test_echo_without_content_type():
    response = router.dispatch(Request("POST", "/echo", body=b"\x00\x01"))
    assert response.headers["Content-Type"] == "application/octet-stream"
    assert response.body == b"\x00\x01"


def test_time_is_json():
    data = json.loads(get("/time").body)
    assert "time" in data and "timestamp" in data


def test_headers_returns_request_headers_as_json():
    request = Request("GET", "/headers", headers={"Host": "h", "X-Test": "1"})
    data = json.loads(router.dispatch(request).body)
    assert data == {"Host": "h", "X-Test": "1"}


def test_query_is_ignored_when_routing():
    assert get("/time?x=1").status == 200


def test_status_code():
    response = get("/status/418")
    assert (response.status, response.reason) == (418, "I'm a teapot")
    assert b"418" in response.body


@pytest.mark.parametrize("code", [204, 304])
def test_status_without_body(code):
    assert get(f"/status/{code}").body == b""


@pytest.mark.parametrize("path", ["/status/abc", "/status/", "/status/99", "/status/600",
                                  "/status/404/extra"])
def test_status_invalid_code(path):
    assert get(path).status == 400


@pytest.mark.parametrize("method, path", [
    ("GET", "/nonexistent"), ("POST", "/"), ("GET", "/echo"), ("DELETE", "/time"),
])
def test_unknown_route_is_404(method, path):
    response = router.dispatch(Request(method, path))
    assert (response.status, response.body) == (404, b"404 Not Found")


def test_custom_route_and_handle_interface():
    custom = Router()
    custom.route("get", "/x", lambda req: Response(status=201))
    assert custom.handle(Request("GET", "/x")).status == 201
