"""Eventos de domínio para acompanhamento e reatividade do ciclo de tradução."""

from dataclasses import dataclass

from tradutor.domain.translate import Usage


class TranslationEvent:
    """Classe base de evento de tradução."""

    pass


@dataclass(frozen=True, slots=True)
class TranslationStartedEvent(TranslationEvent):
    """Disparado quando a tradução do livro inicia, indicando a volumetria total."""

    total_blocks: int


@dataclass(frozen=True, slots=True)
class TranslationProgressEvent(TranslationEvent):
    """Disparado periodicamente para atualizar o progresso dos blocos traduzidos."""

    done: int
    total: int


@dataclass(frozen=True, slots=True)
class TranslationLogEvent(TranslationEvent):
    """Disparado para registrar logs de texto/mensagens durante o pipeline."""

    message: str


@dataclass(frozen=True, slots=True)
class TranslationCompletedEvent(TranslationEvent):
    """Disparado ao concluir com sucesso a tradução e a escrita do e-book."""

    translations: dict[str, dict[int, str]]
    usage: Usage
