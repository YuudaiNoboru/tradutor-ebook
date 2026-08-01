"""Testes do ``OpenAICompatProvider`` com API falsa (respx).

Cobrem: sucesso (com usage), 429/5xx/timeout com retry, Retry-After,
resposta quebrada, falha definitiva (nao interrompe o provider: o
proximo lote continua normal), teste de conexao e chave pela porta
``SecretStore``.
"""

from __future__ import annotations

import json
import random

import httpx
import pytest
import respx

from tradutor.domain import Block, PromptContext, TermPolicy, Usage
from tradutor.providers import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    AuthenticationError,
    ConnectionResult,
    DefinitiveProviderError,
    OpenAICompatProvider,
    TransientProviderError,
)

API = DEFAULT_BASE_URL


class FakeSecretStore:
    def __init__(self, key: str | None = "test-key") -> None:
        self._key = key

    def get(self, name: str) -> str | None:
        return self._key


class SleepRecorder:
    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


def make_provider(**kwargs: object) -> OpenAICompatProvider:
    kwargs.setdefault("secret_store", FakeSecretStore())
    return OpenAICompatProvider(**kwargs)


def chat_response(
    texts: list[str], *, prompt_tokens: int = 5, completion_tokens: int = 3
) -> dict[str, object]:
    return {
        "choices": [
            {"message": {"role": "assistant", "content": json.dumps(texts, ensure_ascii=False)}}
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


def block(text: str, block_id: int = 1) -> Block:
    return Block(id=block_id, kind="p", text=text)


@respx.mock
def test_translate_success_with_defaults_and_usage():
    route = respx.post(f"{API}/chat/completions").mock(
        return_value=httpx.Response(200, json=chat_response(["Ola mundo", "Adeus"]))
    )
    provider = make_provider()
    batch = [block("Hello world", 1), block("Goodbye", 2)]
    result = provider.translate(batch, PromptContext())

    assert result.texts == ("Ola mundo", "Adeus")
    assert result.usage == Usage(prompt_tokens=5, completion_tokens=3)
    assert result.usage.total_tokens == 8

    request = route.calls.last.request
    assert request.headers["authorization"] == "Bearer test-key"
    assert json.loads(request.content)["model"] == DEFAULT_MODEL


@respx.mock
def test_translate_custom_base_url_and_model():
    base = "http://localhost:11434/v1"
    route = respx.post(f"{base}/chat/completions").mock(
        return_value=httpx.Response(200, json=chat_response(["Oi"]))
    )
    provider = make_provider(base_url=base, model="llama3")

    result = provider.translate([block("Hi")], PromptContext())

    assert result.texts == ("Oi",)
    assert json.loads(route.calls.last.request.content)["model"] == "llama3"
    assert provider.base_url == base


@respx.mock
def test_translate_retries_on_429_respecting_retry_after():
    route = respx.post(f"{API}/chat/completions").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "2"}, json={"error": {"message": "slow"}}),
            httpx.Response(200, json=chat_response(["Tudo bem"])),
        ]
    )
    sleeps = SleepRecorder()
    provider = make_provider(sleep=sleeps, rng=random.Random(0))

    result = provider.translate([block("Fine")], PromptContext())

    assert result.texts == ("Tudo bem",)
    assert len(route.calls) == 2
    assert sleeps.calls == [2.0]


@respx.mock
def test_translate_retries_on_5xx_with_jittered_backoff():
    route = respx.post(f"{API}/chat/completions").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200, json=chat_response(["Ok"])),
        ]
    )
    sleeps = SleepRecorder()
    provider = make_provider(sleep=sleeps, rng=random.Random(42))

    result = provider.translate([block("Ok")], PromptContext())

    assert result.texts == ("Ok",)
    assert len(route.calls) == 2
    assert 0.0 <= sleeps.calls[0] < 1.0


