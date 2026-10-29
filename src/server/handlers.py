"""Обработчики маршрутов: /, /echo, /time, /headers, /status/<code>."""
import json
from datetime import datetime, timezone

from src.http.request import Request
from src.http.response import Response
from src.server.router import Router

_TEXT = "text/plain; charset=utf-8"
_HTML = "text/html; charset=utf-8"
_JSON = "application/json"
_HELLO_PAGE = (
    "<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\"><title>Hello</title></head>"
    "<body><h1>Hello</h1></body></html>\n"
)


def index(_req: Request) -> Response:
    """GET / — HTML-страница Hello."""
    return Response(status=200, headers={"Content-Type": _HTML},
                    body=_HELLO_PAGE.encode("utf-8"))


def echo(req: Request) -> Response:
    """POST /echo — вернуть тело, сохранив Content-Type."""
    content_type = req.headers.get("Content-Type", "application/octet-stream")
    return Response(status=200, headers={"Content-Type": content_type}, body=req.body)


def server_time(_req: Request) -> Response:
    """GET /time — текущее время в JSON."""
    now = datetime.now(timezone.utc)
    payload = {"time": now.isoformat(timespec="seconds"), "timestamp": now.timestamp()}
    return Response(status=200, headers={"Content-Type": _JSON},
                    body=json.dumps(payload).encode("utf-8"))


def headers(req: Request) -> Response:
    """GET /headers — все заголовки запроса в JSON."""
    return Response(status=200, headers={"Content-Type": _JSON},
                    body=json.dumps(req.headers, indent=2).encode("utf-8"))


def status(req: Request) -> Response:
    """GET /status/<code> — ответ с указанным кодом (200-599), иначе 400."""
    raw_code = req.path.split("?", 1)[0].rsplit("/", 1)[-1]
    if not raw_code.isdigit() or not 200 <= int(raw_code) <= 599:
        return Response(status=400, headers={"Content-Type": _TEXT},
                        body=b"400 Bad Request: status code must be 200-599")
    response = Response(status=int(raw_code))
    if response.status not in (204, 304):
        response.headers["Content-Type"] = _TEXT
        response.body = f"{response.status} {response.reason}".encode("utf-8")
    return response


def build_router() -> Router:
    """Создать Router со всеми стандартными маршрутами сервера."""
    router = Router()
    router.route("GET", "/", index)
    router.route("POST", "/echo", echo)
    router.route("GET", "/time", server_time)
    router.route("GET", "/headers", headers)
    router.route_prefix("GET", "/status/", status)
    return router
