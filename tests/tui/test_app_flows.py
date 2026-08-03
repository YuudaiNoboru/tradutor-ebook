"""Testes de fluxo com ``textual.pilot`` (tarefa 9.7).

Cobrem os fluxos principais: primeira execucao guiada, configuracao com
teste de conexao, estimativa com confirmacao e ajuste de paralelismo,
progresso com cancelamento ordenado, relatorio final, oferta de
retomada com cache e mensagens de erro acionaveis.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from pathlib import Path

from tests.epub.builders import build_drm_book
from tests.tui.helpers import DictSecretStore, FakeProvider, write_book
from tradutor.domain import Usage
from tradutor.infra.config import AppConfig
from tradutor.providers import DEFAULT_KEY_NAME, ConnectionResult
from tradutor.translate.estado import STATE_FILENAME, WorkState, save_estado, state_compat_key
from tradutor.translate.glossary_store import glossary_version
from tradutor.tui.app import AppEnv, TradutorApp
from tradutor.tui.runner import book_hash, model_for, term_policy
from tradutor.tui.screens.book import BookScreen
from tradutor.tui.screens.config import ConfigScreen
from tradutor.tui.screens.error import ErrorScreen
from tradutor.tui.screens.estimate import EstimateScreen
from tradutor.tui.screens.progress import ProgressScreen
from tradutor.tui.screens.report import ReportScreen
from tradutor.tui.screens.welcome import WelcomeScreen


def make_env(tmp_path: Path, *, key: str | None = None, provider=None, **overrides) -> AppEnv:
    chain = DictSecretStore({DEFAULT_KEY_NAME: key} if key else {})
    env = AppEnv(
        config=AppConfig(),
        config_path=tmp_path / "config.toml",
        chain=chain,
        key_backend=chain,
        provider_factory=lambda: provider if provider is not None else FakeProvider(),
        token_counter=len,
        latency_seconds=1.0,
        work_dir_for=lambda _path: tmp_path / "trabalho",
    )
    for name, value in overrides.items():
        setattr(env, name, value)
    return env


async def wait_for(pilot, condition: Callable[[], bool], timeout: float = 15.0) -> None:
    """Aguarda a condicao, processando mensagens da interface."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            await pilot.pause()
            return
        await pilot.pause(0.02)
    raise AssertionError("tempo esgotado aguardando a interface")


def open_book(app, book: Path) -> None:
    app.screen.query_one("#book-path").value = str(book)


def test_first_run_without_key_shows_welcome(tmp_path):
    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            assert isinstance(app.screen, WelcomeScreen)

    asyncio.run(run(TradutorApp(env=make_env(tmp_path))))


def test_with_key_starts_at_book_selection(tmp_path):
    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            assert isinstance(app.screen, BookScreen)

    asyncio.run(run(TradutorApp(env=make_env(tmp_path, key="sk-123"))))


def test_welcome_guides_key_configuration(tmp_path):
    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            assert isinstance(app.screen, WelcomeScreen)

            await pilot.click("#configure-key")
            await pilot.pause()
            assert isinstance(app.screen, ConfigScreen)

            key_input = app.screen.query_one("#key")
            key_input.value = "sk-9876543210"
            await pilot.click("#save")
            await pilot.pause()

            assert app.has_key()
            assert isinstance(app.screen, WelcomeScreen)

    asyncio.run(run(TradutorApp(env=make_env(tmp_path))))


def test_welcome_skip_goes_to_book_selection(tmp_path):
    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            await pilot.click("#skip-key")
            await pilot.pause()
            assert isinstance(app.screen, BookScreen)

    asyncio.run(run(TradutorApp(env=make_env(tmp_path))))


def test_config_test_connection_ok(tmp_path):
    provider = FakeProvider(connection=ConnectionResult(True, "conexao OK", ("deepseek-chat",)))

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            assert isinstance(app.screen, BookScreen)
            await pilot.click("#config")
            await pilot.pause()
            await pilot.click("#test")
            await wait_for(
                pilot, lambda: "OK" in str(app.screen.query_one("#test-result").render())
            )
            result = str(app.screen.query_one("#test-result").render())
            assert "conexao OK" in result
            assert "deepseek-chat" in result

    asyncio.run(run(TradutorApp(env=make_env(tmp_path, key="sk-123", provider=provider))))


