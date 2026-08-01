"""Testes da porta ``Translator`` e tipos de dados de traducao."""

from tradutor.domain import PromptContext, TermPolicy, TranslationBatch, Usage


def test_usage_total_tokens():
    assert Usage(10, 5).total_tokens == 15


def test_usage_add_accumulates():
    assert Usage(1, 2) + Usage(3, 4) == Usage(4, 6)


def test_prompt_context_defaults():
    context = PromptContext()
    assert context.source_language == "auto"
    assert context.target_language == "pt-BR"
    assert context.policy is TermPolicy.HIBRIDO
    assert context.glossary == ()
    assert context.priming == ""


def test_translation_batch_carries_texts_and_usage():
    batch = TranslationBatch(("a", "b"), Usage(2, 1))
    assert batch.texts == ("a", "b")
    assert batch.usage.total_tokens == 3


def test_term_policy_values():
    assert TermPolicy.TRADUZIR.value == "traduzir"
    assert TermPolicy.MANTER.value == "manter"
    assert TermPolicy.HIBRIDO.value == "hibrido"
