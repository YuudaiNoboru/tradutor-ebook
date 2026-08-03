"""Persistencia do glossario em JSON editavel a mao (tarefas 5.1 e 5.4).

O arquivo segue o formato ``[{"termo": ..., "traducao": ...}, ...]`` para
edicao manual simples. A versao do glossario deriva do conteudo (hash do
JSON canonico): qualquer edicao manual muda a versao e, por consequencia,
invalida o cache de traducoes (chave de compatibilidade da tarefa 6.2).
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
from collections.abc import Sequence
from pathlib import Path


class GlossaryError(ValueError):
    """Glossario ausente/invalido/ilegivel no diretorio de trabalho."""


def save_glossary(path: str | Path, entries: Sequence[tuple[str, str]]) -> Path:
    """Grava o glossario com escrita atomica (tmp + rename)."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        [{"termo": termo, "traducao": traducao} for termo, traducao in entries],
        ensure_ascii=False,
        indent=2,
    )
    fd, tmp = tempfile.mkstemp(prefix=f"{dest.name}.", suffix=".tmp", dir=dest.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
            f.write("\n")
        os.replace(tmp, dest)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise
    return dest


def load_glossary(path: str | Path) -> list[tuple[str, str]]:
    """Le o glossario; arquivo ausente devolve lista vazia.

    Conteudo invalido (JSON quebrado, formato errado) levanta
    ``GlossaryError`` com o caminho do arquivo na mensagem.
    """
    source = Path(path)
    if not source.exists():
        return []
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GlossaryError(f"glossario ilegivel em {source}: {exc}") from exc
    if not isinstance(data, list):
        raise GlossaryError(f"glossario invalido em {source}: esperada uma lista de entradas")
    entries: list[tuple[str, str]] = []
    for item in data:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("termo"), str)
            or not isinstance(item.get("traducao"), str)
        ):
            raise GlossaryError(f"entrada invalida no glossario {source}: {item!r}")
        entries.append((item["termo"], item["traducao"]))
    return entries


def glossary_version(entries: Sequence[tuple[str, str]]) -> str:
    """Hash do conteudo do glossario: edicoes manuais mudam a versao."""
    canonical = json.dumps(
        sorted((termo, traducao) for termo, traducao in entries),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()[:16]
