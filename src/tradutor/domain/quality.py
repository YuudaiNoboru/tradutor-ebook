"""Qualidade da saida: deteccao de marcas de traducao automatica.

O texto de saida deve fluir como livro publicado: sem colchetes, notas,
rotulos de traducao ou outras marcas de IA (spec "Saida apenas
traduzida"). ``has_ai_mark`` e uma funcao pura usada nos testes (5.6) e
pela orquestracao para rejeitar respostas sujas.
"""

from __future__ import annotations

import re

_AI_MARK_PATTERNS = (
    re.compile(r"\[[^\]]*(?:tradu[çc][aã]o|original|nt\.)[^\]]*\]", re.IGNORECASE),
    re.compile(r"\(\s*n\.?\s*t\.?\s*\)", re.IGNORECASE),
    re.compile(r"nota\s+(?:do|da)\s+tradutor", re.IGNORECASE),
    re.compile(r"traduzid[oa]\s+(?:por|com)\s+(?:ia|intelig[eê]ncia\s+artificial)", re.IGNORECASE),
    re.compile(
        r"tradu[çc][aã]o\s+(?:automatica|automática|gerada|feita)\s+(?:por|com|via)", re.IGNORECASE
    ),
    re.compile(r"^\s*original:", re.IGNORECASE | re.MULTILINE),
)


def has_ai_mark(text: str) -> bool:
    """True se o texto contem padrao tipico de saida de IA/tradutor."""
    return any(pattern.search(text) for pattern in _AI_MARK_PATTERNS)
