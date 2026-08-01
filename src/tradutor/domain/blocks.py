"""Modelos do dominio: blocos de texto e capitulos.

Funcoes puras, sem I/O: a camada ``epub`` converte XHTML nestes
modelos e a camada ``translate`` os consome.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Block:
    """Unidade minima de texto traduzivel ou protegido."""

    id: int
    kind: str
    text: str
    protected: bool = False


@dataclass(slots=True)
class Chapter:
    """Capitulo: lista de blocos mais metadados."""

    blocks: list[Block] = field(default_factory=list)
    path: str = ""
    title: str = ""
