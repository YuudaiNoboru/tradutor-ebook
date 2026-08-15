import re
import string

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tradutor.domain import (
    are_tags_balanced,
    clean_placeholders,
    extract_protected,
    is_faithful,
    is_formatting_faithful,
    link_sequence,
    mask_markup,
    normalize_hyphenated_placeholders,
    placeholder_sequence,
    restore_protected,
    unmask_markup,
)

ALPHABET = string.ascii_letters + string.digits + "{}<>/ \t\n-="

st_text = st.text(alphabet=ALPHABET, max_size=200)
st_snippets = st.lists(st.text(alphabet=ALPHABET, min_size=1, max_size=40), max_size=10)


def test_extract_replaces_protected_content():
    extracted = extract_protected("Clique em salvar para gravar", ["salvar"])
    assert extracted.template == "Clique em {{0}} para gravar"
    assert extracted.protected == {0: "salvar"}


def test_extract_multiple_in_order_of_first_occurrence():
    text = "A com B entre C com A de novo"
    extracted = extract_protected(text, ["C", "A", "B"])
    assert extracted.template == "{{0}} com {{1}} entre {{2}} com {{0}} de novo"
    assert extracted.protected == {0: "A", 1: "B", 2: "C"}


def test_extract_ignores_empty_duplicates_and_absent():
    extracted = extract_protected("so texto", ["", "texto", "texto", "ausente", "so"])
    assert extracted.template == "{{0}} {{1}}"
    assert extracted.protected == {0: "so", 1: "texto"}


def test_extract_snippet_containing_literal_placeholder():
    text = "golang {{.Var}} e {{5}} python"
    extracted = extract_protected(text, ["{{5}}"])
    assert extracted.template == "golang {{.Var}} e {{0}} python"
    assert restore_protected(extracted.template, extracted.protected) == text


def test_restore_round_trip_with_literal_placeholder_in_prose():
    text = "use {{name}} no template e {{1}}"
    extracted = extract_protected(text, [])
    assert restore_protected(extracted.template, extracted.protected) == text


def test_extract_no_protected_content():
    extracted = extract_protected("so texto", [])
    assert extracted.template == "so texto"
    assert extracted.protected == {}


def test_extract_empty_text():
    extracted = extract_protected("", [])
    assert extracted.template == ""
    assert extracted.protected == {}


def test_restore_multiple_occurrences():
    template = "{{0}} e {{1}} e {{0}}"
    restored = restore_protected(template, {0: "x", 1: "y"})
    assert restored == "x e y e x"


def test_restore_missing_placeholder_raises():
    with pytest.raises(ValueError, match="sem conteudo protegido"):
        restore_protected("a {{9}} b", {0: "x"})


def test_placeholder_sequence_ordered():
    assert placeholder_sequence("{{2}} {{0}} {{1}}") == (2, 0, 1)


def test_placeholder_sequence_empty():
    assert placeholder_sequence("sem placeholders") == ()


def test_is_faithful_unchanged():
    assert is_faithful("oi {{0}} mundo {{1}}", "oi {{0}} mundo {{1}}")


def test_is_faithful_detects_removed():
    assert not is_faithful("oi {{0}} {{1}}", "oi {{0}}")


def test_is_faithful_detects_reordered():
    assert not is_faithful("oi {{0}} {{1}}", "oi {{1}} {{0}}")


def test_is_faithful_detects_extra():
    assert not is_faithful("oi {{0}}", "oi {{0}} {{1}}")


def test_is_faithful_detects_lost_escaped_literal():
    original = extract_protected("v {{9}} w", []).template
    assert original != "v {{9}} w"
    assert not is_faithful(original, "v w")
    assert is_faithful(original, original)


def test_placeholder_regex_ignores_escaped_literals():
    original = extract_protected("v {{9}} w", []).template
    assert placeholder_sequence(original) == ()


@given(text=st_text, snippets=st_snippets)
@settings(max_examples=200)
def test_property_round_trip_is_bijection(text, snippets):
    extracted = extract_protected(text, snippets)
    assert restore_protected(extracted.template, extracted.protected) == text


