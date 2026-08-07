"""Testes de qualidade da saida: deteccao de marcas de IA (tarefa 5.6)."""

from tradutor.domain import has_ai_mark


def test_clean_text_has_no_mark():
    assert not has_ai_mark("Ola mundo! Como voce esta?")
    assert not has_ai_mark("")
    assert not has_ai_mark("A fila (queue) e uma estrutura de dados.")


def test_bracketed_translation_note_is_mark():
    assert has_ai_mark("[Tradução automática]")


def test_nt_parenthesis_is_mark():
    assert has_ai_mark("Texto qualquer (N.T.)")
    assert has_ai_mark("Texto qualquer (n.t.)")


def test_nota_do_tradutor_is_mark():
    assert has_ai_mark("Nota do tradutor: termo tecnico")


def test_traduzido_por_ia_is_mark():
    assert has_ai_mark("Este texto foi traduzido por IA.")


def test_traducao_automatica_is_mark():
    assert has_ai_mark("Tradução automática via API.")


def test_original_colon_is_mark():
    assert has_ai_mark("Original: queue")


def test_original_colon_in_prose_is_not_mark():
    assert not has_ai_mark("No jogo original: tínhamos três fases.")


def test_original_in_parentheses_is_not_mark():
    assert not has_ai_mark("fila (queue)")
