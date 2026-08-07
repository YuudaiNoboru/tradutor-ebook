"""Agrupamento de blocos em lotes respeitando o limite de contexto (tarefa 6.3).

Lotes preenchidos em ordem de documento: o lote fecha quando adicionar o
proximo bloco estouraria ``max_tokens``. Blocos protegidos ou em branco
nunca sao enviados ao modelo. Um bloco maior que o limite vai sozinho no
proprio lote (a fidelidade de placeholders e verificada pela camada de
orquestracao, nunca por confianca na LLM).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from tradutor.domain import Block


def make_batches(
    blocks: Sequence[Block],
    *,
    token_count: Callable[[str], int],
    max_tokens: int,
) -> list[list[Block]]:
    """Divide blocos traduziveis em lotes com no maximo ``max_tokens``."""
    if max_tokens <= 0:
        raise ValueError("max_tokens deve ser positivo")
    batches: list[list[Block]] = []
    current: list[Block] = []
    current_tokens = 0
    for block in blocks:
        if block.protected or not block.text.strip():
            continue
        tokens = token_count(block.text)
        if current and current_tokens + tokens > max_tokens:
            batches.append(current)
            current = []
            current_tokens = 0
        current.append(block)
        current_tokens += tokens
    if current:
        batches.append(current)
    return batches


def tiktoken_counter(encoding_name: str = "cl100k_base") -> Callable[[str], int]:
    """Contador de tokens via tiktoken (import tardio; cl100k_base aproxima a DeepSeek)."""
    import tiktoken

    encoding = tiktoken.get_encoding(encoding_name)
    return lambda text: len(encoding.encode(text))


def make_batches_by_limits(
    blocks: Sequence[Block],
    *,
    max_chars: int | None = None,
    max_items: int | None = None,
    size: Callable[[str], int] = len,
) -> list[list[Block]]:
    """Agrupa por caracteres/itens para providers sem contexto de tokens."""
    if max_chars is not None and max_chars <= 0:
        raise ValueError("max_chars deve ser positivo")
    if max_items is not None and max_items <= 0:
        raise ValueError("max_items deve ser positivo")
    groups: list[list[Block]] = []
    current: list[Block] = []
    current_chars = 0
    for block in blocks:
        if block.protected or not block.text.strip():
            continue
        chars = size(block.text)
        if max_chars is not None and chars > max_chars:
            raise ValueError(f"bloco {block.id} excede max_chars")
        if current and (
            (max_chars is not None and current_chars + chars > max_chars)
            or (max_items is not None and len(current) >= max_items)
        ):
            groups.append(current)
            current, current_chars = [], 0
        current.append(block)
        current_chars += chars
    if current:
        groups.append(current)
    return groups
