"""Проверка пользовательского ввода (без Tkinter, чтобы легко тестировать)."""
import re
from typing import Dict, Iterable, Tuple

from src.http.exceptions import ParseError
from src.http.parser import is_ascii_digits
from src.http.url import Url

_TOKEN_RE = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")


class ValidationError(ValueError):
    """Ошибка ввода; текст можно показывать пользователю как есть."""


def normalize_url(raw: str) -> str:
    """Проверить URL; если схема не указана, добавить http://."""
    text = raw.strip()
    if not text:
        raise ValidationError("Введите URL, например http://localhost:8080/")
    if "://" not in text:
        text = "http://" + text
    try:
        Url.parse(text)
    except ParseError as exc:
        raise ValidationError(str(exc)) from exc
    return text


def validate_port(raw: str) -> int:
    """Порт: целое число 1-65535."""
    text = raw.strip()
    if not is_ascii_digits(text) or not 1 <= int(text) <= 65535:
        raise ValidationError("Порт должен быть числом от 1 до 65535")
    return int(text)


def validate_timeout(raw: str) -> float:
    """Таймаут в секундах: больше 0 и не больше 300."""
    try:
        value = float(raw.strip().replace(",", "."))
    except ValueError as exc:
        raise ValidationError("Таймаут должен быть числом (секунды)") from exc
    if not 0 < value <= 300:
        raise ValidationError("Таймаут должен быть больше 0 и не больше 300 секунд")
    return value


def validate_redirects(raw: str) -> int:
    """Максимум редиректов: целое число 0-10."""
    text = raw.strip()
    if not is_ascii_digits(text) or int(text) > 10:
        raise ValidationError("Число редиректов должно быть целым от 0 до 10")
    return int(text)


def validate_headers(rows: Iterable[Tuple[str, str]]) -> Dict[str, str]:
    """Превратить строки таблицы в словарь; пустые строки пропускаются."""
    headers: Dict[str, str] = {}
    for number, (name, value) in enumerate(rows, start=1):
        name, value = name.strip(), value.strip()
        if not name and not value:
            continue
        if not _TOKEN_RE.match(name):
            raise ValidationError(f"Строка {number}: недопустимое имя заголовка {name!r}")
        if "\r" in value or "\n" in value:
            raise ValidationError(f"Строка {number}: в значении нельзя переводить строку")
        headers[name] = value
    return headers