@respx.mock
def test_translate_retries_on_timeout():
    route = respx.post(f"{API}/chat/completions").mock(
        side_effect=[
            httpx.TimeoutException("timeout"),
            httpx.Response(200, json=chat_response(["Pronto"])),
        ]
    )
    sleeps = SleepRecorder()
    provider = make_provider(sleep=sleeps, rng=random.Random(0), base_delay=0.5)

    result = provider.translate([block("Ready")], PromptContext())

    assert result.texts == ("Pronto",)
    assert len(route.calls) == 2


@respx.mock
def test_translate_401_is_definitive_without_retry():
    route = respx.post(f"{API}/chat/completions").mock(
        return_value=httpx.Response(401, json={"error": {"message": "invalid key"}})
    )
    provider = make_provider()

    with pytest.raises(AuthenticationError, match="autenticacao falhou"):
        provider.translate([block("X")], PromptContext())
    assert len(route.calls) == 1


@respx.mock
def test_translate_404_is_definitive_without_retry():
    route = respx.post(f"{API}/chat/completions").mock(return_value=httpx.Response(404))
    provider = make_provider()

    with pytest.raises(DefinitiveProviderError, match="HTTP 404"):
        provider.translate([block("X")], PromptContext())
    assert len(route.calls) == 1


@respx.mock
def test_translate_exhausts_retries_and_raises_transient():
    route = respx.post(f"{API}/chat/completions").mock(return_value=httpx.Response(429))
    sleeps = SleepRecorder()
    provider = make_provider(sleep=sleeps, max_retries=2, rng=random.Random(0))

    with pytest.raises(TransientProviderError, match="esgotadas 3 tentativas"):
        provider.translate([block("X")], PromptContext())
    assert len(route.calls) == 3
    assert len(sleeps.calls) == 2


@respx.mock
def test_definitive_failure_does_not_stop_next_batch():
    route = respx.post(f"{API}/chat/completions").mock(
        side_effect=[
            httpx.Response(400),
            httpx.Response(200, json=chat_response(["Sobrevivi"])),
        ]
    )
    provider = make_provider()

    with pytest.raises(DefinitiveProviderError):
        provider.translate([block("Primeiro lote")], PromptContext())
    result = provider.translate([block("Segundo lote")], PromptContext())

    assert result.texts == ("Sobrevivi",)
    assert len(route.calls) == 2


@respx.mock
def test_translate_broken_response_is_transient():
    route = respx.post(f"{API}/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "isto nao e um array"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            },
        )
    )
    provider = make_provider(max_retries=0)

    with pytest.raises(TransientProviderError, match="sem array JSON"):
        provider.translate([block("X")], PromptContext())
    assert len(route.calls) == 1


@respx.mock
def test_translate_mismatched_item_count_is_transient():
    respx.post(f"{API}/chat/completions").mock(
        return_value=httpx.Response(200, json=chat_response(["so um"]))
    )
    provider = make_provider(max_retries=0)

    with pytest.raises(TransientProviderError, match="esperado 2"):
        provider.translate([block("A"), block("B")], PromptContext())


@respx.mock
def test_translate_missing_choices_is_transient():
    respx.post(f"{API}/chat/completions").mock(
        return_value=httpx.Response(200, json={"error": {"message": "boom"}})
    )
    provider = make_provider(max_retries=0)

    with pytest.raises(TransientProviderError, match="sem conteudo de traducao"):
        provider.translate([block("X")], PromptContext())


@respx.mock
def test_translate_content_not_text_is_transient():
    respx.post(f"{API}/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": {"texto": "x"}}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            },
        )
    )
    provider = make_provider(max_retries=0)

    with pytest.raises(TransientProviderError, match="nao e texto"):
        provider.translate([block("X")], PromptContext())


@respx.mock
def test_translate_non_json_body_is_transient():
    respx.post(f"{API}/chat/completions").mock(
        return_value=httpx.Response(200, content=b"<html>oops</html>")
    )
    provider = make_provider(max_retries=0)

    with pytest.raises(TransientProviderError, match="nao e JSON valido"):
        provider.translate([block("X")], PromptContext())


