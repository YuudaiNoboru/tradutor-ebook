"""Excecoes da camada de provedores (adapters de LLM).

Mensagens sempre em portugues e sem chaves/segredos (a redacao e
aplicada em toda saida pela camada ``infra``, secao 8).
"""


class ProviderError(Exception):
    """Erro generico de provedor; a interface mostra mensagens acionaveis."""


class TransientProviderError(ProviderError):
    """Falha transitoria (429, 5xx, timeout, rede, resposta quebrada).

    Repetir a chamada pode ter sucesso; o retry com backoff cuida disso
    e, esgotadas as tentativas, o bloco fica pendente de retomada.
    """

    def __init__(self, message: str, *, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class DefinitiveProviderError(ProviderError):
    """Falha definitiva (4xx exceto 429) — repetir nao resolve."""


class AuthenticationError(DefinitiveProviderError):
    """Credencial invalida ou sem permissao (HTTP 401/403)."""
