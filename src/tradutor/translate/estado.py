"""Estado de traducao por livro (tarefas 6.1, 6.2 e 6.6).

O diretorio de trabalho de um livro contem ``estado.json`` (traducoes
concluidas por capitulo, uso acumulado e chave de compatibilidade) e
``glossario.json`` (secao 5). O estado e gravado com escrita atomica
(tmp + rename) a cada lote concluido, e a leitura e tolerante: arquivo
ausente, ilegivel ou parcialmente malformado nunca bloqueia a execucao
— entradas invalidas sao descartadas e os blocos correspondentes
re-traduzidos.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from tradutor.domain import TermPolicy, Usage

STATE_FILENAME = "estado.json"


def state_compat_key(
    *,
    book_hash: str,
    source_language: str,
    target_language: str,
    model: str,
    policy: TermPolicy,
    glossary_version: str,
) -> str:
    """Chave de compatibilidade do estado (tarefa 6.2).

    Hash do conteudo do livro, idiomas, modelo, politica de termos e
    versao do glossario: qualquer mudanca produz outra chave e invalida
    o estado salvo (recomeco limpo).
    """
    payload = "\x00".join(
        [
            book_hash,
            source_language,
            target_language,
            model,
            policy.value,
            glossary_version,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass(slots=True)
class WorkState:
    """Progresso persistido de um livro: traducoes, uso acumulado e chave."""

    key: str = ""
    translations: dict[str, dict[int, str]] = field(default_factory=dict)
    usage: Usage = field(default_factory=lambda: Usage(0, 0))


def save_estado(path: str | Path, state: WorkState) -> Path:
    """Grava o estado com escrita atomica (tmp + rename)."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        {
            "key": state.key,
            "translations": {
                chapter: {str(block_id): text for block_id, text in blocks.items()}
                for chapter, blocks in state.translations.items()
            },
            "usage": {
                "prompt_tokens": state.usage.prompt_tokens,
                "completion_tokens": state.usage.completion_tokens,
            },
        },
        ensure_ascii=False,
        indent=2,
    )
    fd, tmp = tempfile.mkstemp(prefix=f"{dest.name}.", suffix=".tmp", dir=dest.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.write("\n")
        os.replace(tmp, dest)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise
    return dest


def load_estado(path: str | Path) -> WorkState:
    """Le o estado com tolerancia total a corrupcao (tarefa 6.6).

    Arquivo ausente ou JSON ilegivel devolve estado vazio (re-traduz
    tudo). JSON valido com entradas malformadas descarta apenas as
    entradas invalidas — o restante e reaproveitado.
    """
    source = Path(path)
    if not source.exists():
        return WorkState()
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return WorkState()
    if not isinstance(data, dict):
        return WorkState()
    key = data.get("key") if isinstance(data.get("key"), str) else ""
    translations: dict[str, dict[int, str]] = {}
    raw_translations = data.get("translations")
    if isinstance(raw_translations, dict):
        for chapter, blocks in raw_translations.items():
            if not isinstance(chapter, str) or not isinstance(blocks, dict):
                continue
            valid: dict[int, str] = {}
            for block_id, text in blocks.items():
                if not isinstance(text, str):
                    continue
                try:
                    valid[int(block_id)] = text
                except (TypeError, ValueError):
                    continue
            if valid:
                translations[chapter] = valid
    usage = Usage(0, 0)
    raw_usage = data.get("usage")
    if isinstance(raw_usage, dict):
        usage = Usage(
            _as_nonneg_int(raw_usage.get("prompt_tokens")),
            _as_nonneg_int(raw_usage.get("completion_tokens")),
        )
    return WorkState(key=key, translations=translations, usage=usage)


def _as_nonneg_int(value: object) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return number if number > 0 else 0
