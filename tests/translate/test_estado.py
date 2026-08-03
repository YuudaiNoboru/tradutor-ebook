"""Testes do estado de traducao por livro (tarefas 6.1, 6.2 e 6.6)."""

import json
import os

import pytest

from tradutor.domain import TermPolicy, Usage
from tradutor.translate import WorkState, load_estado, save_estado, state_compat_key

KEY = state_compat_key(
    book_hash="hash-livro",
    source_language="auto",
    target_language="pt-BR",
    model="deepseek-chat",
    policy=TermPolicy.HIBRIDO,
    glossary_version="abc123",
)


def sample_state() -> WorkState:
    return WorkState(
        key=KEY,
        translations={"cap1.xhtml": {0: "Ola mundo", 2: "Segundo bloco"}},
        usage=Usage(100, 40),
    )


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "estado.json"
    save_estado(path, sample_state())

    loaded = load_estado(path)
    assert loaded.key == KEY
    assert loaded.translations == {"cap1.xhtml": {0: "Ola mundo", 2: "Segundo bloco"}}
    assert loaded.usage == Usage(100, 40)


def test_save_creates_parent_directories(tmp_path):
    path = tmp_path / "livro" / "estado" / "estado.json"
    save_estado(path, sample_state())
    assert path.exists()
    assert load_estado(path).key == KEY


def test_save_failure_cleans_tmp_and_reraises(tmp_path, monkeypatch):
    path = tmp_path / "estado.json"

    def boom(src, dst):
        raise OSError("disco cheio")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError, match="disco cheio"):
        save_estado(path, sample_state())
    leftovers = [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == []
    assert not path.exists()


def test_load_missing_file_returns_empty_state(tmp_path):
    state = load_estado(tmp_path / "estado.json")
    assert state.key == ""
    assert state.translations == {}
    assert state.usage == Usage(0, 0)


def test_load_invalid_json_returns_empty_state(tmp_path):
    path = tmp_path / "estado.json"
    path.write_text("{isto nao e json", encoding="utf-8")
    state = load_estado(path)
    assert state.key == ""
    assert state.translations == {}
    assert state.usage == Usage(0, 0)


def test_load_non_dict_returns_empty_state(tmp_path):
    path = tmp_path / "estado.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    assert load_estado(path).translations == {}


def test_load_drops_malformed_entries_and_keeps_valid(tmp_path):
    path = tmp_path / "estado.json"
    path.write_text(
        json.dumps(
            {
                "key": KEY,
                "translations": {
                    "cap1.xhtml": {"0": "ok", "quebra": "id nao numerico", "3": 42},
                    "cap2.xhtml": "nao e dict de blocos",
                },
                "usage": {"prompt_tokens": "dez", "completion_tokens": 5},
            }
        ),
        encoding="utf-8",
    )
    state = load_estado(path)
    assert state.translations == {"cap1.xhtml": {0: "ok"}}
    assert state.usage == Usage(0, 5)
    assert state.key == KEY


def test_load_tolerates_missing_sections(tmp_path):
    path = tmp_path / "estado.json"
    path.write_text(
        json.dumps(
            {
                "key": KEY,
                "translations": {"cap1.xhtml": {"0": "ok"}, "cap2.xhtml": {"0": 42}},
                "usage": "quebrado",
            }
        ),
        encoding="utf-8",
    )
    state = load_estado(path)
    assert state.translations == {"cap1.xhtml": {0: "ok"}}
    assert state.usage == Usage(0, 0)

    path.write_text(
        json.dumps({"key": KEY, "usage": {"prompt_tokens": 1, "completion_tokens": 1}}),
        encoding="utf-8",
    )
    state = load_estado(path)
    assert state.translations == {}
    assert state.usage == Usage(1, 1)


def test_compat_key_stable_for_same_inputs():
    kwargs = dict(
        book_hash="h",
        source_language="auto",
        target_language="pt-BR",
        model="m",
        policy=TermPolicy.HIBRIDO,
        glossary_version="v",
    )
    assert state_compat_key(**kwargs) == state_compat_key(**kwargs)


def test_compat_key_changes_with_any_input():
    base = dict(
        book_hash="h",
        source_language="auto",
        target_language="pt-BR",
        model="m",
        policy=TermPolicy.HIBRIDO,
        glossary_version="v",
    )
    key = state_compat_key(**base)
    for field in ("book_hash", "source_language", "target_language", "model", "glossary_version"):
        altered = dict(base, **{field: "outro"})
        assert state_compat_key(**altered) != key
    assert state_compat_key(**dict(base, policy=TermPolicy.MANTER)) != key
