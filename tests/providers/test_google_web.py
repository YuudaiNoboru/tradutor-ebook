"""Testes do transporte experimental sem rede real."""

from __future__ import annotations

import json

import httpx
import pytest

from tradutor.domain import Block, MachineTranslationContext
from tradutor.providers.errors import DefinitiveProviderError, TransientProviderError
from tradutor.providers.machine_translation.google_web import (
    WEB_PUBLIC_KEY,
    GoogleWebProvider,
    GoogleWebResponseError,
    _find_translations,
)


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_google_html_translation_preserves_alignment_and_reports_chars():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Content-Type"] == "application/json+protobuf"
        assert request.headers["X-Goog-Api-Key"] == WEB_PUBLIC_KEY
        body = json.loads(request.content)
        assert body[1] == "wt_lib"
        assert body[0][1:] == ["en", "pt-BR"]
        return httpx.Response(
            200,
            json=[["<em>Olá</em>", "Mundo"]],
            headers={"content-type": "application/json"},
        )

    provider = GoogleWebProvider(http_client=_client(handler), delay_seconds=0)
    result = provider.translate(
        [Block(1, "texto", "<em>Hello</em>"), Block(2, "texto", "World")],
        MachineTranslationContext("en", "pt-BR"),
    )

    assert result.texts == ("<em>Olá</em>", "Mundo")
    assert result.usage.total_tokens is None
    assert result.usage.characters == len("<em>Hello</em>") + len("World")
    assert result.usage.blocks == 2


def test_google_uses_text_fallback_when_html_unavailable():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path.endswith("translateHtml"):
            return httpx.Response(404, text="not found")
        return httpx.Response(200, json=["Olá"])

    provider = GoogleWebProvider(http_client=_client(handler), delay_seconds=0, max_retries=0)
    result = provider.translate(
        [Block(1, "texto", "Hello")], MachineTranslationContext("en", "pt-BR")
    )

    assert result.texts == ("Olá",)
    assert len(calls) == 2

    result = provider.translate(
        [Block(2, "texto", "Hello again")], MachineTranslationContext("en", "pt-BR")
    )
    assert result.texts == ("Olá",)
    assert len(calls) == 3


def _echo_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("translateHtml"):
        return httpx.Response(404, text="not found")
    return httpx.Response(
        200, json=[q.replace("Hello", "Olá") for q in request.url.params.get_list("q")]
    )


def test_google_text_fallback_translates_markup_when_faithful():
    provider = GoogleWebProvider(http_client=_client(_echo_handler), delay_seconds=0, max_retries=0)
    result = provider.translate(
        [Block(1, "texto", "<em>Hello</em>")], MachineTranslationContext("en", "pt-BR")
    )

    assert result.texts == ("<em>Olá</em>",)


def test_google_text_fallback_restores_attribute_tags_byte_for_byte():
    provider = GoogleWebProvider(http_client=_client(_echo_handler), delay_seconds=0, max_retries=0)
    result = provider.translate(
        [Block(1, "texto", '<span class="x">Hello</span> world')],
        MachineTranslationContext("en", "pt-BR"),
    )

    assert result.texts == ('<span class="x">Olá</span> world',)


def test_google_text_fallback_preserves_empty_pagebreak_element():
    provider = GoogleWebProvider(http_client=_client(_echo_handler), delay_seconds=0, max_retries=0)
    result = provider.translate(
        [Block(1, "p", 'before <span id="p13" epub:type="pagebreak"></span>Hello')],
        MachineTranslationContext("en", "pt-BR"),
    )

    assert result.texts == ('before <span id="p13" epub:type="pagebreak"></span>Olá',)


def test_google_text_fallback_rejected_when_tokens_reordered():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("translateHtml"):
            return httpx.Response(404, text="not found")
        return httpx.Response(200, json=["@@1@@Olá@@0@@"])

    provider = GoogleWebProvider(http_client=_client(handler), delay_seconds=0, max_retries=0)
    with pytest.raises(GoogleWebResponseError, match="markup ou placeholder"):
        provider.translate(
            [Block(1, "texto", "<em>Hello</em>")],
            MachineTranslationContext("en", "pt-BR"),
        )


def test_google_rejects_unfaithful_text_fallback_for_markup():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("translateHtml"):
            return httpx.Response(404, text="not found")
        return httpx.Response(200, json=["texto liso sem marcas"])

    provider = GoogleWebProvider(http_client=_client(handler), delay_seconds=0, max_retries=0)
    with pytest.raises(GoogleWebResponseError, match="markup ou placeholder"):
        provider.translate(
            [Block(1, "texto", "<em>Hello</em>")],
            MachineTranslationContext("en", "pt-BR"),
        )


