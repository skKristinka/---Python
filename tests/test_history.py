"""Unit-тесты HistoryStore."""
import json
import os
import tempfile

from src.gui.history import MAX_RECORDS, HistoryStore


def make_store(directory):
    return HistoryStore(os.path.join(directory, "history.json"))


def test_missing_file_is_empty_history():
    with tempfile.TemporaryDirectory() as directory:
        assert make_store(directory).load() == []


def test_add_and_load_roundtrip_with_unicode():
    with tempfile.TemporaryDirectory() as directory:
        store = make_store(directory)
        store.add({"url": "http://x/", "note": "привет"})
        store.add({"url": "http://y/"})
        assert store.load() == [{"url": "http://x/", "note": "привет"}, {"url": "http://y/"}]


def test_broken_file_is_treated_as_empty_and_overwritten():
    with tempfile.TemporaryDirectory() as directory:
        store = make_store(directory)
        with open(store.path, "w", encoding="utf-8") as file:
            file.write("{not json")
        assert store.load() == []
        store.add({"a": 1})
        assert store.load() == [{"a": 1}]


def test_not_a_list_is_ignored():
    with tempfile.TemporaryDirectory() as directory:
        store = make_store(directory)
        with open(store.path, "w", encoding="utf-8") as file:
            json.dump({"a": 1}, file)
        assert store.load() == []


def test_history_is_capped():
    with tempfile.TemporaryDirectory() as directory:
        store = make_store(directory)
        with open(store.path, "w", encoding="utf-8") as file:
            json.dump([{"n": i} for i in range(MAX_RECORDS)], file)
        store.add({"n": "last"})
        records = store.load()
        assert len(records) == MAX_RECORDS and records[-1] == {"n": "last"}
        assert records[0] == {"n": 1}
