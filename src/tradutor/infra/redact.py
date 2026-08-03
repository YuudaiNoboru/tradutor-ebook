"""Redacao de segredos em logs, erros e relatorios (decisao D8, tarefa 8.6).

``redact`` substitui qualquer ocorrencia de uma chave conhecida por um
mascaramento ``***``; ``RedactingFilter`` aplica isso automaticamente a
toda mensagem de logging. Nenhuma saida (log, erro, relatorio) deve
conter chave — ver testes de ``tests/infra/test_redact.py``.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

MASK = "***"


def redact(text: str, secrets: Iterable[str]) -> str:
    """Substitui toda ocorrencia de cada segredo nao vazio por ``***``."""
    for secret in secrets:
        if secret:
            text = text.replace(secret, MASK)
    return text


class RedactingFilter(logging.Filter):
    """Filtro de logging que redige chaves conhecidas de cada registro."""

    def __init__(self, secrets: Iterable[str]) -> None:
        super().__init__()
        self._secrets = tuple(secrets)

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.msg, self._secrets)
        if isinstance(record.args, tuple):
            record.args = tuple(
                redact(arg, self._secrets) if isinstance(arg, str) else arg for arg in record.args
            )
        elif isinstance(record.args, dict):
            record.args = {
                key: redact(value, self._secrets) if isinstance(value, str) else value
                for key, value in record.args.items()
            }
        return True
