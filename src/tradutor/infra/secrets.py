"""Backends da porta ``SecretStore`` (decisao D8, tarefa 8.3-8.5).

Precedencia de origem: variavel de ambiente > cofre do SO (keyring) >
arquivo cifrado (Fernet) > prompt na TUI. Os backends implementam a
porta ``SecretStore`` de ``tradutor.domain.secrets``: o nucleo do
dominio so enxerga a porta, nunca chaves.
"""

from __future__ import annotations

import base64
import contextlib
import json
import os
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import keyring
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from tradutor.domain.secrets import SecretStore

SERVICE_NAME = "tradutor-ebook"
SALT_SIZE = 16
PBKDF2_ITERATIONS = 600_000


class SecretStoreError(Exception):
    """Falha de segredo: senha incorreta, arquivo corrompido ou cofre indisponivel."""


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


class KeyringSecretStore:
    """Segredos no cofre do SO (Credential Manager, Keychain, libsecret)."""

    def __init__(
        self,
        service_name: str = SERVICE_NAME,
        backend: Any | None = None,
    ) -> None:
        self._service = service_name
        self._backend = backend if backend is not None else keyring

    def get(self, name: str) -> str | None:
        try:
            return self._backend.get_password(self._service, name)
        except keyring.errors.KeyringError:
            return None

    def set(self, name: str, value: str) -> None:
        self._backend.set_password(self._service, name, value)


class EncryptedFileSecretStore:
    """Segredos em arquivo cifrado com Fernet (senha-mestra por sessao).

    Formato do arquivo: salt (16 bytes) seguido de um token Fernet com
    o JSON dos pares nome -> chave. A chave Fernet e derivada da
    senha-mestra via PBKDF2-HMAC-SHA256; a senha vive apenas na
    memoria da sessao (instancia).
    """

    def __init__(self, path: str | Path, key: bytes, salt: bytes) -> None:
        self._path = Path(path)
        self._fernet = Fernet(key)
        self._salt = salt

    @classmethod
    def create(cls, path: str | Path, password: str) -> EncryptedFileSecretStore:
        """Cria um cofre novo (arquivo vazio) com senha-mestra."""
        salt = os.urandom(SALT_SIZE)
        store = cls(path, _derive_key(password, salt), salt)
        store._save({})
        return store

    @classmethod
    def open(cls, path: str | Path, password: str) -> EncryptedFileSecretStore:
        """Abre um cofre existente; senha errada levanta ``SecretStoreError``."""
        raw = Path(path).read_bytes()
        if len(raw) < SALT_SIZE:
            raise SecretStoreError(f"arquivo de segredos corrompido em {path}")
        salt, token = raw[:SALT_SIZE], raw[SALT_SIZE:]
        store = cls(path, _derive_key(password, salt), salt)
        try:
            store._fernet.decrypt(token)
        except InvalidToken as exc:
            raise SecretStoreError("senha-mestra incorreta") from exc
        return store

    def get(self, name: str) -> str | None:
        if not self._path.exists():
            return None
        return self._load().get(name)

    def set(self, name: str, value: str) -> None:
        secrets = self._load() if self._path.exists() else {}
        secrets[name] = value
        self._save(secrets)

    def _load(self) -> dict[str, str]:
        raw = self._path.read_bytes()
        if len(raw) < SALT_SIZE:
            raise SecretStoreError(f"arquivo de segredos corrompido em {self._path}")
        token = raw[SALT_SIZE:]
        try:
            payload = self._fernet.decrypt(token)
        except InvalidToken as exc:
            raise SecretStoreError("senha-mestra incorreta") from exc
        try:
            secrets = json.loads(payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise SecretStoreError(f"arquivo de segredos corrompido em {self._path}") from exc
        if not isinstance(secrets, dict):
            raise SecretStoreError(f"arquivo de segredos corrompido em {self._path}")
        return secrets

    def _save(self, secrets: dict[str, str]) -> None:
        payload = json.dumps(secrets, ensure_ascii=False).encode("utf-8")
        token = self._fernet.encrypt(payload)
        dest = self._path
        dest.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=f"{dest.name}.", suffix=".tmp", dir=dest.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(self._salt)
                handle.write(token)
            os.replace(tmp, dest)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp)
            raise


class EnvSecretStore:
    """Segredo por variavel de ambiente na convencao do provider."""

    def __init__(self, env: Mapping[str, str] | None = None) -> None:
        self._env = os.environ if env is None else env

    def get(self, name: str) -> str | None:
        return self._env.get(name)


class PromptSecretStore:
    """Ultimo recurso: pede a chave na interface (ex.: TUI)."""

    def __init__(self, ask: Callable[[str], str | None]) -> None:
        self._ask = ask

    def get(self, name: str) -> str | None:
        return self._ask(name)


class ChainedSecretStore:
    """Resolve a chave na ordem das fontes: a primeira com valor vence."""

    def __init__(self, stores: Sequence[SecretStore]) -> None:
        self._stores = tuple(stores)

    def get(self, name: str) -> str | None:
        for store in self._stores:
            value = store.get(name)
            if value:
                return value
        return None


def build_secret_chain(
    *,
    env: Mapping[str, str] | None = None,
    keyring_store: SecretStore | None = None,
    file_store: SecretStore | None = None,
    prompt: Callable[[str], str | None] | None = None,
) -> SecretStore:
    """Cadeia na precedencia: env > cofre > arquivo > prompt (tarefa 8.5)."""
    stores: list[SecretStore] = [EnvSecretStore(env)]
    if keyring_store is not None:
        stores.append(keyring_store)
    if file_store is not None:
        stores.append(file_store)
    if prompt is not None:
        stores.append(PromptSecretStore(prompt))
    return ChainedSecretStore(stores)
