"""Testes dos backends da porta ``SecretStore`` (tarefas 8.3-8.5).

Cobrem: cofre do SO com keyring fake (incluindo cofre indisponivel que
degrade para a proxima fonte), arquivo cifrado Fernet com senha-mestra
por sessao (senha errada e arquivo corrompido), override por variavel
de ambiente e a precedencia env > cofre > arquivo > prompt.
"""

from __future__ import annotations

import keyring
import pytest

from tradutor.infra import secrets as secrets_module
from tradutor.infra.secrets import (
    ChainedSecretStore,
    EncryptedFileSecretStore,
    EnvSecretStore,
    KeyringSecretStore,
    SecretStoreError,
    build_secret_chain,
)


class FakeKeyringBackend:
    """Backend keyring em memoria, com modo "sem cofre" para testes."""

    def __init__(self, broken: bool = False) -> None:
        self._passwords: dict[tuple[str, str], str] = {}
        self.broken = broken

    def get_password(self, service: str, username: str) -> str | None:
        if self.broken:
            raise keyring.errors.NoKeyringError("sem cofre disponivel")
        return self._passwords.get((service, username))

    def set_password(self, service: str, username: str, value: str) -> None:
        if self.broken:
            raise keyring.errors.NoKeyringError("sem cofre disponivel")
        self._passwords[(service, username)] = value


@pytest.fixture(autouse=True)
def fast_pbkdf2(monkeypatch):
    monkeypatch.setattr(secrets_module, "PBKDF2_ITERATIONS", 1_000)


def test_keyring_roundtrip():
    backend = FakeKeyringBackend()
    store = KeyringSecretStore(backend=backend)

    store.set("DEEPSEEK_API_KEY", "sk-segredo")
    assert store.get("DEEPSEEK_API_KEY") == "sk-segredo"
    assert store.get("OUTRA_CHAVE") is None


def test_keyring_unavailable_returns_none():
    store = KeyringSecretStore(backend=FakeKeyringBackend(broken=True))

    assert store.get("DEEPSEEK_API_KEY") is None


def test_encrypted_file_roundtrip(tmp_path):
    path = tmp_path / "segredos.enc"
    store = EncryptedFileSecretStore.create(path, "senha-mestra")

    store.set("DEEPSEEK_API_KEY", "sk-um")
    store.set("OPENAI_API_KEY", "sk-dois")

    reopened = EncryptedFileSecretStore.open(path, "senha-mestra")
    assert reopened.get("DEEPSEEK_API_KEY") == "sk-um"
    assert reopened.get("OPENAI_API_KEY") == "sk-dois"
    assert reopened.get("AUSENTE") is None


def test_encrypted_file_get_sem_arquivo_retorna_none(tmp_path):
    path = tmp_path / "segredos.enc"
    store = EncryptedFileSecretStore.create(path, "senha")
    path.unlink()

    assert store.get("QUALQUER") is None


def test_encrypted_file_get_truncado_depois_de_criar(tmp_path):
    path = tmp_path / "segredos.enc"
    store = EncryptedFileSecretStore.create(path, "senha")
    store.set("K", "v")
    path.write_bytes(b"curto")

    with pytest.raises(SecretStoreError, match="corrompido"):
        store.get("K")


def test_encrypted_file_load_com_token_de_outro_cofre(tmp_path):
    path = tmp_path / "segredos.enc"
    store = EncryptedFileSecretStore.create(path, "senha")
    EncryptedFileSecretStore.create(path, "outra-senha").set("K", "v")

    with pytest.raises(SecretStoreError, match="senha-mestra"):
        store.get("K")


def test_encrypted_file_load_com_payload_invalido(tmp_path):
    path = tmp_path / "segredos.enc"
    store = EncryptedFileSecretStore.create(path, "senha")
    path.write_bytes(store._salt + store._fernet.encrypt(b"isto nao e json"))

    with pytest.raises(SecretStoreError, match="corrompido"):
        store.get("K")


def test_encrypted_file_load_com_payload_nao_dict(tmp_path):
    import json as json_module

    path = tmp_path / "segredos.enc"
    store = EncryptedFileSecretStore.create(path, "senha")
    payload = json_module.dumps(["nao-e-dict"]).encode("utf-8")
    path.write_bytes(store._salt + store._fernet.encrypt(payload))

    with pytest.raises(SecretStoreError, match="corrompido"):
        store.get("K")


