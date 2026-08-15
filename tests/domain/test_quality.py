from tradutor.domain import fix_mojibake, has_ai_mark, has_mojibake, sanitize_pre_send


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


def test_bracketed_author_prose_containing_original_is_not_mark():
    text = (
        "[Discussão sobre os desafios de implementação. No formato original de "
        "Alexander, esta discussão teria sido incorporada à seção que descreve a resolução.]"
    )
    assert not has_ai_mark(text)
    assert not has_ai_mark("[Ver diagrama original na página 20]")


def test_bracketed_author_prose_containing_traducao_is_not_mark():
    assert not has_ai_mark("[A tradução entre bounded contexts requer anticorrupção]")


def test_bracketed_translator_notes_are_marks():
    assert has_ai_mark("[Nota da tradução: termo]")
    assert has_ai_mark("[Nota de tradução: termo]")
    assert has_ai_mark("[Tradução: termo original]")
    assert has_ai_mark("[Texto original: queue]")
    assert has_ai_mark("[Original: queue]")
    assert has_ai_mark("[N.T.: termo]")
    assert has_ai_mark("[N.T.]")
    assert has_ai_mark("[Tradução livre]")


def test_sanitize_pre_send_empty():
    assert sanitize_pre_send("") == ""


def test_sanitize_pre_send_replaces_nbsp_and_invisibles():
    raw = "Texto\u00a0com\u00a0espaço \ufeff\u200be\x00 invisíveis"
    sanitized = sanitize_pre_send(raw)
    assert "\u00a0" not in sanitized
    assert "\ufeff" not in sanitized
    assert "\u200b" not in sanitized
    assert "\x00" not in sanitized
    assert sanitized == "Texto com espaço e invisíveis"


def test_sanitize_pre_send_nfc_normalization():
    decomposed = "e\u0301"  # 'e' + combining acute accent (NFD)
    sanitized = sanitize_pre_send(decomposed)
    assert sanitized == "é"  # NFC


def test_has_mojibake_detects_double_encoding():
    assert has_mojibake("faÃ§ade")
    assert has_mojibake("capitulo Â 1")
    assert has_mojibake("capituloÂ\xa01")
    assert has_mojibake("termo â€“ definicao")
    assert has_mojibake("â€œcitacaoâ€ ")
    assert has_mojibake("â\x80\x9ccitacaoâ\x80\x9d")
    assert has_mojibake("pÃ¡gina de portuguÃªs")
    assert not has_mojibake("Olá mundo – sem mojibake “aqui”")
    assert not has_mojibake("")


def test_fix_mojibake_empty():
    assert fix_mojibake("") == ""


def test_fix_mojibake_repairs_all_spec_cases():
    assert fix_mojibake("faÃ§ade") == "façade"
    assert fix_mojibake("capituloÂ\xa01") == "capitulo\xa01"
    assert fix_mojibake("capitulo Â 1") == "capitulo  1"
    assert fix_mojibake("termo â€“ definicao") == "termo – definicao"
    assert fix_mojibake("â€œcitacaoâ€ ") == "“citacao”"
    assert fix_mojibake("â€˜singleâ€™") == "‘single’"
    assert fix_mojibake("itemâ€¦ e pontinhoâ€¢") == "item… e pontinho•"


def test_fix_mojibake_repairs_3byte_latin1_double_encoding():
    assert fix_mojibake("â\x80\x9ccitacaoâ\x80\x9d") == "“citacao”"
    assert fix_mojibake("termoâ\x80\x93en e travessaoâ\x80\x94em") == "termo–en e travessao—em"
    assert fix_mojibake("aspasâ\x80\x98singleâ\x80\x99") == "aspas‘single’"
    assert fix_mojibake("pontosâ\x80\xa6 e marcadorâ\x80\xa2") == "pontos… e marcador•"
    assert fix_mojibake("guiasâ\x80\xb9 e â\x80\xba") == "guias‹ e ›"
    assert fix_mojibake("marcaâ\x84\xa2") == "marca™"


def test_fix_mojibake_repairs_portuguese_diacritics():
    raw = "PÃ¡gina com portuguÃªs, experiÃªncia, aÃ§Ã£o, Ã­cone e Ãºltimo."
    assert fix_mojibake(raw) == "Página com português, experiência, ação, ícone e último."


def test_fix_mojibake_repairs_uppercase_and_symbols():
    raw = "Â«Ã\x81rea de Ã‰ticaÂ» a 100Â°C sob licenÃ§aÂ© e marcaÂ®."
    assert fix_mojibake(raw) == "«Área de Ética» a 100°C sob licença© e marca®."