@respx.mock
def test_translate_generic_network_error_is_transient():
    respx.post(f"{API}/chat/completions").mock(side_effect=httpx.ConnectError("down"))
    provider = make_provider(max_retries=0)

    with pytest.raises(TransientProviderError, match="erro de rede"):
        provider.translate([block("X")], PromptContext())


@respx.mock
def test_translate_invalid_json_inside_array_is_transient():
    body = {
        "choices": [{"message": {"content": "[oops]"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }
    respx.post(f"{API}/chat/completions").mock(return_value=httpx.Response(200, json=body))
    provider = make_provider(max_retries=0)

    with pytest.raises(TransientProviderError, match="array JSON invalido"):
        provider.translate([block("X")], PromptContext())


@respx.mock
def test_translate_non_string_item_is_transient():
    body = {
        "choices": [{"message": {"content": "[1, 2]"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }
    respx.post(f"{API}/chat/completions").mock(return_value=httpx.Response(200, json=body))
    provider = make_provider(max_retries=0)

    with pytest.raises(TransientProviderError, match="item nao textual"):
        provider.translate([block("X"), block("Y")], PromptContext())


@respx.mock
def test_translate_accepts_markdown_fenced_json():
    content = '```json\n["Traduzido"]\n```'
    respx.post(f"{API}/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": content}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            },
        )
    )
    provider = make_provider()

    result = provider.translate([block("X")], PromptContext())

    assert result.texts == ("Traduzido",)


@respx.mock
def test_translate_without_usage_defaults_to_zero():
    body = {"choices": [{"message": {"content": '["Traduzido"]'}}]}
    respx.post(f"{API}/chat/completions").mock(return_value=httpx.Response(200, json=body))
    provider = make_provider()

    result = provider.translate([block("X")], PromptContext())

    assert result.usage == Usage(prompt_tokens=0, completion_tokens=0)


@respx.mock
def test_translate_with_partial_usage_defaults_missing_to_zero():
    body = {
        "choices": [{"message": {"content": '["Traduzido"]'}}],
        "usage": {"completion_tokens": 7},
    }
    respx.post(f"{API}/chat/completions").mock(return_value=httpx.Response(200, json=body))
    provider = make_provider()

    result = provider.translate([block("X")], PromptContext())

    assert result.usage == Usage(prompt_tokens=0, completion_tokens=7)


@respx.mock
def test_translate_invalid_usage_is_transient():
    body = {
        "choices": [{"message": {"content": '["Ok"]'}}],
        "usage": {"prompt_tokens": "x", "completion_tokens": 1},
    }
    respx.post(f"{API}/chat/completions").mock(return_value=httpx.Response(200, json=body))
    provider = make_provider(max_retries=0)

    with pytest.raises(TransientProviderError, match="uso de tokens invalido"):
        provider.translate([block("Ok")], PromptContext())


@respx.mock
def test_retry_after_invalid_falls_back_to_jittered_backoff():
    respx.post(f"{API}/chat/completions").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "banana"}),
            httpx.Response(200, json=chat_response(["Ok"])),
        ]
    )
    sleeps = SleepRecorder()
    provider = make_provider(sleep=sleeps, rng=random.Random(1))

    result = provider.translate([block("Ok")], PromptContext())

    assert result.texts == ("Ok",)
    assert 0.0 <= sleeps.calls[0] < 1.0


@respx.mock
def test_retry_after_capped_at_max_delay():
    respx.post(f"{API}/chat/completions").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "3600"}),
            httpx.Response(200, json=chat_response(["Ok"])),
        ]
    )
    sleeps = SleepRecorder()
    provider = make_provider(sleep=sleeps, max_delay=5.0)

    provider.translate([block("Ok")], PromptContext())

    assert sleeps.calls == [5.0]


def test_translate_without_key_raises_definitive():
    provider = make_provider(secret_store=FakeSecretStore(None))

    with pytest.raises(DefinitiveProviderError, match="chave de API nao encontrada"):
        provider.translate([block("X")], PromptContext())


