"""Porta ``SecretStore``: chaves de API acessiveis apenas por adapters.

O nucleo do dominio nunca recebe nem armazena chaves; adapters de
provedor obtem chaves somente por esta porta. Os backends concretos
(cofre do SO, arquivo cifrado, variavel de ambiente) sao implementados
na camada ``infra`` (tarefas da secao 8).
"""

from __future__ import annotations

from typing import Protocol


class SecretStore(Protocol):
    """Porta de acesso a segredos consumida pelos adapters de provedor."""

    def get(self, name: str) -> str | None: ...
