"""Testes da redacao de segredos (tarefa 8.6).

Nenhuma saida — log, erro ou relatorio — pode conter uma chave;
o mascaramento troca qualquer ocorrencia por ``***``.
"""

from __future__ import annotations

import io
import logging

from tradutor.infra.redact import MASK, RedactingFilter, redact


def test_redact_substitui_chave():
    assert redact("chave: sk-123", ["sk-123"]) == f"chave: {MASK}"


def test_redact_substitui_varias_ocorrencias():
    text = "primeira sk-1 e de novo sk-1"
    assert redact(text, ["sk-1"]) == f"primeira {MASK} e de novo {MASK}"


def test_redact_varias_chaves():
    assert redact("a sk-1 b sk-2 c", ["sk-1", "sk-2"]) == f"a {MASK} b {MASK} c"


def test_redact_sem_chave_mantem_texto():
    assert redact("texto limpo", ["sk-1"]) == "texto limpo"


def test_redact_ignora_segredo_vazio():
    assert redact("texto", [""]) == "texto"


def test_filter_redige_mensagem_e_args():
    logger = logging.getLogger("tradutor.teste.redact")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.addFilter(RedactingFilter(["sk-super-secreta"]))
    logger.addHandler(handler)

    logger.error("falhou com chave sk-super-secreta")
    logger.warning("usa %s aqui", "sk-super-secreta")
    logger.info("chave=%(chave)s", {"chave": "sk-super-secreta"})
    logger.removeHandler(handler)

    output = buffer.getvalue()
    assert "sk-super-secreta" not in output
    assert output.count(MASK) == 3


def test_filter_mantem_registros_sem_chave():
    logger = logging.getLogger("tradutor.teste.redact.limpo")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.addFilter(RedactingFilter(["sk-x"]))
    logger.addHandler(handler)

    logger.info("sem segredos aqui")
    logger.removeHandler(handler)

    assert buffer.getvalue() == "sem segredos aqui\n"
