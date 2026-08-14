"""Mensagens de erro acionaveis em pt-BR para a TUI (tarefa 9.6).

Cada excecao conhecida do dominio/provedores/config vira um par
``(titulo, orientacao)``: o titulo resume o problema e a orientacao diz
o que fazer. Erros desconhecidos caem em um generico sem expor detalhes
tecnicos. Nenhuma mensagem contem chaves ou segredos.
"""

from __future__ import annotations

import traceback
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from platformdirs import user_log_dir

from tradutor.epub.errors import DrmError, EpubError, MalformedEpubError, NotEpubError
from tradutor.infra.config import APP_DIR, ConfigError
from tradutor.infra.redact import redact
from tradutor.providers.errors import (
    AuthenticationError,
    DefinitiveProviderError,
    ProviderError,
    TransientProviderError,
)
from tradutor.translate.orchestrator import SpendingLimitExceeded, TranslationQualityError

KEY_MISSING_MARK = "chave de API nao encontrada"

FALLBACK = (
    "Erro inesperado",
    "Algo deu errado. Tente novamente; se o problema persistir, reporte com os logs do terminal.",
)


MAX_LOG_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB
MAX_LOG_BACKUPS = 3


def _rotate_log_if_needed(
    path: Path,
    max_bytes: int = MAX_LOG_SIZE_BYTES,
    max_backups: int = MAX_LOG_BACKUPS,
) -> None:
    """Rotaciona o arquivo de log se o tamanho exceder max_bytes mantendo ate max_backups."""
    try:
        if not path.is_file() or path.stat().st_size < max_bytes:
            return

        for i in range(max_backups, 0, -1):
            src = path.parent / f"{path.name}.{i - 1}" if i > 1 else path
            dst = path.parent / f"{path.name}.{i}"
            if src.is_file():
                if dst.is_file():
                    dst.unlink(missing_ok=True)
                src.replace(dst)
    except OSError:
        pass


def dump_error_details(
    error: Exception,
    secrets: Iterable[str] = (),
    log_path: Path | None = None,
    max_bytes: int = MAX_LOG_SIZE_BYTES,
    max_backups: int = MAX_LOG_BACKUPS,
) -> Path | None:
    """Grava o traceback redigido em ``erros.log`` para diagnostico offline.

    Devolve o caminho do log (para a interface apontar) ou ``None`` se o
    arquivo nao puder ser gravado. Nenhuma chave conhecida sobrevive.
    """
    try:
        path = log_path if log_path is not None else Path(user_log_dir(APP_DIR)) / "erros.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        _rotate_log_if_needed(path, max_bytes=max_bytes, max_backups=max_backups)
        stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        detalhe = redact("".join(traceback.format_exception(error)), secrets)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"--- {stamp} ---\n{detalhe}\n")
        return path
    except OSError:
        return None


def friendly_error(exc: Exception) -> tuple[str, str]:
    """Converte uma excecao em ``(titulo, orientacao)`` para a interface.

    A orientacao explica o problema e o proximo passo, em portugues e
    sem expor segredos.
    """
    if isinstance(exc, DrmError):
        return (
            "Livro protegido por DRM",
            "Este livro contem conteudo criptografado e nao pode ser "
            "traduzido. Adquira uma copia sem DRM.",
        )
    if isinstance(exc, NotEpubError):
        return (
            "Arquivo invalido",
            "O arquivo nao parece ser um EPUB. Selecione um arquivo terminado em .epub.",
        )
    if isinstance(exc, MalformedEpubError):
        return (
            "EPUB com problemas",
            f"{exc} O livro pode estar danificado; tente outro arquivo "
            "ou reexporte o EPUB a partir do leitor de origem.",
        )
    if isinstance(exc, AuthenticationError):
        return (
            "Chave de API invalida",
            "O provedor rejeitou a chave (HTTP 401/403). Verifique a chave "
            "na tela de configuracao ou gere uma nova no painel do provedor.",
        )
    if isinstance(exc, DefinitiveProviderError):
        if KEY_MISSING_MARK in str(exc):
            return (
                "Chave de API ausente",
                "Nenhuma chave foi encontrada. Configure a chave do provedor "
                "na tela de configuracao (ou via variavel de ambiente).",
            )
        return ("Falha no provedor", str(exc))
    if isinstance(exc, TransientProviderError):
        if "HTTP 429" in str(exc):
            return (
                "Limite de requisicoes do provedor",
                f"{exc} O provedor limitou as requisicoes simultaneas. Reduza o "
                "paralelismo na tela de configuracao e retome; o progresso "
                "concluido fica salvo.",
            )
        if "resposta" in str(exc):
            return (
                "Resposta invalida do provedor",
                f"{exc} A API respondeu sem o formato esperado (resposta truncada "
                "ou malformada). Isso costuma ser um problema temporario do "
                "provedor; tente novamente; o progresso concluido fica salvo "
                "para retomada.",
            )
        return (
            "Falha de rede",
            f"{exc} Verifique sua conexao e tente novamente; o progresso "
            "concluido fica salvo para retomada.",
        )
    if isinstance(exc, TranslationQualityError):
        return (
            "Lote reprovado no controle de qualidade",
            f"{exc} O modelo devolveu um lote corrompido (placeholders ou "
            "formatacao) mesmo apos novas tentativas. Retome a traducao para "
            "reenviar o lote; se persistir, o problema esta em um bloco "
            "especifico do livro.",
        )
    if isinstance(exc, SpendingLimitExceeded):
        return (
            "Teto de gasto atingido",
            f"{exc} Ajuste o teto no config (cost.spending_limit_usd) e retome.",
        )
    if isinstance(exc, ConfigError):
        return (
            "Configuracao invalida",
            f"{exc} Corrija o arquivo de configuracao e tente novamente.",
        )
    if isinstance(exc, (EpubError, ProviderError)):
        return ("Falha ao processar o livro", str(exc))
    return FALLBACK
