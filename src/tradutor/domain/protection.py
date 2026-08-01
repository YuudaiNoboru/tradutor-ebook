"""Politica declarativa de protecao de conteudo.

Regras sao seletores simples (tag + atributos opcionais), totalmente
expansiveis: adicionar um seletor novo nao exige tocar em codigo de
decisao, apenas na tupla ``PROTECTION_POLICY``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProtectionRule:
    """Seletor declarativo: uma tag e, opcionalmente, atributos exigidos."""

    tag: str
    attrs: tuple[tuple[str, str], ...] = ()


PROTECTION_POLICY: tuple[ProtectionRule, ...] = (
    ProtectionRule("code"),
    ProtectionRule("pre"),
    ProtectionRule("svg"),
    ProtectionRule("math"),
    ProtectionRule("script"),
    ProtectionRule("style"),
)


def matches_rule(rule: ProtectionRule, tag: str, attrs: Mapping[str, str]) -> bool:
    """True se ``(tag, attrs)`` casar com todos os criterios da regra."""
    if rule.tag != tag:
        return False
    return all(attrs.get(name) == value for name, value in rule.attrs)


def is_protected(tag: str, attrs: Mapping[str, str] | None = None) -> bool:
    """True se o elemento (tag + atributos) casar com alguma regra da politica."""
    attrs = attrs or {}
    return any(matches_rule(rule, tag, attrs) for rule in PROTECTION_POLICY)
