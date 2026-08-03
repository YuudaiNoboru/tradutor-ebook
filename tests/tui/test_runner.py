"""Testes do pipeline da TUI (tarefas 9.3, 9.4 e 9.5).

Cobrem o runner (passadas, traducao, escrita, cancelamento, reset,
teto de gasto), o plano pre-voo da tela de estimativa e a deteccao de
cache compativel para a oferta de retomada. O livro miniatura dos
builders dourados tem 6 blocos traduziveis (4 no cap. 1, 2 no cap. 2).
"""

from __future__ import annotations

import contextlib
import json
import threading
import time
import zipfile
from pathlib import Path

import pytest

from tests.tui.helpers import DictSecretStore, FakeProvider, write_book
from tradutor.domain import PassadaTask, Usage
from tradutor.epub.appendix import APPENDIX_HREF
from tradutor.epub.container import open_ebook
from tradutor.infra.config import AppConfig, ProviderConfig
from tradutor.providers import DEFAULT_KEY_NAME
from tradutor.translate.estado import STATE_FILENAME, WorkState, save_estado, state_compat_key
from tradutor.translate.glossary_store import glossary_version, save_glossary
from tradutor.translate.orchestrator import SpendingLimitExceeded, TranslationCancelled
from tradutor.tui.runner import (
    RunnerHooks,
    book_hash,
    cache_status,
    default_work_dir_for,
    model_for,
    plan_book,
    run_translation,
    term_policy,
)

MAX_TOKENS = 4000
TRANSLATABLE_BLOCKS = 6


def config(*, parallelism: int = 4) -> AppConfig:
    cfg = AppConfig()
    cfg.execution.parallelism = parallelism
    return cfg


def run(
    tmp_path: Path,
    *,
    provider: FakeProvider | None = None,
    cfg: AppConfig | None = None,
    reset: bool = False,
    hooks: RunnerHooks | None = None,
):
    path = write_book(tmp_path)
    ebook = open_ebook(path)
    return run_translation(
        ebook=ebook,
        provider=provider or FakeProvider(),
        token_counter=len,
        config=cfg or config(),
        work_dir=tmp_path / "trabalho",
        book_hash=book_hash(path),
        max_tokens=MAX_TOKENS,
        reset=reset,
        hooks=hooks,
    )


def test_full_pipeline_writes_translated_epub(tmp_path):
    provider = FakeProvider()
    result = run(tmp_path, provider=provider)

    assert result.out_path == tmp_path / "livro-pt-BR.epub"
    assert result.out_path.exists()
    assert result.usage == Usage(1, 1)

    with zipfile.ZipFile(result.out_path) as zf:
        names = zf.namelist()
        assert f"OEBPS/{APPENDIX_HREF}" in names
        ch1 = zf.read("OEBPS/text/ch1.xhtml").decode("utf-8")
        assert "TR: Hello" in ch1
        assert "var x = 1;" in ch1
        assert "TR: Chapter One" in ch1
        nav = zf.read("OEBPS/nav.xhtml").decode("utf-8")
        assert "TR: Chapter One" in nav
        opf = zf.read("OEBPS/content.opf").decode("utf-8")
        assert "pt-BR" in opf
        assert "TR: The English Book" in opf

    work = tmp_path / "trabalho"
    assert (work / STATE_FILENAME).exists()
    assert (work / "glossario.json").exists()


def test_glossary_pass_skipped_when_saved(tmp_path):
    work = tmp_path / "trabalho"
    work.mkdir()
    save_glossary(work / "glossario.json", [("cache", "cache")])
    provider = FakeProvider()
    run(tmp_path, provider=provider)

    assert provider.contexts[0].task is PassadaTask.PRIMING
    assert len(provider.calls) == 4  # priming, lote, sumario, titulo


def test_glossary_pass_failure_continues(tmp_path):
    from tradutor.providers.errors import ProviderError

    provider = FakeProvider(fail_on=1, error=ProviderError("falha no glossario"))
    result = run(tmp_path, provider=provider)

    assert result.out_path.exists()
    assert not (tmp_path / "trabalho" / "glossario.json").exists()


