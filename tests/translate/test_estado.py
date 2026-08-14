"""Testes do estado de traducao por livro (tarefas 6.1, 6.2 e 6.6)."""

import json
import os

import pytest

from tradutor.domain import TermPolicy, Usage
from tradutor.translate import WorkState, load_estado, save_estado, state_compat_key
from tradutor.translate.estado import safe_replace

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


def test_compat_key_default_llm_deepseek_keeps_legacy_formula():
    legacy = state_compat_key(
        book_hash="h",
        source_language="auto",
        target_language="pt-BR",
        model="deepseek-chat",
        policy=TermPolicy.HIBRIDO,
        glossary_version="v",
    )
    current = state_compat_key(
        book_hash="h",
        source_language="auto",
        target_language="pt-BR",
        model="deepseek-chat",
        policy=TermPolicy.HIBRIDO,
        glossary_version="v",
        family="llm",
        provider_id="deepseek",
        transport_variant="openai-chat",
    )
    assert current == legacy


def test_compat_key_isolates_machine_translation_family():
    base = dict(
        book_hash="h",
        source_language="auto",
        target_language="pt-BR",
        model="",
        policy=TermPolicy.HIBRIDO,
        glossary_version="",
    )
    llm = state_compat_key(**base, family="llm", provider_id="deepseek")
    mt = state_compat_key(
        **base,
        family="machine_translation",
        provider_id="google-web",
        transport_variant="html-v1/text-v1",
    )
    assert llm != mt


def test_compat_key_changes_with_machine_variant():
    base = dict(
        book_hash="h",
        source_language="auto",
        target_language="pt-BR",
        family="machine_translation",
        provider_id="google-web",
    )
    key = state_compat_key(**base, transport_variant="html-v1/text-v1")
    assert state_compat_key(**base, transport_variant="html-v2/text-v1") != key


def test_compat_key_other_llm_provider_does_not_reuse_legacy_state():
    legacy = state_compat_key(
        book_hash="h",
        source_language="auto",
        target_language="pt-BR",
        model="deepseek-chat",
        policy=TermPolicy.HIBRIDO,
        glossary_version="",
    )
    other = state_compat_key(
        book_hash="h",
        source_language="auto",
        target_language="pt-BR",
        model="deepseek-chat",
        policy=TermPolicy.HIBRIDO,
        glossary_version="",
        family="llm",
        provider_id="openrouter",
        transport_variant="openai-chat",
    )
    assert other != legacy


def test_load_unmetered_usage_with_null_tokens_is_valid(tmp_path):
    path = tmp_path / "estado.json"
    path.write_text(
        json.dumps(
            {
                "key": KEY,
                "translations": {"cap1.xhtml": {"0": "oi"}},
                "usage": {
                    "prompt_tokens": None,
                    "completion_tokens": None,
                    "characters": 120,
                    "blocks": 3,
                },
            }
        ),
        encoding="utf-8",
    )
    state = load_estado(path)

    assert state.usage.total_tokens is None
    assert state.usage.characters == 120
    assert state.usage.blocks == 3
    assert state.translations == {"cap1.xhtml": {0: "oi"}}


def test_load_legacy_usage_without_new_fields(tmp_path):
    path = tmp_path / "estado.json"
    path.write_text(
        json.dumps(
            {
                "key": KEY,
                "translations": {"cap1.xhtml": {"0": "oi"}},
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }
        ),
        encoding="utf-8",
    )
    state = load_estado(path)

    assert state.usage == Usage(10, 5)


def test_safe_replace_retries_on_permission_error_and_succeeds(tmp_path, monkeypatch):
    path = tmp_path / "estado.json"
    real_replace = os.replace
    attempts = 0

    def flaky_replace(src, dst):
        nonlocal attempts
        attempts += 1
        if attempts <= 2:
            raise PermissionError(13, "Access is denied")
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", flaky_replace)
    save_estado(path, sample_state())

    assert attempts == 3
    assert path.exists()
    assert load_estado(path).key == KEY


def test_safe_replace_retries_on_winerror_32_and_succeeds(tmp_path, monkeypatch):
    path = tmp_path / "estado.json"
    real_replace = os.replace
    attempts = 0

    def flaky_replace(src, dst):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            err = OSError(
                "The process cannot access the file because it is being used by another process"
            )
            err.winerror = 32
            raise err
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", flaky_replace)
    save_estado(path, sample_state())

    assert attempts == 2
    assert path.exists()
    assert load_estado(path).key == KEY


def test_safe_replace_raises_permission_error_after_max_attempts(tmp_path, monkeypatch):
    path = tmp_path / "estado.json"
    attempts = 0

    def always_locked(src, dst):
        nonlocal attempts
        attempts += 1
        raise PermissionError(13, "Access is denied")

    monkeypatch.setattr(os, "replace", always_locked)
    with pytest.raises(PermissionError, match="Access is denied"):
        save_estado(path, sample_state())

    assert attempts == 5
    leftovers = [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == []
    assert not path.exists()


def test_safe_replace_raises_immediately_on_unrelated_oserror(tmp_path, monkeypatch):
    src = tmp_path / "src.tmp"
    dst = tmp_path / "dst.txt"
    src.write_text("hello", encoding="utf-8")
    attempts = 0

    def disk_error(s, d):
        nonlocal attempts
        attempts += 1
        raise OSError("No space left on device")

    monkeypatch.setattr(os, "replace", disk_error)
    with pytest.raises(OSError, match="No space left on device"):
        safe_replace(src, dst)

    assert attempts == 1
