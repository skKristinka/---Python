"""Модель HTTP-ответа."""
from dataclasses import dataclass, field
from typing import Dict

REASONS = {200: "OK", 400: "Bad Request", 404: "Not Found", 418: "I'm a teapot",
           500: "Internal Server Error"}


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
