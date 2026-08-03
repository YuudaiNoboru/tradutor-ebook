"""Orquestracao: passadas de qualidade, estado por livro, lotes e retomada."""

from tradutor.translate.batching import make_batches, tiktoken_counter
from tradutor.translate.estado import (
    STATE_FILENAME,
    WorkState,
    load_estado,
    save_estado,
    state_compat_key,
)
from tradutor.translate.glossary_store import (
    GlossaryError,
    glossary_version,
    load_glossary,
    save_glossary,
)
from tradutor.translate.orchestrator import (
    DEFAULT_PARALLELISM,
    SpendingLimitExceeded,
    TranslationCancelled,
    TranslationOutcome,
    TranslationQualityError,
    translate_book,
)
from tradutor.translate.passadas import (
    SAMPLE_CHAPTERS,
    build_priming,
    extract_glossary,
)

__all__ = [
    "DEFAULT_PARALLELISM",
    "GlossaryError",
    "SAMPLE_CHAPTERS",
    "STATE_FILENAME",
    "SpendingLimitExceeded",
    "TranslationCancelled",
    "TranslationOutcome",
    "TranslationQualityError",
    "WorkState",
    "build_priming",
    "extract_glossary",
    "glossary_version",
    "load_estado",
    "load_glossary",
    "make_batches",
    "save_estado",
    "save_glossary",
    "state_compat_key",
    "tiktoken_counter",
    "translate_book",
]
