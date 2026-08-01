"""Adapter ``OpenAICompatProvider`` (protocolo de chat completions).

Fala o mesmo protocolo usado por OpenAI, DeepSeek, Ollama, Groq e
OpenRouter: ``POST {base_url}/chat/completions`` com chave Bearer.
Base URL e modelo configuraveis; os defaults apontam para a DeepSeek.
A chave vem da porta ``SecretStore`` — nunca do nucleo do dominio.

O lote e enviado como array JSON e a resposta deve ser um array JSON
na mesma ordem; o adapter valida o formato, conta os itens e expoe o
uso de tokens de cada resposta (relatorio de custo da secao 7).
"""

from __future__ import annotations

import json
import random
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import httpx

from tradutor.domain import Block, PromptContext, SecretStore, TermPolicy, TranslationBatch, Usage
from tradutor.providers.errors import (
    AuthenticationError,
    DefinitiveProviderError,
    TransientProviderError,
)

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_KEY_NAME = "DEEPSEEK_API_KEY"

_TRANSIENT_STATUS = (429, *range(500, 600))


@dataclass(frozen=True, slots=True)
class ConnectionResult:
    """Resultado do teste de conexao, com mensagem pronta para a interface."""

    ok: bool
    message: str
    models: tuple[str, ...] = ()


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After")
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _parse_usage(data: dict[str, Any]) -> Usage:
    raw = data.get("usage")
    if not isinstance(raw, dict):
        return Usage(0, 0)
    try:
        return Usage(
            prompt_tokens=int(raw.get("prompt_tokens", 0)),
            completion_tokens=int(raw.get("completion_tokens", 0)),
        )
    except (TypeError, ValueError) as exc:
        raise TransientProviderError("uso de tokens invalido na resposta da API") from exc


def _extract_models(response: httpx.Response) -> tuple[str, ...]:
    try:
        payload = response.json()
    except json.JSONDecodeError:
        return ()
    data = payload.get("data")
    if not isinstance(data, list):
        return ()
    return tuple(str(item["id"]) for item in data if isinstance(item, dict) and "id" in item)


