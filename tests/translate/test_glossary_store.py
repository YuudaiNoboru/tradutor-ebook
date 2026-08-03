"""Testes da persistencia do glossario (tarefas 5.1 e 5.4)."""

import json

import pytest

from tradutor.translate import GlossaryError, glossary_version, load_glossary, save_glossary


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "glossario.json"
    entries = [("queue", "fila"), ("cache", "cache")]
    save_glossary(path, entries)

    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == [
        {"termo": "queue", "traducao": "fila"},
        {"termo": "cache", "traducao": "cache"},
    ]
    assert load_glossary(path) == entries


def test_save_creates_parent_directories(tmp_path):
    path = tmp_path / "livro" / "estado" / "glossario.json"
    save_glossary(path, [("termo", "traducao")])
    assert path.exists()
    assert load_glossary(path) == [("termo", "traducao")]


def test_save_failure_cleans_tmp_and_reraises(tmp_path, monkeypatch):
    path = tmp_path / "glossario.json"

    import os as os_module

    real_replace = os_module.replace

    def boom(src, dst):
        raise OSError("disco cheio")

    monkeypatch.setattr(os_module, "replace", boom)
    with pytest.raises(OSError, match="disco cheio"):
        save_glossary(path, [("queue", "fila")])
    monkeypatch.setattr(os_module, "replace", real_replace)
    leftovers = [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == []
    assert not path.exists()


def test_load_missing_file_returns_empty(tmp_path):
    assert load_glossary(tmp_path / "nao-existe.json") == []


def test_load_invalid_json_raises(tmp_path):
    path = tmp_path / "glossario.json"
    path.write_text("{isto nao e json", encoding="utf-8")
    with pytest.raises(GlossaryError, match="glossario ilegivel"):
        load_glossary(path)


def test_load_non_list_raises(tmp_path):
    path = tmp_path / "glossario.json"
    path.write_text('{"termo": "x"}', encoding="utf-8")
    with pytest.raises(GlossaryError, match="esperada uma lista"):
        load_glossary(path)


def test_load_malformed_entry_raises(tmp_path):
    path = tmp_path / "glossario.json"
    path.write_text('[{"termo": 42}]', encoding="utf-8")
    with pytest.raises(GlossaryError, match="entrada invalida"):
        load_glossary(path)


def test_load_ignores_extra_keys(tmp_path):
    path = tmp_path / "glossario.json"
    path.write_text(
        '[{"termo": "queue", "traducao": "fila", "nota": "informal"}]', encoding="utf-8"
    )
    assert load_glossary(path) == [("queue", "fila")]


def test_manual_edit_changes_version(tmp_path):
    path = tmp_path / "glossario.json"
    save_glossary(path, [("queue", "fila")])
    before = glossary_version(load_glossary(path))

    path.write_text('[{"termo": "queue", "traducao": "fila (informal)"}]', encoding="utf-8")
    after = glossary_version(load_glossary(path))

    assert before != after


def test_version_stable_for_same_content():
    a = glossary_version([("queue", "fila"), ("cache", "cache")])
    b = glossary_version([("queue", "fila"), ("cache", "cache")])
    assert a == b


def test_version_changes_with_entries():
    assert glossary_version([("queue", "fila")]) != glossary_version([("queue", "fila 2")])
