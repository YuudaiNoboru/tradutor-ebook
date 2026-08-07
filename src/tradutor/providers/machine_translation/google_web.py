"""Adapter experimental do Google Web, sem credencial do usuário.

Os endpoints pertencem à interface web, não à API oficial. Por isso o perfil
de transporte e o parser são explícitos e entram na identidade do cache.
"""

from __future__ import annotations

import json
import random
import time
from collections.abc import Callable, Sequence
from typing import Any

import httpx

from tradutor.domain import (
    Block,
    MachineTranslationContext,
    ProviderCapabilities,
    ProviderDescription,
    ProviderFamily,
    ProviderIdentity,
    ProviderStability,
    TranslationBatch,
    Usage,
    clean_placeholders,
    is_faithful,
    is_formatting_faithful,
    mask_markup,
    unmask_markup,
)
from tradutor.providers.errors import DefinitiveProviderError, TransientProviderError

HTML_ENDPOINT = "https://translate-pa.googleapis.com/v1/translateHtml"
TEXT_ENDPOINT = "https://translate.googleapis.com/translate_a/t"
DEFAULT_USER_AGENT = "tradutor-ebook/experimental (EPUB translator)"
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
)
TEXT_CLIENT = "gtx"
WEB_PUBLIC_KEY = "AIzaSyATBXajvzQLTDHEQbcpq0Ihe0vWDHmO520"
PARSER_VERSION = "html-v2/text-v6"


class GoogleWebResponseError(DefinitiveProviderError):
    """Resposta incompatível ou bloqueio persistente do endpoint web."""


def _retry_after(response: httpx.Response) -> float | None:
    try:
        return float(response.headers.get("Retry-After", ""))
    except (TypeError, ValueError):
        return None