def test_priming_failure_continues(tmp_path):
    from tradutor.providers.errors import ProviderError

    provider = FakeProvider(fail_on=2, error=ProviderError("falha no priming"))
    result = run(tmp_path, provider=provider)

    assert result.out_path.exists()
    assert result.usage.total_tokens > 0


def test_toc_failure_keeps_original_labels(tmp_path):
    from tradutor.providers.errors import ProviderError

    provider = FakeProvider(
        fail_on=4,  # quarta chamada: rotulos do sumario
        error=ProviderError("falha no sumario"),
    )
    result = run(tmp_path, provider=provider)

    with zipfile.ZipFile(result.out_path) as zf:
        nav = zf.read("OEBPS/nav.xhtml").decode("utf-8")
        assert "Chapter One" in nav
        assert "TR: Chapter One" not in nav


def test_title_failure_keeps_original_title(tmp_path):
    from tradutor.providers.errors import ProviderError

    provider = FakeProvider(
        fail_on=5,  # quinta chamada: titulo
        error=ProviderError("falha no titulo"),
    )
    result = run(tmp_path, provider=provider)

    with zipfile.ZipFile(result.out_path) as zf:
        opf = zf.read("OEBPS/content.opf").decode("utf-8")
        assert "The English Book" in opf
        assert "TR: The English Book" not in opf


def _run_safe(tmp_path: Path, provider: FakeProvider, hooks: RunnerHooks) -> None:
    """Roda o pipeline ignorando o cancelamento (apenas para threads)."""
    with contextlib.suppress(TranslationCancelled):
        run(tmp_path, provider=provider, hooks=hooks)


def test_cancel_preserves_progress(tmp_path):
    gate = threading.Event()
    provider = FakeProvider(gate=gate, gate_from=3)
    cancel_flag = {"value": False}
    hooks = RunnerHooks(cancel=lambda: cancel_flag["value"])

    thread = threading.Thread(
        target=lambda: _run_safe(tmp_path, provider, hooks),
        daemon=True,
    )
    thread.start()
    deadline = time.monotonic() + 10
    while len(provider.calls) < 3 and time.monotonic() < deadline:
        time.sleep(0.01)
    assert len(provider.calls) >= 3
    cancel_flag["value"] = True
    gate.set()
    thread.join(timeout=10)
    assert not thread.is_alive()

    estado = json.loads((tmp_path / "trabalho" / STATE_FILENAME).read_text(encoding="utf-8"))
    assert estado["translations"]


def test_second_run_without_reset_skips_translation(tmp_path):
    run(tmp_path, provider=FakeProvider())

    provider2 = FakeProvider()
    result = run(tmp_path, provider=provider2)

    assert len(provider2.calls) == 3  # priming, sumario, titulo
    assert result.out_path.exists()


def test_reset_retranslates_everything(tmp_path):
    run(tmp_path, provider=FakeProvider())

    provider2 = FakeProvider()
    run(tmp_path, provider=provider2, reset=True)

    assert len(provider2.calls) == 4  # priming, lote, sumario, titulo
    assert any(len(call) == TRANSLATABLE_BLOCKS for call in provider2.calls)


def test_spending_limit_aborts_with_cache(tmp_path):
    cfg = config()
    cfg.cost.spending_limit_usd = 0.0000001
    provider = FakeProvider()

    with pytest.raises(SpendingLimitExceeded):
        run(tmp_path, provider=provider, cfg=cfg)

    assert (tmp_path / "trabalho" / STATE_FILENAME).exists()


def test_translation_cancelled_raised_when_flag_set(tmp_path):
    gate = threading.Event()
    provider = FakeProvider(gate=gate, gate_from=3)
    cancel_flag = {"value": False}
    hooks = RunnerHooks(cancel=lambda: cancel_flag["value"])

    thread = threading.Thread(
        target=lambda: _run_safe(tmp_path, provider, hooks),
        daemon=True,
    )
    thread.start()
    deadline = time.monotonic() + 10
    while len(provider.calls) < 3 and time.monotonic() < deadline:
        time.sleep(0.01)
    cancel_flag["value"] = True
    gate.set()
    thread.join(timeout=10)

    assert not thread.is_alive()


