"""Nucleo do dominio: blocos, protecao e placeholders (funcoes puras)."""

from tradutor.domain.blocks import Block, Chapter
from tradutor.domain.placeholders import (
    ExtractedText,
    extract_protected,
    is_faithful,
    placeholder_sequence,
    restore_protected,
)
from tradutor.domain.protection import (
    PROTECTION_POLICY,
    ProtectionRule,
    is_protected,
    matches_rule,
)
from tradutor.domain.secrets import SecretStore
from tradutor.domain.translate import (
    PromptContext,
    TermPolicy,
    TranslationBatch,
    Translator,
    Usage,
)

__all__ = [
    "Block",
    "Chapter",
    "ExtractedText",
    "PROTECTION_POLICY",
    "PromptContext",
    "ProtectionRule",
    "SecretStore",
    "TermPolicy",
    "TranslationBatch",
    "Translator",
    "Usage",
    "extract_protected",
    "is_faithful",
    "is_protected",
    "matches_rule",
    "placeholder_sequence",
    "restore_protected",
]