class GoogleWebProvider:
    """Traduz blocos XHTML usando um perfil HTML e fallback textual seguro."""

    identity = ProviderIdentity(
        ProviderFamily.MACHINE_TRANSLATION, "google-web", "1", PARSER_VERSION
    )
    capabilities = ProviderCapabilities(
        family=ProviderFamily.MACHINE_TRANSLATION,
        supports_html=True,
        requires_credentials=False,
        stability=ProviderStability.UNOFFICIAL,
        max_batch_chars=5000,
        max_batch_items=8,
        max_concurrency=1,
        delay_seconds=0.25,
        reports_token_usage=False,
        reports_character_usage=True,
        supports_model_listing=False,
        supports_connection_test=True,
        experimental=True,
        has_pricing=False,
    )

    def __init__(
        self,
        *,
        http_client: httpx.Client | None = None,
        html_endpoint: str = HTML_ENDPOINT,
        text_endpoint: str = TEXT_ENDPOINT,
        public_key: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        delay_seconds: float | None = None,
        sleep: Callable[[float], None] = time.sleep,
        rng: random.Random | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout deve ser positivo")
        if max_retries < 0:
            raise ValueError("max_retries não pode ser negativo")
        self.html_endpoint = html_endpoint
        self.text_endpoint = text_endpoint
        self.public_key = public_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.delay_seconds = (
            self.capabilities.delay_seconds if delay_seconds is None else delay_seconds
        )
        if self.delay_seconds < 0:
            raise ValueError("delay_seconds não pode ser negativo")
        self._client = http_client or httpx.Client(timeout=timeout)
        self._sleep = sleep
        self._rng = rng or random.Random()
        self._user_agent = user_agent
        self._last_request = 0.0
        self._html_unavailable = False

    def translate(
        self, batch: Sequence[Block], context: MachineTranslationContext
    ) -> TranslationBatch:
        if not batch:
            return TranslationBatch((), Usage(None, None, 0, 0))
        if any(block.protected for block in batch):
            raise DefinitiveProviderError("blocos protegidos não podem ser enviados ao Google Web")
        groups = self._split_batch(batch)
        texts: list[str] = []
        for group in groups:
            translated = self._translate_group(group, context)
            cleaned_group: list[str] = []
            for block, text in zip(group, translated, strict=True):
                c_text = clean_placeholders(text)
                if not c_text.strip() or not is_faithful(block.text, c_text):
                    raise GoogleWebResponseError(
                        f"resposta alterou placeholder do bloco {block.id}"
                    )
                cleaned_group.append(c_text)
            texts.extend(cleaned_group)
        return TranslationBatch(
            tuple(texts),
            Usage(None, None, sum(len(block.text) for block in batch), len(batch)),
        )

    def test_connection(self) -> Any:
        """Verifica os endpoints sem exigir chave ou listar modelos."""

        html_ok, html_message = self._probe_html()
        if html_ok:
            return _ConnectionResult(True, f"{html_message} (sem listagem de modelos)")
        text_ok, text_message = self._probe_text()
        if text_ok:
            return _ConnectionResult(
                True, f"{html_message}; {text_message} (sem listagem de modelos)"
            )
        return _ConnectionResult(False, f"{html_message}; {text_message}")

    def _probe_html(self) -> tuple[bool, str]:
        try:
            response = self._client.post(
                self.html_endpoint,
                headers=self._html_headers(),
                content=json.dumps([[["ok"], "en", "pt-BR"], "wt_lib"]),
            )
        except httpx.TransportError as exc:
            return False, f"não foi possível conectar ao endpoint HTML: {exc}"
        if response.status_code in (200, 400, 405):
            return True, "endpoint HTML acessível"
        if response.status_code in (429, *range(500, 600)):
            return False, (
                f"endpoint HTML temporariamente indisponível (HTTP {response.status_code})"
            )
        return False, f"endpoint HTML recusou a conexão (HTTP {response.status_code})"

    def _probe_text(self) -> tuple[bool, str]:
        try:
            response = self._client.get(
                self.text_endpoint,
                headers=self._headers(),
                params=[
                    ("client", TEXT_CLIENT),
                    ("sl", "en"),
                    ("tl", "pt-BR"),
                    ("dt", "t"),
                    ("q", "ok"),
                ],
            )
        except httpx.TransportError as exc:
            return False, f"fallback textual inacessível: {exc}"
        if response.status_code == 200:
            return True, "fallback textual acessível"
        return False, f"fallback textual indisponível (HTTP {response.status_code})"

    def _split_batch(self, batch: Sequence[Block]) -> list[list[Block]]:
        max_items = self.capabilities.max_batch_items or len(batch)
        max_chars = self.capabilities.max_batch_chars or sum(len(item.text) for item in batch)
        groups: list[list[Block]] = []
        current: list[Block] = []
        chars = 0
        for block in batch:
            size = len(block.text)
            if size > max_chars:
                raise DefinitiveProviderError(
                    f"bloco {block.id} excede o limite de {max_chars} caracteres do Google Web"
                )
            if current and (len(current) >= max_items or chars + size > max_chars):
                groups.append(current)
                current, chars = [], 0
            current.append(block)
            chars += size
        if current:
            groups.append(current)
        return groups

    def _translate_group(
        self, batch: Sequence[Block], context: MachineTranslationContext
    ) -> list[str]:
        self._respect_delay()
        if not self._html_unavailable:
            try:
                response = self._request_html(batch, context)
                translated = self._parse_html(response, len(batch))
                if all(
                    bool(clean_placeholders(text).strip())
                    and is_formatting_faithful(block.text, clean_placeholders(text))
                    for block, text in zip(batch, translated, strict=True)
                ):
                    return translated
                self._html_unavailable = True
            except GoogleWebResponseError:
                self._html_unavailable = True
            except TransientProviderError:
                pass
        try:
            masked = [mask_markup(block.text) for block in batch]
            response = self._request_text([text for text, _, _ in masked], context)
            translated = self._parse_text(response, len(batch))
            return [
                unmask_markup(text, tags, empties)
                for text, (_, tags, empties) in zip(translated, masked, strict=True)
            ]
        except TransientProviderError:
            raise
        except GoogleWebResponseError as text_error:
            raise GoogleWebResponseError(
                f"Google Web não retornou tradução compatível: {text_error}"
            ) from text_error

    def _request_html(
        self, batch: Sequence[Block], context: MachineTranslationContext
    ) -> httpx.Response:
        body = json.dumps(
            [
                [[block.text for block in batch], context.source_language, context.target_language],
                "wt_lib",
            ]
        )
        return self._request_with_retry(
            self.html_endpoint, content=body, extra_headers=self._html_headers()
        )

    def _request_text(
        self, texts: Sequence[str], context: MachineTranslationContext
    ) -> httpx.Response:
        params: list[tuple[str, str]] = [
            ("client", TEXT_CLIENT),
            ("sl", context.source_language),
            ("tl", context.target_language),
            ("dt", "t"),
        ]
        params.extend(("q", text) for text in texts)
        return self._request_with_retry(self.text_endpoint, params=params)

    def _request_with_retry(
        self,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: list[tuple[str, str]] | None = None,
        content: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        headers = self._headers() if extra_headers is None else extra_headers
        last: TransientProviderError | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.post(
                    url, headers=headers, json=json_body, params=params, content=content
                )
            except httpx.TimeoutException:
                last = TransientProviderError("timeout no endpoint Google Web")
            except httpx.TransportError:
                last = TransientProviderError("erro de rede no endpoint Google Web")
            else:
                if response.status_code in (429, *range(500, 600)):
                    last = TransientProviderError(
                        f"falha transitória do Google Web (HTTP {response.status_code})",
                        retry_after=_retry_after(response),
                    )
                elif response.status_code >= 400:
                    raise GoogleWebResponseError(
                        f"Google Web recusou a requisição (HTTP {response.status_code})"
                    )
                else:
                    return response
            if attempt < self.max_retries:
                self._sleep(self._backoff(attempt, last.retry_after if last else None))
        raise TransientProviderError(
            f"esgotadas {self.max_retries + 1} tentativas no Google Web: {last}"
        ) from last

    def _parse_html(self, response: httpx.Response, expected: int) -> list[str]:
        try:
            data = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise GoogleWebResponseError("resposta HTML em JSON inválido") from exc
        if isinstance(data, list) and data and isinstance(data[0], list):
            values = list(data[0])
        else:
            values = _find_translations(data)
        if len(values) != expected or any(
            not isinstance(item, str) or not item.strip() for item in values
        ):
            raise GoogleWebResponseError(
                f"resposta HTML desalinhada: {len(values)} item(ns), esperado {expected}"
            )
        return values

    def _parse_text(self, response: httpx.Response, expected: int) -> list[str]:
        try:
            values = _find_translations(response.json())
        except (ValueError, json.JSONDecodeError) as exc:
            raise GoogleWebResponseError("resposta textual não é JSON válido") from exc
        if len(values) != expected or any(
            not isinstance(item, str) or not item.strip() for item in values
        ):
            raise GoogleWebResponseError(
                f"fallback textual desalinhado: {len(values)} item(ns), esperado {expected}"
            )
        return values

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": self._user_agent, "Accept": "application/json, text/html"}

    def _html_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json+protobuf",
            "X-Goog-Api-Key": self.public_key or WEB_PUBLIC_KEY,
            "User-Agent": BROWSER_USER_AGENT,
        }

    def _respect_delay(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if self._last_request and elapsed < self.delay_seconds:
            self._sleep(self.delay_seconds - elapsed)
        self._last_request = time.monotonic()

    def _backoff(self, attempt: int, retry_after: float | None) -> float:
        if retry_after is not None:
            return min(self.max_delay, max(0.0, retry_after))
        ceiling = min(self.max_delay, self.base_delay * 2**attempt)
        return self._rng.uniform(0.0, ceiling)


def _find_translations(value: Any) -> list[str]:
    if isinstance(value, dict):
        for key in ("translations", "translation", "data", "results"):
            if key in value:
                found = _find_translations(value[key])
                if found:
                    return found
        for key in ("translatedText", "translated", "text", "translationText"):
            if isinstance(value.get(key), str):
                return [value[key]]
    if isinstance(value, list):
        if all(isinstance(item, str) for item in value):
            return list(value)
        values: list[str] = []
        for item in value:
            if isinstance(item, dict):
                values.extend(_find_translations(item))
            elif isinstance(item, list) and item and isinstance(item[0], list):
                values.append(str(item[0][0]))
            elif isinstance(item, list) and item and isinstance(item[0], str):
                values.append(item[0])
        return values
    return []


class _ConnectionResult:
    def __init__(self, ok: bool, message: str) -> None:
        self.ok = ok
        self.message = message
        self.models: tuple[str, ...] = ()


def create_provider(**kwargs):
    return GoogleWebProvider(**kwargs)


DESCRIPTION = ProviderDescription(
    identity=GoogleWebProvider.identity,
    capabilities=GoogleWebProvider.capabilities,
    display_name="Google Web (experimental)",
    description="Tradução automática via endpoint HTML da interface web.",
    experimental_warning=(
        "Endpoint não oficial, sem chave do usuário, sujeito a limites, bloqueios "
        "e mudanças sem aviso; não oferece glossário, priming ou custo mensurável."
    ),
)