class OpenAICompatProvider:
    """Traduz lotes de blocos via API de chat completions OpenAI-compativel."""

    def __init__(
        self,
        secret_store: SecretStore,
        *,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        key_name: str = DEFAULT_KEY_NAME,
        http_client: httpx.Client | None = None,
        max_retries: int = 4,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        timeout: float = 60.0,
        sleep: Callable[[float], None] = time.sleep,
        rng: random.Random | None = None,
    ) -> None:
        self._secret_store = secret_store
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._key_name = key_name
        self._client = http_client if http_client is not None else httpx.Client(timeout=timeout)
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._sleep = sleep
        self._rng = rng if rng is not None else random.Random()

    def translate(self, batch: Sequence[Block], context: PromptContext) -> TranslationBatch:
        messages = self._messages(batch, context)
        key = self._resolve_key()
        last_error: TransientProviderError | None = None
        for attempt in range(self._max_retries + 1):
            try:
                data = self._chat(messages, key)
                return self._parse(data, len(batch))
            except TransientProviderError as exc:
                last_error = exc
                if attempt < self._max_retries:
                    self._sleep(self._backoff_delay(attempt, exc.retry_after))
        raise TransientProviderError(
            f"esgotadas {self._max_retries + 1} tentativas de traducao: {last_error}"
        ) from last_error

    def test_connection(self) -> ConnectionResult:
        """Verifica chave, base URL e modelo antes de traduzir."""
        key = self._resolve_key()
        headers = {"Authorization": f"Bearer {key}"}
        try:
            response = self._client.get(f"{self.base_url}/models", headers=headers)
        except httpx.TransportError as exc:
            return ConnectionResult(False, f"nao foi possivel conectar em {self.base_url}: {exc}")
        if response.status_code == 200:
            models = _extract_models(response)
            if models:
                message = f"conexao OK — {len(models)} modelo(s) disponivel(is)"
            else:
                message = "conexao OK — modelo nao listado pela API"
            return ConnectionResult(True, message, models)
        if response.status_code in (401, 403):
            return ConnectionResult(
                False,
                f"falha de autenticacao (HTTP {response.status_code}): verifique a chave da API",
            )
        return ConnectionResult(False, f"erro ao listar modelos (HTTP {response.status_code})")

    def _chat(self, messages: list[dict[str, str]], key: str) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {key}"}
        body: dict[str, Any] = {"model": self.model, "messages": messages}
        try:
            response = self._client.post(
                f"{self.base_url}/chat/completions", headers=headers, json=body
            )
        except httpx.TimeoutException as exc:
            raise TransientProviderError(
                f"timeout ao falar com {self.base_url} ({self.model})"
            ) from exc
        except httpx.TransportError as exc:
            raise TransientProviderError(f"erro de rede ao falar com {self.base_url}") from exc
        return self._classify(response)

    def _classify(self, response: httpx.Response) -> dict[str, Any]:
        if response.status_code in _TRANSIENT_STATUS:
            raise TransientProviderError(
                f"erro transitorio HTTP {response.status_code}",
                retry_after=_retry_after(response),
            )
        if response.status_code in (401, 403):
            raise AuthenticationError(
                f"autenticacao falhou (HTTP {response.status_code}): chave invalida "
                "ou sem permissao"
            )
        if response.status_code >= 400:
            raise DefinitiveProviderError(f"erro HTTP {response.status_code}")
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise TransientProviderError("resposta da API nao e JSON valido") from exc

    def _backoff_delay(self, attempt: int, retry_after: float | None) -> float:
        if retry_after is not None:
            return min(retry_after, self._max_delay)
        delay = min(self._max_delay, self._base_delay * (2**attempt))
        return self._rng.uniform(0.0, delay)

    def _resolve_key(self) -> str:
        key = self._secret_store.get(self._key_name)
        if not key:
            raise DefinitiveProviderError(
                f"chave de API nao encontrada ({self._key_name}); configure a chave "
                "antes de traduzir"
            )
        return key

    def _messages(self, batch: Sequence[Block], context: PromptContext) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self._system_prompt(context)},
            {"role": "user", "content": self._user_prompt(batch, context)},
        ]

    def _system_prompt(self, context: PromptContext) -> str:
        parts = [
            "Voce e um tradutor profissional de livros (EPUB). Traduza com "
            "naturalidade, como um livro publicado: sem marcas de IA, colchetes, "
            "notas ou rotulos.",
            f"Traduza do idioma {context.source_language} para o idioma "
            f"{context.target_language}. Preserve os placeholders {{N}} exatamente "
            "como estao.",
        ]
        if context.priming:
            parts.append(f"Estilo e tom do livro:\n{context.priming}")
        if context.glossary:
            entries = "\n".join(f"- {source} -> {target}" for source, target in context.glossary)
            parts.append(f"Glossario obrigatorio, use exatamente estas traducoes:\n{entries}")
        parts.append(self._policy_instruction(context.policy))
        return "\n\n".join(parts)

    def _user_prompt(self, batch: Sequence[Block], context: PromptContext) -> str:
        items = [block.text for block in batch]
        payload = json.dumps(items, ensure_ascii=False)
        return (
            f"Traduza cada item do JSON abaixo para o idioma {context.target_language}. "
            "Responda APENAS com um array JSON com as traducoes na MESMA ordem do "
            "original, sem texto adicional e sem explicacoes. Cada item pode conter "
            "multiplos paragrafos — preserve essa estrutura.\n" + payload
        )

    def _policy_instruction(self, policy: TermPolicy) -> str:
        if policy is TermPolicy.TRADUZIR:
            return "Termos tecnicos: traduza todos para o idioma de destino."
        if policy is TermPolicy.MANTER:
            return "Termos tecnicos: mantenha no idioma original."
        return (
            "Termos tecnicos: na primeira ocorrencia, traduza e acrescente o termo "
            "original entre parenteses; nas demais, use apenas a traducao."
        )

    def _parse(self, data: dict[str, Any], expected: int) -> TranslationBatch:
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise TransientProviderError("resposta da API sem conteudo de traducao") from exc
        if not isinstance(content, str):
            raise TransientProviderError("conteudo da resposta nao e texto")
        texts = self._extract_texts(content, expected)
        return TranslationBatch(texts=texts, usage=_parse_usage(data))

    def _extract_texts(self, content: str, expected: int) -> tuple[str, ...]:
        start = content.find("[")
        end = content.rfind("]")
        if start == -1 or end == -1 or end <= start:
            raise TransientProviderError("resposta sem array JSON de traducoes")
        try:
            parsed = json.loads(content[start : end + 1])
        except json.JSONDecodeError as exc:
            raise TransientProviderError("resposta com array JSON invalido") from exc
        if len(parsed) != expected:
            raise TransientProviderError(f"resposta com {len(parsed)} itens; esperado {expected}")
        if not all(isinstance(item, str) for item in parsed):
            raise TransientProviderError("resposta com item nao textual")
        return tuple(parsed)
