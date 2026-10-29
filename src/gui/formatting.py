"""Форматирование и подсветка тела ответа (без Tkinter)."""
import json
import re
from typing import List, Tuple

MAX_DISPLAY = 1_000_000
_CHARSET_RE = re.compile(r"charset=([\w\-]+)", re.IGNORECASE)
_JSON_RE = re.compile(
    r'(?P<key>"(?:\\.|[^"\\])*"(?=\s*:))'
    r'|(?P<string>"(?:\\.|[^"\\])*")'
    r"|(?P<number>-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"
    r"|(?P<keyword>\b(?:true|false|null)\b)"
)
_HTML_RE = re.compile(r"(?P<comment><!--.*?-->)|(?P<tag></?[A-Za-z!][^>]*>)", re.DOTALL)


def decode_body(body: bytes, content_type: str) -> str:
    """Декодировать тело по charset из Content-Type (по умолчанию utf-8)."""
    match = _CHARSET_RE.search(content_type)
    charset = match.group(1) if match else "utf-8"
    try:
        return body.decode(charset, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def format_body(body: bytes, content_type: str) -> Tuple[str, str]:
    """Вернуть (текст для показа, тип подсветки: json / html / text)."""
    text = decode_body(body, content_type)
    if len(text) > MAX_DISPLAY:
        return text[:MAX_DISPLAY] + "\n… (тело обрезано для показа)", "text"
    lowered = content_type.lower()
    stripped = text.lstrip()
    if "json" in lowered or stripped.startswith(("{", "[")):
        try:
            return json.dumps(json.loads(text), ensure_ascii=False, indent=2), "json"
        except ValueError:
            pass
    if "html" in lowered or stripped.lower().startswith(("<!doctype html", "<html")):
        return text, "html"
    return text, "text"


def tokenize(text: str, kind: str) -> List[Tuple[int, int, str]]:
    """Найти фрагменты для подсветки: (начало, конец, имя) по смещениям в тексте."""
    pattern = {"json": _JSON_RE, "html": _HTML_RE}.get(kind)
    if pattern is None:
        return []
    return [(m.start(), m.end(), m.lastgroup) for m in pattern.finditer(text) if m.lastgroup]