@respx.mock
def test_translate_empty_batch():
    respx.post(f"{API}/chat/completions").mock(
        return_value=httpx.Response(200, json=chat_response([]))
    )
    provider = make_provider()

    result = provider.translate([], PromptContext())

    assert result.texts == ()
    assert result.usage.total_tokens == 8


@respx.mock
def test_prompt_keeps_placeholders_and_context():
    route = respx.post(f"{API}/chat/completions").mock(
        return_value=httpx.Response(200, json=chat_response(["Texto com {{0}}"]))
    )
    context = PromptContext(
        source_language="en",
        target_language="pt-BR",
        policy=TermPolicy.TRADUZIR,
        glossary=(("queue", "fila"),),
        priming="Livro tecnico, tom direto.",
    )
    provider = make_provider()

    result = provider.translate([block("Text with {{0}}")], context)

    assert result.texts == ("Texto com {{0}}",)
    messages = json.loads(route.calls.last.request.content)["messages"]
    system, user = messages[0]["content"], messages[1]["content"]
    assert "queue -> fila" in system
    assert "Livro tecnico" in system
    assert "traduza todos" in system
    assert "{{0}}" in user


@respx.mock
def test_prompt_manter_policy_instruction():
    respx.post(f"{API}/chat/completions").mock(
        return_value=httpx.Response(200, json=chat_response(["X"]))
    )
    provider = make_provider()

    provider.translate([block("X")], PromptContext(policy=TermPolicy.MANTER))

    request = respx.calls.last.request
    system = json.loads(request.content)["messages"][0]["content"]
    assert "mantenha no idioma original" in system


@respx.mock
def test_connection_success_lists_models():
    route = respx.get(f"{API}/models").mock(
        return_value=httpx.Response(
            200,
            json={"data": [{"id": "deepseek-chat"}, {"id": "deepseek-reasoner"}, {"name": "x"}]},
        )
    )
    provider = make_provider()

    result = provider.test_connection()

    assert result == ConnectionResult(
        True, "conexao OK — 2 modelo(s) disponivel(is)", ("deepseek-chat", "deepseek-reasoner")
    )
    assert route.calls.last.request.headers["authorization"] == "Bearer test-key"


@respx.mock
def test_connection_auth_failure_message():
    respx.get(f"{API}/models").mock(return_value=httpx.Response(401))
    provider = make_provider()

    result = provider.test_connection()

    assert result.ok is False
    assert "autenticacao" in result.message
    assert "401" in result.message


@respx.mock
def test_connection_network_error_message():
    respx.get(f"{API}/models").mock(side_effect=httpx.TransportError("boom"))
    provider = make_provider()

    result = provider.test_connection()

    assert result.ok is False
    assert "nao foi possivel conectar" in result.message


@respx.mock
def test_connection_other_http_error_message():
    respx.get(f"{API}/models").mock(return_value=httpx.Response(500))
    provider = make_provider()

    result = provider.test_connection()

    assert result.ok is False
    assert "HTTP 500" in result.message


@respx.mock
def test_connection_ok_without_model_list():
    respx.get(f"{API}/models").mock(return_value=httpx.Response(200, json={}))
    provider = make_provider()

    result = provider.test_connection()

    assert result.ok is True
    assert result.models == ()
    assert "conexao OK" in result.message


@respx.mock
def test_connection_ok_with_non_json_body():
    respx.get(f"{API}/models").mock(return_value=httpx.Response(200, content=b"<html>oops</html>"))
    provider = make_provider()

    result = provider.test_connection()

    assert result.ok is True
    assert result.models == ()
    assert "modelo nao listado" in result.message


@respx.mock
def test_connection_without_key_raises_definitive():
    provider = make_provider(secret_store=FakeSecretStore(None))

    with pytest.raises(DefinitiveProviderError, match="chave de API nao encontrada"):
        provider.test_connection()
