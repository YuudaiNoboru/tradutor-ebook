"""Testes E2E assincronos da TUI com Textual Pilot.

Exercita os fluxos de ponta a ponta sem emulador de terminal real:
- Onboarding de primeira execucao (boas-vindas, configuracao de chave e fallback sem credenciais).
- Configuracao da aplicacao e teste assincrono de conexao do provedor.
- Execucao de traducao com cancelamento gracioso e retencao de estado para retomada.
- Ciclo completo de traducao ate a tela de relatorio final.
"""

from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path

from textual.widgets import Input

from tests.epub.builders import build_epub3_many_chapters
from tests.tui.helpers import FakeProvider, write_book
from tests.tui.test_app_flows import make_env, open_book, wait_for
from tradutor.providers import ConnectionResult
from tradutor.translate.estado import STATE_FILENAME
from tradutor.tui.app import TradutorApp
from tradutor.tui.screens.book import BookScreen
from tradutor.tui.screens.config import ConfigScreen
from tradutor.tui.screens.estimate import EstimateScreen
from tradutor.tui.screens.progress import ProgressScreen
from tradutor.tui.screens.report import ReportScreen
from tradutor.tui.screens.welcome import WelcomeScreen


def test_e2e_onboarding_configure_key(tmp_path: Path) -> None:
    """Valida o fluxo de onboarding guiado: tela de boas-vindas -> configuracao -> chave salva."""

    async def run(app: TradutorApp) -> None:
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            assert isinstance(app.screen, WelcomeScreen)

            # Clica no botao de configuracao de chave
            await pilot.click("#configure-key")
            await pilot.pause()
            assert isinstance(app.screen, ConfigScreen)

            # Preenche a chave e salva
            key_input = app.screen.query_one("#key", Input)
            key_input.value = "sk-e2e-test-key-12345"
            await pilot.click("#save")
            await pilot.pause()

            # Chave foi gravada no cofre e app retorna ao onboarding pronto
            assert app.has_key()
            assert isinstance(app.screen, WelcomeScreen)

    asyncio.run(run(TradutorApp(env=make_env(tmp_path))))


def test_e2e_onboarding_skip_to_machine_translation(tmp_path: Path) -> None:
    """Valida pular configuracao no onboarding, ativando traducao automatica."""

    async def run(app: TradutorApp) -> None:
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            assert isinstance(app.screen, WelcomeScreen)

            # Clica para pular configuracao de chave
            await pilot.click("#skip-key")
            await pilot.pause()

            # Direciona para selecao de livro configurado como machine_translation
            assert isinstance(app.screen, BookScreen)
            assert app.env.config.family == "machine_translation"

    asyncio.run(run(TradutorApp(env=make_env(tmp_path))))


def test_e2e_configuration_and_connection_test(tmp_path: Path) -> None:
    """Valida navegacao para tela de configuracao, teste assincrono de conexao e persistencia."""
    provider = FakeProvider(
        connection=ConnectionResult(
            True, "Conexao estabelecida com sucesso", ("modelo-alpha", "modelo-beta")
        )
    )

    async def run(app: TradutorApp) -> None:
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            assert isinstance(app.screen, BookScreen)

            # Abre tela de configuracao via atalho 'c'
            await pilot.press("c")
            await pilot.pause()
            assert isinstance(app.screen, ConfigScreen)

            # Dispara teste assincrono de conexao
            await pilot.click("#test")
            await wait_for(
                pilot,
                lambda: "sucesso" in str(app.screen.query_one("#test-result").render()),
            )
            result_text = str(app.screen.query_one("#test-result").render())
            assert "modelo-alpha" in result_text

            # Altera paralelismo e salva
            app.screen.query_one("#parallelism", Input).value = "4"
            await pilot.click("#save")
            await pilot.pause()

            # Retorna para a tela de selecao de livro e salva config.toml
            assert isinstance(app.screen, BookScreen)
            assert app.env.config.execution.parallelism == 4
            config_path = tmp_path / "config.toml"
            assert config_path.exists()
            assert "parallelism = 4" in config_path.read_text(encoding="utf-8")

    asyncio.run(run(TradutorApp(env=make_env(tmp_path, key="sk-test", provider=provider))))


def test_e2e_translation_graceful_cancellation(tmp_path: Path) -> None:
    """Valida inicio de traducao, cancelamento gracioso pelo usuario e retencao de estado."""
    book = write_book(tmp_path, data=build_epub3_many_chapters(6))
    gate = threading.Event()
    provider = FakeProvider(gate=gate, gate_from=3)

    async def run(app: TradutorApp) -> None:
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            assert isinstance(app.screen, BookScreen)

            # Abre o livro
            open_book(app, book)
            await pilot.click("#open")
            await wait_for(pilot, lambda: isinstance(app.screen, EstimateScreen))

            # Inicia traducao
            await pilot.click("#go")
            await wait_for(pilot, lambda: isinstance(app.screen, ProgressScreen))

            # Aguarda execucao de chamadas iniciais
            deadline = time.monotonic() + 15
            while len(provider.calls) < 3 and time.monotonic() < deadline:
                await pilot.pause(0.02)

            # Cancela a operacao
            await pilot.click("#cancel")
            gate.set()

            # Deve retornar a EstimateScreen com aviso de cancelamento
            await wait_for(pilot, lambda: isinstance(app.screen, EstimateScreen))
            await wait_for(
                pilot,
                lambda: "cancelada" in str(app.screen.query_one("#notice").render()),
            )

            # Estado parcial foi persistido para permitir retomada futura
            assert (tmp_path / "trabalho" / STATE_FILENAME).exists()

    asyncio.run(run(TradutorApp(env=make_env(tmp_path, key="sk-test", provider=provider))))


def test_e2e_full_translation_to_report(tmp_path: Path) -> None:
    """Valida ciclo completo: selecao de livro -> estimativa -> execucao -> tela de relatorio final."""
    book = write_book(tmp_path)
    provider = FakeProvider()

    async def run(app: TradutorApp) -> None:
        async with app.run_test(size=(110, 50)) as pilot:
            await pilot.pause()
            assert isinstance(app.screen, BookScreen)

            # Abre o livro e confere tela de estimativa
            open_book(app, book)
            await pilot.click("#open")
            await wait_for(pilot, lambda: isinstance(app.screen, EstimateScreen))
            assert "The English Book" in str(app.screen.query_one("#book-title").render())

            # Inicia traducao e aguarda conclusao com transicao para ReportScreen
            await pilot.click("#go")
            await wait_for(pilot, lambda: isinstance(app.screen, ReportScreen), timeout=20.0)

            # Relatorio exibe sumario e caminho do arquivo de saida
            output_text = str(app.screen.query_one("#output-path").render())
            assert "Arquivo gerado" in output_text
            assert "livro-pt-BR.epub" in output_text

            # Clica no botao 'Traduzir outro' para reiniciar sessao
            await pilot.click("#again")
            await wait_for(pilot, lambda: isinstance(app.screen, BookScreen))

    asyncio.run(run(TradutorApp(env=make_env(tmp_path, key="sk-test", provider=provider))))
