"""Provider OpenAI-compatível baseado no protocolo de chat completions.

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
import logging
import random
import time
from collections.abc import Callable, Sequence
from typing import Any, cast

import httpx

from tradutor.domain import (
    Block,
    PassadaTask,
    PromptContext,
    ProviderCapabilities,
    ProviderDescription,
    ProviderFamily,
    ProviderIdentity,
    SecretStore,
    TermPolicy,
    TranslationBatch,
    Usage,
)
from tradutor.providers.discovery import ConnectionResult
from tradutor.providers.errors import (
    AuthenticationError,
    DefinitiveProviderError,
    TransientProviderError,
)

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_KEY_NAME = "DEEPSEEK_API_KEY"
DEFAULT_MAX_OUTPUT_TOKENS = 8192
DEFAULT_LATENCY_SECONDS = 90.0

_TRANSIENT_STATUS = (429, *range(500, 600))

# Passadas de qualidade nao tem correspondencia 1:1 com o lote: o modelo
# pode devolver varias entradas (glossario) e a quantidade nao e exigida.
_LENIENT_COUNT_TASKS = (PassadaTask.GLOSSARIO, PassadaTask.PRIMING)


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

    capabilities: ProviderCapabilities = ProviderCapabilities(
        family=ProviderFamily.LLM,
        supports_glossary=True,
        supports_priming=True,
        supports_term_policy=True,
        supports_html=True,
        requires_credentials=True,
        max_batch_items=32,
        max_concurrency=20,
        latency_seconds=DEFAULT_LATENCY_SECONDS,
        max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
        reports_token_usage=True,
        supports_model_listing=True,
        has_pricing=True,
    )

    @property
    def identity(self) -> ProviderIdentity:
        provider_id = "deepseek" if self.base_url == DEFAULT_BASE_URL else "openai-compatible"
        return ProviderIdentity(ProviderFamily.LLM, provider_id, "1", "openai-chat")

    def __init__(
        self,
        secret_store: SecretStore,
        *,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        key_name: str = DEFAULT_KEY_NAME,
        http_client: httpx.Client | None = None,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 15.0,
        timeout: float = 45.0,
        max_output_tokens: int | None = DEFAULT_MAX_OUTPUT_TOKENS,
        thinking: bool | None = None,
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
        self._max_output_tokens = max_output_tokens
        self._thinking = thinking
        self._sleep = sleep
        self._rng = rng if rng is not None else random.Random()

    def translate(self, batch: Sequence[Block], context: PromptContext) -> TranslationBatch:
        messages = self._messages(batch, context)
        key = self._resolve_key()
        last_error: TransientProviderError | None = None
        expected = None if context.task in _LENIENT_COUNT_TASKS else len(batch)
        for attempt in range(self._max_retries + 1):
            try:
                data = self._chat(messages, key)
                return self._parse(data, expected)
            except TransientProviderError as exc:
                last_error = exc
                if attempt < self._max_retries:
                    delay = self._backoff_delay(attempt, exc.retry_after)
                    logger.warning(
                        "retry %d/%d: %s; backoff de %.1fs%s",
                        attempt + 1,
                        self._max_retries,
                        exc,
                        delay,
                        " (via Retry-After)" if exc.retry_after is not None else "",
                    )
                    self._sleep(delay)
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
        if response.status_code in (404, 405, 501):
            return ConnectionResult(
                True,
                f"conexao OK — rota de modelos indisponivel (HTTP {response.status_code})",
                (),
            )
        return ConnectionResult(False, f"erro ao listar modelos (HTTP {response.status_code})")

    def _chat(self, messages: list[dict[str, str]], key: str) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {key}"}
        body: dict[str, Any] = {"model": self.model, "messages": messages}
        if self._max_output_tokens is not None:
            body["max_tokens"] = self._max_output_tokens
        if self._thinking is not None:
            body["thinking"] = {"type": "enabled" if self._thinking else "disabled"}
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
            return cast(dict[str, Any], response.json())
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
        if context.task is PassadaTask.GLOSSARIO:
            return self._glossary_system_prompt(context)
        if context.task is PassadaTask.PRIMING:
            return self._priming_system_prompt(context)
        parts = [
            "Voce e um tradutor profissional de livros (EPUB). Traduza com "
            "naturalidade, como um livro publicado: sem marcas de IA, colchetes, "
            "notas ou rotulos.",
            f"Traduza do idioma {context.source_language} para o idioma "
            f"{context.target_language}. REGRA CRITICA: Preserve e reproduza TODAS as "
            'tags HTML/XHTML inline (especialmente tags de hiperlink <a href="...">...</a>, '
            "<em>, <strong>, <small>, <span>, <br/>) e TODOS os placeholders {{N}} (ex.: {{0}}, {{1}}) "
            "exatamente como estao, sem espacos internos (ex.: {{0}}, nao {{ 0 }}). "
            "NUNCA omita, remova ou altere nenhum placeholder ou tag. "
            'Ao traduzir texto dentro de links <a href="...">...</a> (como em sumarios ou citacoes), '
            'MANTENHA SEMPRE a tag <a href="..."> ao redor do texto traduzido.',
        ]
        if context.priming:
            parts.append(f"Estilo e tom do livro:\n{context.priming}")
        if context.glossary:
            entries = "\n".join(f"- {source} -> {target}" for source, target in context.glossary)
            parts.append(f"Glossario obrigatorio, use exatamente estas traducoes:\n{entries}")
        parts.append(self._policy_instruction(context.policy))
        return "\n\n".join(parts)

    def _glossary_system_prompt(self, context: PromptContext) -> str:
        return (
            "Voce e um lexicografo. Extraia do texto do livro os termos tecnicos, "
            "jargoes e nomes proprios relevantes para uma traducao consistente. "
            "Para cada termo, proponha uma traducao natural para o idioma "
            f"{context.target_language}. Responda APENAS com um array JSON "
            "contendo um unico item: uma string com uma entrada por linha no "
            "formato 'termo original -> traducao'. Nao adicione texto fora do array."
        )

    def _priming_system_prompt(self, context: PromptContext) -> str:
        return (
            "Voce e um editor literario. Analise o texto do livro e escreva um "
            "resumo de 3 a 6 frases sobre o estilo e o tom da escrita (formal ou "
            "informal, vocabulario, ritmo, publico-alvo, caracteristicas "
            "marcantes), para guiar uma traducao consistente. Responda APENAS com "
            "um array JSON contendo um unico item: o resumo escrito no idioma "
            f"{context.target_language}. Nao adicione texto fora do array."
        )

    def _user_prompt(self, batch: Sequence[Block], context: PromptContext) -> str:
        items = [block.text for block in batch]
        payload = json.dumps(items, ensure_ascii=False)
        if context.task is PassadaTask.GLOSSARIO:
            return f"Amostra do livro (capitulos iniciais):\n{payload}"
        if context.task is PassadaTask.PRIMING:
            return f"Amostra do livro (capitulos iniciais):\n{payload}"
        return (
            f"Traduza cada item do JSON abaixo para o idioma {context.target_language}. "
            "Responda APENAS com um array JSON com as traducoes na MESMA ordem do "
            "original, sem texto adicional e sem explicacoes. Cada item pode conter "
            'multiplos paragrafos ou tags de link <a href="..."> — preserve toda a estrutura e tags.\n'
            + payload
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

    def _parse(self, data: dict[str, Any], expected: int | None) -> TranslationBatch:
        try:
            choice = data["choices"][0]
            message = choice["message"]
            content = message.get("content") or ""
            reasoning = message.get("reasoning_content") or ""
            finish_reason = choice.get("finish_reason")
        except (KeyError, IndexError, TypeError) as exc:
            raise TransientProviderError(
                f"resposta da API sem conteudo de traducao (JSON recebido: {data!r})"
            ) from exc

        # Se content vier vazio mas houver reasoning_content, tentamos usá-lo como fallback
        if not content and reasoning:
            logger.warning(
                "Campo 'content' vazio, tentando extrair do 'reasoning_content' de raciocinio."
            )
            content = reasoning

        # Verifica finish_reason para diagnósticos específicos
        if finish_reason == "content_filter":
            raise DefinitiveProviderError(
                "requisicao bloqueada pelos filtros de moderacao/seguranca do provedor (content_filter)"
            )
        elif finish_reason == "length":
            raise TransientProviderError(
                "resposta interrompida ao atingir o limite de tokens de saida (length)"
            )
        elif finish_reason == "insufficient_system_resource":
            raise TransientProviderError(
                "requisicao interrompida por falta de recursos no servidor do provedor (insufficient_system_resource)"
            )

        if not isinstance(content, str):
            raise TransientProviderError(
                f"conteudo da resposta nao e texto (tipo: {type(content).__name__})"
            )

        try:
            texts = self._extract_texts(content, expected)
        except TransientProviderError as exc:
            # Se falhar a extração, anexamos o JSON de resposta completo para diagnóstico detalhado no log
            logger.error("Falha ao extrair JSON da resposta. Payload completo da API: %r", data)
            raise TransientProviderError(
                f"{exc} (payload completo no log de erros; finish_reason: {finish_reason!r})"
            ) from exc

        return TranslationBatch(texts=texts, usage=_parse_usage(data))

    def _extract_texts(self, content: str, expected: int | None) -> tuple[str, ...]:
        import re

        # Remove blocos de raciocínio (<think>...</think> ou <thought>...</thought>) de forma case-insensitive e multi-linha.
        clean_content = re.sub(r"(?is)<(think|thought)>.*?</\1>", "", content)

        starts = [i for i, char in enumerate(clean_content) if char == "["]
        ends = [i for i, char in enumerate(clean_content) if char == "]"]

        parsed = None
        parsed_sintatico = None
        last_json_exc = None

        for start in starts:
            valid_ends = [end for end in ends if end > start]
            for end in reversed(valid_ends):
                substring = clean_content[start : end + 1]
                try:
                    data = json.loads(substring)
                    if isinstance(data, list):
                        # Guardamos o primeiro array JSON sintaticamente válido que encontrarmos
                        if parsed_sintatico is None:
                            parsed_sintatico = data

                        # Garante que todos os itens do array sejam strings
                        if not all(isinstance(item, str) for item in data):
                            continue
                        # Garante correspondência de tamanho com o esperado, se fornecido
                        if expected is not None and len(data) != expected:
                            continue
                        parsed = data
                        break
                except json.JSONDecodeError as exc:
                    last_json_exc = exc
            if parsed is not None:
                break

        if parsed is None:
            # Se encontramos algum array JSON válido sintaticamente, usamos ele para as validações específicas
            if parsed_sintatico is not None:
                parsed = parsed_sintatico
            else:
                # Geramos uma amostra segura do conteúdo original recebido para auxiliar no diagnóstico técnico
                sample = content[:300] + "..." + content[-300:] if len(content) > 600 else content
                # Logamos o erro de forma detalhada no sistema de logs
                logger.error(
                    "Falha ao extrair JSON da resposta do provedor. Conteudo recebido: %r", content
                )

                # Se não houver colchetes na string limpa
                if not starts or not ends:
                    raise TransientProviderError(
                        f"resposta sem array JSON de traducoes (amostra do conteudo: {sample!r})"
                    )

                # Se havia colchetes mas falhou o parsing de todos os blocos tentados
                raise TransientProviderError(
                    f"resposta com array JSON invalido (amostra do conteudo: {sample!r})"
                ) from last_json_exc

        if expected is None and not parsed:
            raise TransientProviderError("resposta com array JSON vazio")
        # As checagens de validação finais garantem que levantamos as exceções específicas e corretas
        if expected is not None and len(parsed) != expected:
            raise TransientProviderError(f"resposta com {len(parsed)} itens; esperado {expected}")
        if not all(isinstance(item, str) for item in parsed):
            raise TransientProviderError("resposta com item nao textual")
        return tuple(parsed)


# Metadados expostos pelo adapter e pelo módulo descobrível.

DESCRIPTION = ProviderDescription(
    identity=ProviderIdentity(ProviderFamily.LLM, "openai-compatible", "1", "openai-chat"),
    capabilities=ProviderCapabilities(
        family=ProviderFamily.LLM,
        supports_glossary=True,
        supports_priming=True,
        supports_term_policy=True,
        supports_html=True,
        requires_credentials=True,
        max_batch_items=32,
        max_concurrency=20,
        reports_token_usage=True,
        supports_model_listing=True,
        has_pricing=False,
    ),
    display_name="OpenAI compatível",
    description="Provider para APIs compatíveis com o protocolo OpenAI.",
)


def create_provider(secret_store: SecretStore, **kwargs: Any) -> OpenAICompatProvider:
    """Cria o adapter compartilhado sem colocar segredos na configuração."""

    return OpenAICompatProvider(secret_store, **kwargs)