def test_plan_book_summary_and_estimate(tmp_path):
    path = write_book(tmp_path)
    ebook = open_ebook(path)
    plan = plan_book(
        ebook,
        config=config(),
        token_counter=len,
        max_tokens=MAX_TOKENS,
        latency_seconds=10,
    )

    assert plan.title == "The English Book"
    assert plan.language == "en"
    assert plan.chapter_count == 2
    assert plan.translatable_blocks == TRANSLATABLE_BLOCKS
    assert plan.input_tokens > 0
    assert plan.batch_count == 1
    assert plan.estimate is not None
    assert plan.estimate.output_tokens > 0
    assert plan.estimate.batch_count == 1
    assert plan.prices is not None


def test_plan_book_without_prices_has_no_estimate(tmp_path):
    path = write_book(tmp_path)
    ebook = open_ebook(path)
    cfg = config()
    cfg.provider = "provedor-sem-preco"

    plan = plan_book(ebook, config=cfg, token_counter=len)

    assert plan.estimate is None
    assert plan.prices is None


def test_plan_book_parallelism_affects_time(tmp_path):
    path = write_book(tmp_path)
    ebook = open_ebook(path)

    plan1 = plan_book(ebook, config=config(), token_counter=len, parallelism=1)
    plan4 = plan_book(ebook, config=config(), token_counter=len, parallelism=4)

    assert plan4.estimate.estimated_seconds == pytest.approx(plan1.estimate.estimated_seconds / 4)


def test_cache_status_detects_resumable_state(tmp_path):
    path = write_book(tmp_path)
    work = tmp_path / "trabalho"
    work.mkdir()
    key = state_compat_key(
        book_hash=book_hash(path),
        source_language="auto",
        target_language="pt-BR",
        model=model_for(config()),
        policy=term_policy(config()),
        glossary_version=glossary_version([]),
    )
    save_estado(
        work / STATE_FILENAME,
        WorkState(key=key, translations={"cap.xhtml": {0: "oi"}}, usage=Usage(1, 1)),
    )

    status = cache_status(work, book_hash=book_hash(path), config=config(), glossary=[])

    assert status.compatible is True
    assert status.saved_blocks == 1


def test_cache_status_incompatible_when_target_changes(tmp_path):
    path = write_book(tmp_path)
    work = tmp_path / "trabalho"
    work.mkdir()
    key = state_compat_key(
        book_hash=book_hash(path),
        source_language="auto",
        target_language="pt-BR",
        model=model_for(config()),
        policy=term_policy(config()),
        glossary_version=glossary_version([]),
    )
    save_estado(work / STATE_FILENAME, WorkState(key=key))

    cfg = config()
    cfg.translation.target = "es"
    status = cache_status(work, book_hash=book_hash(path), config=cfg, glossary=[])

    assert status.compatible is False
    assert status.saved_blocks == 0


def test_cache_status_empty_work_dir(tmp_path):
    status = cache_status(tmp_path / "nao-existe", book_hash="x", config=config(), glossary=[])

    assert status.compatible is False
    assert status.saved_blocks == 0


def test_model_for_default_and_configured():
    assert model_for(config()) == "deepseek-chat"

    cfg = config()
    cfg.provider = "openrouter"
    cfg.providers["openrouter"] = ProviderConfig(
        base_url="https://openrouter.ai/api/v1", model="deepseek/deepseek-chat"
    )
    assert model_for(cfg) == "deepseek/deepseek-chat"


def test_term_policy_fallback():
    cfg = config()
    cfg.translation.policy = "hibrido"
    assert term_policy(cfg).value == "hibrido"

    cfg.translation.policy = "manter"
    assert term_policy(cfg).value == "manter"

    cfg.translation.policy = "valor-invalido"
    assert term_policy(cfg).value == "hibrido"


