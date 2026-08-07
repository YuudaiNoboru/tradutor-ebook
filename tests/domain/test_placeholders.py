import re
import string

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tradutor.domain import (
    clean_placeholders,
    extract_protected,
    is_faithful,
    is_formatting_faithful,
    mask_markup,
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
