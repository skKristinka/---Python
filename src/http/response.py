"""Модель HTTP-ответа."""
from dataclasses import dataclass, field
from typing import Dict

REASONS = {
    100: "Continue", 101: "Switching Protocols",
    200: "OK", 201: "Created", 202: "Accepted", 204: "No Content",
    301: "Moved Permanently", 302: "Found", 303: "See Other", 304: "Not Modified",
    307: "Temporary Redirect", 308: "Permanent Redirect",
    400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found",
    405: "Method Not Allowed", 408: "Request Timeout", 413: "Payload Too Large",
    418: "I'm a teapot", 429: "Too Many Requests",
    500: "Internal Server Error", 501: "Not Implemented", 502: "Bad Gateway",
    503: "Service Unavailable", 504: "Gateway Timeout",
}


@dataclass
class Response:
    """HTTP-ответ."""

    status: int = 200
    reason: str = ""
    version: str = "HTTP/1.1"
    headers: Dict[str, str] = field(default_factory=dict)
    body: bytes = b""

    def __post_init__(self) -> None:
        """Подставить стандартную причину, если не задана."""
        if not self.reason:
            self.reason = REASONS.get(self.status, "Unknown")
