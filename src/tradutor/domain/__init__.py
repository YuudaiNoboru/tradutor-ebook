"""Nucleo do dominio: blocos, protecao, placeholders e custo (funcoes puras)."""

from tradutor.domain.blocks import Block, Chapter
from tradutor.domain.cost import (
    DEFAULT_EXPANSION_FACTOR,
    CostEstimate,
    CostReport,
    Prices,
    cost_of,
    estimate,
    expansion_factor,
    make_cost_report,
    translatable_tokens,
)
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
from tradutor.domain.quality import has_ai_mark
from tradutor.domain.secrets import SecretStore
from tradutor.domain.translate import (
    PassadaTask,
    PromptContext,
    TermPolicy,
    TranslationBatch,
    Translator,
    Usage,
)

__all__ = [
    "Block",
    "Chapter",
    "CostEstimate",
    "CostReport",
    "DEFAULT_EXPANSION_FACTOR",
    "ExtractedText",
    "PROTECTION_POLICY",
    "PassadaTask",
    "Prices",
    "PromptContext",
    "ProtectionRule",
    "SecretStore",
    "TermPolicy",
    "TranslationBatch",
    "Translator",
    "Usage",
    "cost_of",
    "estimate",
    "expansion_factor",
    "extract_protected",
    "has_ai_mark",
    "is_faithful",
    "is_protected",
    "make_cost_report",
    "matches_rule",
    "placeholder_sequence",
    "restore_protected",
    "translatable_tokens",
]