def test_config_test_connection_failure(tmp_path):
    provider = FakeProvider(connection=ConnectionResult(False, "falha de autenticacao"))

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            await pilot.click("#skip-key")
            await pilot.pause()
            await pilot.click("#config")
            await pilot.pause()
            await pilot.click("#test")
            await wait_for(
                pilot, lambda: "FALHA" in str(app.screen.query_one("#test-result").render())
            )
            assert "autenticacao" in str(app.screen.query_one("#test-result").render())

    asyncio.run(run(TradutorApp(env=make_env(tmp_path, provider=provider))))


def test_config_save_persists_settings(tmp_path):
    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            await pilot.click("#config")
            await pilot.pause()
            app.screen.query_one("#parallelism").value = "2"
            await pilot.click("#save")
            await pilot.pause()

            config_path = tmp_path / "config.toml"
            assert config_path.exists()
            assert "parallelism = 2" in config_path.read_text(encoding="utf-8")
            assert app.env.config.execution.parallelism == 2

    asyncio.run(run(TradutorApp(env=make_env(tmp_path, key="sk-123"))))


def test_full_flow_reaches_report_with_output(tmp_path):
    book = write_book(tmp_path)
    provider = FakeProvider()

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            assert isinstance(app.screen, BookScreen)
            open_book(app, book)
            await pilot.click("#open")
            await wait_for(pilot, lambda: isinstance(app.screen, EstimateScreen))

            assert "The English Book" in str(app.screen.query_one("#book-title").render())
            assert "Custo estimado" in str(app.screen.query_one("#estimate-values").render())

            await pilot.click("#go")
            await wait_for(pilot, lambda: isinstance(app.screen, ReportScreen))

            report = app.screen
            output = str(report.query_one("#output-path").render())
            assert str(book.with_name("livro-pt-BR.epub")) in output
            assert (tmp_path / "livro-pt-BR.epub").exists()
            assert "Previsto" in str(report.query_one("#cost-report").render())

            # glossario, priming, lote, sumario, titulo
            assert len(provider.calls) == 5

    asyncio.run(run(TradutorApp(env=make_env(tmp_path, key="sk-123", provider=provider))))


def test_estimate_shows_warning_and_recommendation(tmp_path):
    book = write_book(tmp_path)

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            open_book(app, book)
            await pilot.click("#open")
            await wait_for(pilot, lambda: isinstance(app.screen, EstimateScreen))

            warning = str(app.screen.query_one("#estimate-warning").render())
            assert "AVISO" in warning
            assert "teto de gasto" in warning

    asyncio.run(run(TradutorApp(env=make_env(tmp_path, key="sk-123"))))


def test_estimate_without_prices_explains_config(tmp_path):
    book = write_book(tmp_path)
    env = make_env(tmp_path, key="sk-123")
    env.config.provider = "provedor-sem-preco"

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            open_book(app, book)
            await pilot.click("#open")
            await wait_for(pilot, lambda: isinstance(app.screen, EstimateScreen))

            assert "Precos nao configurados" in str(
                app.screen.query_one("#estimate-values").render()
            )

    asyncio.run(run(TradutorApp(env=env)))


def test_parallelism_invalid_notifies_and_stays(tmp_path):
    book = write_book(tmp_path)

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            open_book(app, book)
            await pilot.click("#open")
            await wait_for(pilot, lambda: isinstance(app.screen, EstimateScreen))

            app.screen.query_one("#parallelism").value = "abc"
            await pilot.click("#go")
            await pilot.pause()

            assert isinstance(app.screen, EstimateScreen)
            assert app.env.config.execution.parallelism == 4

    asyncio.run(run(TradutorApp(env=make_env(tmp_path, key="sk-123"))))


def test_parallelism_adjusted_on_estimate(tmp_path):
    book = write_book(tmp_path)

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            open_book(app, book)
            await pilot.click("#open")
            await wait_for(pilot, lambda: isinstance(app.screen, EstimateScreen))

            app.screen.query_one("#parallelism").value = "1"
            await pilot.click("#go")
            await wait_for(
                pilot,
                lambda: isinstance(app.screen, (ProgressScreen, ReportScreen)),
            )

            assert app.env.config.execution.parallelism == 1

    asyncio.run(run(TradutorApp(env=make_env(tmp_path, key="sk-123"))))