def test_connection_reports_text_fallback_when_html_blocked():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("translateHtml"):
            return httpx.Response(403, text="requires API key")
        assert request.url.params["client"] == "gtx"
        return httpx.Response(200, json=[[["ok", "ok"]]])

    provider = GoogleWebProvider(http_client=_client(handler), delay_seconds=0)
    result = provider.test_connection()

    assert result.ok
    assert "fallback textual acessível" in result.message
    assert result.models == ()


def test_connection_reports_failure_when_both_profiles_down():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found")

    provider = GoogleWebProvider(http_client=_client(handler), delay_seconds=0)
    result = provider.test_connection()

    assert not result.ok
    assert "HTML" in result.message
    assert "textual" in result.message


def test_text_fallback_uses_validated_client_variant():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("translateHtml"):
            return httpx.Response(404, text="not found")
        assert request.url.params["client"] == "gtx"
        assert request.url.path.endswith("translate_a/t")
        return httpx.Response(200, json=["Olá"])

    provider = GoogleWebProvider(http_client=_client(handler), delay_seconds=0, max_retries=0)
    result = provider.translate(
        [Block(1, "texto", "Hello")], MachineTranslationContext("en", "pt-BR")
    )

    assert result.texts == ("Olá",)


def test_google_retries_rate_limit_then_succeeds():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json={"translations": ["Olá"]})

    sleeps: list[float] = []
    provider = GoogleWebProvider(
        http_client=_client(handler),
        delay_seconds=0,
        sleep=sleeps.append,
        max_retries=1,
    )
    result = provider.translate([Block(1, "texto", "Hello")], MachineTranslationContext())

    assert result.texts == ("Olá",)
    assert attempts == 2
    assert sleeps == [0]


def test_constructor_validates_limites():
    with pytest.raises(ValueError, match="timeout"):
        GoogleWebProvider(timeout=0)
    with pytest.raises(ValueError, match="max_retries"):
        GoogleWebProvider(max_retries=-1)
    with pytest.raises(ValueError, match="delay_seconds"):
        GoogleWebProvider(delay_seconds=-0.5)


def test_empty_batch_returns_empty_usage():
    provider = GoogleWebProvider(http_client=_client(lambda _r: httpx.Response(200)))
    result = provider.translate([], MachineTranslationContext())

    assert result.texts == ()
    assert result.usage.characters == 0
    assert result.usage.blocks == 0


def test_protected_blocks_are_rejected():
    provider = GoogleWebProvider(http_client=_client(lambda _r: httpx.Response(200)))

    with pytest.raises(DefinitiveProviderError, match="protegidos"):
        provider.translate(
            [Block(1, "texto", "Hello", protected=True)], MachineTranslationContext()
        )


def test_block_over_char_limit_is_rejected():
    provider = GoogleWebProvider(http_client=_client(lambda _r: httpx.Response(200)))
    huge = Block(1, "texto", "x" * (provider.capabilities.max_batch_chars + 1))

    with pytest.raises(DefinitiveProviderError, match="excede o limite"):
        provider.translate([huge], MachineTranslationContext())


def test_unfaithful_response_is_rejected_before_cache():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"translations": ["texto sem nada"]},
            headers={"content-type": "application/json"},
        )

    provider = GoogleWebProvider(http_client=_client(handler), delay_seconds=0)

    with pytest.raises(GoogleWebResponseError, match="markup ou placeholder"):
        provider.translate(
            [Block(1, "texto", "texto com {{0}}")], MachineTranslationContext("en", "pt-BR")
        )


def test_batches_are_split_by_items_and_respect_delay():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        items = json.loads(request.content)[0][0]
        return httpx.Response(
            200,
            json=[f"TR:{item}" for item in items],
            headers={"content-type": "application/json"},
        )

    sleeps: list[float] = []
    provider = GoogleWebProvider(
        http_client=_client(handler),
        delay_seconds=0.5,
        sleep=sleeps.append,
    )
    blocks = [Block(i, "texto", f"frase {i}") for i in range(9)]
    result = provider.translate(blocks, MachineTranslationContext("en", "pt-BR"))

    assert len(requests) == 2
    assert len(result.texts) == 9
    assert sleeps


def test_connection_ok_when_html_profile_available():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    provider = GoogleWebProvider(http_client=_client(handler), delay_seconds=0)
    result = provider.test_connection()

    assert result.ok
    assert "endpoint HTML acessível" in result.message


def test_connection_transport_errors_explained():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sem rede")

    provider = GoogleWebProvider(http_client=_client(handler), delay_seconds=0)
    result = provider.test_connection()

    assert not result.ok
    assert "endpoint HTML" in result.message
    assert "fallback textual" in result.message