def test_book_hash_deterministic_and_distinct(tmp_path):
    from tests.epub.builders import build_epub2

    path = write_book(tmp_path)
    assert book_hash(path) == book_hash(path)
    other = write_book(tmp_path, name="outro.epub", data=build_epub2())
    assert book_hash(path) != book_hash(other)


def test_reset_without_existing_state_is_noop(tmp_path):
    provider = FakeProvider()
    result = run(tmp_path, provider=provider, reset=True)

    assert result.out_path.exists()


def test_book_without_toc_labels(tmp_path):
    from tests.epub.builders import build_epub2_without_toc

    path = write_book(tmp_path, data=build_epub2_without_toc())
    ebook = open_ebook(path)
    provider = FakeProvider()

    result = run_translation(
        ebook=ebook,
        provider=provider,
        token_counter=len,
        config=config(),
        work_dir=tmp_path / "trabalho",
        book_hash=book_hash(path),
        max_tokens=MAX_TOKENS,
    )

    assert result.out_path.exists()
    assert len(provider.calls) == 4  # glossario, priming, lote, titulo (sem sumario)


def test_toc_incomplete_response_keeps_original(tmp_path):
    provider = FakeProvider(short_on=4)
    result = run(tmp_path, provider=provider)

    with zipfile.ZipFile(result.out_path) as zf:
        nav = zf.read("OEBPS/nav.xhtml").decode("utf-8")
        assert "Chapter One" in nav
        assert "TR: Chapter One" not in nav


def test_book_without_title_skips_title_call(tmp_path):
    from tests.epub.builders import build_opf_without_title_language

    path = write_book(tmp_path, data=build_opf_without_title_language())
    ebook = open_ebook(path)
    provider = FakeProvider()

    result = run_translation(
        ebook=ebook,
        provider=provider,
        token_counter=len,
        config=config(),
        work_dir=tmp_path / "trabalho",
        book_hash=book_hash(path),
        max_tokens=MAX_TOKENS,
    )

    assert result.out_path.exists()
    assert len(provider.calls) == 4  # glossario, priming, lote, sumario (sem titulo)


def test_empty_title_response_keeps_original(tmp_path):
    provider = FakeProvider(empty_on=5)
    result = run(tmp_path, provider=provider)

    with zipfile.ZipFile(result.out_path) as zf:
        opf = zf.read("OEBPS/content.opf").decode("utf-8")
        assert "The English Book" in opf


def test_default_work_dir_slugifies_stem():
    work = default_work_dir_for(Path("meu livro (1).epub"))

    assert work.name == "meu-livro--1-"


def test_build_provider_without_factory_builds_real_provider(tmp_path):
    from tradutor.providers import OpenAICompatProvider

    chain = DictSecretStore({DEFAULT_KEY_NAME: "sk-123"})
    from tradutor.tui.app import AppEnv, TradutorApp

    env = AppEnv(
        config=AppConfig(),
        config_path=tmp_path / "config.toml",
        chain=chain,
        key_backend=chain,
        token_counter=len,
    )
    app = TradutorApp(env=env)

    provider = app.build_provider()
    assert isinstance(provider, OpenAICompatProvider)
    assert provider.model == "deepseek-chat"
    assert provider.base_url == "https://api.deepseek.com"

    with_override = app.build_provider(key_override="chave-nova")
    assert isinstance(with_override, OpenAICompatProvider)


def test_build_provider_uses_configured_provider(tmp_path):
    from tradutor.tui.app import AppEnv, TradutorApp

    env = AppEnv(
        config=AppConfig(),
        config_path=tmp_path / "config.toml",
        chain=DictSecretStore({DEFAULT_KEY_NAME: "sk-123"}),
        key_backend=DictSecretStore({}),
        token_counter=len,
    )
    env.config.provider = "openrouter"
    env.config.providers["openrouter"] = ProviderConfig(
        base_url="https://openrouter.ai/api/v1", model="deepseek/deepseek-chat"
    )
    app = TradutorApp(env=env)

    provider = app.build_provider()

    assert provider.base_url == "https://openrouter.ai/api/v1"
    assert provider.model == "deepseek/deepseek-chat"