@given(text=st_text, snippets=st_snippets)
@settings(max_examples=200)
def test_property_placeholder_ids_are_sequential(text, snippets):
    extracted = extract_protected(text, snippets)
    sequence = placeholder_sequence(extracted.template)
    assert set(sequence) == set(range(len(extracted.protected)))


@given(text=st_text, snippets=st_snippets)
@settings(max_examples=200)
def test_property_no_snippet_in_template(text, snippets):
    extracted = extract_protected(text, snippets)
    for snippet in snippets:
        if snippet and not re.search(r"[0-9{}]", snippet):
            assert snippet not in extracted.template


@given(text=st_text, snippets=st_snippets)
@settings(max_examples=200)
def test_property_extraction_is_faithful_to_original(text, snippets):
    extracted = extract_protected(text, snippets)
    assert is_faithful(extracted.template, extracted.template)


def test_mask_markup_hides_tags_behind_tokens():
    masked, tags, empties = mask_markup('<span class="x">oi {{0}} fim</span>')

    assert masked == "@@0@@oi {{0}} fim@@1@@"
    assert tags == ('<span class="x">', "</span>")
    assert empties == ()


def test_mask_unmask_round_trip_restores_tags_byte_for_byte():
    original = '<a href="x">oi</a> e <br/> fim'
    masked, tags, empties = mask_markup(original)

    assert "<" not in masked
    assert unmask_markup(masked, tags, empties) == original


def test_unmask_leaves_unknown_numbers_untouched():
    _masked, tags, empties = mask_markup("<em>oi</em>")

    assert unmask_markup("@@0@@ fica @@5@@", tags, empties) == "<em> fica @@5@@"


def test_masked_translation_passes_formatting_check():
    original = '<span class="x">Hello</span>'
    masked, tags, empties = mask_markup(original)

    final = unmask_markup(masked.replace("Hello", "Olá"), tags, empties)

    assert is_formatting_faithful(original, final)


def test_mask_markup_masks_empty_element_with_sentinel_pair():
    original = 'antes <span id="p13" epub:type="pagebreak"></span>depois'
    masked, tags, empties = mask_markup(original)

    assert masked == "antes @@0@@\u00a0@@1@@depois"
    assert tags == ('<span id="p13" epub:type="pagebreak">', "</span>")
    assert empties == ('<span id="p13" epub:type="pagebreak"></span>',)
    assert unmask_markup(masked, tags, empties) == original


def test_unmask_removes_sentinel_left_as_space():
    original = 'antes <span id="p13" epub:type="pagebreak"></span>depois'
    masked, tags, empties = mask_markup(original)

    translated = masked.replace("\u00a0", " ")
    assert unmask_markup(translated, tags, empties) == original


def test_clean_placeholders_removes_internal_spaces():
    assert clean_placeholders("oi {{ 0 }} e {{1 }} e {{ 2}}") == "oi {{0}} e {{1}} e {{2}}"


def test_clean_placeholders_removes_mask_spaces():
    assert clean_placeholders("oi @@ 0 @@ e @ @ 1 @ @") == "oi @@0@@ e @@1@@"


def test_unmask_markup_handles_spaced_mask_tokens():
    assert unmask_markup("oi @@ 0 @@", ("<em>",), ()) == "oi <em>"


def test_is_formatting_faithful_tolerates_tag_whitespace_variations():
    original = '<span class="x">Hello</span> world <br/>'
    translated = '<span class="x" >Olá</span> mundo <br />'
    assert is_formatting_faithful(original, translated)


def test_extract_and_restore_inline_image():
    original = 'Texto antes <img src="fig1.png" alt="Figura 1"/> e texto depois.'
    img_snippet = '<img src="fig1.png" alt="Figura 1"/>'
    extracted = extract_protected(original, [img_snippet])

    assert extracted.template == "Texto antes {{0}} e texto depois."
    assert extracted.protected == {0: img_snippet}
    assert is_faithful(extracted.template, "Texto traduzido {{0}} e depois.")

    restored = restore_protected("Texto traduzido {{0}} e depois.", extracted.protected)
    assert restored == 'Texto traduzido <img src="fig1.png" alt="Figura 1"/> e depois.'