def test_connection_html_transient_and_text_probe_status():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("translateHtml"):
            return httpx.Response(429)
        return httpx.Response(403)

    provider = GoogleWebProvider(http_client=_client(handler), delay_seconds=0)
    result = provider.test_connection()

    assert not result.ok
    assert "temporariamente indisponível" in result.message
    assert "HTTP 403" in result.message


def test_transient_failure_propagates_when_both_profiles_down():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429)

    provider = GoogleWebProvider(
        http_client=_client(handler), delay_seconds=0, max_retries=0, sleep=lambda _s: None
    )

    with pytest.raises(TransientProviderError):
        provider.translate(
            [Block(1, "texto", "<em>Hello</em>")], MachineTranslationContext("en", "pt-BR")
        )


def test_text_fallback_failure_produces_actionable_error():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("translateHtml"):
            return httpx.Response(404, text="not found")
        return httpx.Response(400, text="bad request")

    provider = GoogleWebProvider(http_client=_client(handler), delay_seconds=0, max_retries=0)

    with pytest.raises(GoogleWebResponseError, match="não retornou tradução compatível"):
        provider.translate([Block(1, "texto", "Hello")], MachineTranslationContext("en", "pt-BR"))


def test_public_key_override_goes_in_header_not_config():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Goog-Api-Key"] == "chave-publica-da-web"
        return httpx.Response(200, json=[["Olá"]], headers={"content-type": "application/json"})

    provider = GoogleWebProvider(
        http_client=_client(handler), delay_seconds=0, public_key="chave-publica-da-web"
    )
    result = provider.translate([Block(1, "texto", "Hello")], MachineTranslationContext())

    assert result.texts == ("Olá",)


def test_timeout_and_transport_are_transient_then_exhaust():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        if not request.url.path.endswith("translateHtml"):
            return httpx.Response(200, json=[[["Olá", "Hello"]]])
        attempts += 1
        if attempts == 1:
            raise httpx.ConnectTimeout("lento")
        raise httpx.ConnectError("sem rede")

    provider = GoogleWebProvider(
        http_client=_client(handler),
        delay_seconds=0,
        max_retries=1,
        sleep=lambda _s: None,
    )
    result = provider.translate([Block(1, "texto", "Hello")], MachineTranslationContext())

    assert result.texts == ("Olá",)
    assert attempts == 2


def test_invalid_retry_after_falls_back_to_jitter():
    attempts = 0
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "invalido"})
        return httpx.Response(
            200, json={"translations": ["Olá"]}, headers={"content-type": "application/json"}
        )

    provider = GoogleWebProvider(
        http_client=_client(handler),
        delay_seconds=0,
        max_retries=1,
        sleep=sleeps.append,
    )
    result = provider.translate([Block(1, "texto", "Hello")], MachineTranslationContext())

    assert result.texts == ("Olá",)
    assert len(sleeps) == 1
    assert sleeps[0] >= 0


def test_html_invalid_json_is_definitive():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="{invalido", headers={"content-type": "application/json"})

    provider = GoogleWebProvider(http_client=_client(handler), delay_seconds=0, max_retries=0)

    with pytest.raises(GoogleWebResponseError, match="JSON inválido|compatível"):
        provider.translate([Block(1, "texto", "Hello")], MachineTranslationContext())


def test_html_misaligned_response_is_rejected():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"translations": ["só um"]},
            headers={"content-type": "application/json"},
        )

    provider = GoogleWebProvider(http_client=_client(handler), delay_seconds=0, max_retries=0)

    with pytest.raises(GoogleWebResponseError, match="desalinhada|compatível"):
        provider.translate(
            [Block(1, "texto", "Hello"), Block(2, "texto", "World")],
            MachineTranslationContext(),
        )


def test_find_translations_supports_known_payload_shapes():
    assert _find_translations({"translatedText": "Olá"}) == ["Olá"]
    assert _find_translations({"data": {"translations": ["Olá"]}}) == ["Olá"]
    assert _find_translations([{"translations": ["Olá"]}]) == ["Olá"]
    assert _find_translations([["Olá", "Hello"]]) == ["Olá"]
    assert _find_translations(["Olá"]) == ["Olá"]
    assert _find_translations(123) == []
    assert _find_translations({"nada": 1}) == []


def test_html_unfaithful_markup_falls_back_to_text_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("translateHtml"):
            return httpx.Response(200, json=[["Olá mundo"]])
        return httpx.Response(200, json=["@@0@@Olá@@1@@ mundo"])

    provider = GoogleWebProvider(http_client=_client(handler), delay_seconds=0, max_retries=0)
    result = provider.translate(
        [Block(1, "texto", "<em>Hello</em> world")],
        MachineTranslationContext("en", "pt-BR"),
    )

    assert result.texts == ("<em>Olá</em> mundo",)
