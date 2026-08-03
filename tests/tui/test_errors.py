"""Testes das mensagens de erro acionaveis em pt-BR (tarefa 9.6).

Cada excecao conhecida produz titulo e orientacao claros; nenhuma
mensagem contem segredos ou detalhes tecnicos de baixo nivel.
"""

from __future__ import annotations

import pytest

from tradutor.epub.errors import DrmError, MalformedEpubError, NotEpubError
from tradutor.infra.config import ConfigError
from tradutor.providers.errors import (
    AuthenticationError,
    DefinitiveProviderError,
    ProviderError,
    TransientProviderError,
)
from tradutor.translate.orchestrator import SpendingLimitExceeded, TranslationQualityError
from tradutor.tui.errors import friendly_error


def test_drm_error():
    title, message = friendly_error(DrmError("protegido"))

    assert title == "Livro protegido por DRM"
    assert "DRM" in message
    assert "copia sem DRM" in message


def test_not_epub_error():
    title, message = friendly_error(NotEpubError("nao e zip"))

    assert title == "Arquivo invalido"
    assert ".epub" in message


def test_malformed_epub_error():
    title, message = friendly_error(MalformedEpubError("mimetype ausente"))

    assert title == "EPUB com problemas"
    assert "mimetype ausente" in message


def test_authentication_error():
    title, message = friendly_error(AuthenticationError("HTTP 401"))

    assert title == "Chave de API invalida"
    assert "401/403" in message


def test_missing_key_error():
    title, message = friendly_error(
        DefinitiveProviderError("chave de API nao encontrada (DEEPSEEK_API_KEY)")
    )

    assert title == "Chave de API ausente"
    assert "configuracao" in message


def test_other_definitive_error():
    error = DefinitiveProviderError("erro HTTP 400")

    title, message = friendly_error(error)

    assert title == "Falha no provider"
    assert "erro HTTP 400" in message


def test_transient_error():
    title, message = friendly_error(TransientProviderError("timeout"))

    assert title == "Falha de rede"
    assert "retomada" in message


def test_transient_error_shows_cause():
    title, message = friendly_error(
        TransientProviderError(
            "esgotadas 5 tentativas de traducao: resposta com array JSON invalido"
        )
    )

    assert title == "Falha de rede"
    assert "array JSON invalido" in message


def test_rate_limit_error_suggests_lower_parallelism():
    title, message = friendly_error(
        TransientProviderError("esgotadas 5 tentativas de traducao: erro transitorio HTTP 429")
    )

    assert title == "Limite de requisicoes do provider"
    assert "paralelismo" in message
    assert "retome" in message


def test_quality_error_suggests_resume():
    title, message = friendly_error(
        TranslationQualityError("resposta reprovada na verificacao de qualidade (tentativa 3)")
    )

    assert title == "Lote reprovado no controle de qualidade"
    assert "Retome" in message


def test_spending_limit_exceeded():
    error = SpendingLimitExceeded("teto de gasto atingido: US$ 5.00")

    title, message = friendly_error(error)

    assert title == "Teto de gasto atingido"
    assert "spending_limit_usd" in message


def test_config_error():
    title, message = friendly_error(ConfigError("campo 'cost.x' invalido"))

    assert title == "Configuracao invalida"
    assert "cost.x" in message


def test_generic_provider_error():
    title, message = friendly_error(ProviderError("falha interna"))

    assert title == "Falha ao processar o livro"
    assert "falha interna" in message


def test_unknown_error_falls_back():
    title, message = friendly_error(RuntimeError("segredo=abc123"))

    assert title == "Erro inesperado"
    assert "abc123" not in message
    assert "segredo" not in message


@pytest.mark.parametrize(
    "error",
    [
        DrmError("x"),
        AuthenticationError("x"),
        DefinitiveProviderError("x"),
        TransientProviderError("x"),
        SpendingLimitExceeded("x"),
        TranslationQualityError("x"),
        ConfigError("x"),
        RuntimeError("x"),
    ],
)
def test_messages_never_expose_secrets(error):
    title, message = friendly_error(error)
    text = f"{title} {message}".lower()

    assert "api_key" not in text.replace("_", " ")
    assert "sk-" not in text