def test_extract_and_restore_empty_anchors():
    original = 'Antes <a id="page_42"></a> meio <span id="p43"></span> fim.'
    extracted = extract_protected(original, ['<a id="page_42"></a>', '<span id="p43"></span>'])

    assert extracted.template == "Antes {{0}} meio {{1}} fim."
    assert extracted.protected == {0: '<a id="page_42"></a>', 1: '<span id="p43"></span>'}

    restored = restore_protected("Before {{0}} middle {{1}} end.", extracted.protected)
    assert restored == 'Before <a id="page_42"></a> middle <span id="p43"></span> end.'


def test_extract_and_restore_hyphenated_anchor_normalizes_word():
    original = 'what every-<a id="page_419"></a>one needs to know'
    extracted = extract_protected(original, ['<a id="page_419"></a>'])

    assert extracted.template == "what everyone {{0}} needs to know"
    assert extracted.protected == {0: '<a id="page_419"></a>'}

    translated = "o que todos {{0}} precisam saber"
    assert is_faithful(extracted.template, translated)

    restored = restore_protected(translated, extracted.protected)
    assert restored == 'o que todos <a id="page_419"></a> precisam saber'


def test_normalize_hyphenated_placeholders_multiple():
    text = "ar-{{0}}chitecture and non-{{1}}technical and every- {{2}}one"
    normalized = normalize_hyphenated_placeholders(text)
    assert normalized == "architecture {{0}} and nontechnical {{1}} and everyone {{2}}"


def test_link_sequence_extracts_and_normalizes_anchor_tags():
    text = '<p class="toc"><a  href="ch03.html#sec1" >Texto</a> e <a href="bib.html">Ref</a></p>'
    seq = link_sequence(text)
    assert seq == ('<a href="ch03.html#sec1">', "</a>", '<a href="bib.html">', "</a>")


def test_are_tags_balanced_detects_valid_and_broken_nesting():
    assert are_tags_balanced("<em>Texto <strong>negrito</strong></em>")
    assert are_tags_balanced('<a href="x">H<small>ANDS</small>-O<small>N</small></a>')
    assert are_tags_balanced("<br/> texto <img src='x.png'/> fim")
    assert not are_tags_balanced("<em>Texto <strong>negrito</em></strong>")
    assert not are_tags_balanced("<em>Texto sem fechar")
    assert not are_tags_balanced("Texto </strong> so fechando")


def test_is_formatting_faithful_accepts_style_count_variation_with_preserved_links():
    orig = '<a href="ch03.html#sec4">H<small>ANDS</small>-O<small>N</small> M<small>ODELERS</small></a>'
    # 2 small tags em vez de 3 na tradução em português (mesmo tipo de tag, contagem diferente)
    trans_with_fewer_small = (
        '<a href="ch03.html#sec4">M<small>ODELADORES</small> P<small>RÁTICOS</small></a>'
    )
    # Sem small tags (tag type perdida)
    trans_plain_link = '<a href="ch03.html#sec4">MODELADORES PRÁTICOS</a>'
    # Link removido
    trans_lost_link = "MODELADORES PRÁTICOS"

    assert is_formatting_faithful(orig, trans_with_fewer_small)
    assert not is_formatting_faithful(orig, trans_plain_link)
    assert not is_formatting_faithful(orig, trans_lost_link)


def test_unmask_markup_strips_sentinel_even_if_not_in_empty():
    masked = "antes @@0@@\u00a0@@1@@ depois"
    tags = ("<span>", "</span>")
    unmasked = unmask_markup(masked, tags, ())
    assert "\u00a0" not in unmasked
    assert unmasked == "antes <span></span> depois"


def test_clean_placeholders_tolerates_nested_spaces():
    assert clean_placeholders("oi { { 0 } } e { {1} } e {{ 2 }}") == "oi {{0}} e {{1}} e {{2}}"
    assert clean_placeholders("marcador @ @ 0 @ @ e @@ 1 @@") == "marcador @@0@@ e @@1@@"
