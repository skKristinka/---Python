"""Unit-тесты форматирования и подсветки тела ответа."""
from src.gui.formatting import MAX_DISPLAY, decode_body, format_body, tokenize


def test_json_is_pretty_printed():
    text, kind = format_body(b'{"a":1,"b":[true,null]}', "application/json")
    assert kind == "json"
    assert text == '{\n  "a": 1,\n  "b": [\n    true,\n    null\n  ]\n}'


def test_json_detected_without_content_type():
    assert format_body(b'[1, 2]', "")[1] == "json"


def test_invalid_json_falls_back_to_text():
    assert format_body(b"{not json", "application/json") == ("{not json", "text")


def test_json_keeps_unicode():
    text, _ = format_body('{"имя": "мир"}'.encode("utf-8"), "application/json")
    assert "имя" in text and "мир" in text


def test_html_detected():
    assert format_body(b"<!DOCTYPE html><html></html>", "text/html")[1] == "html"
    assert format_body(b"<html><body>x</body></html>", "")[1] == "html"


def test_plain_text():
    assert format_body(b"hello", "text/plain") == ("hello", "text")


def test_charset_from_content_type():
    body = "привет".encode("cp1251")
    assert decode_body(body, "text/plain; charset=windows-1251") == "привет"


def test_unknown_charset_falls_back():
    assert decode_body(b"abc", "text/plain; charset=nonsense-xyz") == "abc"


def test_broken_bytes_do_not_crash():
    assert "\ufffd" in decode_body(b"\xff\xfe", "text/plain; charset=utf-8")


def test_huge_body_is_truncated():
    text, kind = format_body(b"a" * (MAX_DISPLAY + 10), "text/plain")
    assert kind == "text" and "обрезано" in text


def test_tokenize_json():
    text = '{"k": "v", "n": -1.5e3, "t": true}'
    tokens = [(text[s:e], tag) for s, e, tag in tokenize(text, "json")]
    assert tokens == [('"k"', "key"), ('"v"', "string"), ('"n"', "key"), ("-1.5e3", "number"),
                      ('"t"', "key"), ("true", "keyword")]


def test_tokenize_json_escaped_quote():
    text = '{"a": "x\\"y"}'
    assert ('"x\\"y"', "string") in [(text[s:e], tag) for s, e, tag in tokenize(text, "json")]


def test_tokenize_html():
    text = '<!-- c --><p class="a">hi</p>'
    tokens = [(text[s:e], tag) for s, e, tag in tokenize(text, "html")]
    assert tokens == [("<!-- c -->", "comment"), ('<p class="a">', "tag"), ("</p>", "tag")]


def test_tokenize_plain_text_has_no_tokens():
    assert tokenize("anything", "text") == []
