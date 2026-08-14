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
    """Seletor declarativo: uma tag opcional, atributos exigidos e/ou classes CSS exigidas."""

    tag: str | None = None
    attrs: tuple[tuple[str, str], ...] = ()
    classes: tuple[str, ...] = ()


PROTECTION_POLICY: tuple[ProtectionRule, ...] = (
    ProtectionRule("code"),
    ProtectionRule("pre"),
    ProtectionRule("svg"),
    ProtectionRule("math"),
    ProtectionRule("script"),
    ProtectionRule("style"),
    ProtectionRule("img"),
    ProtectionRule("picture"),
    ProtectionRule("hr"),
    ProtectionRule(classes=("programlisting",)),
    ProtectionRule(classes=("sourcecode",)),
    ProtectionRule(classes=("codelisting",)),
    ProtectionRule(classes=("code",)),
    ProtectionRule(classes=("screen",)),
)


def matches_rule(rule: ProtectionRule, tag: str, attrs: Mapping[str, str]) -> bool:
    """True se ``(tag, attrs)`` casar com todos os criterios da regra."""
    if rule.tag is not None and rule.tag != tag:
        return False
    if rule.attrs and not all(attrs.get(name) == value for name, value in rule.attrs):
        return False
    if rule.classes:
        element_classes = set(attrs.get("class", "").split())
        if not all(c in element_classes for c in rule.classes):
            return False
    return not (rule.tag is None and not rule.attrs and not rule.classes)


def is_protected(tag: str, attrs: Mapping[str, str] | None = None) -> bool:
    """True se o elemento (tag + atributos) casar com alguma regra da politica."""
    attrs = attrs or {}
    return any(matches_rule(rule, tag, attrs) for rule in PROTECTION_POLICY)
