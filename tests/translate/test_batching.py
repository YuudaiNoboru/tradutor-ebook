"""Testes do agrupamento de blocos em lotes (tarefa 6.3)."""

import pytest

from tradutor.domain import Block
from tradutor.translate import make_batches, tiktoken_counter


def block(text: str, *, protected: bool = False) -> Block:
    return Block(id=0, kind="texto", text=text, protected=protected)


def batch_texts(batches: list[list[Block]]) -> list[list[str]]:
    return [[b.text for b in batch] for batch in batches]


def test_splits_batches_at_token_limit():
    blocks = [block("aaaa"), block("bb"), block("cccc")]
    batches = make_batches(blocks, token_count=len, max_tokens=3)
    assert batch_texts(batches) == [["aaaa"], ["bb"], ["cccc"]]


def test_fills_batch_until_limit():
    blocks = [block("aa"), block("bb"), block("cc"), block("dd")]
    batches = make_batches(blocks, token_count=len, max_tokens=4)
    assert batch_texts(batches) == [["aa", "bb"], ["cc", "dd"]]


def test_oversized_single_block_goes_alone():
    blocks = [block("x" * 100), block("aa")]
    batches = make_batches(blocks, token_count=len, max_tokens=10)
    assert batch_texts(batches) == [["x" * 100], ["aa"]]


def test_skips_protected_and_blank_blocks():
    blocks = [block("aa", protected=True), block("   "), block("bb")]
    batches = make_batches(blocks, token_count=len, max_tokens=10)
    assert batch_texts(batches) == [["bb"]]


def test_empty_input_returns_no_batches():
    assert make_batches([], token_count=len, max_tokens=10) == []


def test_preserves_order_across_batches():
    texts = [f"bloco-{i}" for i in range(8)]
    batches = make_batches([block(t) for t in texts], token_count=lambda t: 1, max_tokens=3)
    flattened = [b.text for batch in batches for b in batch]
    assert flattened == texts
    assert len(batches) == 3


def test_rejects_non_positive_max_tokens():
    with pytest.raises(ValueError, match="max_tokens"):
        make_batches([block("a")], token_count=len, max_tokens=0)


def test_tiktoken_counter_counts_tokens():
    counter = tiktoken_counter()
    assert counter("hello world") >= 1
    assert counter("a") < counter("hello world")
