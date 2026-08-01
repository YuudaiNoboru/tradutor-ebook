"""Mecanica de placeholders ``{{N}}`` para conteudo protegido.

Conteudo protegido e extraido do texto e substituido por placeholders
``{{N}}`` antes da traducao; depois a traducao e restaurada colocando
os conteudos originais de volta. Assim a LLM nunca altera codigo,
SVG, MathML, script ou style — e um verificador de fidelidade rejeita
respostas que corrompam os placeholders.

A restauracao e uma bijecao mesmo quando o texto original ja continha
sequencias com formato de placeholder (ex.: ``{{5}}`` em texto sobre
templates): durante a extracao essas sequencias sao ``escapadas`` com
marcadores internos, restauradas antes da substituicao final.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

_ESCAPE = "\x00"
_PLACEHOLDER_RE = re.compile(
    "(?<!" + re.escape(_ESCAPE) + r")\{\{(\d+)\}\}(?!" + re.escape(_ESCAPE) + ")"
)
_LITERAL_RE = re.compile(r"\{\{(\d+)\}\}")


@dataclass(frozen=True, slots=True)
class ExtractedText:
    """Resultado da extracao: template com placeholders + conteudo salvo."""

    template: str
    protected: Mapping[int, str]


def _marker(number: int) -> str:
    return "{{" + str(number) + "}}"


def _escape_literals(text: str) -> str:
    return _LITERAL_RE.sub(rf"{_ESCAPE}\g<0>{_ESCAPE}", text)


def _best_key(keys: Sequence[str], text: str, pos: int) -> str | None:
    best: str | None = None
    for key in keys:
        if text.startswith(key, pos) and (best is None or len(key) > len(best)):
            best = key
    return best


def extract_protected(text: str, protected: Sequence[str]) -> ExtractedText:
    """Substitui cada conteudo protegido por um placeholder ``{{N}}``.

    Placeholders sao numerados na ordem de primeira ocorrencia de cada
    conteudo no texto. Conteudos vazios, duplicados ou ausentes do texto
    sao ignorados.
    """
    escaped = _escape_literals(text)
    keys = list(dict.fromkeys(_escape_literals(s) for s in protected if s))
    keys = [key for key in keys if key in escaped]
    marker_by_key: dict[str, int] = {}
    mapping: dict[int, str] = {}
    template: list[str] = []
    i = 0
    while i < len(escaped):
        best = _best_key(keys, escaped, i)
        if best is not None:
            if best not in marker_by_key:
                marker_by_key[best] = len(marker_by_key)
                mapping[marker_by_key[best]] = best
            template.append(_marker(marker_by_key[best]))
            i += len(best)
        elif escaped[i] == _ESCAPE:
            end = escaped.find(_ESCAPE, i + 1)
            span_end = len(escaped) if end == -1 else end + 1
            template.append(escaped[i:span_end])
            i = span_end
        else:
            template.append(escaped[i])
            i += 1
    return ExtractedText(template="".join(template), protected=mapping)


def restore_protected(template: str, protected: Mapping[int, str]) -> str:
    """Devolve os conteudos protegidos aos seus placeholders."""

    def _restore(match: re.Match[str]) -> str:
        number = int(match.group(1))
        try:
            return protected[number]
        except KeyError:
            raise ValueError(
                f"placeholder {_marker(number)} sem conteudo protegido correspondente"
            ) from None

    restored = _PLACEHOLDER_RE.sub(_restore, template)
    return restored.replace(_ESCAPE, "")


def placeholder_sequence(text: str) -> tuple[int, ...]:
    """Sequencia de placeholders (em ordem de aparicao) no texto."""
    return tuple(int(number) for number in _PLACEHOLDER_RE.findall(text))


def is_faithful(original: str, translated: str) -> bool:
    """True se ``translated`` reproduzir fielmente os placeholders de ``original``.

    Detecta placeholders removidos, adicionados, reordenados ou duplicados,
    alem de literais escapados perdidos.
    """
    return placeholder_sequence(original) == placeholder_sequence(translated) and original.count(
        _ESCAPE
    ) == translated.count(_ESCAPE)