def test_encrypted_file_save_falha_remove_tmp(tmp_path, monkeypatch):
    path = tmp_path / "segredos.enc"
    store = EncryptedFileSecretStore.create(path, "senha")

    def boom(*args, **kwargs):
        raise OSError("disco cheio")

    monkeypatch.setattr(secrets_module.os, "replace", boom)

    with pytest.raises(OSError, match="disco cheio"):
        store.set("K", "v")
    assert list(tmp_path.glob("segredos.enc.*.tmp")) == []


def test_encrypted_file_senha_errada(tmp_path):
    path = tmp_path / "segredos.enc"
    EncryptedFileSecretStore.create(path, "senha-certa").set("K", "v")

    with pytest.raises(SecretStoreError, match="senha-mestra"):
        EncryptedFileSecretStore.open(path, "senha-errada")


def test_encrypted_file_corrompido(tmp_path):
    path = tmp_path / "segredos.enc"
    store = EncryptedFileSecretStore.create(path, "senha")
    store.set("K", "v")
    path.write_bytes(b"lixo-curto")

    with pytest.raises(SecretStoreError, match="corrompido"):
        EncryptedFileSecretStore.open(path, "senha")


def test_env_override():
    env = {"DEEPSEEK_API_KEY": "sk-do-ambiente"}
    store = EnvSecretStore(env)

    assert store.get("DEEPSEEK_API_KEY") == "sk-do-ambiente"
    assert store.get("OUTRA") is None


def test_precedencia_env_sobre_cofre(tmp_path):
    chain = build_secret_chain(
        env={"DEEPSEEK_API_KEY": "sk-env"},
        keyring_store=KeyringSecretStore(backend=_with_key("sk-cofre")),
        file_store=EncryptedFileSecretStore.create(tmp_path / "s.enc", "x"),
        prompt=lambda name: "sk-prompt",
    )

    assert chain.get("DEEPSEEK_API_KEY") == "sk-env"


def test_precedencia_cofre_sobre_arquivo(tmp_path):
    file_store = EncryptedFileSecretStore.create(tmp_path / "s.enc", "senha")
    file_store.set("DEEPSEEK_API_KEY", "sk-arquivo")

    chain = build_secret_chain(
        env={},
        keyring_store=KeyringSecretStore(backend=_with_key("sk-cofre")),
        file_store=file_store,
        prompt=lambda name: "sk-prompt",
    )

    assert chain.get("DEEPSEEK_API_KEY") == "sk-cofre"


def test_precedencia_arquivo_sobre_prompt(tmp_path):
    file_store = EncryptedFileSecretStore.create(tmp_path / "s.enc", "senha")
    file_store.set("DEEPSEEK_API_KEY", "sk-arquivo")

    chain = build_secret_chain(
        env={},
        keyring_store=KeyringSecretStore(backend=_with_key(None)),
        file_store=file_store,
        prompt=lambda name: "sk-prompt",
    )

    assert chain.get("DEEPSEEK_API_KEY") == "sk-arquivo"


def test_precedencia_prompt_como_ultimo_recurso():
    chain = build_secret_chain(
        env={},
        keyring_store=KeyringSecretStore(backend=_with_key(None)),
        prompt=lambda name: f"sk-por-prompt-{name}",
    )

    assert chain.get("DEEPSEEK_API_KEY") == "sk-por-prompt-DEEPSEEK_API_KEY"


def test_chain_sem_nenhuma_fonte_retorna_none():
    chain = ChainedSecretStore([KeyringSecretStore(backend=_with_key(None))])

    assert chain.get("DEEPSEEK_API_KEY") is None


def test_build_chain_sem_cofre_ou_arquivo():
    chain = build_secret_chain(
        env={"DEEPSEEK_API_KEY": "sk-env"},
    )

    assert chain.get("DEEPSEEK_API_KEY") == "sk-env"
    assert chain.get("AUSENTE") is None


def test_cofre_indisponivel_degrade_para_arquivo(tmp_path):
    file_store = EncryptedFileSecretStore.create(tmp_path / "s.enc", "senha")
    file_store.set("DEEPSEEK_API_KEY", "sk-arquivo")

    chain = build_secret_chain(
        env={},
        keyring_store=KeyringSecretStore(backend=FakeKeyringBackend(broken=True)),
        file_store=file_store,
        prompt=lambda name: "sk-prompt",
    )

    assert chain.get("DEEPSEEK_API_KEY") == "sk-arquivo"


def _with_key(key: str | None) -> FakeKeyringBackend:
    backend = FakeKeyringBackend()
    if key is not None:
        backend.set_password("tradutor-ebook", "DEEPSEEK_API_KEY", key)
    return backend