def test_cancel_returns_to_estimate_with_resume_offer(tmp_path):
    import threading

    book = write_book(tmp_path)
    gate = threading.Event()
    provider = FakeProvider(gate=gate, gate_from=3)

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            open_book(app, book)
            await pilot.click("#open")
            await wait_for(pilot, lambda: isinstance(app.screen, EstimateScreen))
            await pilot.click("#go")
            await wait_for(pilot, lambda: isinstance(app.screen, ProgressScreen))

            deadline = time.monotonic() + 15
            while len(provider.calls) < 3 and time.monotonic() < deadline:
                await pilot.pause(0.02)
            await pilot.click("#cancel")
            await pilot.press("ctrl+c")
            gate.set()
            await wait_for(pilot, lambda: isinstance(app.screen, EstimateScreen))
            await wait_for(
                pilot,
                lambda: "cancelada" in str(app.screen.query_one("#notice").render()),
            )

            assert app.screen.query_one("#cache-info") is not None
            assert (tmp_path / "trabalho" / STATE_FILENAME).exists()

    asyncio.run(run(TradutorApp(env=make_env(tmp_path, key="sk-123", provider=provider))))


def test_resume_offer_when_cache_exists(tmp_path):
    book = write_book(tmp_path)
    work = tmp_path / "trabalho"
    work.mkdir()
    config = AppConfig()
    key = state_compat_key(
        book_hash=book_hash(book),
        source_language=config.translation.source,
        target_language=config.translation.target,
        model=model_for(config),
        policy=term_policy(config),
        glossary_version=glossary_version([]),
    )
    save_estado(
        work / STATE_FILENAME,
        WorkState(key=key, translations={"cap.xhtml": {0: "ja traduzido"}}, usage=Usage(1, 1)),
    )

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            open_book(app, book)
            await pilot.click("#open")
            await wait_for(pilot, lambda: isinstance(app.screen, EstimateScreen))

            assert "1 bloco" in str(app.screen.query_one("#cache-info").render())
            assert str(app.screen.query_one("#go").label) == "Continuar traducao"
            assert app.screen.query_one("#restart") is not None

    asyncio.run(run(TradutorApp(env=make_env(tmp_path, key="sk-123"))))


def test_drm_book_shows_actionable_error(tmp_path):
    book = write_book(tmp_path, data=build_drm_book())

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            open_book(app, book)
            await pilot.click("#open")
            await wait_for(pilot, lambda: isinstance(app.screen, ErrorScreen))

            assert "DRM" in str(app.screen.query_one(".error-title").render())
            await pilot.click("#error-ok")
            await pilot.pause()
            assert isinstance(app.screen, BookScreen)

    asyncio.run(run(TradutorApp(env=make_env(tmp_path, key="sk-123"))))


def test_non_epub_file_shows_actionable_error(tmp_path):
    book = tmp_path / "nao-ebook.epub"
    book.write_bytes(b"isto nao e um epub")

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            open_book(app, book)
            await pilot.click("#open")
            await wait_for(pilot, lambda: isinstance(app.screen, ErrorScreen))

            assert "Arquivo invalido" in str(app.screen.query_one(".error-title").render())

    asyncio.run(run(TradutorApp(env=make_env(tmp_path, key="sk-123"))))


def test_report_again_resets_session(tmp_path):
    book = write_book(tmp_path)

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            open_book(app, book)
            await pilot.click("#open")
            await wait_for(pilot, lambda: isinstance(app.screen, EstimateScreen))
            await pilot.click("#go")
            await wait_for(pilot, lambda: isinstance(app.screen, ReportScreen))

            await pilot.click("#again")
            await pilot.pause()
            assert isinstance(app.screen, BookScreen)
            assert app.session.ebook is None

    asyncio.run(run(TradutorApp(env=make_env(tmp_path, key="sk-123"))))


def test_report_quit_exits_app(tmp_path):
    book = write_book(tmp_path)

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            open_book(app, book)
            await pilot.click("#open")
            await wait_for(pilot, lambda: isinstance(app.screen, EstimateScreen))
            await pilot.click("#go")
            await wait_for(pilot, lambda: isinstance(app.screen, ReportScreen))

            await pilot.click("#quit")
            await pilot.pause()
            assert app._exit is True

    asyncio.run(run(TradutorApp(env=make_env(tmp_path, key="sk-123"))))


def test_report_without_prices_shows_hint(tmp_path):
    book = write_book(tmp_path)
    env = make_env(tmp_path, key="sk-123")
    env.config.provider = "provedor-sem-preco"

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            open_book(app, book)
            await pilot.click("#open")
            await wait_for(pilot, lambda: isinstance(app.screen, EstimateScreen))
            await pilot.click("#go")
            await wait_for(pilot, lambda: isinstance(app.screen, ReportScreen))

            assert "Custo real indisponivel" in str(app.screen.query_one("#cost-report").render())

    asyncio.run(run(TradutorApp(env=env)))


def test_book_screen_empty_path_notifies(tmp_path):
    app = TradutorApp(env=make_env(tmp_path, key="sk-123"))

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            assert isinstance(app.screen, BookScreen)
            await pilot.click("#open")
            await pilot.pause()
            assert isinstance(app.screen, BookScreen)

    asyncio.run(run(app))


def test_book_screen_config_back_and_quit(tmp_path):
    app = TradutorApp(env=make_env(tmp_path, key="sk-123"))

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            await pilot.click("#config")
            await pilot.pause()
            assert isinstance(app.screen, ConfigScreen)

            await pilot.click("#back")
            await pilot.pause()
            assert isinstance(app.screen, BookScreen)

            await pilot.click("#quit")
            await pilot.pause()
            assert app._exit is True

    asyncio.run(run(app))


def test_config_save_invalid_parallelism_notifies(tmp_path):
    app = TradutorApp(env=make_env(tmp_path, key="sk-123"))

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            await pilot.click("#config")
            await pilot.pause()
            app.screen.query_one("#parallelism").value = "abc"
            await pilot.click("#save")
            await pilot.pause()

            assert isinstance(app.screen, ConfigScreen)
            assert not (tmp_path / "config.toml").exists()

    asyncio.run(run(app))


def test_connection_test_worker_error(tmp_path):
    from tradutor.providers.errors import ProviderError

    provider = FakeProvider(connection_error=ProviderError("sem rede"))
    app = TradutorApp(env=make_env(tmp_path, key="sk-123", provider=provider))

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            await pilot.click("#config")
            await pilot.pause()
            await pilot.click("#test")
            await wait_for(
                pilot,
                lambda: "FALHA ao testar" in str(app.screen.query_one("#test-result").render()),
            )
            assert "sem rede" in str(app.screen.query_one("#test-result").render())

    asyncio.run(run(app))


def test_spending_limit_shows_error_modal_and_returns(tmp_path):
    book = write_book(tmp_path)
    env = make_env(tmp_path, key="sk-123")
    env.config.cost.spending_limit_usd = 0.0000001

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            open_book(app, book)
            await pilot.click("#open")
            await wait_for(pilot, lambda: isinstance(app.screen, EstimateScreen))
            await pilot.click("#go")
            await wait_for(pilot, lambda: isinstance(app.screen, ErrorScreen))

            assert "Teto de gasto" in str(app.screen.query_one(".error-title").render())
            await pilot.click("#error-ok")
            await wait_for(pilot, lambda: isinstance(app.screen, EstimateScreen))

            assert "Traduzir agora" in str(app.screen.query_one("#go").label)
            assert (tmp_path / "trabalho" / "estado.json").exists()

    asyncio.run(run(TradutorApp(env=env)))


def test_estimate_back_returns_to_book(tmp_path):
    book = write_book(tmp_path)

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            open_book(app, book)
            await pilot.click("#open")
            await wait_for(pilot, lambda: isinstance(app.screen, EstimateScreen))

            await pilot.click("#back")
            await pilot.pause()
            assert isinstance(app.screen, BookScreen)
            assert app.session.ebook is None

    asyncio.run(run(TradutorApp(env=make_env(tmp_path, key="sk-123"))))


def test_parallelism_zero_and_text_notify(tmp_path):
    book = write_book(tmp_path)

    async def run(app):
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            open_book(app, book)
            await pilot.click("#open")
            await wait_for(pilot, lambda: isinstance(app.screen, EstimateScreen))

            app.screen.query_one("#parallelism").value = "0"
            await pilot.click("#go")
            await pilot.pause()
            assert isinstance(app.screen, EstimateScreen)
            assert app.env.config.execution.parallelism == 4

            app.screen.query_one("#parallelism").value = "abc"
            await pilot.click("#go")
            await pilot.pause()
            assert isinstance(app.screen, EstimateScreen)

    asyncio.run(run(TradutorApp(env=make_env(tmp_path, key="sk-123"))))
